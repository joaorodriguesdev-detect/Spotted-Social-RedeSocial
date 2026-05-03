"""Notification model."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base
from utils import br_time
from .enums import NotificationCategory


class Notification(Base):
    __tablename__ = "notification"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    sender_name = Column(String(80))
    action_type = Column(String(100))
    category = Column(String(50), default=NotificationCategory.GENERAL.value)
    post_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=br_time)

    receiver = relationship("User", back_populates="notifications")
