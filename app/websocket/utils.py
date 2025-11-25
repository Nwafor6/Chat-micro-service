from typing import Optional

from fastapi import WebSocket
from loguru import logger
from sqlalchemy import and_, select

from app.core.auth import decode_jwt_token
from app.core.logging import setup_logging
from app.models import Room, User, room_members_table

setup_logging()


async def authenticate_websocket(websocket: WebSocket, token: str) -> Optional[User]:
    """Authenticate user from JWT token for WebSocket connection."""
    try:
        logger.info(f"Authenticating WebSocket with token: {token[:50]}...")

        # Decode the JWT token
        payload = decode_jwt_token(token)
        if not payload:
            logger.error("JWT token decode failed - invalid token")
            await websocket.close(code=4001, reason="Invalid token")
            return None

        logger.info(f"WebSocket token payload: {payload}")

        # Get user ID from payload - try multiple possible keys
        user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
        if not user_id:
            logger.error(
                f"No user ID found in token payload. Available keys: {list(payload.keys())}"
            )
            await websocket.close(code=4001, reason="Invalid token payload")
            return None

        logger.info(f"Looking for user with user_id: {user_id}")

        # Try to find existing user
        user = await User.first(user_id=str(user_id))
        if not user:
            logger.info(
                f"User not found, creating new user with user_id: {user_id}"
            )
            user, created = await User.get_or_create(user_id=str(user_id))
            logger.info(f"User {'created' if created else 'found'}: {user.id}")
        else:
            logger.info(f"Found existing user: {user.id}")

        return user

    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}", exc_info=True)
        await websocket.close(code=4001, reason="Authentication failed")
        return None


async def validate_room_access(user: User, room_id: str) -> Optional[Room]:
    """Validate that user has access to the specified room."""
    try:
        logger.info(
            f"Validating room access for user {user.user_id} to room {room_id}"
        )

        # Get the room
        room = await Room.find(room_id)
        if not room:
            logger.error(f"Room {room_id} not found")
            return None

        logger.info(
            f"Found room: {room.id}, type: {room.room_type}, creator: {room.created_by_user_id}"
        )

        db = Room._get_db()

        # Check if user is creator
        if str(room.created_by_user_id) == str(user.id):
            logger.info(f"User {user.user_id} is the creator of room {room_id}")
            return room

        # Check if user is a member
        member_query = select(room_members_table.c.room_id).where(
            and_(
                room_members_table.c.room_id == room.id,
                room_members_table.c.user_id == user.id,
            )
        )

        member_result = await db.execute(member_query)
        is_member = member_result.scalar() is not None

        if is_member:
            logger.info(f"User {user.user_id} is a member of room {room_id}")
            return room

        logger.warning(f"User {user.user_id} has no access to room {room_id}")
        return None

    except Exception as e:
        logger.error(f"Room access validation error: {e}", exc_info=True)
        return None
