"""Pydantic schemas for Direct Messages / Chat."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Message ─────────────────────────────────────────────────────────────
class MessageResponse(BaseModel):
    """A single message in the chat history."""
    id: int
    conversation_id: int
    sender_id: int
    content: str
    media_url: Optional[str] = None
    created_at: Optional[str] = None
    all_read: bool = False
    is_mine: bool = False  # client-side helper

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)


class SendMessageResponse(BaseModel):
    ok: bool = True
    message_id: int
    conversation_id: int
    delivered_online: bool = False


# ── History ─────────────────────────────────────────────────────────────
class ChatHistoryResponse(BaseModel):
    conversation_id: int
    other_user_id: int
    other_username: Optional[str] = None
    other_name: Optional[str] = None
    other_profile_pic: Optional[str] = None
    messages: list[dict[str, Any]] = []
    is_online: bool = False


# ── Conversation (list item) ────────────────────────────────────────────
class ConversationItem(BaseModel):
    conversation_id: int
    other_user_id: Optional[int] = None
    other_username: Optional[str] = None
    other_name: Optional[str] = None
    other_profile_pic: Optional[str] = None
    last_message: Optional[str] = None
    last_message_at: Optional[str] = None
    unread_count: int = 0
    is_online: bool = False


class ConversationListResponse(BaseModel):
    items: list[ConversationItem] = []
