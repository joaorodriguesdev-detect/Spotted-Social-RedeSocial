from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from database import Base
from utils import br_time
from .associations import post_likes


class Post(Base):
    __tablename__ = "post"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    media_url = Column(String(200), nullable=True)
    media_urls = Column(JSON, nullable=True)
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
