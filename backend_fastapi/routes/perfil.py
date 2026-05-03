"""Perfil (Profile) routes – FastAPI APIRouter.

Provides: # No change here
  • GET  /api/perfil/{username}  – Dados públicos do perfil
  • PUT  /api/perfil/update      – Editar próprio perfil (bio, name, social_link)
  • PUT  /api/perfil/update-photo – Trocar foto de perfil

Migrated from routes/perfil.py with:
  • async def
  • Pydantic schemas (UserProfileResponse, UserUpdate)
  • JWT auth via get_current_user / get_optional_user
  • Dados agregados: bio, foto, seguidores, posts recentes, cupons ativos
"""

import uuid
from datetime import datetime # Added for sorting
from typing import Optional # No change here

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from dependencies import get_current_user, get_optional_user
from models import User, followers, Post, Coupon, post_likes, Comment # Import from models/__init__.py, including post_likes
from schemas.user import UserProfileResponse, UserUpdate
from schemas.cupons import CouponBrief
from schemas.post import PostResponse
from services.image_service import save_and_optimize_image
from services.security_service import sanitize_user_text
from config import settings

router = APIRouter(prefix="/api/perfil", tags=["perfil"])


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /api/perfil/{username} – Consulta pública do perfil             ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/{username}", response_model=UserProfileResponse)
async def get_profile(
    username: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Retorna os dados públicos do perfil de um usuário.

    Inclui:
      • Bio, nome, foto, link social
      • Contagem de seguidores / seguindo
      • Posts recentes do usuário (até 10)
      • Cupons ativos criados por ele

    O campo ``is_owner`` indica se o perfil pertence ao usuário logado.
    O campo ``is_following`` indica se o usuário logado segue este perfil.
    """
    # ── Busca o usuário pelo username ─────────────────────────────────
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.posts).selectinload(Post.comments),
            selectinload(User.coupons),
        )
        .where(User.username == username.lower().strip())
    )
    profile_user = result.scalar_one_or_none()

    if not profile_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    current_user_id = current_user.id if current_user else None
    is_owner = current_user_id is not None and current_user_id == profile_user.id

    # ── Contagens (via queries) ───────────────────────────────────────
    # followers: quantos seguem este usuário
    followers_result = await db.execute(
        select(func.count()).select_from(followers).where(
            followers.c.followed_id == profile_user.id
        )
    )
    followers_count = followers_result.scalar() or 0

    # following: quantos este usuário segue
    following_result = await db.execute(
        select(func.count()).select_from(followers).where(
            followers.c.follower_id == profile_user.id
        )
    )
    following_count = following_result.scalar() or 0

    # posts_count
    posts_result = await db.execute(
        select(func.count()).select_from(Post).where(Post.user_id == profile_user.id)
    )
    posts_count = posts_result.scalar() or 0

    # ── Segue? (usuário logado → perfil) ──────────────────────────────
    is_following = False
    if current_user_id and current_user_id != profile_user.id:
        follow_check_result = await db.execute(
            select(followers).where(
                followers.c.follower_id == current_user_id,
                followers.c.followed_id == profile_user.id,
            )
        )
        is_following = follow_check_result.first() is not None

    # ── Posts recentes (até 10) ────────────────────────────────────────
    # Filtra posts anônimos se o visitante não for o dono do perfil
    visible_posts = [
        p
        for p in (profile_user.posts or [])
        if not p.is_anonymous or is_owner
    ]

    recent_posts_raw = sorted(visible_posts, key=lambda p: p.timestamp, reverse=True)
    recent_posts_raw = recent_posts_raw[:10]

    recent_posts = []
    
    # Otimização para evitar N+1 queries de likes
    post_ids = [p.id for p in recent_posts_raw]
    user_likes = set()
    if current_user_id and post_ids:
        likes_result = await db.execute(
            select(post_likes.c.post_id).where(
                post_likes.c.user_id == current_user_id,
                post_likes.c.post_id.in_(post_ids)
            )
        )
        user_likes = {row[0] for row in likes_result}

    for post in recent_posts_raw:
        liked_by_me = post.id in user_likes

        recent_posts.append(
            PostResponse(
                id=post.id,
                content=post.content,
                media_url=post.media_url,
                media_urls=post.media_urls or [],
                timestamp=post.timestamp,
                likes=post.likes,
                user_id=post.user_id,
                is_anonymous=post.is_anonymous,
                liked_by_me=liked_by_me,
                author_username=profile_user.username,
                author_name=profile_user.name,
                author_profile_pic=profile_user.profile_pic,
                comment_count=len(post.comments) if post.comments else 0,
            ).model_dump()
        )

    # ── Cupons ativos criados por este usuário ────────────────────────
    active_coupons_raw = [
        c for c in (profile_user.coupons or [])
        if c.is_active
    ]
    active_coupons = [
        CouponBrief(
            id=c.id,
            code=c.code,
            title=c.title,
            discount_percent=c.discount_percent,
            is_active=c.is_active,
            current_uses=c.current_uses,
            max_uses=c.max_uses,
            expires_at=c.expires_at,
        ).model_dump()
        for c in active_coupons_raw
    ]

    # ── Monta resposta ────────────────────────────────────────────────
    return UserProfileResponse(
        id=profile_user.id,
        username=profile_user.username,
        name=profile_user.name,
        university=profile_user.university,
        bio=profile_user.bio,
        profile_pic=profile_user.profile_pic,
        social_link=profile_user.social_link,
        is_admin=profile_user.is_admin,
        is_verified=profile_user.is_verified,
        created_at=profile_user.created_at,
        followers_count=followers_count,
        following_count=following_count,
        posts_count=posts_count,
        recent_posts=recent_posts,
        active_coupons=active_coupons,
        is_owner=is_owner,
        is_following=is_following,
    )


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PUT /api/perfil/update – Editar perfil (FormData: name + bio + foto)║
# ╚══════════════════════════════════════════════════════════════════════╝
#
# ATENÇÃO: Usamos Form(...) e File(...) em vez de UserUpdateSchema (JSON)
# porque o frontend envia multipart/form-data (FormData) para permitir
# o upload opcional da foto de perfil junto com os campos de texto.
#
# FastAPI NÃO consegue misturar JSON body + File no mesmo PUT. Por isso
# cada campo de texto é recebido como Form() individual.

@router.put("/update", response_model=UserProfileResponse)
async def update_profile(
    name: Optional[str] = Form(None, max_length=80),
    bio: Optional[str] = Form(None, max_length=150),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza perfil + opcionalmente foto em UMA chamada FormData.

    - name (Form): novo nome
    - bio  (Form): nova bio
    - file (File): nova foto de perfil (JPEG/PNG/WebP/GIF)
    """
    # 1. Atualiza campos de texto
    if name is not None:
        current_user.name = sanitize_user_text(name, max_len=80)
    if bio is not None:
        current_user.bio = sanitize_user_text(bio, max_len=150)

    # 2. Se tiver foto, processa e salva
    if file is not None and file.filename:
        allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato nao permitido. Use JPEG, PNG, WebP ou GIF.",
            )

        unique_name = f"profile_{current_user.id}_{uuid.uuid4().hex[:8]}"
        result = await save_and_optimize_image(
            file=file,
            filename=unique_name,
            upload_folder=settings.UPLOAD_FOLDER,
            max_size=(600, 600),
            quality=80,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao processar a imagem.",
            )

        current_user.profile_pic = result

    await db.flush()

    return await get_profile(username=current_user.username, db=db, current_user=current_user)
