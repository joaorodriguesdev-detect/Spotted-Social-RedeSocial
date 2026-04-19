import re
from datetime import datetime

from sqlalchemy import and_, or_, select

from models import Event, Post, User, db, post_likes, br_time


ALLOWED_FEED_PAGE_SIZES = {6, 8, 12}


def normalize_search_category(raw_value):
    category = (raw_value or 'usuarios').strip().lower()
    return category if category in {'usuarios', 'eventos'} else 'usuarios'


def get_feed_chunk(cursor_ts=None, cursor_id=None, limit=8):
    query = Post.query.order_by(Post.timestamp.desc(), Post.id.desc())
    if cursor_ts is not None and cursor_id is not None:
        query = query.filter(
            or_(
                Post.timestamp < cursor_ts,
                and_(Post.timestamp == cursor_ts, Post.id < cursor_id),
            )
        )

    posts = query.limit(limit + 1).all()
    has_more = len(posts) > limit
    posts = posts[:limit]

    next_cursor_ts = None
    next_cursor_id = None
    if posts:
        next_cursor_ts = posts[-1].timestamp.isoformat()
        next_cursor_id = posts[-1].id

    return posts, has_more, next_cursor_ts, next_cursor_id


def annotate_posts_with_like_info(posts, user_id):
    if not posts:
        return

    try:
        uid = int(user_id) if user_id else None
    except Exception:
        uid = None

    post_ids = [p.id for p in posts if p and getattr(p, 'id', None) is not None]
    liked_ids = set()
    if uid and post_ids:
        rows = db.session.execute(
            select(post_likes.c.post_id).where(
                post_likes.c.user_id == uid,
                post_likes.c.post_id.in_(post_ids),
            )
        ).all()
        liked_ids = {r[0] for r in rows}

    for p in posts:
        try:
            p.liked_by_me = p.id in liked_ids
        except Exception:
            p.liked_by_me = False


def normalize_event_description(value):
    if value is None:
        return ''
    normalized = value.replace('\r\n', '\n').strip()
    normalized = re.sub(r'\n{3,}', '\n\n', normalized)
    return normalized


def parse_event_datetime(date_value, time_value):
    clean_date = (date_value or '').strip()
    clean_time = (time_value or '').strip()

    if not clean_date or not clean_time:
        return None, 'Selecione data e horario validos para o evento.'

    try:
        event_date = datetime.strptime(clean_date, '%Y-%m-%d').date()
        event_time = datetime.strptime(clean_time, '%H:%M').time()
    except ValueError:
        return None, 'Data ou horário invalido.'

    # Compare using naive datetimes in the same reference used by br_time().
    combined = datetime.combine(event_date, event_time)
    now_br = br_time()
    if getattr(now_br, 'tzinfo', None) is not None:
        now_br = now_br.replace(tzinfo=None)

    if combined < now_br:
        return None, 'Nao e permitido criar ou editar evento com data/horario no passado.'

    return combined, None


def build_event_post_content(title, location, event_date, description, username):
    clean_description = normalize_event_description(description)
    return (
        f"📢 NOVO EVENTO: {title}\n"
        f"📍 Local: {location}\n"
        f"📅 Data: {event_date}\n\n"
        f"{clean_description}\n\n"
        f"Criado por @{username}"
    )


def sync_event_feed_post(event, old_title, old_location, old_event_date, old_description):
    owner = User.query.get(event.user_id)
    if not owner:
        return

    old_content = build_event_post_content(old_title, old_location, old_event_date, old_description, owner.username)
    new_content = build_event_post_content(event.title, event.location, event.event_date, event.description, owner.username)

    query = Post.query.filter(
        Post.user_id == event.user_id,
        Post.is_anonymous.is_(False),
        Post.content.contains('📢 NOVO EVENTO:'),
    )
    if event.media_url:
        query = query.filter(Post.media_url == event.media_url)

    post = query.order_by(Post.id.desc()).first()
    if post and post.content == old_content:
        post.content = new_content
        return

    exact = Post.query.filter_by(
        user_id=event.user_id,
        is_anonymous=False,
        content=old_content,
    ).order_by(Post.id.desc()).first()
    if exact:
        exact.content = new_content

