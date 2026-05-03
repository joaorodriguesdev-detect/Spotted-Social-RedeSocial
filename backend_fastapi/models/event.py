"""Event model."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base
from utils import br_time
from .enums import EventCategory


class Event(Base):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    event_date = Column(String(50), nullable=False)
    location = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, default=EventCategory.OUTRO.value)
    media_url = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=br_time)
    user_id = Column(Integer, ForeignKey("user.id"))

    creator = relationship("User", back_populates="my_events")
