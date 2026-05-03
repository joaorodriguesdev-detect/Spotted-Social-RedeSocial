"""Pydantic schemas for User model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Public Profile Response (completo) ─────────────────────────────────
class UserProfileResponse(BaseModel):
    """Schema for GET /api/perfil/{username}."""
    id: int
    username: str
    name: Optional[str] = None
    university: Optional[str] = None
    bio: Optional[str] = None
    profile_pic: Optional[str] = None
    social_link: Optional[str] = None
    is_admin: bool = False
    is_verified: bool = False
    created_at: Optional[datetime] = None

    # Estatísticas
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0

    # Conteúdo recente
    recent_posts: list = []
    active_coupons: list = []

    # Se o perfil é do próprio usuário logado
    is_owner: bool = False
    is_following: bool = False

    model_config = {"from_attributes": True}


class UserBrief(BaseModel):
    """Versão resumida para listas."""
    id: int
    username: str
    name: Optional[str] = None
    profile_pic: Optional[str] = None
    is_verified: bool = False

    model_config = {"from_attributes": True}


# ── Edição do Perfil ───────────────────────────────────────────────────
class UserUpdate(BaseModel):
    """Schema for PUT /api/perfil/update."""
    name: Optional[str] = Field(None, max_length=80)
    university: Optional[str] = Field(None, max_length=50)
    bio: Optional[str] = Field(None, max_length=150)
    social_link: Optional[str] = Field(None, max_length=200)
