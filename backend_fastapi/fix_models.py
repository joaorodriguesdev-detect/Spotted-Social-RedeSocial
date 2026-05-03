#!/usr/bin/env python
"""Script to fix all model files at once."""

import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

files = {}

# ── 1. __init__.py ─────────────────────────────────────────────────────
files["models/__init__.py"] = '''"""
Centraliza a importação de todos os modelos SQLAlchemy.

Ordem de importação:
  1. association tables (sem dependências)
  2. User (strings para Post, sem dependência direta)
  3. Post, Comment (strings para User, dependem de post_likes)
  4. Demais modelos (dependem de User)
"""

from .associations import followers, post_likes
from .user import User
from .post import Post, Comment
from .notification import Notification
from .message import Conversation, ConversationMember, DirectChatMessage, Message, MessageReaction
from .coupon import Coupon
from .mural import MuralPost
'''

# ── 2. user.py ─────────────────────────────────────────────────────────
files["models/user.py"] = '''"""User model and followers association table."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from database import Base
from utils import br_time

from .associations import followers, post_likes


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), nullable=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password = Column(String(120), nullable=False)  # bcrypt hash
    university = Column(String(50), nullable=True)
    bio = Column(String(150), default="Estudante no Spotted University")
    profile_pic = Column(String(200), nullable=True)
    social_link = Column(String(200), nullable=True, comment="Link social (Instagram, TikTok, etc.)")
    is_admin = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=br_time, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────
    posts = relationship("Post", back_populates="author", lazy="selectin")
    notifications = relationship("Notification", back_populates="receiver", lazy="selectin", cascade="all, delete-orphan")
    followed = relationship(
        "User",
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref="followers",
        lazy="selectin",
    )
    liked_posts = relationship("Post", secondary=post_likes, back_populates="liked_by", lazy="selectin")
    comments = relationship("Comment", back_populates="user", lazy="selectin")
    conversation_memberships = relationship("ConversationMember", back_populates="user", lazy="selectin")
    direct_messages_sent = relationship("DirectChatMessage", back_populates="sender", lazy="selectin")
    my_events = relationship("Event", back_populates="creator", lazy="selectin")
    mural_posts = relationship("MuralPost", back_populates="author", lazy="selectin")
    coupons = relationship("Coupon", back_populates="created_by", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"
'''

# ── 3. post.py ─────────────────────────────────────────────────────────
files["models/post.py"] = '''from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base
from utils import br_time
from .associations import post_likes


class Post(Base):
    __tablename__ = "post"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    media_url = Column(String(200), nullable=True)
    timestamp = Column(DateTime, default=br_time)
    likes = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    is_anonymous = Column(Boolean, default=False)

    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan", lazy="selectin")
    liked_by = relationship("User", secondary=post_likes, back_populates="liked_posts", lazy="selectin")


class Comment(Base):
    __tablename__ = "comment"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("post.id"), nullable=False)
    content = Column(String(200), nullable=False)
    username = Column(String(80), default="Anonimo")
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    timestamp = Column(DateTime, default=br_time)
    is_edited = Column(Boolean, default=False)

    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
'''

# ── 4. notification.py ─────────────────────────────────────────────────
files["models/notification.py"] = '''"""Notification model."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base
from utils import br_time


class Notification(Base):
    __tablename__ = "notification"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    sender_name = Column(String(80))
    action_type = Column(String(100))
    category = Column(String(50), default="general")
    post_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=br_time)

    receiver = relationship("User", back_populates="notifications")
'''

# ── 5. message.py ──────────────────────────────────────────────────────
files["models/message.py"] = '''"""Direct messaging models: Message, Conversation, ConversationMember, DirectChatMessage, MessageReaction."""

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
'''

# ── 6. mural.py ────────────────────────────────────────────────────────
files["models/mural.py"] = '''"""MuralPost model (classified ads / mural de avisos)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base
from utils import br_time


class MuralPost(Base):
    __tablename__ = "mural_post"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, default="Geral")
    contact_info = Column(String(200), nullable=False)
    timestamp = Column(DateTime, default=br_time)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    author = relationship("User", back_populates="mural_posts")
'''

# ── 7. event.py ────────────────────────────────────────────────────────
files["models/event.py"] = '''"""Event model."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base
from utils import br_time


class Event(Base):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    event_date = Column(String(50), nullable=False)
    location = Column(String(100), nullable=False)
    media_url = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=br_time)
    user_id = Column(Integer, ForeignKey("user.id"))

    creator = relationship("User", back_populates="my_events")
'''

# ── 8. audit.py ────────────────────────────────────────────────────────
files["models/audit.py"] = '''"""Audit Log model – tracks all admin moderation actions."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base
from utils import br_time


class AuditLog(Base):
    """Records admin actions for accountability and rollback."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("user.id"), nullable=False, comment="Admin who performed the action")
    action = Column(String(50), nullable=False, comment="Action type: ban_user, unban_user, delete_post, delete_mural, delete_coupon, approve_coupon")
    target_id = Column(Integer, nullable=True, comment="ID of the target resource")
    target_type = Column(String(50), nullable=False, comment="Resource type: user, post, mural, coupon, message")
    details = Column(Text, nullable=True, comment="Extra context (reason, description)")
    timestamp = Column(DateTime, default=br_time, nullable=False)

    admin = relationship("User", backref="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, admin={self.admin_id}, action='{self.action}')>"
'''


# ── Write all files ─────────────────────────────────────────────────────
for path, content in files.items():
    full_path = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ {path}")

# ── Clear __pycache__ ──────────────────────────────────────────────────
for root, dirs, files in os.walk(os.path.join(BASE, "models")):
    for d in dirs:
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))
            print(f"✓ Removed {os.path.join(root, d)}")

print("\n✅ Todos os arquivos foram corrigidos!")
