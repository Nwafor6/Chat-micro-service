from contextvars import ContextVar
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def create_async_database_engine() -> AsyncEngine:
    """
    Create and return an asynchronous SQLAlchemy engine based on configuration.

    Returns:
        AsyncEngine: Configured async SQLAlchemy engine.

    Raises:
        ValueError: If an unsupported database type is specified in settings.
    """
    if settings.db_type not in ["postgres", "mysql"]:
        raise ValueError(
            f"Unsupported database type specified in settings: {settings.db_type}"
        )

    database_url = settings.get_database_url()

    # Replace with async-compatible dialect
    if settings.db_type == "postgres":
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif settings.db_type == "mysql":
        database_url = database_url.replace("mysql://", "mysql+aiomysql://", 1)

    return create_async_engine(database_url, pool_pre_ping=True, echo=False)


# Create the async engine and sessionmaker
async_engine: AsyncEngine = create_async_database_engine()

AsyncSessionLocal: sessionmaker = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

db_context: ContextVar[AsyncSession] = ContextVar("db_session")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a new async database session.

    Yields:
        AsyncGenerator[AsyncSession, None]: A SQLAlchemy async session.
    """
    async with AsyncSessionLocal() as session:
        token = db_context.set(session)
        try:
            yield session
        finally:
            db_context.reset(token)
