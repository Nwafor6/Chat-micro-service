"""
Chat model for the chat service.
"""

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from .base import BaseModel as Base
from .enums import MessageType, RoomType
from .type_decorators import GUID

room_members_table = sa.Table(
    "room_members",
    Base.metadata,
    sa.Column("room_id", GUID(), sa.ForeignKey("rooms.id"), primary_key=True),
    sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), primary_key=True),
)


class Room(Base):
    """Room model representing chat rooms.

    name: A string representing the name of the room.
    room_type: An enum representing the type of room (e.g., "public", "private").
    description: A string representing the description of the room.
    is_locked: A boolean indicating whether the room is locked.
    created_by_user_id: A GUID representing the user ID of the room creator.

    creator: A relationship to the User model representing the creator of the room.
    members: A relationship to the User model representing the members of the room.
    messages: A relationship to the Message model representing the messages in the room.
    classroom: A relationship to the Classroom model representing the classroom associated with the room.

    """

    __tablename__ = "rooms"

    name = sa.Column(sa.String, nullable=True)
    room_type = sa.Column(sa.Enum(RoomType), nullable=False, default=RoomType.PUBLIC)
    description = sa.Column(sa.Text, nullable=True)
    is_locked = sa.Column(sa.Boolean, default=False)
    bildup_classroom_id = sa.Column(GUID(), nullable=True)
    created_by_user_id = sa.Column(GUID(), sa.ForeignKey("users.id"), nullable=False)

    # Relationships
    creator = relationship(
        "User", foreign_keys=[created_by_user_id], back_populates="created_rooms"
    )
    members = relationship("User", secondary=room_members_table, back_populates="rooms")
    messages = relationship(
        "Message", back_populates="room", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Transient attribute for last message (not persisted to DB)
        self.last_message = None
        self.member_count = 0
        self.last_message_sender_info = {}
        # self.members_list = []
        self.room_custom_name = {}
        

    class Config:
        from_attributes = True

    # @classmethod
    # def from_orm(cls, obj):
    #     # Map _members_list to members for serialization
    #     data = super().from_orm(obj)
    #     if hasattr(obj, 'members_list'):
    #         data.members = obj.members_list
    #     return data


class Message(Base):
    """Message model representing chat messages.

    room_id: A GUID representing the ID of the room the message belongs to.
    user_id: A GUID representing the ID of the user who sent the message.
    content: A text field representing the content of the message.
    message_type: An enum representing the type of message (e.g., "text", "image").

    room: A relationship to the Room model representing the room the message belongs to.
    user: A relationship to the User model representing the user who sent the message.
    replies: A relationship to the Message model representing replies to this message.
    reply_to: A relationship to the Message model representing the message this message is replying to.

    """

    __tablename__ = "messages"

    room_id = sa.Column(GUID(), sa.ForeignKey("rooms.id"), nullable=False)
    user_id = sa.Column(GUID(), sa.ForeignKey("users.id"), nullable=False)
    content = sa.Column(sa.Text, nullable=False)
    message_type = sa.Column(
        sa.Enum(MessageType), nullable=False, default=MessageType.TEXT
    )
    reply_to_id = sa.Column(GUID(), sa.ForeignKey("messages.id"), nullable=True)

    # relationships
    room = relationship("Room", back_populates="messages")
    user = relationship("User", back_populates="messages")
    replies = relationship(
        "Message", back_populates="reply_to", remote_side="Message.reply_to_id"
    )
    reply_to = relationship(
        "Message", remote_side="Message.id", back_populates="replies"
    )
