"""Coupon / Cupom model – novo recurso para emissão de cupons promocionais."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base # Assuming Base is defined in database.py
from utils import br_time # Centralized import


class Coupon(Base):
    """Represents a promotional coupon that can be created and used."""

    __tablename__ = "coupon"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True, comment="Código único do cupom (ex: SPOTTED10)")
    title = Column(String(120), nullable=False, comment="Título / nome do cupom")
    description = Column(Text, nullable=True, comment="Descrição detalhada")
    discount_percent = Column(Integer, default=0, comment="Percentual de desconto (0-100)")
    max_uses = Column(Integer, default=0, comment="0 = ilimitado")
    current_uses = Column(Integer, default=0, comment="Quantas vezes foi usado")
    is_active = Column(Boolean, default=True, comment="Se o cupom está ativo")
    expires_at = Column(DateTime, nullable=True, comment="Data de expiração")
    created_at = Column(DateTime, default=br_time, nullable=False)
    updated_at = Column(DateTime, default=br_time, onupdate=br_time, nullable=False)

    # ── Creator (using string reference for User) ─────────────────────
    created_by_id = Column(Integer, ForeignKey("user.id"), nullable=False, comment="Quem criou o cupom") # ForeignKey uses string
    created_by = relationship("User", back_populates="coupons") # relationship uses string

    def __repr__(self) -> str:
        return f"<Coupon(id={self.id}, code='{self.code}', active={self.is_active})>"
