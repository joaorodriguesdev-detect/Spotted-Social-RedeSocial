"""Pydantic schemas for Event model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from models.enums import EventCategory


def _coerce_category(v: object) -> EventCategory:
    """Converte string case-insensitive para EventCategory."""
    if isinstance(v, EventCategory):
        return v
    if isinstance(v, str):
        for member in EventCategory:
            if member.value.lower() == v.lower():
                return member
    raise ValueError(f"Categoria inválida: {v}")


class EventCreate(BaseModel):
    """Schema for creating a new event."""
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=2000)
    event_date: str = Field(..., description="Data do evento (ex: 2025-12-25 20:00)")
    location: str = Field(..., min_length=3, max_length=100)
    category: EventCategory = EventCategory.OUTRO
    media_url: Optional[str] = None

    @field_validator("category", mode="before")
    @classmethod
    def category_case_insensitive(cls, v: object) -> EventCategory:
        return _coerce_category(v)


class EventUpdate(BaseModel):
    """Schema for updating an event."""
    title: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    event_date: Optional[str] = None
    location: Optional[str] = Field(None, min_length=3, max_length=100)
    category: Optional[EventCategory] = None
    media_url: Optional[str] = None

    @field_validator("category", mode="before")
    @classmethod
    def category_case_insensitive(cls, v: object) -> Optional[EventCategory]:
        if v is None:
            return None
        return _coerce_category(v)


class EventResponse(BaseModel):
    """Schema for event response."""
    id: int
    title: str
    description: str
    event_date: str
    location: str
    category: str = "Outro"
    media_url: Optional[str] = None
    created_at: Optional[datetime] = None
    user_id: Optional[int] = None
    creator_username: Optional[str] = None
    creator_name: Optional[str] = None
    creator_profile_pic: Optional[str] = None

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    """Wrapper for paginated event list."""
    items: list[EventResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
