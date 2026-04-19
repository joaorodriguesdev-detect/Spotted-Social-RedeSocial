import re

from flask import session
from sqlalchemy import func

from extensions import socketio
from models import Notification, User, db


def create_notification(user_id, sender_name, action_type, post_id=None, category='general', commit=True):
    try:
        notif = Notification(
            user_id=user_id,
            sender_name=sender_name,
            action_type=action_type,
            post_id=post_id,
            category=category,
        )
        db.session.add(notif)
        if commit:
            db.session.commit()
        else:
            db.session.flush()

        payload = {
            'id': notif.id,
            'user_id': notif.user_id,
            'sender_name': notif.sender_name,
            'action_type': notif.action_type,
            'post_id': notif.post_id,
            'is_read': notif.is_read,
            'category': notif.category,
            'timestamp': notif.timestamp.isoformat() if notif.timestamp else None,
        }
        try:
            socketio.emit('notification:new', payload, room=f'user:{user_id}')
        except Exception:
            pass
        return notif
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return None


def notify_mentions(content, sender_name, post_id):
    mentions = re.findall(r'@(\w+)', content)
    for username in mentions:
        user = User.query.filter_by(username=username.lower()).first()
        if user and user.id != session.get('user_id'):
            db.session.add(
                Notification(
                    user_id=user.id,
                    sender_name=sender_name,
                    action_type='mencionou voce em uma publicacao',
                    post_id=post_id,
                )
            )


def resolve_user_by_sender_name(sender_name):
    if not sender_name:
        return None

    normalized_sender = sender_name.strip().lower()
    if not normalized_sender:
        return None

    user = User.query.filter(func.lower(User.username) == normalized_sender).first()
    if user:
        return user

    return User.query.filter(func.lower(User.name) == normalized_sender).order_by(User.id.desc()).first()

