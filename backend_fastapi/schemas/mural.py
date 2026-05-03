"""Pydantic schemas for Mural de Recados / MuralPost (classified ads)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from models.enums import MuralCategory


# ── Allowed categories (from enum) ────────────────────────────────────
ALLOWED_CATEGORIES = [c.value for c in MuralCategory]


def _coerce_mural_category(v: object) -> MuralCategory:
    """Converte string case-insensitive e sem acentos para MuralCategory."""
    if isinstance(v, MuralCategory):
        return v
    if isinstance(v, str):
        v_normalized = (
            v.lower()
            .replace("ç", "c")
            .replace("é", "e").replace("ê", "e")
            .replace("á", "a").replace("ã", "a").replace("â", "a")
            .replace("í", "i").replace("ó", "o").replace("ô", "o")
            .replace("ú", "u").replace("ü", "u")
        )
        for member in MuralCategory:
            member_normalized = (
                member.value.lower()
                .replace("ç", "c")
                .replace("é", "e").replace("ê", "e")
                .replace("á", "a").replace("ã", "a").replace("â", "a")
                .replace("í", "i").replace("ó", "o").replace("ô", "o")
                .replace("ú", "u").replace("ü", "u")
            )
            if member_normalized == v_normalized:
                return member
    raise ValueError(f"Categoria inválida: {v}")


# ── Request Schemas ────────────────────────────────────────────────────
class MuralPostCreate(BaseModel):
    """Schema for creating a new mural post (classified ad)."""
    title: str = Field(..., min_length=5, max_length=150)
    content: str = Field(..., min_length=10, max_length=2000)
    category: MuralCategory = MuralCategory.GERAL
    contact_info: str = Field(..., min_length=5, max_length=200)

    @field_validator("category", mode="before")
    @classmethod
    def category_case_insensitive(cls, v: object) -> MuralCategory:
        return _coerce_mural_category(v)


class MuralPostUpdate(BaseModel):
    """Schema for updating a mural post."""
    title: Optional[str] = Field(None, min_length=5, max_length=150)
    content: Optional[str] = Field(None, min_length=10, max_length=2000)
    category: Optional[str] = Field(None, max_length=50)
    contact_info: Optional[str] = Field(None, min_length=5, max_length=200)

    @field_validator("category", mode="before")
    @classmethod
    def category_case_insensitive(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        coerced = _coerce_mural_category(v)
        return coerced.value if coerced else None


# ── Response Schemas ───────────────────────────────────────────────────
class MuralPostResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    contact_info: str
    timestamp: Optional[datetime] = None
    user_id: int
    author_username: Optional[str] = None
    author_name: Optional[str] = None
    author_pic: Optional[str] = None

    model_config = {"from_attributes": True}


class MuralPostBrief(BaseModel):
    """Short version for list views."""
    id: int
    title: str
    category: str
    preview: str
    timestamp: Optional[datetime] = None
    author_username: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Recado (profile wall message) Schemas ──────────────────────────────
class RecadoCreate(BaseModel):
    """Schema for leaving a message on someone's profile wall."""
    content: str = Field(..., min_length=1, max_length=500)
    anon_mode: bool = False


class RecadoResponse(BaseModel):
    id: int
    receiver_id: int
    sender_name: str
    content: str
    timestamp: Optional[datetime] = None

    model_config = {"from_attributes": True}
