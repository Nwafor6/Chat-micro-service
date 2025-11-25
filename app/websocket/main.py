import json

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from app.core.logging import setup_logging
from app.websocket import manager
from app.websocket.consumer import MainConsumer

setup_logging()


async def websocket_endpoint(websocket: WebSocket, room_id: str, token: str):
    """Main WebSocket endpoint for chat."""
    consumer = MainConsumer()

    try:
        logger.info(f"WebSocket endpoint called for room {room_id}")

        # Handle connection
        connection_successful = await consumer.connect(websocket, room_id, token)

        if not connection_successful:
            logger.error("WebSocket connection failed")
            return

        # Listen for messages
        while True:
            try:
                # Receive message from WebSocket
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Handle different message types
                msg_type = message_data.get("type", "message")

                if msg_type == "message":
                    await consumer.receive_message(message_data)
                elif msg_type == "typing":
                    is_typing = message_data.get("is_typing", False)
                    await consumer.handle_typing(is_typing)
                else:
                    await manager.send_personal_message(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {msg_type}",
                        },
                        websocket,
                    )

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {"type": "error", "message": "Invalid JSON format"}, websocket
                )
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
                break
            except Exception as e:
                logger.error(f"Error in websocket loop: {e}", exc_info=True)
                await manager.send_personal_message(
                    {"type": "error", "message": "Internal server error"}, websocket
                )

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}", exc_info=True)
    finally:
        # Ensure cleanup on disconnect
        await consumer.disconnect()
