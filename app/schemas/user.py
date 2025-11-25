import uuid
from typing import Dict, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class UserBase(BaseModel):
    """Base model for user data."""

    user_info: Dict[str, str]


class UpdateProfileBase(UserBase):
    """Base model for user data."""

    class Config:
        from_attributes = True


class UserResponse(UpdateProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    is_ai: bool
