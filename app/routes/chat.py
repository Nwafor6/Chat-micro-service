from fastapi import APIRouter, Depends, Request

from app.controllers import RoomController
from app.core.auth import require_auth
from app.schemas import RoomBase
from app.schemas.chat import MembersBase
from app.utils.http import api_success

chat_routes = APIRouter(
    prefix="/rooms",
    dependencies=[
        Depends(require_auth),
    ],
    tags=["Chats"],
)


class ChatRoutes:
    """Routes to handles chat related operations."""

    @staticmethod
    @chat_routes.post("/create-room")
    async def create_room(request: Request, room_data: RoomBase):
        """
        Create a new chat room.
        Args:
            request (Request): The FastAPI request object.
            room_data (RoomBase): The data for the new chat room.

        Returns:
            dict: API success response with the created chat room data.

        """
        room = await RoomController.create_room(request, room_data)
        return api_success(data=room, message="Room created successfully")

    @staticmethod
    @chat_routes.get("/user-rooms")
    async def get_user_rooms(request: Request, classroom_id: str = None):
        """
        Retrieve all chat rooms created by the authenticated user or the user is a member of.
        Args:
            request (Request): The FastAPI request object.
            classroom_id (str, optional): Filter rooms by classroom ID.

        Returns:
            dict: API success response with list of rooms the user created or is a member of.
        """
        rooms = await RoomController.get_user_rooms(request, classroom_id)
        return api_success(data=rooms, message="User rooms retrieved successfully")

    @staticmethod
    @chat_routes.get("/{room_id}")
    async def get_room(room_id: str):
        """
        Retrieve a chat room by its ID.
        Args:
            room_id (str): The unique identifier of the chat room.

        Returns:
            dict: API success response with the chat room data.

        """
        room = await RoomController.get_room_by_id(room_id)
        return api_success(data=room, message="Room retrieved successfully")

    @staticmethod
    @chat_routes.get("/dm/{member_user_id}")
    async def get_or_create_room(request: Request, member_user_id: str):
        """
        This is a DM (Direct Message) endpoint. It will retrieve an existing
        room between the authenticated user and the specified member user.
        If no such room exists, a new private room is created for them both.

        Args:
            request (Request): The FastAPI request object.
            member_user_id (str): The user ID.
        Returns:
            dict: API success response with the existing or newly created chat room data.
        """
        room = await RoomController.get_or_create_private_room(request, member_user_id)
        return api_success(
            data=room, message="Private room retrieved/created successfully"
        )

    @staticmethod
    @chat_routes.post("/add-members/{room_id}")
    async def add_members_to_room(request: Request, room_id: str, users: MembersBase):
        """
        Add multiple users to a chat room.
        Args:
            request (Request): The FastAPI request object.
            room_id (str): The unique identifier of the chat room.
            users (MembersBase): The data containing user IDs to add as members.

        Returns:
            dict: API success response indicating members were added successfully.

        """
        room = await RoomController.get_room_by_id(room_id)
        await RoomController.add_members_to_room(room, users)
        return api_success(message="Members added successfully")

    # remove members from a room
    @staticmethod
    @chat_routes.post("/remove-members/{room_id}")
    async def remove_members_from_room(
        request: Request, room_id: str, users: MembersBase
    ):
        """
        Remove multiple users from a chat room.
        Args:
            request (Request): The FastAPI request object.
            room_id (str): The unique identifier of the chat room.
            users (MembersBase): The data containing user IDs to remove from members.

        Returns:
            dict: API success response indicating members were removed successfully.

        """
        room = await RoomController.get_room_by_id(room_id)
        await RoomController.remove_members_from_room(request, room, users)
        return api_success(message="Members removed successfully")

    @staticmethod
    @chat_routes.get("/{room_id}/members")
    async def get_room_members(room_id: str):
        """
        Retrieve all members of a chat room.
        Args:
            room_id (str): The unique identifier of the chat room.

        Returns:
            dict: API success response with list of room members.
        """
        members = await RoomController.get_room_members(room_id)
        return api_success(data=members, message="Room members retrieved successfully")

    # delete a room
    @staticmethod
    @chat_routes.delete("/{room_id}")
    async def delete_room(request: Request, room_id: str):
        """
        Delete a chat room by its ID.
        Args:
            room_id (str): The unique identifier of the chat room.

        Returns:
            dict: API success response indicating the room was deleted successfully.

        """
        await RoomController.delete_room(request, room_id)
        return api_success(message="Room deleted successfully")
