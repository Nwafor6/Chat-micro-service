"""
User model for the chat service.
"""

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from .base import BaseModel as Base


class User(Base):
    """User model representing users.

    user_id: A string representing the unique user ID from the BildUp system.
    is_ai: A boolean indicating whether the user is an AI user, i.e if its bildup AI or a human user.
    user_info: A JSON field storing additional information about the user.
    These info are information from the bildup system.

    created_rooms: A relationship to the Room model representing rooms created by this user.
    rooms: A relationship to the Room model representing the chat rooms the user is a member of.
    messages: A relationship to the Message model representing the messages sent by the user.

    """

    __tablename__ = "users"

    user_id = sa.Column(sa.String, unique=True, nullable=False)
    is_ai = sa.Column(sa.Boolean, default=False)
    user_info = sa.Column(sa.JSON, nullable=True)

    # relationships
    created_rooms = relationship(
        "Room", foreign_keys="Room.created_by_user_id", back_populates="creator"
    )
    rooms = relationship("Room", secondary="room_members", back_populates="members")
    messages = relationship("Message", back_populates="user")
