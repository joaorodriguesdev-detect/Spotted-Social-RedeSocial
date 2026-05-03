"""Eventos – FastAPI APIRouter.

Provides:
  • GET    /api/events          – Listar eventos (paginado)
  • GET    /api/events/{id}     – Detalhes de um evento
  • POST   /api/events          – Criar evento (autenticado)
  • PATCH  /api/events/{id}     – Atualizar evento (autor/admin)
  • DELETE /api/events/{id}     – Deletar evento (autor/admin)
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import get_current_user
from models import Event, User
from models.enums import EventCategory
from utils import br_time

from schemas.event import (
    EventCreate,
    EventListResponse,
    EventResponse,
    EventUpdate,
)
from services.security_service import sanitize_user_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])


async def _build_event_response(
    event: Event,
    db: AsyncSession,
) -> EventResponse:
    """Convert an Event ORM object into an EventResponse."""
    creator_username = None
    creator_name = None
    creator_profile_pic = None
    if event.creator:
        creator_username = event.creator.username
        creator_name = event.creator.name
        creator_profile_pic = event.creator.profile_pic

    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        event_date=event.event_date,
        location=event.location,
        category=event.category,
        media_url=event.media_url,
        created_at=event.created_at,
        user_id=event.user_id,
        creator_username=creator_username,
        creator_name=creator_name,
        creator_profile_pic=creator_profile_pic,
    )


# ── GET /api/events ─────────────────────────────────────────────────────
@router.get("/", response_model=EventListResponse)
async def list_events(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(12, ge=1, le=50, description="Itens por página"),
    user_id: Optional[int] = Query(None, description="Filtrar por autor do evento"),
    category: Optional[EventCategory] = Query(None, description="Filtrar por categoria"),
    search: Optional[str] = Query(None, max_length=80, description="Buscar no título ou descrição"),
    db: AsyncSession = Depends(get_db),
):
    """List events with pagination, optional category filter, and search."""
    query = (
        select(Event)
        .options(selectinload(Event.creator))
        .order_by(Event.event_date.desc(), Event.created_at.desc())
    )

    if user_id is not None:
        query = query.where(Event.user_id == user_id)

    if category:
        query = query.where(Event.category == category.value)

    if search:
        safe_pattern = f"%{search}%"
        query = query.where(
            (Event.title.ilike(safe_pattern))
            | (Event.description.ilike(safe_pattern))
        )

    # Count total
    count_query = select(Event.id)
    if user_id is not None:
        count_query = count_query.where(Event.user_id == user_id)
    if category:
        count_query = count_query.where(Event.category == category.value)
    if search:
        safe_pattern = f"%{search}%"
        count_query = count_query.where(
            (Event.title.ilike(safe_pattern))
            | (Event.description.ilike(safe_pattern))
        )
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())

    # Pagination
    offset = (page - 1) * per_page
    result = await db.execute(query.offset(offset).limit(per_page))
    events = result.scalars().all()

    items = [await _build_event_response(e, db) for e in events]

    return EventListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page,
    )


# ── GET /api/events/{event_id} ──────────────────────────────────────────
@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single event by ID."""
    result = await db.execute(
        select(Event).options(selectinload(Event.creator)).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")

    return await _build_event_response(event, db)


# ── POST /api/events ────────────────────────────────────────────────────
@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new event."""
    title = sanitize_user_text(payload.title, max_len=100)
    description = sanitize_user_text(payload.description, max_len=2000)
    location = sanitize_user_text(payload.location, max_len=100)

    event = Event(
        title=title,
        description=description,
        event_date=payload.event_date,
        location=location,
        category=payload.category.value if payload.category else EventCategory.OUTRO.value,
        media_url=payload.media_url,
        user_id=current_user.id,
        created_at=br_time(),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    # Reload with creator
    result = await db.execute(
        select(Event).options(selectinload(Event.creator)).where(Event.id == event.id)
    )
    event = result.scalar_one()

    return await _build_event_response(event, db)


# ── PATCH /api/events/{event_id} ────────────────────────────────────────
@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    payload: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an event (author or admin only)."""
    result = await db.execute(
        select(Event).options(selectinload(Event.creator)).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")

    if event.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar este evento.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            if field in ("title", "description", "location"):
                value = sanitize_user_text(value)
            if field == "category" and isinstance(value, EventCategory):
                value = value.value
            setattr(event, field, value)

    await db.commit()
    await db.refresh(event)

    # Reload with creator
    result = await db.execute(
        select(Event).options(selectinload(Event.creator)).where(Event.id == event.id)
    )
    event = result.scalar_one()

    return await _build_event_response(event, db)


# ── DELETE /api/events/{event_id} ───────────────────────────────────────
@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an event (author or admin only)."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")

    if event.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Você não tem permissão para deletar este evento.")

    await db.delete(event)
    await db.commit()
