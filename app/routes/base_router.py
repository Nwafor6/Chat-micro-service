from fastapi import APIRouter

from app.routes import chat_routes, docs_router, user_routes

router = APIRouter()
router.include_router(user_routes)
router.include_router(chat_routes, prefix="/chats")
router.include_router(docs_router)
# router.include_router(websocket_routes)
