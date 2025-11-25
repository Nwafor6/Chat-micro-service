from .chat import chat_routes
from .docs import docs_router
from .user import user_routes
from .websocket import websocket_routes

__all__ = [
    "user_routes",
    "chat_routes",
    "websocket_routes",
    "docs_router",
]
