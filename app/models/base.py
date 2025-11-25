import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional, Sequence, Type, TypeVar

from sqlalchemy import Boolean, Column, DateTime, and_, select
from sqlalchemy.exc import PendingRollbackError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.database import AsyncSessionLocal, db_context
from app.core.exceptions import NotFoundException
from app.models.type_decorators import GUID

T = TypeVar("T", bound="BaseMixin")


class BaseMixin:
    """
    Base mixin providing async ORM helpers using a context-local DB session.
    This mixin should be used with SQLAlchemy ORM models to provide common
    functionality like querying, filtering, and soft deletion.
    It provides methods to initialize queries, execute them, and manage
    soft-deletion logic.
    It also provides a way to get the current request-scoped async DB session
    or create a new one if not in a request context.

    You can either use the classmethods to perform quick queries or take control
    of the query by calling `query()` and then chaining methods like `where()`,
    `order_by()`, and finally calling `execute()` to run the query.
    """

    # id: Mapped[Any]  # Should be overridden in child models with actual primary key type

    @classmethod
    def _get_db(cls) -> AsyncSession:
        """
        Get the current request-scoped async DB session from the context,
        or create one if not in a request.
        """
        try:
            return db_context.get()
        except LookupError:
            # Not in a request context, create a new session
            # Return a new session each time to avoid state issues
            return AsyncSessionLocal()

    @classmethod
    @asynccontextmanager
    async def _get_db_session(cls):
        """
        Get a database session with proper error handling and cleanup.
        Use this for operations that need guaranteed cleanup.
        """
        try:
            db = db_context.get()
            # Use existing session from context
            yield db
        except LookupError:
            # Not in a request context, create a new session
            db = AsyncSessionLocal()
            try:
                yield db
            except Exception:
                await db.rollback()
                raise
            finally:
                await db.close()

    @classmethod
    async def _execute_with_session_recovery(cls, operation_func, *args, **kwargs):
        """
        Execute a database operation with automatic session recovery on PendingRollbackError.
        """
        try:
            async with cls._get_db_session() as db:
                return await operation_func(db, *args, **kwargs)
        except PendingRollbackError:
            # Session is in a bad state, try to recover
            try:
                # Try to get the session and rollback
                try:
                    db = db_context.get()
                    await db.rollback()
                except LookupError:
                    # Not in request context, can't recover existing session
                    pass

                # Retry the operation with a fresh session approach
                async with cls._get_db_session() as db:
                    return await operation_func(db, *args, **kwargs)
            except Exception as retry_exc:
                # If retry fails, raise the original error context
                raise retry_exc

    def _check_query_initialized(self: T):
        """
        Check if the query has been initialized.
        Raises ValueError if no query has been initialized.
        """
        if not hasattr(self, "_query"):
            raise ValueError("No query has been initialized. Use `query()` first.")

    async def execute(self: T):
        """
        Execute the query for the model.
        This is a shortcut to execute the query and return the result.
        """
        self._check_query_initialized()

        async with self._get_db_session() as db:
            result = await db.execute(self._query)
            return result

    def where(self: T, *args, **kwargs) -> T:
        """
        Add a where clause to the query.
        This is a shortcut to add a where clause to the query.
        """
        self._check_query_initialized()

        self._query = self._query.where(*args, **kwargs)
        return self

    def order_by(self: T, *args, **kwargs) -> T:
        """
        Add an order by clause to the query.
        This is a shortcut to add an order by clause to the query.
        """
        self._check_query_initialized()

        self._query = self._query.order_by(*args, **kwargs)
        return self

    async def get(self: T) -> Sequence[T]:
        """
        Get the results of the query.
        This is a shortcut to execute the query and return the results.
        It automatically applies the soft delete filter if the model has a `deleted_at` field.
        """
        self._check_query_initialized()

        self._query = self._query.where(self._soft_delete_filter())
        result = await self.execute()
        return result.scalars().all()

    @classmethod
    def query(cls: Type[T], **kwargs) -> T:
        """
        Initialize a query for the model
        You need to end this with a `exetute()`, etc.
        If no kwargs are provided, it returns a query for all records of the model.
        """
        init = cls()
        init._query = select(**kwargs) if kwargs else select(cls)
        return init

    @classmethod
    def _soft_delete_filter(cls: Type[T]):
        """Return a filter condition for non-deleted records if model has `deleted_at`."""
        if hasattr(cls, "deleted_at"):
            return getattr(cls, "deleted_at") is None  # noqa: E711
        return True

    @classmethod
    async def find(cls: Type[T], record_id: Any) -> Optional[T]:
        """Fetch a single record by its primary key, skipping soft-deleted ones."""

        async def _find_operation(db, record_id):
            stmt = select(cls).where(cls.id == record_id, cls._soft_delete_filter())
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

        return await cls._execute_with_session_recovery(_find_operation, record_id)

    @classmethod
    async def all(cls: Type[T]) -> Sequence[T]:
        """Fetch all non-deleted records, ordered by id descending."""

        async def _all_operation(db):
            stmt = (
                select(cls)
                .where(cls._soft_delete_filter())
                .order_by(cls.created_at.desc())
            )
            result = await db.execute(stmt)
            return result.scalars().all()

        return await cls._execute_with_session_recovery(_all_operation)

    @classmethod
    async def filter_by(cls: Type[T], **kwargs) -> Sequence[T]:
        """Filter records by given keyword arguments (soft delete aware), ordered by id descending."""

        async def _filter_by_operation(db, **kwargs):
            stmt = (
                select(cls)
                .filter_by(**kwargs)
                .where(cls._soft_delete_filter())
                .order_by(cls.created_at.desc())
            )
            result = await db.execute(stmt)
            return result.scalars().all()

        return await cls._execute_with_session_recovery(_filter_by_operation, **kwargs)

    @classmethod
    async def latest(
        cls: Type[T], order_by_created: bool = True, **kwargs
    ) -> Optional[T]:
        """
        Return the first matching record or None (soft delete aware).

        Args:
            order_by_created: If True (default), orders by created_at desc to get the most recent
            **kwargs: Fields to filter by

        Returns:
            The first (or most recent if ordered) matching record
        """

        async def _latest_operation(db, order_by_created, **kwargs):
            stmt = select(cls).filter_by(**kwargs).where(cls._soft_delete_filter())

            # By default, order by created_at desc to get the most recent record
            if order_by_created and hasattr(cls, "created_at"):
                stmt = stmt.order_by(cls.created_at.desc())

            result = await db.execute(stmt)
            return result.scalars().first()

        return await cls._execute_with_session_recovery(
            _latest_operation, order_by_created, **kwargs
        )

    @classmethod
    async def first(cls: Type[T], **kwargs) -> Optional[T]:
        """Return the first matching record or None (soft delete aware)."""

        async def _first_operation(db, **kwargs):
            stmt = select(cls).filter_by(**kwargs).where(cls._soft_delete_filter())
            result = await db.execute(stmt)
            return result.scalars().first()

        return await cls._execute_with_session_recovery(_first_operation, **kwargs)

    @classmethod
    async def get_from_user(cls: Type[T], user: T) -> Optional[T]:
        return await cls.first(user_id=user.id)

    async def save(self) -> None:
        """Add the instance to the DB session, commit, and refresh."""

        async def _save_operation(db):
            now = datetime.now(timezone.utc)

            if hasattr(self, "created_at") and getattr(self, "created_at") is None:
                setattr(self, "created_at", now)

            if hasattr(self, "updated_at") and getattr(self, "updated_at") is None:
                setattr(self, "updated_at", now)

            db.add(self)
            await db.commit()
            await db.refresh(self)

        await self._execute_with_session_recovery(_save_operation)

    async def _update_or_merge(self, use_merge: bool = False, **kwargs) -> T:
        """
        Internal helper to update fields and either add or merge the instance.

        Args:
            use_merge (bool): Whether to use merge instead of add.
            **kwargs: Fields to update.

        Returns:
            The updated and refreshed instance (self or merged).
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        if hasattr(self, "updated_at"):
            setattr(self, "updated_at", datetime.now(timezone.utc))

        async with self._get_db_session() as db:
            instance = await db.merge(self) if use_merge else self
            if not use_merge:
                # fuck sqlachemy on this one,
                # why use same name for add and update
                # Fucking confusing
                db.add(instance)

            await db.commit()
            await db.refresh(instance)
            return instance

    async def update(self, **kwargs) -> None:
        """Update fields on the model, set updated_at, commit, and refresh."""
        await self._update_or_merge(use_merge=False, **kwargs)

    async def merge(self, **kwargs) -> T:
        """
        Merge the field into the database and return the database contentas well
        Returns a new model
        """
        return await self._update_or_merge(use_merge=True, **kwargs)

    async def delete(self) -> None:
        """Delete the instance from the DB session and commit."""
        async with self._get_db_session() as db:
            if hasattr(self, "deleted_at"):
                self.deleted_at = datetime.now(timezone.utc)
                db.add(self)
            else:
                await db.delete(self)
            await db.commit()

    @classmethod
    async def find_by_ids(
        cls: Type[T], ids: list[Any], raise_if_missing: bool = True
    ) -> tuple[Sequence[T], set[Any]]:
        """
        Fetch multiple records by their IDs and optionally validate all exist.

        Args:
            ids: List of record IDs to fetch
            raise_if_missing: If True, raises NotFoundException when any ID is not found

        Returns:
            Tuple of (found records, missing IDs)

        Raises:
            NotFoundException: If raise_if_missing is True and any IDs are not found
        """
        if not ids:
            return [], set()

        async with cls._get_db_session() as db:
            stmt = select(cls).where(and_(cls.id.in_(ids), cls._soft_delete_filter()))
            result = await db.execute(stmt)
            records = result.scalars().all()

            # Find missing IDs
            found_ids = {str(record.id) for record in records}
            requested_ids = {str(id_) for id_ in ids}
            missing_ids = requested_ids - found_ids

            if missing_ids and raise_if_missing:
                raise NotFoundException(
                    f"{cls.__name__}s with IDs {', '.join(missing_ids)} not found"
                )

            return records, missing_ids

    @classmethod
    async def get_or_create(
        cls: Type[T], defaults: Optional[dict] = None, **kwargs
    ) -> tuple[T, bool]:
        """
        Get an object matching the given kwargs or create a new one.
        Similar to Django's get_or_create method.

        Args:
            defaults: Dictionary of field names and values to use when creating
                     the object if it doesn't exist. These values are NOT used
                     for the lookup.
            **kwargs: Keyword arguments used for the lookup and creation
                     (unless overridden by defaults).

        Returns:
            Tuple of (object, created) where created is a boolean indicating
            whether the object was created (True) or retrieved (False).

        Raises:
            MultipleObjectsReturned: If more than one object matches the lookup.

        Example:
            # Get or create a room
            room, created = await Room.get_or_create(
                name="General Chat",
                room_type=RoomType.PUBLIC,
                defaults={
                    "description": "A general chat room for everyone",
                    "created_by_user_id": user.id
                }
            )
        """
        defaults = defaults or {}

        async with cls._get_db_session() as db:
            # Try to get the existing object
            try:
                stmt = select(cls).filter_by(**kwargs).where(cls._soft_delete_filter())
                result = await db.execute(stmt)
                objects = result.scalars().all()

                if len(objects) > 1:
                    raise ValueError(
                        f"get_or_create() returned more than one {cls.__name__} -- "
                        f"it returned {len(objects)}! Lookup parameters were {kwargs}"
                    )

                # If object exists, return it
                if len(objects) == 1:
                    return objects[0], False

            except Exception as e:
                # If there's an error in the query, re-raise it
                if "returned more than one" in str(e):
                    raise
                # For other database errors, let them bubble up
                raise

            # Object doesn't exist, create it
            # Merge kwargs with defaults (defaults take precedence)
            create_kwargs = {**kwargs, **defaults}

            # Create the new object
            obj = cls(**create_kwargs)

            # Set timestamps if they exist and aren't already set
            now = datetime.now(timezone.utc)
            if hasattr(obj, "created_at") and getattr(obj, "created_at") is None:
                setattr(obj, "created_at", now)
            if hasattr(obj, "updated_at") and getattr(obj, "updated_at") is None:
                setattr(obj, "updated_at", now)

            try:
                db.add(obj)
                await db.commit()
                await db.refresh(obj)
                return obj, True

            except Exception as e:
                # Handle potential race condition where another process
                # created the object between our check and creation
                await db.rollback()

                # Try to get the object again
                stmt = select(cls).filter_by(**kwargs).where(cls._soft_delete_filter())
                result = await db.execute(stmt)
                existing_obj = result.scalars().first()

                if existing_obj:
                    return existing_obj, False

                # If we still can't find it, re-raise the original exception
                raise e

    @classmethod
    async def update_or_create(
        cls: Type[T], defaults: Optional[dict] = None, **kwargs
    ) -> tuple[T, bool]:
        """
        Update an object matching the given kwargs or create a new one.
        Similar to Django's update_or_create method.

        Args:
            defaults: Dictionary of field names and values to use when updating
                     or creating the object.
            **kwargs: Keyword arguments used for the lookup.

        Returns:
            Tuple of (object, created) where created is a boolean indicating
            whether the object was created (True) or updated (False).

        Example:
            # Update or create a user
            user, created = await User.update_or_create(
                user_id="user123",
                defaults={
                    "is_ai": False,
                    "user_info": {"name": "John Doe", "email": "john@example.com"}
                }
            )
        """
        defaults = defaults or {}

        async with cls._get_db_session() as db:
            # Try to get the existing object
            stmt = select(cls).filter_by(**kwargs).where(cls._soft_delete_filter())
            result = await db.execute(stmt)
            obj = result.scalars().first()

            if obj:
                # Object exists, update it
                for key, value in defaults.items():
                    if hasattr(obj, key):
                        setattr(obj, key, value)

                if hasattr(obj, "updated_at"):
                    setattr(obj, "updated_at", datetime.now(timezone.utc))

                db.add(obj)
                await db.commit()
                await db.refresh(obj)
                return obj, False

            # Object doesn't exist, create it
            create_kwargs = {**kwargs, **defaults}
            obj = cls(**create_kwargs)

            # Set timestamps
            now = datetime.now(timezone.utc)
            if hasattr(obj, "created_at") and getattr(obj, "created_at") is None:
                setattr(obj, "created_at", now)
            if hasattr(obj, "updated_at") and getattr(obj, "updated_at") is None:
                setattr(obj, "updated_at", now)

            db.add(obj)
            await db.commit()
            await db.refresh(obj)
            return obj, True


class BaseModel(BaseMixin, DeclarativeBase):
    """Base model class to be inherited by all ORM models."""

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_fake = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Indicates if the record is fake/test data",
    )


async def table_migration(engine: AsyncEngine):
    """Create tables in the database using the async engine."""
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
