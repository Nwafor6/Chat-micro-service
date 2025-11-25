"""All middlewares for the application."""

import json
import time
from typing import Any, Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from jose import JWTError
from loguru import logger
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_404_NOT_FOUND

from app.core.auth import decode_jwt_token
from app.core.database import AsyncSessionLocal
from app.models import User
from app.utils.http import build_error_response


class RequestContextLogMiddleware(BaseHTTPMiddleware):
    """Middleware to log request context and timing."""

    async def dispatch(self, request: Request, call_next):
        # Skip middleware for OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)

        start_time = time.time()

        # Log the request
        logger.info(f"Request: {request.method} {request.url}")

        # Process the request
        response = await call_next(request)

        # Log the response
        logger.info(f"Response time: {time.time() - start_time}")
        logger.info(f"Response status: {response.status_code}")

        return response


class CatchAll(BaseHTTPMiddleware):
    """
    Middleware to catch all 404 errors and return a custom response.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        if response.status_code == 404:
            return JSONResponse(
                status_code=HTTP_404_NOT_FOUND,
                content=build_error_response(
                    request,
                    "NotFoundError",
                    "The requested resource was not found.",
                    HTTP_404_NOT_FOUND,
                ),
            )
        return response


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to handle JWT authentication."""

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)

        await self.set_user(request)
        return await call_next(request)

    async def set_user(self, request: Request) -> None:
        request._user = None  # Default to unauthenticated

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            logger.info(f"Attempting JWT validation for token: {token}")
            try:
                payload = decode_jwt_token(token=token)

                logger.debug(f"JWT payload: {payload}")
                # Use the same logic as get_current_user
                user_id = payload.get("sub") or payload.get("user_id")
                if user_id:
                    # Ensure user_id is always a string for consistency
                    user_id_str = str(user_id)

                    async with AsyncSessionLocal() as session:
                        # First try to find by user_id (matching get_current_user)
                        result = await session.execute(
                            select(User).filter(User.user_id == user_id_str)
                        )
                        user = result.scalar_one_or_none()

                        # Fallback to internal ID if not found
                        if not user:
                            result = await session.execute(
                                select(User).filter(User.id == user_id_str)
                            )
                            user = result.scalar_one_or_none()

                        if user:
                            logger.debug(f"Authenticated User: {user.user_id}")
                            request._user = user
                        else:
                            # create the user
                            user, created = await User.get_or_create(
                                user_id=user_id_str
                            )
                            request._user = user
                            logger.debug(
                                f"User created: {created} with ID: {user.user_id}"
                            )

            except JWTError as e:
                logger.debug(f"JWT validation failed: {e}")

        # Monkey-patch `user` property to Request class
        setattr(Request, "user", property(lambda self: getattr(request, "_user", None)))


class DBSessionMiddleware(BaseHTTPMiddleware):
    """Middleware to handle database sessions."""

    async def dispatch(self, request: Request, call_next):
        # Skip DB session for OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # Your existing DB session logic here
        return await call_next(request)


class ResponseTransformerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to transform successful JSON responses into a consistent format.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        # Might be useful in the future
        # List of url to exclude from the response transformation
        # Without the leading slash
        excluded_routes = ["openapi.json", ".well-known/"]
        request_path = str(request.url.path).lstrip("/")  # removes leading slash
        if any(request_path.startswith(route) for route in excluded_routes):
            return response

        # if not str(request.url.path).startswith(settings.api_prefix):
        #     return response

        if (
            200 <= response.status_code < 300
            and "application/json" in response.headers.get("content-type", "")
        ):
            route = request.scope.get("route")
            message: str | None = (
                getattr(route.endpoint, "response_message", None) if route else None
            )

            original_body = b"".join([chunk async for chunk in response.body_iterator])
            try:
                data: Any = json.loads(original_body.decode())
            except json.JSONDecodeError:
                data = original_body.decode()

            wrapped_body = {
                "success": True,
                "status_code": response.status_code,
                "message": message or "Success",
                "data": data,
            }

            # Create new response preserving CORS headers
            new_response = JSONResponse(
                content=wrapped_body, status_code=response.status_code
            )

            # Copy headers from original response to preserve CORS headers,
            # but exclude content-related headers
            headers_to_exclude = {
                "content-length",
                "content-encoding",
                "transfer-encoding",
            }
            for key, value in response.headers.items():
                if key.lower() not in headers_to_exclude:
                    new_response.headers[key] = value

            return new_response

        return response
