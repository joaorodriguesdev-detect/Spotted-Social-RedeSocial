"""Notification service – async version for FastAPI.

Mirrors backend/services/notification_service.py but with:
  • async def
  • SQLAlchemy async session
  • No SocketIO for now (can be added later with python-socketio)
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import Notification
from models.user import User
from services.security_service import sanitize_user_text


async def create_notification(
    user_id: int,
    sender_name: str,
    action_type: str,
    post_id: Optional[int] = None,
    category: str = "general",
    db: Optional[AsyncSession] = None,
) -> Optional[Notification]:
    """Create a notification for a user.

    Parameters
    ----------
    user_id : int
        The user who will receive the notification.
    sender_name : str
        Name/username of who triggered the notification.
    action_type : str
        Description of the action (e.g. "curtiu sua publicação").
    post_id : int, optional
        Related post ID (if any).
    category : str
        Notification category: general, mural, follow, etc.
    db : AsyncSession
        Database session (required).

    Returns
    -------
    Notification or None
        The created notification object, or None on failure.
    """
    if not db:
        return None

    try:
        clean_sender = sanitize_user_text(sender_name, max_len=80)
        clean_action = sanitize_user_text(action_type, max_len=100)

        notif = Notification(
            user_id=user_id,
            sender_name=clean_sender,
            action_type=clean_action,
            post_id=post_id,
            category=category,
        )
        db.add(notif)
        # Não faz flush/commit aqui – o dependency get_db cuida do commit
        return notif
    except Exception:
        return None


async def notify_mentions(
    content: str,
    sender_name: str,
    post_id: int,
    db: AsyncSession,
    current_user_id: Optional[int] = None,
) -> None:
    """Notify users mentioned (@username) in a post."""
    import re

    mentions = re.findall(r"@(\w+)", content)
    for username in mentions:
        result = await db.execute(
            select(User).where(User.username == username.lower())
        )
        user = result.scalar_one_or_none()
        if user and user.id != current_user_id:
            notif = Notification(
                user_id=user.id,
                sender_name=sender_name,
                action_type="mencionou voce em uma publicacao",
                post_id=post_id,
            )
            db.add(notif)
