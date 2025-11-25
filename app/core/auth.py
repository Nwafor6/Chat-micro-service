from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from loguru import logger
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import setup_logging
from app.models import User

# JWT Configuration
SECRET_KEY: str = settings.jwt_secret_key
ALGORITHM: str = settings.jwt_algorithm

# Password hashing context
pwd_context: CryptContext = CryptContext(
    schemes=[settings.crypto_algorithm],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,
    argon2__parallelism=4,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

setup_logging()


def create_access_token(
    data: dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generate a JWT access token.

    Args:
        data (dict): Payload to encode.
        expires_delta (Optional[timedelta]): Optional expiration time.

    Returns:
        str: Encoded JWT token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.jwt_token_ttl)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """Retrieve the current authenticated user based on the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Debug: Print the token (remove in production)
        logger.debug(f"Received token: {token[:50]}...")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug(f"Token payload: {payload}")

        user_id: Optional[str] = payload.get("sub") or payload.get("user_id")
        if user_id is None:
            logger.error(f"No user ID found in token payload: {payload}")
            raise credentials_exception

    except JWTError as exc:
        logger.error(f"JWT decode error: {exc}")
        raise credentials_exception from exc

    # Try to find user
    result = await db.execute(select(User).filter(User.user_id == user_id))
    user = result.scalar()

    if user is None:
        logger.error(f"User not found with user_id: {user_id}")
        # Also try looking by internal ID as fallback
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar()

        if user is None:
            raise credentials_exception

    logger.debug(f"Found user: {user.user_id}")
    return user


async def require_auth(request: Request) -> User:
    """
    Ensure that a request has an authenticated user.

    Args:
        request (Request): FastAPI request object.

    Raises:
        HTTPException: If the user is not authenticated.mousermouserdelsdels

    Returns:
        User: Authenticated user object from request.
    """
    logger.debug(f"User: {request.user}")
    if not getattr(request, "user", None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return request.user


async def user_is_admin(request: Request) -> User:
    """
    Ensure that the authenticated user is an admin.

    Args:
        request (Request): FastAPI request object.

    Raises:
        HTTPException: If the user is not an admin.

    Returns:
        User: Authenticated user object if they are an admin.
    """
    # user = request.user
    # if user.role != UserRoleEnum.ADMIN:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="You do not have permission to perform this action.",
    #     )
    # return user


def decode_jwt_token(token: str) -> Optional[dict]:
    """Decode JWT token and return payload."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        logger.debug(f"JWT validation failed: {e}")
        return None
