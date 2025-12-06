"""Main FastAPI application for BildupAI Chat Service."""

from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.admin import setup_admin
from app.core.config import settings
from app.core.database import sync_engine  # Change this import
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.core.management.lifecycle_manager import LifecycleManager
from app.core.middlewares import DBSessionMiddleware, JWTAuthMiddleware
from app.routes import websocket_routes
from app.routes.base_router import router
from app.utils.http import api_success

setup_logging()

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    debug=settings.debug,
    docs_url="/docs" if settings.env != "production" else None,
    redoc_url="/redoc" if settings.env != "production" else None,
    redirect_slashes=False,  # Add this to prevent automatic redirects
)


# Add CORS middleware with specific origins for credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
        "http://localhost:3001",
        "http://localhost:5173",
        "https://valcertra.com",
        "https://www.valcertra.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight response for 1 hour
)
app.add_middleware(DBSessionMiddleware)
app.add_middleware(JWTAuthMiddleware)

# Register exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.get("/")
async def home(request: Request) -> Dict[str, Any]:
    """Home endpoint to test connections and service health."""
    logger.info(f"Home endpoint accessed from {request.client.host}")

    # API endpoints info
    endpoints = {
        "docs": (
            f"{settings.base_url}/docs" if settings.env != "production" else "disabled"
        ),
        "websocket_docs": f"{settings.base_url}{settings.api_prefix}/docs/websockets",
        "health": f"{settings.base_url}/health",
        "api_prefix": settings.api_prefix,
        "admin_route": f"{settings.base_url}/val-admin" if settings.env != "production" else "disabled",
    }

    response_data = {
        "endpoints": endpoints if settings.env != "production" else {},
    }

    return api_success(
        data=response_data,
        message="Chat service is running and ready to accept connections",
    )


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for load balancers and monitoring."""
    return api_success(
        data={
            "service": settings.app_name,
            "status": "healthy",
            "version": settings.app_version,
            "timestamp": datetime.now(),
            "database": settings.db_type,
        },
        message="Service is healthy",
    )


LifecycleManager(app)
# Include API routers
app.include_router(router, prefix=settings.api_prefix)
app.include_router(websocket_routes)

# Setup admin interface
setup_admin(app, sync_engine)  # Use sync_engine instead
