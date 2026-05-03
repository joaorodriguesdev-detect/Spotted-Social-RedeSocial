"""Notifications routes – FastAPI APIRouter.

Provides:
  • GET    /api/notifications           – Listar notificações do usuário logado
  • PATCH  /api/notifications/{id}/read – Marcar uma como lida
  • PATCH  /api/notifications/read-all  – Marcar todas como lidas

The actual creation of notifications is already integrated into:
  • routes/social.py   → create_notification on follow
  • routes/mural.py    → Notification on recado / mural post
  • routes/feed.py     → Notification on like / comment

Migrated from routes/notifications.py with:
  • async def
  • Pydantic schemas
  • JWT auth via get_current_user
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db # Assuming get_db is in database.py
from dependencies import get_current_user # Assuming this is in dependencies.py
from models import Notification, User # Import from models/__init__.py
from schemas.notification import (
    MarkReadResponse,
    NotificationResponse,
    NotificationsListResponse,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /api/notifications – Listar notificações                        ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/", response_model=NotificationsListResponse)
async def list_notifications(
    skip: int = Query(0, ge=0, description="Saltar registros"),
    limit: int = Query(30, ge=1, le=100, description="Limite por página"),
    unread_only: bool = Query(False, description="Filtrar apenas não lidas"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista as notificações do usuário logado, das mais recentes para as mais antigas.

    Retorna:
      - items: lista de notificações
      - unread_count: total de não lidas (do usuário)
      - total: total de notificações do usuário
    """
    # ── Base query ────────────────────────────────────────────────────
    query = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.timestamp.desc(), Notification.id.desc())
    )

    if unread_only:
        query = query.where(Notification.is_read.is_(False))

    # ── Paginação ─────────────────────────────────────────────────────
    result = await db.execute(query.offset(skip).limit(limit))
    notifications = result.scalars().all()

    # ── Contagens ─────────────────────────────────────────────────────
    total_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id
        )
    )
    total = total_result.scalar() or 0

    unread_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
    )
    unread_count = unread_result.scalar() or 0

    # ── Monta resposta ────────────────────────────────────────────────
    items = [
        NotificationResponse.model_validate(n)
        for n in notifications
    ]

    return NotificationsListResponse(
        items=items,
        unread_count=unread_count,
        total=total,
    )


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PATCH /api/notifications/{id}/read – Marcar uma como lida           ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.patch("/{notification_id}/read", response_model=MarkReadResponse)
async def mark_as_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marca uma notificação específica como lida.

    Só o dono da notificação pode marcá-la como lida.
    """
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()

    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificação não encontrada.",
        )

    notif.is_read = True
    await db.flush()

    return MarkReadResponse()


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PATCH /api/notifications/read-all – Marcar todas como lidas         ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.patch("/read-all", response_model=MarkReadResponse)
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marca todas as notificações não lidas do usuário como lidas."""
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.flush()

    return MarkReadResponse(message="Todas as notificações foram marcadas como lidas.")


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /api/notifications/unread-count – Contagem rápida               ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/unread-count", response_model=dict)
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna apenas a contagem de notificações não lidas.

    Útil para o badge do frontend (sininho) sem carregar a lista toda.
    """
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
    )
    count = result.scalar() or 0

    return {"unread_count": count}
