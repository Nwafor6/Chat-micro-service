from fastapi import Request
from sqlalchemy import and_, or_, select

from app.core.exceptions import BadRequestException, NotFoundException
from app.models import Message, Room, RoomType, User, room_members_table
from app.schemas import MembersBase, RoomBase


class RoomController:
    """Controller for room-related operations."""

    @staticmethod
    async def create_room(request: Request, room_data: RoomBase) -> Room:
        """Create a new chat room.

        Args:
            request (Request): The FastAPI request object.
            room_data (RoomBase): The data for the new chat room.

        Returns:
            Room: The chat room object.
        """
        room_data = room_data.model_dump(exclude_unset=True)
        room = Room(**room_data, created_by_user_id=request.user.id)
        await room.save()
        if not room:
            raise BadRequestException("Failed to create room")

        # Add the creator as the first member of the room
        db = Room._get_db()
        await db.execute(
            room_members_table.insert().values(room_id=room.id, user_id=request.user.id)
        )
        await db.commit()

        return room

    @staticmethod
    async def get_room_by_id(room_id: str) -> Room:
        """Retrieve a chat room by its ID.

        Args:
            room_id (str): The unique identifier of the chat room.

        Returns:
            Room: The chat room object.
        """
        room = await Room.first(id=room_id)
        if not room:
            raise NotFoundException("Room not found")
        return room

    @staticmethod
    async def get_user_rooms(request: Request, classroom_id: str = None) -> list[Room]:
        """
        Retrieve all chat rooms created by the authenticated user or the user is a member of.
        Args:
            request (Request): The FastAPI request object.
            classroom_id (str, optional): Filter rooms by classroom ID.

        Returns:
            list[Room]: List of rooms the user created or is a member of with last messages.
        """
        user_id = request.user.id

        # Use existing query method and chain operations
        rooms_query = Room.query()

        # Add the complex WHERE clause for creator OR member
        rooms_query._query = rooms_query._query.where(
            or_(
                Room.created_by_user_id == user_id,  # Rooms created by user
                Room.id.in_(  # Rooms where user is a member
                    select(room_members_table.c.room_id).where(
                        room_members_table.c.user_id == user_id
                    )
                ),
            )
        )

        # Add classroom filter if provided
        if classroom_id:
            rooms_query = rooms_query.where(Room.bildup_classroom_id == classroom_id)

        rooms_query = rooms_query.order_by(Room.created_at.desc())

        # Use existing get method to execute and return results
        rooms = await rooms_query.get()

        # Fetch last message for each room (excluding soft-deleted messages)
        db = Room._get_db()
        try:
            for room in rooms:
                last_message = await Message.latest(room_id=room.id)

                # Attach last message to room object for serialization
                room.last_message = last_message

                # get the total number of members in the room
                member_count_query = select(room_members_table.c.user_id).where(
                    room_members_table.c.room_id == room.id
                )
                member_result = await db.execute(member_count_query)
                members = member_result.scalars().all()
                room.member_count = len(members)
                room.last_message_sender_info = {}

                # get the last message sender info
                if last_message:
                    sender = await User.first(id=last_message.user_id)
                    room.last_message_sender_info = sender.user_info

                # check the room members
                print(room.id, "this si the room id")
                members = await RoomController.get_room_members(room.id)
                # room.members_list = members
                if room.room_type == RoomType.PRIVATE:
                    for member in members:
                        if member.user_id != user_id:
                            room.room_custom_name = member.user_info
                            break
        finally:
            await db.close()

        return rooms

    # create private room
    @staticmethod
    async def get_or_create_private_room(request: Request, member_user_id: str) -> Room:
        """
        Get or create a private room between two users. First check if such room already exists.
        If it exists, return the existing room. Otherwise, create a new one.
        """
        current_user_id = request.user.id

        # Get database session
        db = Room._get_db()

        # Check if the other user exists, create if not
        member_user = await User.first(user_id=member_user_id)
        if not member_user:
            member_user, _ = await User.get_or_create(user_id=member_user_id)

        # Look for existing private room between these two users
        # A private room should have exactly these two users as members
        existing_room_query = (
            select(Room)
            .where(
                and_(
                    Room.room_type == "PRIVATE",  # Use enum value
                    Room._soft_delete_filter(),
                )
            )
            .where(
                # Room must contain both users as members
                Room.id.in_(
                    select(room_members_table.c.room_id).where(
                        room_members_table.c.user_id == current_user_id
                    )
                )
            )
            .where(
                Room.id.in_(
                    select(room_members_table.c.room_id).where(
                        room_members_table.c.user_id == member_user.id
                    )
                )
            )
        )

        result = await db.execute(existing_room_query)
        existing_room = result.scalars().first()

        if existing_room:
            # Verify it only has 2 members (extra safety check)
            member_count_query = select(room_members_table.c.user_id).where(
                room_members_table.c.room_id == existing_room.id
            )
            member_result = await db.execute(member_count_query)
            members = member_result.scalars().all()

            if len(members) == 2:
                return existing_room

        room = Room(
            room_type=RoomType.PRIVATE,  # Use the enum
            created_by_user_id=current_user_id,
            name="Private chat",  # Optional: generate a name
        )
        await room.save()

        # Add both users as members
        await db.execute(
            room_members_table.insert().values(
                [
                    {"room_id": room.id, "user_id": current_user_id},
                    {"room_id": room.id, "user_id": member_user.id},
                ]
            )
        )
        await db.commit()

        return room

    @staticmethod
    async def add_members_to_room(room: Room, users: MembersBase) -> None:
        """
        Add multiple users to a chat room.
        Args:
            room (Room): The chat room to add members to.
            users (MembersBase): Object containing list of user IDs to add as members.

        # check if the user exists else create them then add as a member
        """
        db = Room._get_db()
        for user_id in users.user_ids:
            # Convert UUID to string for user_id
            user_id_str = str(user_id)
            user = await User.first(user_id=user_id_str)
            if not user:
                user = User(user_id=user_id_str)
                await user.save()
            await db.execute(
                room_members_table.insert().values(room_id=room.id, user_id=user.id)
            )
        await db.commit()

    # remove members from a room
    @staticmethod
    async def remove_members_from_room(
        request: Request, room: Room, users: MembersBase
    ) -> None:
        """
        Remove multiple users from a chat room.
        Args:
            room (Room): The chat room to remove members from.
            users (MembersBase): Object containing list of user IDs to remove from members.
        """

        if room.created_by_user_id != request.user.id:
            raise BadRequestException(
                "You do not have permission to remove members from this room"
            )

        async def _remove_members_operation(db):
            for user_id in users.user_ids:
                # Convert UUID to string for user_id lookup
                user_id_str = str(user_id)
                user = await User.first(user_id=user_id_str)
                if user:  # Only try to remove if user exists
                    await db.execute(
                        room_members_table.delete().where(
                            and_(
                                room_members_table.c.room_id == room.id,
                                room_members_table.c.user_id
                                == user.id,  # Use actual user.id from database
                            )
                        )
                    )
            await db.commit()

        await Room._execute_with_session_recovery(_remove_members_operation)

    @staticmethod
    async def get_room_members(room_id: str) -> list[User]:
        """
        Retrieve all members of a chat room.
        Args:
            room_id (str): The unique identifier of the chat room.

        Returns:
            list[User]: List of users who are members of the room.
        """
        # First verify the room exists
        room = await Room.first(id=room_id)
        if not room:
            raise NotFoundException("Room not found")

        # Get all member user IDs for this room
        db = Room._get_db()
        try:
        
            member_ids_query = select(room_members_table.c.user_id).where(
                room_members_table.c.room_id == room_id
            )
            result = await db.execute(member_ids_query)
            member_ids = result.scalars().all()

            if not member_ids:
                return []

            # Fetch all member users using proper SQLAlchemy syntax
            stmt = select(User).where(User.id.in_(member_ids), User._soft_delete_filter())
            result = await db.execute(stmt)
            members = result.scalars().all()
        finally:
            await db.close()
        return members

    # delete a group
    @staticmethod
    async def delete_room(request: Request, room_id: str) -> None:
        """
        Delete a chat room if the requesting user is the creator.
        Args:
            request (Request): The FastAPI request object.
            room_id (str): The unique identifier of the chat room to delete.
        """
        room = await Room.first(id=room_id)
        if not room:
            raise NotFoundException("Room not found")
        if room.created_by_user_id != request.user.id:
            raise BadRequestException("You do not have permission to delete this room")
        await room.delete()
