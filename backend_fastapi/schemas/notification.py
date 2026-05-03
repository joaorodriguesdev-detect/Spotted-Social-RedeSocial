"""Pydantic schemas for Notification model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """Schema for a single notification (list item)."""
    id: int
    user_id: int
    sender_name: Optional[str] = None
    action_type: Optional[str] = None
    category: str = "general"
    post_id: Optional[int] = None
    is_read: bool = False
    timestamp: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NotificationsListResponse(BaseModel):
    """Wrapper for the notification list endpoint."""
    items: list[NotificationResponse]
    unread_count: int
    total: int


class MarkReadResponse(BaseModel):
    """Response after marking a notification as read."""
    ok: bool = True
    message: str = "Notificação marcada como lida."
