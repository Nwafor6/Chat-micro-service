from enum import Enum


class RoomType(str, Enum):
    """Enumeration for room types."""

    PUBLIC = "public"
    PRIVATE = "private"


class MessageType(str, Enum):
    """Enumeration for message types."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"
