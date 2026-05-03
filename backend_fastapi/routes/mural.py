"""Mural de Recados – FastAPI APIRouter.

Includes:
  • MuralPost CRUD (classified ads) – from original routes/mural.py
  • Recados (profile wall messages) – from original routes/perfil.py (enviar_recado)

Migrated patterns:
  • async def everywhere
  • Pydantic schemas for validation (instead of request.form)
  • get_current_user dependency (JWT) instead of flask.session
  • Direct dict/Model returns instead of jsonify
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db # No change here
from dependencies import get_current_user, get_optional_user # No change here
from models import MuralPost, Message, Notification, User # Import from models/__init__.py
from utils import br_time # Centralized import

from schemas.mural import (
    ALLOWED_CATEGORIES,
    MuralPostBrief,
    MuralPostCreate,
    MuralPostResponse,
    MuralPostUpdate,
    RecadoCreate,
    RecadoResponse,
)
from services.security_service import sanitize_user_text, build_contains_pattern

router = APIRouter(prefix="/api/mural", tags=["mural"])


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  MURAL POSTS (Classified Ads) – CRUD                                ║
# ╚══════════════════════════════════════════════════════════════════════╝

# ── GET /api/mural ─────────────────────────────────────────────────────
@router.get("/", response_model=dict)
async def list_mural_posts(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(12, ge=1, le=50, description="Itens por página"),
    category: Optional[str] = Query(None, description="Filtrar por categoria"),
    search: Optional[str] = Query(None, max_length=80, description="Buscar no título ou conteúdo"),
    db: AsyncSession = Depends(get_db),
):
    """List mural posts with pagination, category filter, and search.
    
    Public endpoint - nao requer autenticacao.
    """
    query = select(MuralPost).options(selectinload(MuralPost.author)).order_by(MuralPost.timestamp.desc())

    # Category filter
    if category and category in ALLOWED_CATEGORIES:
        query = query.where(MuralPost.category == category)

    # Search filter
    if search:
        safe_pattern = build_contains_pattern(search)
        query = query.where(
            (MuralPost.title.ilike(safe_pattern, escape="\\"))
            | (MuralPost.content.ilike(safe_pattern, escape="\\"))
        )

    # Pagination
    offset = (page - 1) * per_page
    total_query = select(MuralPost.id)  # count is done client-side via len
    result = await db.execute(query.offset(offset).limit(per_page))
    posts = result.scalars().all()

    # Count total for pagination info
    count_result = await db.execute(select(MuralPost.id))
    total = len(count_result.scalars().all())

    # Build response list with author info
    items = []
    for post in posts:
        post_data = MuralPostResponse.model_validate(post)
        if post.author:
            post_data.author_username = post.author.username
            post_data.author_name = post.author.name
            post_data.author_pic = post.author.profile_pic
        items.append(post_data)

    return {
        "items": [item.model_dump() for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


# ── GET /api/mural/{post_id} ───────────────────────────────────────────
@router.get("/{post_id}", response_model=MuralPostResponse)
async def get_mural_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single mural post by ID."""
    result = await db.execute(
        select(MuralPost).options(selectinload(MuralPost.author)).where(MuralPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado.")

    response = MuralPostResponse.model_validate(post)
    if post.author:
        response.author_username = post.author.username
        response.author_name = post.author.name
        response.author_pic = post.author.profile_pic
    return response


# ── POST /api/mural ────────────────────────────────────────────────────
@router.post("/", response_model=MuralPostResponse, status_code=status.HTTP_201_CREATED)
async def create_mural_post(
    payload: MuralPostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new mural post (classified ad).

    This is the "envio de recado no mural" endpoint.
    The post is automatically associated with the authenticated user (JWT).
    """
    # Validate category
    if payload.category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Categoria inválida. Escolha entre: {', '.join(ALLOWED_CATEGORIES)}",
        )

    # Sanitize inputs
    title = sanitize_user_text(payload.title, max_len=150)
    content = sanitize_user_text(payload.content, max_len=2000)
    contact_info = sanitize_user_text(payload.contact_info, max_len=200)

    post = MuralPost(
        title=title,
        content=content,
        category=payload.category,
        contact_info=contact_info,
        user_id=current_user.id,
        timestamp=br_time(),
    )
    db.add(post)
    await db.flush()
    await db.commit()
    await db.refresh(post)

    # Notify all users about the new post (background-friendly)
    # We do a simple notification for now
    all_users_result = await db.execute(select(User))
    all_users = all_users_result.scalars().all()
    for user in all_users:
        notif = Notification(
            user_id=user.id,
            sender_name=current_user.username,
            action_type=f"Novo anúncio: {title[:80]}",
            post_id=post.id,
            category="mural",
        )
        db.add(notif)
    await db.commit()

    response = MuralPostResponse.model_validate(post)
    response.author_username = current_user.username
    response.author_name = current_user.name
    response.author_pic = current_user.profile_pic
    return response


# ── PATCH /api/mural/{post_id} ─────────────────────────────────────────
@router.patch("/{post_id}", response_model=MuralPostResponse)
async def update_mural_post(
    post_id: int,
    payload: MuralPostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a mural post (only the author can edit)."""
    result = await db.execute(
        select(MuralPost).options(selectinload(MuralPost.author)).where(MuralPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado.")

    if post.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar este anúncio.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            if field in ("title", "content", "contact_info"):
                value = sanitize_user_text(value)
            setattr(post, field, value)

    await db.commit()
    await db.refresh(post)

    response = MuralPostResponse.model_validate(post)
    if post.author:
        response.author_username = post.author.username
        response.author_name = post.author.name
        response.author_pic = post.author.profile_pic
    return response


# ── DELETE /api/mural/{post_id} ────────────────────────────────────────
@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mural_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a mural post (author or admin only)."""
    result = await db.execute(select(MuralPost).where(MuralPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado.")

    if post.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Você não tem permissão para deletar este anúncio.")

    await db.delete(post)
    await db.commit()
    # 204 No Content


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  RECADOS (Profile Wall Messages)                                     ║
# ╚══════════════════════════════════════════════════════════════════════╝

# ── POST /api/mural/recados/{user_id} ──────────────────────────────────
@router.post("/recados/{user_id}", response_model=RecadoResponse, status_code=201)
async def leave_recado(
    user_id: int,
    payload: RecadoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Leave a message (recado) on a user's profile wall.

    Migrated from routes/perfil.py → enviar_recado().
    """
    # Verify target user exists
    target_result = await db.execute(select(User).where(User.id == user_id))
    target_user = target_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    content = sanitize_user_text(payload.content, max_len=500)
    if not content:
        raise HTTPException(status_code=422, detail="O recado não pode estar vazio.")

    sender = "Anonimo" if payload.anon_mode else current_user.username

    recado = Message(
        receiver_id=user_id,
        sender_name=sender,
        content=content,
    )
    db.add(recado)

    # Create notification for the target user
    notif = Notification(
        user_id=user_id,
        sender_name=sender,
        action_type="deixou um recado no mural",
    )
    db.add(notif)
    await db.commit()
    await db.refresh(recado)

    return RecadoResponse(
        id=recado.id,
        receiver_id=recado.receiver_id,
        sender_name=recado.sender_name,
        content=recado.content,
        timestamp=recado.timestamp,
    )


# ── GET /api/mural/recados/{user_id} ──────────────────────────────────
@router.get("/recados/{user_id}", response_model=List[RecadoResponse])
async def list_recados(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List recados (wall messages) for a user."""
    result = await db.execute(
        select(Message)
        .where(Message.receiver_id == user_id)
        .order_by(Message.timestamp.desc())
        .offset(skip)
        .limit(limit)
    )
    recados = result.scalars().all()
    return [RecadoResponse.model_validate(r) for r in recados]
