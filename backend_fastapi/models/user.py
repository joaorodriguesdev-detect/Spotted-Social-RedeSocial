"""User model – PostgreSQL."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base
from utils import br_time

from .associations import followers, post_likes


class User(Base):
    __tablename__ = "user"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(80), nullable=True)
    username      = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(120), nullable=False)
    university    = Column(String(50), nullable=True)
    bio           = Column(Text, default="Estudante no Spotted University")
    profile_pic   = Column(String(200), nullable=True)
    social_link   = Column(String(200), nullable=True)
    is_admin      = Column(Boolean, default=False)
    is_verified   = Column(Boolean, default=False)
    is_banned     = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=br_time, nullable=True)

    # ── Relationships ────────────────────────────────────────────────
    posts        = relationship("Post",        back_populates="author",            lazy="selectin")
    notifications = relationship("Notification", back_populates="receiver",        lazy="selectin", cascade="all, delete-orphan")
    followed     = relationship(
        "User",
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref="followers",
        lazy="selectin",
    )
    liked_posts  = relationship("Post",        secondary=post_likes,               back_populates="liked_by", lazy="selectin")
    comments     = relationship("Comment",     back_populates="user",             lazy="selectin")
    conversation_memberships = relationship("ConversationMember", back_populates="user", lazy="selectin")
    direct_messages_sent     = relationship("DirectChatMessage",  back_populates="sender", lazy="selectin")
    my_events    = relationship("Event",       back_populates="creator",          lazy="selectin")
    mural_posts  = relationship("MuralPost",   back_populates="author",           lazy="selectin")
    coupons      = relationship("Coupon",      back_populates="created_by",       lazy="selectin")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username}>"
