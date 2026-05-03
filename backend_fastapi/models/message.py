"""Direct messaging models: Message, Conversation, ConversationMember, DirectChatMessage, MessageReaction."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base
from utils import br_time


class Message(Base):
    """Legacy message (recados no mural)."""
    __tablename__ = "message"

    id = Column(Integer, primary_key=True, index=True)
    receiver_id = Column(Integer, ForeignKey("user.id"))
    sender_name = Column(String(80))
    content = Column(String(500), nullable=False)
    timestamp = Column(DateTime, default=br_time)


class Conversation(Base):
    __tablename__ = "conversation"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(80), unique=True, nullable=True)
    title = Column(String(80), nullable=True)
    is_group = Column(Boolean, default=False, nullable=False)
    group_photo = Column(String(200), nullable=True)
    pinned_message_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=br_time, nullable=False)

    members = relationship("ConversationMember", back_populates="conversation", lazy="selectin", cascade="all, delete-orphan")
    messages = relationship("DirectChatMessage", back_populates="conversation", lazy="selectin", cascade="all, delete-orphan")


class ConversationMember(Base):
    __tablename__ = "conversation_member"
    __table_args__ = (UniqueConstraint("conversation_id", "user_id", name="uq_conversation_member"),)

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversation.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    last_read_message_id = Column(Integer, nullable=True)
    joined_at = Column(DateTime, default=br_time, nullable=False)

    conversation = relationship("Conversation", back_populates="members")
    user = relationship("User", back_populates="conversation_memberships")


class DirectChatMessage(Base):
    __tablename__ = "direct_chat_message"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversation.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    content = Column(String(500), nullable=False)
    media_url = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=br_time, nullable=False)
    all_read = Column(Boolean, default=False, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", back_populates="direct_messages_sent")


class MessageReaction(Base):
    __tablename__ = "message_reaction"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_message_reaction"),)

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("direct_chat_message.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    reaction = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=br_time)
