# pylint: disable=unused-argument

"""Custom SQLAlchemy types"""

import uuid

from sqlalchemy.dialects.mysql import BINARY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator

from app.core.config import settings


class GUID(TypeDecorator):
    """Platform-independent GUID type."""

    impl = PG_UUID if settings.db_type == "postgres" else BINARY
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if dialect.name == "postgresql":
                return str(value)
            return value.bytes
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if isinstance(value, uuid.UUID):
                return value
            return uuid.UUID(str(value))
        return value

    def process_literal_param(self, value, dialect):
        """Process literal parameters to ensure proper formatting."""
        if value is not None:
            return str(value)
        return value

    @property
    def python_type(self):
        """Return the Python type associated with this GUID type."""
        return uuid.UUID
