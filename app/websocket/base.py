import asyncio
import json
import logging
from typing import Dict, List, Optional, Set

from fastapi import WebSocket

from app.models import Room, User

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for chat rooms."""

    def __init__(self):
        # Dictionary to store active connections by room_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Dictionary to store user info for each connection
        self.connection_users: Dict[WebSocket, User] = {}
        # Dictionary to store room info for each connection
        self.connection_rooms: Dict[WebSocket, Room] = {}

    async def connect(self, websocket: WebSocket, room_id: str, user: User, room: Room):
        """Accept a new WebSocket connection and add to room."""
        await websocket.accept()

        # Initialize room connections if not exists
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()

        # Add connection to room
        self.active_connections[room_id].add(websocket)
        self.connection_users[websocket] = user
        self.connection_rooms[websocket] = room

        logger.info("User %s connected to room %s", user.user_id, room_id)

        # Notify other users in the room about new connection
        await self.broadcast_to_room(
            room_id,
            {
                "type": "user_joined",
                "user_id": str(user.user_id),
                "message": f"User {user.user_id} joined the room",
            },
            exclude=websocket,
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        user = self.connection_users.get(websocket)
        room = self.connection_rooms.get(websocket)

        if room and user:
            room_id = str(room.id)

            # Remove from room connections
            if room_id in self.active_connections:
                self.active_connections[room_id].discard(websocket)

                # Remove empty room
                if not self.active_connections[room_id]:
                    del self.active_connections[room_id]

            logger.info(
                "User %s disconnected from room %s", user.user_id, room_id
            )

            # Notify other users about disconnection
            if room_id in self.active_connections:
                # Create a coroutine for the broadcast but don't await it here
                # since disconnect might be called from a non-async context

                try:
                    asyncio.create_task(
                        self.broadcast_to_room(
                            room_id,
                            {
                                "type": "user_left",
                                "user_id": str(user.user_id),
                                "message": f"User {user.user_id} left the room",
                            },
                            exclude=websocket,
                        )
                    )
                except RuntimeError:
                    # If no event loop is running, skip the notification
                    pass

        # Clean up connection mappings
        self.connection_users.pop(websocket, None)
        self.connection_rooms.pop(websocket, None)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error("Error sending message to websocket: %s", e)
            # Connection might be closed, remove it
            self.disconnect(websocket)

    async def broadcast_to_room(
        self, room_id: str, message: dict, exclude: Optional[WebSocket] = None
    ):
        """Broadcast a message to all connections in a room."""
        if room_id not in self.active_connections:
            return

        # Create a copy of connections to avoid modification during iteration
        connections = self.active_connections[room_id].copy()

        for connection in connections:
            if exclude and connection == exclude:
                continue

            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error("Error broadcasting to connection: %s", e)
                # Remove failed connection
                self.disconnect(connection)

    def get_room_connections(self, room_id: str) -> List[WebSocket]:
        """Get all active connections for a room."""
        return list(self.active_connections.get(room_id, set()))

    def get_room_users(self, room_id: str) -> List[User]:
        """Get all users currently connected to a room."""
        connections = self.get_room_connections(room_id)
        return [
            self.connection_users[conn]
            for conn in connections
            if conn in self.connection_users
        ]


# Global connection manager instance
manager = ConnectionManager()
