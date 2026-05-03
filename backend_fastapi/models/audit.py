"""Audit Log model – tracks all admin moderation actions."""

from datetime import datetime

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
