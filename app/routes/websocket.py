from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from loguru import logger

from app.websocket.main import websocket_endpoint

websocket_routes = APIRouter(
    prefix="/ws",
    tags=["WebSocket"],
)


@websocket_routes.websocket("/rooms/{room_id}/")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    room_id: str,
    token: str = Query(..., description="JWT authentication token"),
):
    """
    WebSocket endpoint for chat rooms.

    Args:
        websocket: WebSocket connection
        room_id: ID of the chat room to connect to
        token: JWT authentication token passed as query parameter
    """
    try:
        logger.info(f"WebSocket route handler called for room {room_id}")
        await websocket_endpoint(websocket, room_id, token)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected in route handler")
    except Exception as e:
        logger.error(f"WebSocket route error: {e}", exc_info=True)


@websocket_routes.websocket("/test/")
async def test_websocket(websocket: WebSocket):
    """Simple test WebSocket endpoint."""
    logger.info("=== TEST WebSocket endpoint called ===")
    await websocket.accept()
    await websocket.send_text('{"type": "test", "message": "WebSocket works!"}')

    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received: {data}")
            await websocket.send_text(f'{{"type": "echo", "message": "{data}"}}')
    except WebSocketDisconnect:
        logger.info("Test WebSocket disconnected")
