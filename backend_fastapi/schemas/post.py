"""Pydantic schemas for Post / Comment models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PostCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    is_anonymous: bool = False
    # media handling is done via upload endpoint


class PostResponse(BaseModel):
    id: int
    content: str
    media_url: Optional[str] = None
    media_urls: Optional[list[str]] = []
    timestamp: Optional[datetime] = None
    likes: int = 0
    user_id: Optional[int] = None
    is_anonymous: bool = False
    liked_by_me: bool = False
    author_username: Optional[str] = None
    author_name: Optional[str] = None
    author_profile_pic: Optional[str] = None
    comment_count: int = 0

    model_config = {"from_attributes": True}


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)


class CommentResponse(BaseModel):
    id: int
    post_id: int
    content: str
    username: str
    user_id: Optional[int] = None
    timestamp: Optional[datetime] = None
    is_edited: bool = False

    model_config = {"from_attributes": True}
