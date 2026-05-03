"""Social routes – Follow / Unfollow system.

Provides:
  • POST   /api/follow/{user_id}       – Seguir um usuário
  • DELETE /api/unfollow/{user_id}     – Deixar de seguir
  • GET    /api/follow/status/{user_id} – Verificar se segue

Migrated from routes/perfil.py → seguir() with:
  • async def
  • JWT auth (get_current_user)
  • Validação: não pode seguir a si mesmo
  • SQLAlchemy async na tabela de associação ``followers``
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db # No change here
from dependencies import get_current_user # No change here
from models import User, followers # Import from models/__init__.py
from services.notification_service import create_notification

router = APIRouter(prefix="/api", tags=["social"])


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  POST /api/follow/{user_id} – Seguir                                 ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.post("/follow/{user_id}", response_model=dict)
async def follow_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Seguir um usuário.

    Regras:
      • Não pode seguir a si mesmo.
      • O alvo deve existir.
      • Se já segue, retorna sucesso (idempotente).
    """
    # ── Validação: não pode seguir a si mesmo ─────────────────────────
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Você não pode seguir a si mesmo.",
        )

    # ── Verificar se o alvo existe ────────────────────────────────────
    target_result = await db.execute(select(User).where(User.id == user_id))
    target_user = target_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    # ── Verificar se já segue ─────────────────────────────────────────
    follow_check = await db.execute(
        select(followers).where(
            and_(
                followers.c.follower_id == current_user.id,
                followers.c.followed_id == user_id,
            )
        )
    )
    already_following = follow_check.first() is not None

    if already_following:
        return {
            "ok": True,
            "following": True,
            "message": f"Você já segue @{target_user.username}.",
        }

    # ── Inserir na tabela de associação ───────────────────────────────
    await db.execute(
        followers.insert().values(
            follower_id=current_user.id,
            followed_id=user_id,
        )
    )

    # ── Notificar o usuário seguido ───────────────────────────────────
    try:
        await create_notification(
            user_id=user_id,
            sender_name=current_user.name or current_user.username,
            action_type="começou a te seguir",
            db=db,
        )
    except Exception:
        # Notificação não crítica
        pass

    # O commit é feito automaticamente pelo get_db dependency

    return {
        "ok": True,
        "following": True,
        "message": f"Agora você segue @{target_user.username}.",
    }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DELETE /api/unfollow/{user_id} – Deixar de seguir                   ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.delete("/unfollow/{user_id}", response_model=dict)
async def unfollow_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deixar de seguir um usuário.

    Regras:
      • Não pode deixar de seguir a si mesmo.
      • Se não segue, retorna erro 404.
    """
    # ── Validação ─────────────────────────────────────────────────────
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Você não pode deixar de seguir a si mesmo.",
        )

    target_result = await db.execute(select(User).where(User.id == user_id))
    target_user = target_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    # ── Verificar se segue ────────────────────────────────────────────
    follow_check = await db.execute(
        select(followers).where(
            and_(
                followers.c.follower_id == current_user.id,
                followers.c.followed_id == user_id,
            )
        )
    )
    existing = follow_check.first()

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Você não segue este usuário.",
        )

    # ── Remover associação ────────────────────────────────────────────
    await db.execute(
        followers.delete().where(
            and_(
                followers.c.follower_id == current_user.id,
                followers.c.followed_id == user_id,
            )
        )
    )
    # O commit é feito automaticamente pelo get_db dependency

    return {
        "ok": True,
        "following": False,
        "message": f"Você deixou de seguir @{target_user.username}.",
    }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /api/follow/status/{user_id} – Verificar status                 ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/follow/status/{user_id}", response_model=dict)
async def follow_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verifica se o usuário logado segue o usuário alvo."""
    if user_id == current_user.id:
        return {"is_following": False, "is_self": True}

    check = await db.execute(
        select(followers).where(
            and_(
                followers.c.follower_id == current_user.id,
                followers.c.followed_id == user_id,
            )
        )
    )
    is_following = check.first() is not None

    return {"is_following": is_following, "is_self": False}


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /api/follow/counts/{user_id} – Contagem                         ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/follow/counts/{user_id}", response_model=dict)
async def follow_counts(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Retorna quantos seguidores e quantos o usuário segue."""
    # Seguidores (quem segue o user_id)
    followers_count = await db.execute(
        select(followers.c.follower_id).where(
            followers.c.followed_id == user_id
        )
    )
    followers_total = len(followers_count.all())

    # Seguindo (quem o user_id segue)
    following_count = await db.execute(
        select(followers.c.followed_id).where(
            followers.c.follower_id == user_id
        )
    )
    following_total = len(following_count.all())

    return {
        "user_id": user_id,
        "followers": followers_total,
        "following": following_total,
    }
