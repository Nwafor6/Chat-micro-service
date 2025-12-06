import uuid
from datetime import datetime
from typing import List, Optional, TypeVar

from pydantic import BaseModel
from app.schemas.user import UserResponse

T = TypeVar("T")


class RoomBase(BaseModel):
    """Base model for room data."""

    name: Optional[str] = None
    description: Optional[str] = None
    # bildup_classroom_id: Optional[uuid.UUID] = None


class MessageResponse(BaseModel):
    """Response model for message data."""

    id: uuid.UUID
    content: str
    message_type: str
    user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class RoomResponse(RoomBase):
    """Response model for room data."""

    id: uuid.UUID
    created_by_user_id: uuid.UUID
    room_type: str
    is_locked: bool
    last_message: Optional[MessageResponse] = None
    last_message_sender_info: dict = None
    member_count: int = 0
    # members_list: Optional[List[UserResponse]] = None  # List of RoomMemberResponse
    room_custom_name: Optional[dict] = {}

    class Config:
        from_attributes = True


class MembersBase(BaseModel):
    """Base model for adding members to a room."""

    user_ids: List[uuid.UUID]


class RoomMemberResponse(BaseModel):
    """Response model for room member data."""

    id: uuid.UUID
    user_id: str
    user_info: dict = {}
    is_ai: bool = False

    class Config:
        from_attributes = True
