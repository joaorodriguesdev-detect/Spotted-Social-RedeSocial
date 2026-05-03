"""Users routes – FastAPI APIRouter.

Provides:
  • GET /users/search?q={query} – Busca ao vivo de usuários (ilike)
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from database import get_db
from dependencies import get_optional_user
from models import User, followers

router = APIRouter(prefix="/users", tags=["users"])


# ── Schema para resultado da busca ─────────────────────────────────────
class UserSearchResult(BaseModel):
    id: int
    username: str
    name: Optional[str] = None
    profile_pic: Optional[str] = None
    is_verified: bool = False
    followers_count: int = 0

    model_config = {"from_attributes": True}


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /users/search – Busca de usuários (LIKE)                       ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/search", response_model=List[UserSearchResult])
async def search_users(
    q: str = Query(..., min_length=1, max_length=100, description="Termo de busca"),
    limit: int = Query(10, ge=1, le=50, description="Máximo de resultados"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Busca usuários pelo username ou nome (case-insensitive).

    Usa ``ILIKE`` no SQLite/PostgreSQL para encontrar correspondências
    parciais. Retorna até ``limit`` resultados ordenados por username.
    """
    # ── Query com ILIKE no username e name ────────────────────────────
    term = f"%{q}%"
    stmt = (
        select(User)
        .where(
            User.username.ilike(term),
        )
        .order_by(User.username)
        .limit(limit)
    )
    result = await db.execute(stmt)
    users = result.scalars().all()

    # ── Monta resposta com contagem de seguidores ────────────────────
    response: List[UserSearchResult] = []
    for user in users:
        # Conta seguidores
        count_result = await db.execute(
            select(func.count()).select_from(followers).where(
                followers.c.followed_id == user.id
            )
        )
        followers_count = count_result.scalar() or 0

        response.append(
            UserSearchResult(
                id=user.id,
                username=user.username,
                name=user.name,
                profile_pic=user.profile_pic,
                is_verified=user.is_verified or False,
                followers_count=followers_count,
            )
        )

    return response


# ── Schema para listagem de seguidores/seguindo ────────────────────────
class UserBrief(BaseModel):
    id: int
    username: str
    name: Optional[str] = None
    profile_pic: Optional[str] = None
    is_verified: bool = False

    model_config = {"from_attributes": True}


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /users/{username}/followers – Seguidores                       ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/{username}/followers", response_model=List[UserBrief])
async def get_followers(
    username: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Retorna a lista de seguidores de um usuário."""
    # Busca o usuario
    user_result = await db.execute(
        select(User).where(User.username == username.lower().strip())
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    # Query: quem segue este usuário
    stmt = (
        select(User)
        .join(followers, followers.c.follower_id == User.id)
        .where(followers.c.followed_id == user.id)
        .order_by(User.username)
    )
    result = await db.execute(stmt)
    followers_list = result.scalars().all()

    return [
        UserBrief(
            id=u.id,
            username=u.username,
            name=u.name,
            profile_pic=u.profile_pic,
            is_verified=u.is_verified or False,
        )
        for u in followers_list
    ]


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /users/{username}/following – Quem o usuário segue             ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/{username}/following", response_model=List[UserBrief])
async def get_following(
    username: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Retorna a lista de usuários que este usuário segue."""
    user_result = await db.execute(
        select(User).where(User.username == username.lower().strip())
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    # Query: quem este usuário segue
    stmt = (
        select(User)
        .join(followers, followers.c.followed_id == User.id)
        .where(followers.c.follower_id == user.id)
        .order_by(User.username)
    )
    result = await db.execute(stmt)
    following_list = result.scalars().all()

    return [
        UserBrief(
            id=u.id,
            username=u.username,
            name=u.name,
            profile_pic=u.profile_pic,
            is_verified=u.is_verified or False,
        )
        for u in following_list
    ]
