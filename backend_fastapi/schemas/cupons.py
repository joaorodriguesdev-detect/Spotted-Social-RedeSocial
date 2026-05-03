"""Pydantic schemas for Coupon (Cupom) CRUD operations."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Request Schemas ─────────────────────────────────────────────────────
class CouponCreate(BaseModel):
    """Schema for creating a new coupon."""

    code: str = Field(..., min_length=3, max_length=50, description="Código único do cupom")
    title: str = Field(..., min_length=3, max_length=120, description="Título do cupom")
    description: Optional[str] = Field(None, max_length=1000, description="Descrição detalhada")
    discount_percent: int = Field(0, ge=0, le=100, description="Percentual de desconto (0-100)")
    max_uses: int = Field(0, ge=0, description="0 = ilimitado")
    expires_at: Optional[datetime] = Field(None, description="Data de expiração (ISO 8601)")

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        return v.strip().upper()


class CouponUpdate(BaseModel):
    """Schema for updating an existing coupon (partial)."""

    title: Optional[str] = Field(None, min_length=3, max_length=120)
    description: Optional[str] = Field(None, max_length=1000)
    discount_percent: Optional[int] = Field(None, ge=0, le=100)
    max_uses: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class CouponUseRequest(BaseModel):
    """Schema when a user tries to redeem/use a coupon."""

    code: str = Field(..., min_length=1, max_length=50)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        return v.strip().upper()


# ── Response Schemas ────────────────────────────────────────────────────
class CouponResponse(BaseModel):
    """Schema returned when reading a coupon."""

    id: int
    code: str
    title: str
    description: Optional[str] = None
    discount_percent: int
    max_uses: int
    current_uses: int
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by_id: int

    model_config = {"from_attributes": True}


class CouponBrief(BaseModel):
    """Short summary for listing coupons."""

    id: int
    code: str
    title: str
    discount_percent: int
    is_active: bool
    current_uses: int
    max_uses: int
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
