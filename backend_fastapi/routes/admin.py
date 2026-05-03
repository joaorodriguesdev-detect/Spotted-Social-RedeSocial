"""Admin panel – FastAPI APIRouter.

Provides full moderation capabilities:
  • GET    /api/admin/stats           – Dashboard statistics
  • GET    /api/admin/users           – List all users
  • PATCH  /api/admin/users/{id}/ban  – Suspend / unsuspend a user
  • DELETE /api/admin/posts/{id}      – Delete any post
  • DELETE /api/admin/mural/{id}      – Delete any mural post
  • DELETE /api/admin/coupons/{id}    – Delete a coupon
  • PATCH  /api/admin/coupons/{id}/approve – Approve a coupon
  • GET    /api/admin/logs            – View audit logs

All routes require is_admin=True via get_current_admin dependency.
Every destructive action is recorded in the AuditLog table.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import get_current_admin
from models.audit import AuditLog
from models.coupon import Coupon
from models.mural import MuralPost
from models.notification import Notification
from models.post import Comment, Post
from models.user import User
from utils import br_time
from services.socket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  HELPERS                                                             ║
# ╚══════════════════════════════════════════════════════════════════════╝

async def _log_action(
    db: AsyncSession,
    admin_id: int,
    action: str,
    target_type: str,
    target_id: Optional[int] = None,
    details: Optional[str] = None,
) -> AuditLog:
    """Record an admin action in the audit log."""
    log = AuditLog(
        admin_id=admin_id,
        action=action,
        target_id=target_id,
        target_type=target_type,
        details=details,
    )
    db.add(log)
    await db.flush()
    return log


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /api/admin/stats – Dashboard statistics                         ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/stats", response_model=dict)
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Return aggregated statistics for the admin dashboard.

    Returns:
      - total_users: número de usuários cadastrados
      - active_users: usuários não banidos
      - banned_users: usuários banidos
      - online_users: conectados via WebSocket agora
      - new_users_today: registros das últimas 24h
      - posts_today: posts criados nas últimas 24h
      - total_posts: total de posts
      - active_coupons: cupons ativos
      - pending_coupons: cupons pendentes (se houver campo)
    """
    now = br_time()
    yesterday = now - timedelta(hours=24)

    # ── Total users ───────────────────────────────────────────────────
    total_users = await db.execute(select(func.count(User.id)))
    total_users = total_users.scalar() or 0

    active_users = await db.execute(
        select(func.count(User.id)).where(User.is_banned.is_(False))
    )
    active_users = active_users.scalar() or 0

    banned_users = await db.execute(
        select(func.count(User.id)).where(User.is_banned.is_(True))
    )
    banned_users = banned_users.scalar() or 0

    new_users_today = await db.execute(
        select(func.count(User.id)).where(User.created_at >= yesterday)
    )
    new_users_today = new_users_today.scalar() or 0

    # ── Posts ─────────────────────────────────────────────────────────
    total_posts = await db.execute(select(func.count(Post.id)))
    total_posts = total_posts.scalar() or 0

    posts_today = await db.execute(
        select(func.count(Post.id)).where(Post.timestamp >= yesterday)
    )
    posts_today = posts_today.scalar() or 0

    # ── Coupons ───────────────────────────────────────────────────────
    active_coupons = await db.execute(
        select(func.count(Coupon.id)).where(Coupon.is_active.is_(True))
    )
    active_coupons = active_coupons.scalar() or 0

    total_coupons = await db.execute(select(func.count(Coupon.id)))
    total_coupons = total_coupons.scalar() or 0

    # ── Online users via WebSocket ────────────────────────────────────
    online_users = len(await manager.get_online_users())

    return {
        "total_users": total_users,
        "active_users": active_users,
        "banned_users": banned_users,
        "online_users": online_users,
        "new_users_today": new_users_today,
        "total_posts": total_posts,
        "posts_today": posts_today,
        "active_coupons": active_coupons,
        "total_coupons": total_coupons,
    }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /api/admin/users – List all users                               ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/users", response_model=dict)
