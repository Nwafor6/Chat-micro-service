from typing import Any, Dict

import httpx
from fastapi import WebSocket
from loguru import logger
from sqlalchemy import select

from app.core.logging import setup_logging
from app.models import Message, MessageType, User, room_members_table
from app.websocket import manager
from app.websocket.utils import authenticate_websocket, validate_room_access

setup_logging()


class MainConsumer:
    """WebSocket consumer functionality."""

    def __init__(self):
        self.websocket: WebSocket = None
        self.room_id: str = None
        self.user = None
        self.room = None
        self.token: str = None  # store sender access token

    async def connect(self, websocket: WebSocket, room_id: str, token: str):
        """Handle WebSocket connection."""
        logger.info(f"WebSocket connection attempt to room {room_id}")

        self.websocket = websocket
        self.room_id = room_id
        self.token = token  # keep token for notifications

        try:
            # Authenticate user
            logger.info("Starting user authentication...")
            self.user = await authenticate_websocket(websocket, token)
            if not self.user:
                logger.error("User authentication failed")
                return False

            logger.info(f"User authenticated: {self.user.user_id}")

            # Validate room access
            logger.info("Validating room access...")
            self.room = await validate_room_access(self.user, room_id)
            if not self.room:
                logger.error("Room access validation failed")
                await websocket.close(
                    code=4003, reason="Room not found or access denied"
                )
                return False

            logger.info(f"Room access validated for room: {self.room.id}")

            # Connect to room
            await manager.connect(websocket, room_id, self.user, self.room)

            # Send connection success message
            await manager.send_personal_message(
                {
                    "type": "connection_established",
                    "room_id": room_id,
                    "user_id": str(self.user.user_id),
                    "message": "Successfully connected to room",
                },
                websocket,
            )

            # Fetch and send room messages
            await self.send_room_messages()

            logger.info(
                f"WebSocket connection established for user {self.user.user_id} in room {room_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error during WebSocket connection: {e}", exc_info=True)
            try:
                await websocket.close(code=4000, reason="Connection failed")
            except Exception as err:
                logger.error(
                    "Failed to close websocket after connection error: %s", err
                )
            return False

    async def send_room_messages(self, limit: int = 50):
        """Fetch and send all messages from the room to the newly connected user."""
        try:
            logger.info("Fetching messages for room %s", self.room.id)

            # Get database session
            db = Message._get_db()

            # Query for messages in the room, ordered by creation time
            messages_query = (
                select(Message)
                .where(Message.room_id == self.room.id)
                .where(Message._soft_delete_filter())  # Only non-deleted messages
                .order_by(Message.created_at.asc())
                .limit(limit)
            )  # Most recent messages first, then reverse

            result = await db.execute(messages_query)
            messages = result.scalars().all()

            logger.info(f"Found {len(messages)} messages for room {self.room.id}")

            if messages:
                # Convert messages to the format expected by frontend
                message_list = []
                for msg in messages:

                    message_user = await User.find(msg.user_id)

                    message_data = {
                        "message_id": str(msg.id),
                        "content": msg.content,
                        "message_type": (
                            msg.message_type.value
                            if hasattr(msg.message_type, "value")
                            else str(msg.message_type)
                        ),
                        "user_id": (
                            str(message_user.user_id)
                            if message_user
                            else "unknown"
                        ),
                        "room_id": str(self.room.id),
                        "timestamp": msg.created_at.isoformat(),
                        "user_info": (
                            getattr(message_user, "user_info", {})
                            if message_user
                            else {}
                        ),
                    }
                    message_list.append(message_data)

                # Send all messages to the connected user
                await manager.send_personal_message(
                    {
                        "type": "room_messages",
                        "room_id": str(self.room.id),
                        "messages": message_list,
                        "total_count": len(message_list),
                        "message": f"Loaded {len(message_list)} messages",
                    },
                    self.websocket,
                )
            else:
                # Send empty message list
                await manager.send_personal_message(
                    {
                        "type": "room_messages",
                        "room_id": str(self.room.id),
                        "messages": [],
                        "total_count": 0,
                        "message": "No messages in this room yet",
                    },
                    self.websocket,
                )

        except Exception as e:
            logger.error(f"Error fetching room messages: {e}", exc_info=True)
            await manager.send_personal_message(
                {"type": "error", "message": "Failed to load room messages"},
                self.websocket,
            )

    async def disconnect(self):
        """Handle WebSocket disconnection."""
        if self.websocket:
            manager.disconnect(self.websocket)

    async def receive_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket message."""
        try:
            message_type = data.get("type", "text")
            content = data.get("message", "")

            if not content.strip():
                await manager.send_personal_message(
                    {"type": "error", "message": "Message content cannot be empty"},
                    self.websocket,
                )
                return

            # Save message to database
            message = await self.save_message(content, message_type)

            # Broadcast message to room
            message_data = {
                "type": "message",
                "message_id": str(message.id),
                "content": content,
                "message_type": message_type,
                "user_id": str(self.user.user_id),
                "room_id": self.room_id,
                "timestamp": message.created_at.isoformat(),
                "user_info": getattr(self.user, "user_info", {}),
            }

            await manager.broadcast_to_room(
                self.room_id, message_data, exclude=self.websocket
            )

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await manager.send_personal_message(
                {"type": "error", "message": "Failed to process message"},
                self.websocket,
            )

    async def save_message(self, content: str, message_type: str = "text") -> Message:
        """Save message to database."""
        try:
            # Convert string message type to enum if needed
            if isinstance(message_type, str):
                message_type = MessageType.TEXT  # Default to TEXT, you can extend this

            message = Message(
                room_id=self.room.id,
                user_id=self.user.id,
                content=content,
                message_type=message_type,
            )

            await message.save()

            # Send notifications to other members after saving
            await self.send_notifications(message, content)

            return message

        except Exception as e:
            logger.error(f"Error saving message: {e}")
            raise

    async def send_notifications(self, message: Message, content: str):
        """Send notification to other users in the room (exclude sender)."""
        try:
            db = Message._get_db()

            # Get member internal user IDs for the room
            member_query = select(room_members_table.c.user_id).where(
                room_members_table.c.room_id == self.room.id
            )
            member_result = await db.execute(member_query)
            member_user_ids = member_result.scalars().all()  # internal GUIDs

            if not member_user_ids:
                return

            # Load User rows to map to user_id
            users_query = select(User).where(User.id.in_(member_user_ids))
            users_result = await db.execute(users_query)
            users = users_result.scalars().all()

            # Build list of external user ids (user_id), excluding sender
            recipient_ids = [
                str(u.user_id)
                for u in users
                if str(u.user_id) != str(self.user.user_id)
            ]

            if not recipient_ids:
                logger.info("No recipients for notification (only sender in room)")
                return

            # Truncate content to first 20 characters
            truncated_content = content[:20] + "..." if len(content) > 20 else content

            # Prepare payload and headers (include "hears" header as requested)
            urls = [
                "https://api-prod.bildup.ai/notification/send-multiple-notification/",
                "https://api-dev1.bildup.ai/notification/send-multiple-notification/",
            ]
            # url = "https://api-prod.bildup.ai/notification/send-multiple-notification/"
            for url in urls:
                payload = {
                    "title": "New chat message.",
                    "message": f"{truncated_content}",
                    "user_ids": recipient_ids,
                }
                headers = {
                    "Authorization": f"Bearer {str(self.token)}" if self.token else ""
                }
                logger.info(self.token)
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code >= 200 and resp.status_code < 300:
                        logger.info(
                            "Notification sent to %d users for room %s",
                            len(recipient_ids),
                            self.room.id,
                        )
                    else:
                        logger.info(resp.text)
                        logger.warning(
                            "Failed to send notification (status=%s): %s",
                            resp.status_code,
                            resp.text,
                        )

        except Exception as e:
            logger.error(f"Error sending notifications: {e}", exc_info=True)

    async def handle_typing(self, is_typing: bool):
        """Handle typing indicator."""
        await manager.broadcast_to_room(
            self.room_id,
            {
                "type": "typing",
                "user_id": str(self.user.user_id),
                "is_typing": is_typing,
            },
            exclude=self.websocket,
        )