async def list_users(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(20, ge=1, le=100, description="Usuários por página"),
    search: Optional[str] = Query(None, description="Buscar por username ou nome"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """List all users with pagination and optional search."""
    query = select(User).order_by(User.created_at.desc())

    if search:
        pattern = f"%{search}%"
        query = query.where(
            (User.username.ilike(pattern)) | (User.name.ilike(pattern))
        )

    # Total count
    total_q = select(func.count(User.id))
    if search:
        pattern = f"%{search}%"
        total_q = total_q.where(
            (User.username.ilike(pattern)) | (User.name.ilike(pattern))
        )
    total_result = await db.execute(total_q)
    total = total_result.scalar() or 0

    # Paginated query
    offset = (page - 1) * per_page
    result = await db.execute(query.offset(offset).limit(per_page))
    users = result.scalars().all()

    items = []
    for u in users:
        items.append({
            "id": u.id,
            "username": u.username,
            "name": u.name,
            "university": u.university,
            "bio": u.bio,
            "profile_pic": u.profile_pic,
            "is_admin": u.is_admin,
            "is_verified": u.is_verified,
            "is_banned": u.is_banned,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "posts_count": len(u.posts) if u.posts else 0,
            "is_online": manager.is_online(u.id),
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total else 0,
    }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PATCH /api/admin/users/{user_id}/ban – Suspend / Unsuspend         ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.patch("/users/{user_id}/ban", response_model=dict)
async def toggle_user_ban(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Toggle the ban status of a user (suspend / unsuspend).

    An admin cannot ban themselves.
    If the user is already banned, they are unbanned.
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Você não pode banir a si mesmo.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    # Toggle ban
    target_user.is_banned = not target_user.is_banned
    action = "ban_user" if target_user.is_banned else "unban_user"
    status_text = "banido" if target_user.is_banned else "desbanido"

    # Audit log
    await _log_action(
        db,
        admin.id,
        action,
        "user",
        target_user.id,
        f"Usuário @{target_user.username} foi {status_text} por @{admin.username}.",
    )

    await db.flush()

    # Force disconnect if banned
    if target_user.is_banned:
        await manager.force_disconnect(user_id)

    return {
        "ok": True,
        "is_banned": target_user.is_banned,
        "message": f"@{target_user.username} foi {status_text}.",
    }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DELETE /api/admin/posts/{post_id} – Delete any post                 ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.delete("/posts/{post_id}", status_code=status.HTTP_200_OK, response_model=dict)
async def admin_delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Delete any post from the feed (moderation)."""
    result = await db.execute(
        select(Post).options(
            selectinload(Post.comments),
            selectinload(Post.liked_by),
        ).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post não encontrado.")

    # Capture info for audit
    author_name = post.author.username if post.author else "desconhecido"
    content_preview = post.content[:100] if post.content else ""

    # Delete likes, comments, then post
    for comment in post.comments:
        await db.delete(comment)
    post.liked_by.clear()
    await db.delete(post)

    # Audit log
    await _log_action(
        db,
        admin.id,
        "delete_post",
        "post",
        post_id,
        f"Post de @{author_name}: '{content_preview}'",
    )

    await db.flush()

    return {
        "ok": True,
        "message": f"Post #{post_id} de @{author_name} foi removido.",
    }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DELETE /api/admin/mural/{post_id} – Delete any mural post           ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.delete("/mural/{post_id}", status_code=status.HTTP_200_OK, response_model=dict)
async def admin_delete_mural(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Delete any mural / classified ad (moderation)."""
    result = await db.execute(select(MuralPost).where(MuralPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado.")

    author_name = post.author.username if post.author else "desconhecido"
    title_preview = post.title[:80] if post.title else ""

    await db.delete(post)

    await _log_action(
        db,
        admin.id,
        "delete_mural",
        "mural",
        post_id,
        f"Anúncio de @{author_name}: '{title_preview}'",
    )

    await db.flush()

    return {
        "ok": True,
        "message": f"Anúncio #{post_id} de @{author_name} foi removido.",
    }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DELETE /api/admin/coupons/{coupon_id} – Delete a coupon             ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.delete("/coupons/{coupon_id}", status_code=status.HTTP_200_OK, response_model=dict)
async def admin_delete_coupon(
    coupon_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Delete a coupon (moderation)."""
    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="Cupom não encontrado.")

    code = coupon.code
    await db.delete(coupon)

    await _log_action(
        db,
        admin.id,
        "delete_coupon",
        "coupon",
        coupon_id,
        f"Cupom '{code}' removido.",
    )

    await db.flush()

    return {
        "ok": True,
        "message": f"Cupom '{code}' (#{coupon_id}) foi removido.",
    }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PATCH /api/admin/coupons/{coupon_id}/approve – Approve a coupon    ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.patch("/coupons/{coupon_id}/approve", response_model=dict)
async def admin_approve_coupon(
    coupon_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Approve / activate a coupon (set is_active=True)."""
    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="Cupom não encontrado.")

    coupon.is_active = True

    await _log_action(
        db,
        admin.id,
        "approve_coupon",
        "coupon",
        coupon_id,
        f"Cupom '{coupon.code}' aprovado.",
    )

    await db.flush()

    return {
        "ok": True,
        "message": f"Cupom '{coupon.code}' (#{coupon_id}) foi ativado.",
    }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /api/admin/logs – View audit logs                               ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/logs", response_model=dict)
async def get_audit_logs(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(30, ge=1, le=100, description="Logs por página"),
    action_filter: Optional[str] = Query(None, description="Filtrar por ação"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Return recent audit log entries with admin info."""
    query = (
        select(AuditLog)
        .options(selectinload(AuditLog.admin))
        .order_by(AuditLog.timestamp.desc())
    )

    if action_filter:
        query = query.where(AuditLog.action == action_filter)

    total_q = select(func.count(AuditLog.id))
    if action_filter:
        total_q = total_q.where(AuditLog.action == action_filter)
    total_result = await db.execute(total_q)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    result = await db.execute(query.offset(offset).limit(per_page))
    logs = result.scalars().all()

    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "admin_id": log.admin_id,
            "admin_username": log.admin.username if log.admin else None,
            "action": log.action,
            "target_id": log.target_id,
            "target_type": log.target_type,
            "details": log.details,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total else 0,
    }
