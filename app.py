import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
import logging
import traceback
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, and_, or_, func, UniqueConstraint, select
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configure a simple file logger for uncaught exceptions to aid local debugging.
LOG_PATH = os.environ.get('SPOTTED_ERROR_LOG', 'instance/error.log')
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True) if os.path.dirname(LOG_PATH) else None
file_handler = logging.FileHandler(LOG_PATH)
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
app.logger.addHandler(file_handler)

app.secret_key = os.environ.get('SECRET_KEY', 'spotted_university_ultra_v8_final_fix') 
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///spotted.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['PUBLIC_FOLDER'] = os.path.join(app.root_path, 'static', 'public')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
# Feature flag: force the Direct (messaging) system to be enabled for all
# non-admin users. Per requirement, messaging must remain active for regular
# users and disabled only for admin users. We therefore force DIRECT_ENABLED
# to True regardless of environment configuration to avoid accidental global
# disabling in production.
app.config['DIRECT_ENABLED'] = True

db = SQLAlchemy(app)
# Use explicit settings to force polling mode on hosts that disallow WebSocket upgrades
# (PythonAnywhere/uWSGI blocks WebSocket upgrade attempts and raises "Cannot obtain socket").
socketio = SocketIO(app,
                    cors_allowed_origins="*",
                    async_mode='threading',
                    engineio_logger=False,
                    logger=False,
                    allow_upgrades=False)  # Isso impede o erro de 'Cannot obtain socket'

online_user_connections = {}

ALLOWED_FEED_PAGE_SIZES = {6, 8, 12}


def resolve_feed_page_size():
    raw_value = os.environ.get('FEED_PAGE_SIZE', '8')
    try:
        parsed_value = int(raw_value)
    except (TypeError, ValueError):
        return 8
    return parsed_value if parsed_value in ALLOWED_FEED_PAGE_SIZES else 8


FEED_PAGE_SIZE = resolve_feed_page_size()

# Server-side group definitions (UI-only for now). This prevents clients
# from forcing group mode through query params.
GROUP_CHAT_PARTICIPANTS = {
    'bruno_eventos': ['bruno_eventos', 'vsfdds', 'ana_atletica']
}

# Group-scoped admins (WhatsApp-like): only creator/promoted members can manage group.
GROUP_CHAT_ADMINS = {
    'bruno_eventos': ['bruno_eventos', 'vsfdds']
}


def normalize_search_category(raw_value):
    category = (raw_value or 'usuarios').strip().lower()
    return category if category in {'usuarios', 'eventos'} else 'usuarios'


def get_feed_chunk(cursor_ts=None, cursor_id=None, limit=FEED_PAGE_SIZE):
    query = Post.query.order_by(Post.timestamp.desc(), Post.id.desc())
    if cursor_ts is not None and cursor_id is not None:
        query = query.filter(
            or_(
                Post.timestamp < cursor_ts,
                and_(Post.timestamp == cursor_ts, Post.id < cursor_id)
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
    """Annotate a list of Post objects with `liked_by_me` boolean attribute for user_id.

    This avoids N+1 queries by fetching all liked post ids in a single query.
    """
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
                post_likes.c.post_id.in_(post_ids)
            )
        ).all()
        liked_ids = {r[0] for r in rows}

    for p in posts:
        try:
            p.liked_by_me = (p.id in liked_ids)
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

    combined = datetime.combine(event_date, event_time)
    if combined < br_time():
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
        Post.content.contains('📢 NOVO EVENTO:')
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
        content=old_content
    ).order_by(Post.id.desc()).first()
    if exact:
        exact.content = new_content

@app.route('/public/')
def public_index():
    files = []
    for root, _, filenames in os.walk(app.config['PUBLIC_FOLDER']):
        rel_root = os.path.relpath(root, app.config['PUBLIC_FOLDER'])
        for name in filenames:
            rel_path = os.path.join(rel_root, name) if rel_root != '.' else name
            files.append(rel_path.replace('\\', '/'))
    return jsonify(sorted(files))

@app.route('/public/<path:filename>')
def public_files(filename):
    return send_from_directory(app.config['PUBLIC_FOLDER'], filename)

def br_time():
    # Return a timezone-aware datetime in Brazil time (UTC-3).
    # Use a proper tzinfo with a fixed -3 hours offset so callers receive
    # aware datetimes consistently.
    tz_br = timezone(timedelta(hours=-3))
    return datetime.now(tz_br)


@app.errorhandler(Exception)
def log_exception(e):
    """Log unhandled exceptions to a file with traceback for local debugging.

    This handler captures any exception not explicitly handled by routes and
    writes a full traceback to the configured log file. It then returns the
    default 500 response so the behavior is unchanged for clients.
    """
    try:
        tb = traceback.format_exc()
        app.logger.error('Unhandled exception:\n%s', tb)
    except Exception:
        # If logging itself fails, fall back to printing to stderr
        print('Failed to log exception', flush=True)
        traceback.print_exc()
    # Return a simple 500 response without rendering templates to avoid
    # cascading template errors during debugging.
    return ("<h1>Internal Server Error</h1><p>An unexpected error occurred."
            " The full traceback has been written to the error log."), 500

def ensure_user_created_at_column():
    inspector = inspect(db.engine)
    user_columns = {col['name'] for col in inspector.get_columns('user')}
    if 'created_at' in user_columns:
        return
    with db.engine.begin() as conn:
        conn.exec_driver_sql('ALTER TABLE user ADD COLUMN created_at DATETIME')


def ensure_conversation_member_last_read_column():
    inspector = inspect(db.engine)
    member_columns = {col['name'] for col in inspector.get_columns('conversation_member')}
    if 'last_read_message_id' in member_columns:
        return
    with db.engine.begin() as conn:
        conn.exec_driver_sql('ALTER TABLE conversation_member ADD COLUMN last_read_message_id INTEGER')


def ensure_conversation_pinned_message_column():
    inspector = inspect(db.engine)
    conversation_columns = {col['name'] for col in inspector.get_columns('conversation')}
    if 'pinned_message_id' in conversation_columns:
        return
    with db.engine.begin() as conn:
        conn.exec_driver_sql('ALTER TABLE conversation ADD COLUMN pinned_message_id INTEGER')


def ensure_direct_chat_message_all_read_column():
    inspector = inspect(db.engine)
    try:
        cols = {col['name'] for col in inspector.get_columns('direct_chat_message')}
    except Exception:
        cols = set()
    if 'all_read' in cols:
        return
    with db.engine.begin() as conn:
        # SQLite uses INTEGER for booleans; default to 0 (False)
        conn.exec_driver_sql("ALTER TABLE direct_chat_message ADD COLUMN all_read BOOLEAN DEFAULT 0 NOT NULL")


def ensure_notification_category_column():
    inspector = inspect(db.engine)
    try:
        cols = {col['name'] for col in inspector.get_columns('notification')}
    except Exception:
        cols = set()
    if 'category' in cols:
        return
    with db.engine.begin() as conn:
        # SQLite allows adding a column with a default value
        conn.exec_driver_sql("ALTER TABLE notification ADD COLUMN category VARCHAR(50) DEFAULT 'general'")

@app.template_filter('joined_month_year')
def joined_month_year_filter(ts):
    if not ts:
        return ''
    months_pt = {
        1: 'janeiro', 2: 'fevereiro', 3: 'marco', 4: 'abril',
        5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
        9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
    }
    return f"{months_pt[ts.month]} de {ts.year}"

@app.template_filter('post_time')
def post_time_filter(ts):
    if not ts:
        return ''

    # Normalize both now and the provided timestamp to the same timezone
    # so subtraction does not fail when mixing naive and aware datetimes.
    tz_br = timezone(timedelta(hours=-3))
    now = datetime.now(tz_br)

    # If the stored timestamp is naive, assume it was recorded in UTC and
    # attach UTC tzinfo. Then convert to Brazil timezone for delta math.
    try:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ts = ts.astimezone(tz_br)
    except Exception:
        # If conversion fails for any reason, fall back to treating both
        # values as naive in the system local time by removing tzinfo.
        try:
            now = now.replace(tzinfo=None)
            ts = ts.replace(tzinfo=None)
        except Exception:
            # As a last resort, return an empty label rather than crash.
            return ''

    delta = now - ts

    # Guard against future timestamps caused by clock drift.
    if delta.total_seconds() < 0:
        return 'agora'

    if delta < timedelta(minutes=1):
        return 'agora'
    if delta < timedelta(hours=1):
        return f"{int(delta.total_seconds() // 60)} min"
    if delta < timedelta(days=1):
        return f"{int(delta.total_seconds() // 3600)} h"
    if delta < timedelta(days=30):
        return f"{delta.days} d"
    if delta < timedelta(days=365):
        return ts.strftime('%d/%m')
    return ts.strftime('%d/%m/%Y')

@app.template_filter('mention')
def mention_filter(text):
    def replace_mention(match):
        username = match.group(1).lower()
        exists = User.query.filter_by(username=username).first()
        if exists:
            return f'<a href="/perfil/{username}" class="text-indigo-500 font-bold hover:underline">@{username}</a>'
        return f'@{username}' 
    return re.sub(r'@(\w+)', replace_mention, text)


@app.template_global('is_verified_platform_account')
def is_verified_platform_account(username):
    clean_username = (username or '').strip().lower()
    if not clean_username or clean_username == 'anônimo' or clean_username == 'anonimo':
        return False
    user = User.query.filter(func.lower(User.username) == clean_username).first()
    return bool(user and user.is_admin)


@app.template_global('post_is_liked_by')
def post_is_liked_by(post, user_id):
    """Return True if the given post is liked by user_id.

    This is exposed to templates to render like state server-side.
    """
    try:
        if not user_id:
            return False
        # `liked_by` backref is configured with lazy='dynamic'
        return post.liked_by.filter_by(id=user_id).count() > 0
    except Exception:
        return False

def notify_mentions(content, sender_name, post_id):
    mentions = re.findall(r'@(\w+)', content)
    for username in mentions:
        user = User.query.filter_by(username=username.lower()).first()
        if user and user.id != session.get('user_id'):
            db.session.add(Notification(
                user_id=user.id, 
                sender_name=sender_name, 
                action_type="mencionou você em uma publicação", 
                post_id=post_id
            ))


def resolve_user_by_sender_name(sender_name):
    if not sender_name:
        return None

    normalized_sender = sender_name.strip().lower()
    if not normalized_sender:
        return None

    # Prefer exact username match, then fallback to display name.
    user = User.query.filter(func.lower(User.username) == normalized_sender).first()
    if user:
        return user

    return User.query.filter(func.lower(User.name) == normalized_sender).order_by(User.id.desc()).first()


def users_follow_each_other(user_a, user_b):
    if not user_a or not user_b:
        return False
    return bool(user_a.is_following(user_b) and user_b.is_following(user_a))

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

post_likes = db.Table('post_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'))
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=True) 
    username = db.Column(db.String(80), unique=True, nullable=False) 
    password = db.Column(db.String(120), nullable=False)
    university = db.Column(db.String(50), nullable=True)
    bio = db.Column(db.String(150), default="Estudante no Spotted University 🎓")
    profile_pic = db.Column(db.String(200), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=br_time, nullable=True)
    posts = db.relationship('Post', backref='author', lazy=True)
    notifications = db.relationship('Notification', backref='receiver', lazy=True, cascade="all, delete-orphan")
    followed = db.relationship('User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    liked_posts = db.relationship('Post', secondary=post_likes, backref=db.backref('liked_by', lazy='dynamic'))

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=br_time)
    likes = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_anonymous = db.Column(db.Boolean, default=False)
    comments = db.relationship('Comment', backref='post', cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    content = db.Column(db.String(200), nullable=False)
    username = db.Column(db.String(80), default="Anônimo") 
    timestamp = db.Column(db.DateTime, default=br_time)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender_name = db.Column(db.String(80))
    action_type = db.Column(db.String(100))
    category = db.Column(db.String(50), default='general')
    post_id = db.Column(db.Integer, nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=br_time)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sender_name = db.Column(db.String(80))
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=br_time)


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=True)
    title = db.Column(db.String(80), nullable=True)
    is_group = db.Column(db.Boolean, default=False, nullable=False)
    group_photo = db.Column(db.String(200), nullable=True)
    pinned_message_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=br_time, nullable=False)
    members = db.relationship('ConversationMember', backref='conversation', lazy=True, cascade='all, delete-orphan')
    messages = db.relationship('DirectChatMessage', backref='conversation', lazy=True, cascade='all, delete-orphan')


class ConversationMember(db.Model):
    __table_args__ = (UniqueConstraint('conversation_id', 'user_id', name='uq_conversation_member'),)

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    # Tracks the newest message seen by this member to compute "Nao lidas".
    last_read_message_id = db.Column(db.Integer, nullable=True)
    joined_at = db.Column(db.DateTime, default=br_time, nullable=False)
    user = db.relationship('User', backref=db.backref('conversation_memberships', lazy=True))


class DirectChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    media_url = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=br_time, nullable=False)
    sender = db.relationship('User', backref=db.backref('direct_messages_sent', lazy=True))
    # Tracks whether all current members have read this message (set when everyone seen it)
    all_read = db.Column(db.Boolean, default=False, nullable=False)


class MessageReaction(db.Model):
    __table_args__ = (UniqueConstraint('message_id', 'user_id', name='uq_message_reaction'),)
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('direct_chat_message.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reaction = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=br_time)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    event_date = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    media_url = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=br_time)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    creator = db.relationship('User', backref='my_events')

with app.app_context():
    db.create_all()
    ensure_user_created_at_column()
    ensure_conversation_member_last_read_column()
    ensure_conversation_pinned_message_column()
    ensure_direct_chat_message_all_read_column()
    ensure_notification_category_column()
    missing_created_at = User.query.filter(User.created_at.is_(None)).all()
    for user in missing_created_at:
        user.created_at = br_time()
    admin_master = User.query.filter_by(username='admin').first()
    if not admin_master:
        nova_senha_hash = generate_password_hash('Migo@2026!#')
        admin_master = User(name="Spotted Social", username='admin', password=nova_senha_hash, is_admin=True, bio="Sistema")
        db.session.add(admin_master)
    db.session.commit()

@app.route('/api/users')
def api_users():
    q = request.args.get('q', '').lower()
    if not q: return jsonify([])
    users = User.query.filter(User.username.like(f'{q}%'), User.is_admin == False).limit(5).all()
    return jsonify([{'username': u.username, 'name': u.name} for u in users])


@app.route('/api/direct/users')
def api_direct_users():
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    q = (request.args.get('q') or '').strip().lower().replace('@', '')
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)

    query = User.query.filter(
        User.id != current_user_id,
        User.is_admin.is_(False)
    )

    if q:
        query = query.filter(
            or_(
                User.username.ilike(f'%{q}%'),
                User.name.ilike(f'%{q}%')
            )
        )

    # Apply mutual-follow filter at the database level so the LIMIT applies to
    # already-filtered results. This prevents returning non-mutual users when
    # the current user follows nobody.
    users = []
    if current_user:
        try:
            mutual_a = select([1]).where(and_(followers.c.follower_id == current_user_id, followers.c.followed_id == User.id)).exists()
            mutual_b = select([1]).where(and_(followers.c.follower_id == User.id, followers.c.followed_id == current_user_id)).exists()
            users = query.filter(mutual_a, mutual_b).order_by(User.username.asc()).limit(20).all()
        except Exception:
            # Fallback to previous Python-level filtering in case the SQL EXISTS
            # expression isn't supported in this environment/version.
            users = query.order_by(User.username.asc()).limit(50).all()
            users = [user for user in users if users_follow_each_other(current_user, user)]
    else:
        users = []

    return jsonify({'users': [
        {
            'username': user.username,
            'name': user.name,
            'profile_pic': user.profile_pic
        }
        for user in users
    ]})


@app.route('/api/direct/conversations/start', methods=['POST'])
def api_direct_start_conversation():
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    payload = request.get_json(silent=True) or {}
    username = (payload.get('username') or '').strip().lower().replace('@', '')
    if not username:
        return jsonify({'error': 'usuario invalido'}), 400

    current_user_id = session.get('user_id')
    target_user = User.query.filter_by(username=username).first()
    if not target_user:
        return jsonify({'error': 'usuario nao encontrado'}), 404
    if target_user.id == current_user_id or target_user.is_admin:
        return jsonify({'error': 'nao permitido'}), 400

    get_or_create_dm_conversation(current_user_id, target_user.id)
    return jsonify({'ok': True, 'url': url_for('direct_conversation', username=target_user.username)})


def generate_group_slug(title):
    base = re.sub(r'[^a-z0-9]+', '-', (title or '').strip().lower()).strip('-')
    if not base:
        base = f'grupo-{uuid.uuid4().hex[:6]}'

    slug = base[:72]
    if not Conversation.query.filter_by(slug=slug).first():
        return slug

    while True:
        suffix = uuid.uuid4().hex[:6]
        candidate = f"{slug[:65]}-{suffix}"
        if not Conversation.query.filter_by(slug=candidate).first():
            return candidate


@app.route('/api/direct/groups', methods=['POST'])
def api_direct_create_group():
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    payload = request.get_json(silent=True) or {}
    title = (payload.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'nome do grupo e obrigatorio'}), 400

    current_user_id = session.get('user_id')
    raw_usernames = payload.get('usernames') or []
    if not isinstance(raw_usernames, list):
        raw_usernames = []

    normalized_usernames = []
    seen = set()
    for raw_username in raw_usernames:
        clean_username = (raw_username or '').strip().lower().replace('@', '')
        if not clean_username or clean_username in seen:
            continue
        seen.add(clean_username)
        normalized_usernames.append(clean_username)

    current_user = User.query.get(current_user_id)
    if not current_user:
        return jsonify({'error': 'usuario invalido'}), 400

    selected_users = []
    if normalized_usernames:
        selected_users = User.query.filter(
            User.username.in_(normalized_usernames),
            User.id != current_user_id,
            User.is_admin.is_(False)
        ).all()

    selected_users = [user for user in selected_users if users_follow_each_other(current_user, user)]

    if not selected_users:
        return jsonify({'error': 'selecione ao menos um integrante valido para criar o grupo'}), 400

    conversation = Conversation(
        slug=generate_group_slug(title),
        title=title[:80],
        is_group=True
    )
    db.session.add(conversation)
    db.session.flush()

    db.session.add(ConversationMember(
        conversation_id=conversation.id,
        user_id=current_user_id,
        is_admin=True
    ))

    for user in selected_users:
        db.session.add(ConversationMember(
            conversation_id=conversation.id,
            user_id=user.id,
            is_admin=False
        ))

    db.session.commit()
    emit_group_members_updated(conversation.id)
    return jsonify({'ok': True, 'url': url_for('direct_conversation', username=conversation.slug)})

@app.route('/')
def welcome():
    if 'user_id' in session: return redirect(url_for('feed'))
    return render_template('welcome.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username').lower().strip()
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        session.clear()
        session['user_id'] = user.id
        session['username'] = user.username
        session['name'] = user.name
        session['is_admin'] = user.is_admin
        session['profile_pic'] = user.profile_pic
        return redirect(url_for('feed'))
    flash('Usuário ou senha incorretos.')
    return redirect(url_for('welcome'))

@app.route('/registro', methods=['POST'])
def registro():
    name = request.form.get('name').strip()
    username = request.form.get('username').lower().strip()
    password = request.form.get('password')
    university = request.form.get('university')
    if " " in username:
        flash('O usuário não pode conter espaços.')
        return redirect(url_for('welcome'))
    if len(password) < 8 or not re.search(r"[!@#$%^&*()]", password):
        flash('Senha inválida.')
        return redirect(url_for('welcome'))
    if User.query.filter_by(username=username).first():
        flash('Login já existe.')
        return redirect(url_for('welcome'))
    user = User(name=name, username=username, password=generate_password_hash(password), university=university)
    db.session.add(user); db.session.commit()
    session.clear()
    session['user_id'] = user.id
    session['username'] = user.username
    session['name'] = user.name
    session['is_admin'] = False
    session['profile_pic'] = user.profile_pic 
    return redirect(url_for('feed'))

@app.route('/feed')
def feed():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    posts, has_more, next_cursor_ts, next_cursor_id = get_feed_chunk()
    annotate_posts_with_like_info(posts, session.get('user_id'))
    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    return render_template(
        'index.html',
        posts=posts,
        unread_count=unread,
        has_more=has_more,
        next_cursor_ts=next_cursor_ts,
        next_cursor_id=next_cursor_id
    )


@app.route('/feed/more')
def feed_more():
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401

    cursor_ts_raw = request.args.get('cursor_ts')
    cursor_id_raw = request.args.get('cursor_id')

    cursor_ts = None
    cursor_id = None
    if cursor_ts_raw and cursor_id_raw:
        try:
            cursor_ts = datetime.fromisoformat(cursor_ts_raw)
            cursor_id = int(cursor_id_raw)
        except (TypeError, ValueError):
            return jsonify({'error': 'cursor invalido'}), 400

    posts, has_more, next_cursor_ts, next_cursor_id = get_feed_chunk(
        cursor_ts=cursor_ts,
        cursor_id=cursor_id
    )
    # Annotate posts with liked_by_me to allow client-side partial to render like state without per-post queries
    annotate_posts_with_like_info(posts, session.get('user_id'))
    html = render_template('_feed_posts.html', posts=posts)
    return jsonify({
        'html': html,
        'has_more': has_more,
        'next_cursor_ts': next_cursor_ts,
        'next_cursor_id': next_cursor_id
    })

@app.route('/search')
def search():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    query = request.args.get('query', '').lower().strip().replace('@', '')
    category = normalize_search_category(request.args.get('category'))
    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    if not query:
        posts = Post.query.order_by(Post.timestamp.desc()).all()
        return render_template(
            'index.html',
            searching=True,
            query='',
            posts=posts,
            unread_count=unread,
            search_category=category,
            search_results=[],
            event_results=[]
        )

    if category == 'eventos':
        event_results = Event.query.filter(
            or_(
                Event.title.ilike(f'%{query}%'),
                Event.location.ilike(f'%{query}%'),
                Event.description.ilike(f'%{query}%')
            )
        ).order_by(Event.created_at.desc()).all()
        return render_template(
            'index.html',
            event_results=event_results,
            search_results=[],
            query=query,
            searching=True,
            unread_count=unread,
            search_category=category
        )

    results = User.query.filter(User.username.contains(query), User.is_admin == False).all()
    return render_template(
        'index.html',
        search_results=results,
        event_results=[],
        query=query,
        searching=True,
        unread_count=unread,
        search_category=category
    )


@app.route('/api/search')
def api_search():
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401

    query = (request.args.get('query') or '').lower().strip().replace('@', '')
    category = normalize_search_category(request.args.get('category'))

    if not query:
        return jsonify({'category': category, 'query': query, 'users': [], 'events': []})

    if category == 'eventos':
        events = Event.query.filter(
            or_(
                Event.title.ilike(f'%{query}%'),
                Event.location.ilike(f'%{query}%'),
                Event.description.ilike(f'%{query}%')
            )
        ).order_by(Event.created_at.desc()).limit(20).all()

        payload = []
        for event in events:
            event_date_parts = (event.event_date or '').split(' às ')
            raw_event_date = event_date_parts[0] if event_date_parts and event_date_parts[0] else (event.event_date or '')
            parsed = raw_event_date.split('-')
            event_date_label = raw_event_date
            if len(parsed) == 3:
                event_date_label = f"{parsed[2]}/{parsed[1]}/{parsed[0]}"
            payload.append({
                'id': event.id,
                'title': event.title,
                'description': event.description,
                'location': event.location,
                'media_url': event.media_url,
                'event_date_label': event_date_label,
                'creator_username': event.creator.username if event.creator else ''
            })

        return jsonify({'category': category, 'query': query, 'users': [], 'events': payload})

    users = User.query.filter(User.username.contains(query), User.is_admin == False).limit(20).all()
    return jsonify({
        'category': category,
        'query': query,
        'users': [{'username': u.username, 'name': u.name} for u in users],
        'events': []
    })

@app.route('/postar', methods=['POST'])
def postar():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    content = request.form.get('content')
    anon_mode = request.form.get('anon_mode') == 'true'
    file = request.files.get('file'); filename = None
    if file and file.filename != '':
        ext = os.path.splitext(file.filename)[1]
        filename = str(uuid.uuid4()) + ext
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    new_post = Post(content=content, media_url=filename, user_id=session.get('user_id'), is_anonymous=anon_mode)
    db.session.add(new_post)
    db.session.flush() 
    if not anon_mode:
        notify_mentions(content, session.get('name'), new_post.id)
    db.session.commit()
    return redirect(url_for('feed'))

@app.route('/excluir_post/<int:post_id>')
def excluir_post(post_id):
    post = Post.query.get_or_404(post_id)
    if (post.user_id == session.get('user_id') and post.user_id is not None) or session.get('is_admin'):
        db.session.delete(post)
        db.session.commit()
    return redirect(request.referrer or url_for('feed'))

@app.route('/like/<int:post_id>')
def like(post_id):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    post = Post.query.get_or_404(post_id)
    user = User.query.get(session['user_id'])
    if post not in user.liked_posts:
        user.liked_posts.append(post)
        post.likes += 1
        if post.user_id and post.user_id != user.id:
            db.session.add(Notification(user_id=post.user_id, sender_name=user.name, action_type="curtiu sua publicação", post_id=post.id))
    else:
        user.liked_posts.remove(post)
        post.likes -= 1
    db.session.commit()
    # If the request is AJAX, return JSON so the client can update UI without full redirect.
    try:
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json
    except Exception:
        is_ajax = False

    liked = post.liked_by.filter_by(id=user.id).count() > 0
    if is_ajax:
        return jsonify({'ok': True, 'liked': liked, 'likes': post.likes})

    return redirect(url_for('feed', _anchor=f"post-{post_id}"))

@app.route('/comentar/<int:post_id>', methods=['POST'])
def comentar(post_id):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    content = request.form.get('comment_content'); post = Post.query.get_or_404(post_id)
    if content:
        autor_username = session.get('username') 
        db.session.add(Comment(content=content, post_id=post_id, username=autor_username))
        if post.user_id and post.user_id != session.get('user_id'):
            db.session.add(Notification(user_id=post.user_id, sender_name=session.get('name'), action_type="comentou sua publicação", post_id=post.id))
        notify_mentions(content, session.get('name'), post.id)
        db.session.commit()
    return redirect(url_for('feed', _anchor=f"post-{post_id}"))

@app.route('/perfil/<username>')
def perfil(username):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter(
        Post.user_id == user.id,
        Post.is_anonymous.is_(False),
        ~Post.content.contains('📢 NOVO EVENTO:')
    ).order_by(Post.timestamp.desc()).all()
    user_events = Event.query.filter_by(user_id=user.id).order_by(Event.created_at.desc()).all()
    messages = Message.query.filter_by(receiver_id=user.id).order_by(Message.timestamp.desc()).all()
    me = User.query.get(session['user_id'])
    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    return render_template(
        'profile.html',
        user=user,
        posts=posts,
        user_events=user_events,
        messages=messages,
        me=me,
        unread_count=unread
    )


@app.route('/perfil_por_remetente')
def perfil_por_remetente():
    if 'user_id' not in session:
        return redirect(url_for('welcome'))

    sender_name = request.args.get('sender_name', '')
    user = resolve_user_by_sender_name(sender_name)
    if not user:
        flash('Perfil do remetente nao encontrado.')
        return redirect(request.referrer or url_for('feed'))


    return redirect(url_for('perfil', username=user.username))

@app.route('/editar_perfil', methods=['POST'])
def editar_perfil():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    user = User.query.get(session['user_id'])
    name_post = request.form.get('name')
    university_post = request.form.get('university')
    bio_post = request.form.get('bio')
    if name_post:
        user.name = name_post[:80]
        session['name'] = user.name
    if university_post: user.university = university_post[:50]
    if bio_post is not None: user.bio = bio_post[:150]
    file = request.files.get('profile_pic')
    if file and file.filename != '':
        ext = os.path.splitext(file.filename)[1]
        filename = f"pfp_{user.id}_{str(uuid.uuid4())[:8]}{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        user.profile_pic = filename
        session['profile_pic'] = filename 
    db.session.commit()
    return redirect(url_for('perfil', username=user.username))

@app.route('/seguir/<username>')
def seguir(username):
    if 'user_id' not in session: return redirect(url_for('perfil', username=username))
    user_to_follow = User.query.filter_by(username=username).first_or_404()
    me = User.query.get(session['user_id'])
    if user_to_follow.id != me.id:
        if not me.is_following(user_to_follow):
            me.followed.append(user_to_follow)
            db.session.add(Notification(user_id=user_to_follow.id, sender_name=me.username, action_type="começou a te seguir"))
        else:
            me.followed.remove(user_to_follow)
        db.session.commit()
    return redirect(url_for('perfil', username=username))

@app.route('/enviar_recado/<int:user_id>', methods=['POST'])
def enviar_recado(user_id):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    content = request.form.get('content')
    if content:
        sender = session.get('username')
        db.session.add(Message(receiver_id=user_id, sender_name=sender, content=content))
        db.session.add(Notification(user_id=user_id, sender_name=sender, action_type="deixou um recado no mural"))
        db.session.commit()
    return redirect(url_for('perfil', username=User.query.get(user_id).username))

@app.route('/notificacoes')
def notificacoes():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    notifs = Notification.query.filter_by(user_id=session['user_id']).order_by(Notification.timestamp.desc()).all()
    for n in notifs: n.is_read = True
    db.session.commit()
    return render_template('notifications.html', notifications=notifs, unread_count=0)


@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
def api_mark_notification_read(notif_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    user_id = session.get('user_id')
    notif = Notification.query.get(notif_id)
    if not notif or notif.user_id != user_id:
        return jsonify({'error': 'notificacao nao encontrada'}), 404
    if not notif.is_read:
        notif.is_read = True
        db.session.commit()
    # Broadcast updated unread count to the user's room so other tabs/clients can sync
    try:
        unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
        socketio.emit('notification:marked-read', {'unread_count': unread_count}, room=f'user:{user_id}')
    except Exception:
        pass
    return jsonify({'ok': True, 'unread_count': Notification.query.filter_by(user_id=user_id, is_read=False).count()})


def get_membership(conversation_id, user_id):
    return ConversationMember.query.filter_by(conversation_id=conversation_id, user_id=user_id).first()


def can_user_access_group_conversation(conversation, user):
    if not conversation or not conversation.is_group:
        return True
    if not user:
        return False

    slug = (conversation.slug or '').strip().lower()
    static_members = GROUP_CHAT_PARTICIPANTS.get(slug)
    if static_members is None:
        return True

    return (user.username or '').strip().lower() in set(static_members)


def is_direct_blocked_for_system_admin():
    # Historically this project blocked the built-in 'admin' seeded account
    # from using Direct so developers could test maintenance flows. Restore
    # that behavior: when the current session is an admin, block Direct.
    try:
        return bool(session.get('is_admin'))
    except Exception:
        # If session is not available for some reason, be conservative and
        # block access to admin-only behavior by returning True when unable
        # to determine session state.
        return True


def is_direct_temporarily_disabled_for_users():
    """Return True when Direct is globally disabled via the DIRECT_MAINTENANCE
    environment variable and the current session user is NOT an admin.

    Set DIRECT_MAINTENANCE=1 (or true/yes/on) in the environment to enable the
    temporary redirect/block for normal users while preserving admin access so
    developers can still test.
    """
    # When the environment variable DIRECT_MAINTENANCE is present (values
    # '1', 'true', 'yes', 'on' are accepted), non-admin users should be
    # prevented from accessing Direct while admins can still test. This
    # helper returns True for non-admin users when maintenance mode is set.
    try:
        raw = os.environ.get('DIRECT_MAINTENANCE', '') or ''
        enabled = str(raw).strip().lower() in {'1', 'true', 'yes', 'on'}
        if not enabled:
            return False
        # If maintenance is enabled, block for non-admins only
        return not bool(session.get('is_admin'))
    except Exception:
        # On error, do not accidentally disable Direct for regular users;
        # return False to keep the system available.
        return False


def is_direct_globally_disabled():
    """Return True when the entire Direct/messaging system is disabled.

    The configuration `app.config['DIRECT_ENABLED']` holds a simple boolean
    (True = enabled, False = disabled). This helper returns True when the
    system should be considered disabled.
    """
    # The configuration `app.config['DIRECT_ENABLED']` controls whether the
    # messaging system is globally enabled. If set to False, Direct should be
    # considered disabled for all users. Default to True when not configured.
    try:
        return not bool(app.config.get('DIRECT_ENABLED', True))
    except Exception:
        # On error, assume not globally disabled.
        return False


@app.before_request
def block_direct_when_maintenance():
    """If DIRECT_MAINTENANCE is enabled, prevent non-admin users from
    accessing Direct pages and APIs. API calls under /api/direct will receive
    a 403 JSON response; browser page requests to /direct will be redirected
    to the feed with a maintenance flash message.
    """
    # If the entire Direct system is turned off via DIRECT_ENABLED, block all users
    try:
        if is_direct_globally_disabled():
            path = (request.path or '')
            if path.startswith('/api/direct'):
                return jsonify({'error': 'direct desativado'}), 403
            if path.startswith('/direct'):
                flash('Direct desativado.')
                return redirect(url_for('feed'))
    except Exception:
        # If our feature-flag check fails, fall back to normal behavior
        pass

    try:
        if not is_direct_temporarily_disabled_for_users():
            return None
    except Exception:
        return None

    # Only apply to Direct-related HTTP endpoints (temporary maintenance mode)
    path = (request.path or '')
    if path.startswith('/api/direct'):
        return jsonify({'error': 'direct temporariamente desativado'}), 403
    if path.startswith('/direct'):
        flash('Direct temporariamente desativado. Voltaremos em breve.')
        return redirect(url_for('feed'))


def conversation_room_name(conversation_id):
    return f'conversation:{conversation_id}'


def serialize_group_member(member):
    user = member.user
    return {
        'username': user.username if user else '',
        'profile_pic': user.profile_pic if user else None,
        'is_admin': bool(member.is_admin)
    }


def build_members_payload(conversation_id):
    members = get_group_members(conversation_id)
    return [serialize_group_member(member) for member in members]


def emit_group_members_updated(conversation_id):
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return
    socketio.emit('direct:members-updated', {
        'conversation_id': conversation_id,
        'members': build_members_payload(conversation_id)
    }, room=conversation_room_name(conversation_id))


def emit_group_updated(conversation):
    if not conversation:
        return
    socketio.emit('direct:group-updated', {
        'conversation_id': conversation.id,
        'title': conversation.title,
        'group_photo': conversation.group_photo
    }, room=conversation_room_name(conversation.id))


def emit_presence_for_user(user, is_online):
    if not user:
        return
    memberships = ConversationMember.query.filter_by(user_id=user.id).all()
    payload = {
        'user_id': user.id,
        'username': user.username,
        'is_online': bool(is_online)
    }
    for membership in memberships:
        socketio.emit('direct:presence', payload, room=conversation_room_name(membership.conversation_id))


def create_notification(user_id, sender_name, action_type, post_id=None, category='general', commit=True):
    """Create a Notification and emit a realtime event.

    When `commit` is False the function will add the object and flush so callers
    can batch multiple notifications and commit once. Returns the Notification
    instance on success or None on failure. Non-fatal: exceptions are swallowed
    to avoid breaking callers.
    """
    try:
        notif = Notification(user_id=user_id, sender_name=sender_name, action_type=action_type, post_id=post_id, category=category)
        db.session.add(notif)
        # If caller requests batching, flush to populate `id` but don't commit yet.
        if commit:
            db.session.commit()
        else:
            # Flush ensures notif.id and other defaults (timestamp) are available
            # for the realtime payload without committing the transaction.
            db.session.flush()

        payload = {
            'id': notif.id,
            'user_id': notif.user_id,
            'sender_name': notif.sender_name,
            'action_type': notif.action_type,
            'post_id': notif.post_id,
            'is_read': notif.is_read,
            'category': notif.category,
            'timestamp': notif.timestamp.isoformat() if notif.timestamp else None
        }
        # Emit to the specific user's personal room
        try:
            socketio.emit('notification:new', payload, room=f'user:{user_id}')
        except Exception:
            # Don't fail the whole flow if emit fails
            pass
        return notif
    except Exception:
        # Non-fatal: swallow errors to avoid breaking callers
        try:
            db.session.rollback()
        except Exception:
            pass
        return None


def ensure_group_conversation(slug):
    clean_slug = (slug or '').strip().lower()
    if not clean_slug:
        return None

    conversation = Conversation.query.filter_by(slug=clean_slug, is_group=True).first()
    if clean_slug not in GROUP_CHAT_PARTICIPANTS:
        return conversation

    changed = False
    if not conversation:
        conversation = Conversation(slug=clean_slug, title=clean_slug, is_group=True)
        db.session.add(conversation)
        db.session.flush()
        changed = True

    static_members = GROUP_CHAT_PARTICIPANTS.get(clean_slug) or []
    static_admins = set(GROUP_CHAT_ADMINS.get(clean_slug) or [])

    allowed_users = User.query.filter(User.username.in_(static_members)).all()
    allowed_by_username = {user.username: user for user in allowed_users}
    allowed_user_ids = {user.id for user in allowed_users}

    for username in static_members:
        user = allowed_by_username.get(username)
        if not user:
            continue
        membership = get_membership(conversation.id, user.id)
        should_be_admin = username in static_admins
        if not membership:
            db.session.add(ConversationMember(
                conversation_id=conversation.id,
                user_id=user.id,
                is_admin=should_be_admin
            ))
            changed = True
            continue
        if membership.is_admin != should_be_admin:
            membership.is_admin = should_be_admin
            changed = True

    existing_members = ConversationMember.query.filter_by(conversation_id=conversation.id).all()
    for member in existing_members:
        if member.user_id in allowed_user_ids:
            continue
        db.session.delete(member)
        changed = True

    if changed:
        db.session.commit()
        emit_group_members_updated(conversation.id)

    return conversation


def get_or_create_dm_conversation(current_user_id, target_user_id):
    current_memberships = ConversationMember.query.filter_by(user_id=current_user_id).all()
    candidate_ids = [membership.conversation_id for membership in current_memberships]

    if candidate_ids:
        candidates = Conversation.query.filter(
            Conversation.id.in_(candidate_ids),
            Conversation.is_group.is_(False)
        ).all()
        for conversation in candidates:
            members = ConversationMember.query.filter_by(conversation_id=conversation.id).all()
            member_ids = {member.user_id for member in members}
            if member_ids == {current_user_id, target_user_id}:
                return conversation

    conversation = Conversation(is_group=False)
    db.session.add(conversation)
    db.session.flush()
    db.session.add(ConversationMember(conversation_id=conversation.id, user_id=current_user_id, is_admin=False))
    db.session.add(ConversationMember(conversation_id=conversation.id, user_id=target_user_id, is_admin=False))
    db.session.commit()
    return conversation


def serialize_direct_message(message, current_user_id):
    return {
        'id': message.id,
        'conversation_id': message.conversation_id,
        'sender_id': message.sender_id,
        'sender_username': message.sender.username if message.sender else '',
        'sender_profile_pic': message.sender.profile_pic if message.sender else None,
        'content': message.content,
        'media_url': message.media_url,
        'created_at': message.created_at.isoformat() if message.created_at else None,
        'is_mine': message.sender_id == current_user_id
    }


def serialize_direct_message_broadcast(message):
    return {
        'id': message.id,
        'conversation_id': message.conversation_id,
        'sender_id': message.sender_id,
        'sender_username': message.sender.username if message.sender else '',
        'sender_profile_pic': message.sender.profile_pic if message.sender else None,
        'content': message.content,
        'media_url': message.media_url,
        'created_at': message.created_at.isoformat() if message.created_at else None
    }


def get_conversation_pinned_message(conversation_id, current_user_id):
    conversation = Conversation.query.get(conversation_id)
    if not conversation or not conversation.pinned_message_id:
        return None

    message = DirectChatMessage.query.filter_by(
        id=conversation.pinned_message_id,
        conversation_id=conversation_id
    ).first()
    if not message:
        return None

    return serialize_direct_message(message, current_user_id)


def get_group_members(conversation_id):
    return ConversationMember.query.join(User).filter(
        ConversationMember.conversation_id == conversation_id
    ).order_by(
        ConversationMember.is_admin.desc(),
        ConversationMember.joined_at.asc(),
        User.username.asc()
    ).all()


def can_manage_group(conversation_id, user_id):
    membership = get_membership(conversation_id, user_id)
    return bool(membership and membership.is_admin)


def get_latest_message_id(conversation_id):
    last_message = DirectChatMessage.query.filter_by(conversation_id=conversation_id).order_by(DirectChatMessage.id.desc()).first()
    return last_message.id if last_message else None


def mark_conversation_read(conversation_id, user_id):
    membership = get_membership(conversation_id, user_id)
    if not membership:
        return

    latest_message_id = get_latest_message_id(conversation_id)
    if latest_message_id is None:
        return

    if membership.last_read_message_id != latest_message_id:
        membership.last_read_message_id = latest_message_id
        db.session.commit()

    # After updating this member's last_read, check if ALL members have seen the latest message.
    try:
        # Recompute latest in case of concurrent writes
        latest_message_id = get_latest_message_id(conversation_id)
        if latest_message_id is None:
            return

        members = ConversationMember.query.filter_by(conversation_id=conversation_id).all()
        if not members:
            return

        all_seen = True
        for m in members:
            if not m.last_read_message_id or m.last_read_message_id < latest_message_id:
                all_seen = False
                break

        if all_seen:
            message = DirectChatMessage.query.get(latest_message_id)
            if message and not message.all_read:
                message.all_read = True
                db.session.commit()
                # Notify clients in the conversation room that the message was read by all
                socketio.emit('direct:message-all-read', {
                    'conversation_id': conversation_id,
                    'message_id': latest_message_id
                }, room=conversation_room_name(conversation_id))
    except Exception:
        # Non-critical; ignore failures in all-read bookkeeping
        pass


def get_unread_message_count(conversation_id, user_id, last_read_message_id):
    query = DirectChatMessage.query.filter(
        DirectChatMessage.conversation_id == conversation_id,
        DirectChatMessage.sender_id != user_id
    )
    if last_read_message_id:
        query = query.filter(DirectChatMessage.id > last_read_message_id)
    return query.count()


def get_direct_unread_total(user_id):
    if not user_id:
        return 0

    memberships = ConversationMember.query.filter_by(user_id=user_id).all()
    total = 0
    for membership in memberships:
        conversation = membership.conversation
        if not conversation:
            continue
        total += get_unread_message_count(
            conversation_id=conversation.id,
            user_id=user_id,
            last_read_message_id=membership.last_read_message_id
        )
    return total


@app.context_processor
def inject_global_unread_counters():
    # Compute whether the Direct (messaging) UI should be enabled for the
    # current session/user. This takes into account the global feature flag
    # (`DIRECT_ENABLED`), the admin-block (admins are intentionally blocked
    # from Direct in this project), and the temporary maintenance mode which
    # disables Direct for non-admins when `DIRECT_MAINTENANCE` is set.
    try:
        direct_globally_disabled = is_direct_globally_disabled()
    except Exception:
        direct_globally_disabled = False

    user_id = session.get('user_id')

    # If Direct is globally disabled or the user is not authenticated, report
    # zero unread messages and mark the UI as disabled.
    if direct_globally_disabled or not user_id:
        return {'direct_unread_count': 0, 'direct_enabled': False}

    # By default assume enabled for the authenticated user, then apply
    # per-session restrictions (admin-block and temporary maintenance).
    direct_enabled_for_user = True
    try:
        if is_direct_blocked_for_system_admin() or is_direct_temporarily_disabled_for_users():
            direct_enabled_for_user = False
    except Exception:
        # on error be conservative and keep it disabled
        direct_enabled_for_user = False

    return {
        'direct_unread_count': get_direct_unread_total(user_id),
        'direct_enabled': direct_enabled_for_user
    }


def build_direct_inbox_items(current_user_id, current_filter='all', search_query='', for_api=False):
    current_user = User.query.get(current_user_id)
    if not current_user:
        return []

    memberships = ConversationMember.query.filter_by(user_id=current_user_id).all()
    conversations = []

    for membership in memberships:
        conversation = membership.conversation
        if not conversation:
            continue
        if conversation.is_group:
            synchronized = ensure_group_conversation(conversation.slug)
            if not synchronized:
                continue
            conversation = synchronized
            if not get_membership(conversation.id, current_user_id):
                continue
        if not can_user_access_group_conversation(conversation, current_user):
            continue

        members = get_group_members(conversation.id)
        last_message = DirectChatMessage.query.filter_by(conversation_id=conversation.id).order_by(DirectChatMessage.id.desc()).first()


        time_value = last_message.created_at if last_message and last_message.created_at else conversation.created_at
        item = {
            'id': conversation.id,
            'conversation_id': conversation.id,
            'slug': conversation.slug,
            'direct_key': conversation.slug,
            'is_group': bool(conversation.is_group),
            'title': '',
            'subtitle': '',
            'preview': 'Sem mensagens ainda.',
            'avatar_pic': None,
            'avatar_text': 'D',
            'time': time_value,
            'last_message': serialize_direct_message(last_message, current_user_id) if last_message else None,
            'members_count': len(members)
        }

        unread_count = get_unread_message_count(conversation.id, current_user_id, membership.last_read_message_id)
        item['unread_count'] = unread_count
        item['is_unread'] = unread_count > 0

        if conversation.is_group:
            title = (conversation.title or conversation.slug or 'grupo').strip()
            item['title'] = title
            item['subtitle'] = f'{len(members)} participantes'
            item['preview'] = last_message.content if last_message and last_message.content else 'Grupo criado.'
            item['avatar_pic'] = conversation.group_photo
            item['avatar_text'] = title[0].upper() if title else 'G'
        else:
            other_member = next((member for member in members if member.user_id != current_user_id and member.user), None)
            if not other_member:
                continue
            item['direct_key'] = other_member.user.username
            item['title'] = '@' + other_member.user.username
            item['subtitle'] = other_member.user.name or ''
            item['avatar_pic'] = other_member.user.profile_pic
            item['avatar_text'] = other_member.user.username[0].upper() if other_member.user.username else 'U'
            if last_message and last_message.content:
                prefix = 'Voce: ' if last_message.sender_id == current_user_id else ''
                item['preview'] = prefix + last_message.content

        if not item['direct_key']:
            continue

        if search_query:
            searchable = (item['title'] + ' ' + item['subtitle'] + ' ' + item['preview']).lower()
            if search_query not in searchable:
                continue

        if current_filter == 'unread' and not item['is_unread']:
            continue

        conversations.append(item)

    conversations.sort(key=lambda convo: convo['time'] or datetime.min, reverse=True)

    if for_api:
        for item in conversations:
            item['time'] = item['time'].isoformat() if item.get('time') else None

    return conversations

@app.route('/direct')
def direct():
    if 'user_id' not in session:
        return redirect(url_for('welcome'))
    if is_direct_blocked_for_system_admin():
        flash('Conta administradora do sistema nao possui acesso ao Direct.')
        return redirect(url_for('feed'))

    current_filter = (request.args.get('filter') or 'all').strip().lower()
    if current_filter not in {'all', 'unread'}:
        current_filter = 'all'
    search_query = (request.args.get('q') or '').strip().lower()

    current_user_id = session.get('user_id')
    conversations = build_direct_inbox_items(
        current_user_id=current_user_id,
        current_filter=current_filter,
        search_query=search_query,
        for_api=False
    )

    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    return render_template(
        'direct.html',
        unread_count=unread,
        conversations=conversations,
        current_filter=current_filter,
        search_query=search_query
        , direct_enabled=app.config.get('DIRECT_ENABLED', True)
    )


@app.route('/api/direct/conversations')
def api_direct_conversations():
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_filter = (request.args.get('filter') or 'all').strip().lower()
    if current_filter not in {'all', 'unread'}:
        current_filter = 'all'
    search_query = (request.args.get('q') or '').strip().lower()

    payload = build_direct_inbox_items(
        current_user_id=session.get('user_id'),
        current_filter=current_filter,
        search_query=search_query,
        for_api=True
    )
    return jsonify(payload)


@app.route('/api/direct/conversations/<int:conversation_id>/messages')
def api_direct_messages(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    membership = get_membership(conversation_id, current_user_id)
    current_user = User.query.get(current_user_id)
    conversation = Conversation.query.get(conversation_id)
    if not membership or not can_user_access_group_conversation(conversation, current_user):
        return jsonify({'error': 'acesso negado'}), 403

    messages = DirectChatMessage.query.filter_by(conversation_id=conversation_id).order_by(DirectChatMessage.id.asc()).all()
    mark_conversation_read(conversation_id, current_user_id)
    return jsonify({
        'messages': [serialize_direct_message(msg, current_user_id) for msg in messages],
        'pinned_message': get_conversation_pinned_message(conversation_id, current_user_id)
    })


@app.route('/api/direct/conversations/<int:conversation_id>/read', methods=['POST'])
def api_direct_mark_read(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    membership = get_membership(conversation_id, current_user_id)
    current_user = User.query.get(current_user_id)
    conversation = Conversation.query.get(conversation_id)
    if not membership or not can_user_access_group_conversation(conversation, current_user):
        return jsonify({'error': 'acesso negado'}), 403

    mark_conversation_read(conversation_id, current_user_id)
    return jsonify({'ok': True})


@app.route('/api/direct/conversations/<int:conversation_id>/pin', methods=['PATCH'])
def api_direct_pin_message(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    membership = get_membership(conversation_id, current_user_id)
    current_user = User.query.get(current_user_id)
    conversation = Conversation.query.get(conversation_id)
    if not membership or not can_user_access_group_conversation(conversation, current_user):
        return jsonify({'error': 'acesso negado'}), 403
    if not conversation:
        return jsonify({'error': 'conversa nao encontrada'}), 404

    payload = request.get_json(silent=True) or {}
    raw_message_id = payload.get('message_id')
    pinned_payload = None

    if raw_message_id is None:
        conversation.pinned_message_id = None
    else:
        try:
            message_id = int(raw_message_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'mensagem invalida'}), 400

        message = DirectChatMessage.query.filter_by(id=message_id, conversation_id=conversation_id).first()
        if not message:
            return jsonify({'error': 'mensagem nao encontrada'}), 404
        conversation.pinned_message_id = message.id
        pinned_payload = serialize_direct_message(message, current_user_id)

    db.session.commit()

    if pinned_payload is None:
        pinned_payload = get_conversation_pinned_message(conversation_id, current_user_id)

    socketio.emit('direct:pinned-updated', {
        'conversation_id': conversation_id,
        'pinned_message': pinned_payload
    }, room=conversation_room_name(conversation_id))
    return jsonify({'ok': True, 'pinned_message': pinned_payload})


@app.route('/api/direct/conversations/<int:conversation_id>/members')
def api_direct_members(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    membership = get_membership(conversation_id, current_user_id)
    current_user = User.query.get(current_user_id)
    conversation = Conversation.query.get(conversation_id)
    if not membership or not can_user_access_group_conversation(conversation, current_user):
        return jsonify({'error': 'acesso negado'}), 403

    conversation = Conversation.query.get_or_404(conversation_id)
    if not conversation.is_group:
        return jsonify({'error': 'conversa nao e grupo'}), 400

    return jsonify({'members': build_members_payload(conversation_id)})


@app.route('/api/direct/conversations/<int:conversation_id>/messages', methods=['POST'])
def api_direct_send_message(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    membership = get_membership(conversation_id, current_user_id)
    current_user = User.query.get(current_user_id)
    conversation = Conversation.query.get(conversation_id)
    if not membership or not can_user_access_group_conversation(conversation, current_user):
        return jsonify({'error': 'acesso negado'}), 403

    payload = request.get_json(silent=True) or {}
    content = (payload.get('content') or '').strip()
    if not content:
        return jsonify({'error': 'mensagem vazia'}), 400
    if len(content) > 500:
        return jsonify({'error': 'mensagem muito longa'}), 400

    import time
    t0 = time.time()
    message = DirectChatMessage(conversation_id=conversation_id, sender_id=current_user_id, content=content)
    db.session.add(message)
    db.session.flush()

    sender_user = User.query.get(current_user_id)
    sender_label = sender_user.username if sender_user else (session.get('username') or 'usuario')
    recipients = ConversationMember.query.filter(
        ConversationMember.conversation_id == conversation_id,
        ConversationMember.user_id != current_user_id
    ).all()

    # Batch notifications to avoid commit per-recipient (performance improvement)
    pending_notifs = []
    for recipient in recipients:
        pending_notifs.append(Notification(
            user_id=recipient.user_id,
            sender_name=sender_label,
            action_type='enviou uma mensagem no DM',
            category='direct'
        ))
        db.session.add(pending_notifs[-1])

    sender_membership = get_membership(conversation_id, current_user_id)
    if sender_membership:
        sender_membership.last_read_message_id = message.id

    db_commit_start = time.time()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to commit direct message and notifications')
        return jsonify({'error': 'falha ao enviar mensagem'}), 500
    db_commit_end = time.time()

    serialized = serialize_direct_message(message, current_user_id)

    # Emit message and notifications asynchronously so the request doesn't block on socket I/O
    try:
        # Broadcast message to conversation room in background
        def _emit_message(payload, room):
            try:
                socketio.emit('direct:message', payload, room=room)
            except Exception:
                app.logger.exception('Failed to emit direct:message')

        socketio.start_background_task(_emit_message, serialize_direct_message_broadcast(message), conversation_room_name(conversation_id))

        # Emit notification:new for each created notification in background
        def _emit_notifications(notifs):
            for n in notifs:
                try:
                    payload = {
                        'id': n.id,
                        'user_id': n.user_id,
                        'sender_name': n.sender_name,
                        'action_type': n.action_type,
                        'post_id': n.post_id,
                        'is_read': n.is_read,
                        'category': n.category,
                        'timestamp': n.timestamp.isoformat() if n.timestamp else None
                    }
                    socketio.emit('notification:new', payload, room=f'user:{n.user_id}')
                except Exception:
                    app.logger.exception('Failed to emit notification for user %s', getattr(n, 'user_id', None))

        socketio.start_background_task(_emit_notifications, pending_notifs)
    except Exception:
        app.logger.exception('Failed to start background emit tasks')

    socketio_emit_end = time.time()
    t1 = time.time()
    app.logger.info(f"[PERF] POST /api/direct/conversations/{conversation_id}/messages total: {(t1-t0)*1000:.1f}ms | commit: {(db_commit_end-db_commit_start)*1000:.1f}ms | socketio-bg: {(socketio_emit_end-db_commit_end)*1000:.1f}ms")
    return jsonify({'message': serialized}), 201


@app.route('/api/direct/conversations/<int:conversation_id>/group', methods=['PATCH'])
def api_direct_update_group(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    conversation = Conversation.query.get_or_404(conversation_id)
    if not conversation.is_group:
        return jsonify({'error': 'conversa nao e grupo'}), 400
    if not can_manage_group(conversation_id, current_user_id):
        return jsonify({'error': 'apenas administrador do grupo pode editar o grupo'}), 403

    payload = request.get_json(silent=True) or {}
    title = payload.get('title')
    if title is not None:
        clean_title = (title or '').strip()
        if not clean_title:
            return jsonify({'error': 'nome do grupo vazio'}), 400
        conversation.title = clean_title[:80]

    group_photo = payload.get('group_photo')
    if group_photo is not None:
        conversation.group_photo = (group_photo or '').strip() or None

    db.session.commit()
    emit_group_updated(conversation)
    return jsonify({'ok': True, 'title': conversation.title, 'group_photo': conversation.group_photo})


@app.route('/api/direct/conversations/<int:conversation_id>/members', methods=['POST'])
def api_direct_add_member(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    conversation = Conversation.query.get_or_404(conversation_id)
    if not conversation.is_group:
        return jsonify({'error': 'conversa nao e grupo'}), 400
    if not can_manage_group(conversation_id, current_user_id):
        return jsonify({'error': 'apenas administrador do grupo pode gerenciar membros'}), 403

    payload = request.get_json(silent=True) or {}
    username = (payload.get('username') or '').strip().lower().replace('@', '')
    if not username:
        return jsonify({'error': 'usuario invalido'}), 400

    current_user = User.query.get(current_user_id)
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'usuario nao encontrado'}), 404
    if get_membership(conversation_id, user.id):
        return jsonify({'error': 'usuario ja esta no grupo'}), 400
    if not users_follow_each_other(current_user, user):
        return jsonify({'error': 'Para adicionar alguém ao grupo, é necessário que ambos se sigam mutuamente.'}), 400

    db.session.add(ConversationMember(conversation_id=conversation_id, user_id=user.id, is_admin=False))
    db.session.commit()
    emit_group_members_updated(conversation_id)
    # Notify the added user in realtime
    try:
        create_notification(user_id=user.id, sender_name=current_user.username, action_type='foi adicionado ao grupo', category='group')
    except Exception:
        pass
    return jsonify({'ok': True, 'username': user.username}), 201


@app.route('/api/direct/conversations/<int:conversation_id>/members/<username>', methods=['DELETE'])
def api_direct_remove_member(conversation_id, username):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    conversation = Conversation.query.get_or_404(conversation_id)
    if not conversation.is_group:
        return jsonify({'error': 'conversa nao e grupo'}), 400
    if not can_manage_group(conversation_id, current_user_id):
        return jsonify({'error': 'apenas administrador do grupo pode gerenciar membros'}), 403

    target_user = User.query.filter_by(username=(username or '').strip().lower()).first()
    if not target_user:
        return jsonify({'error': 'usuario nao encontrado'}), 404
    if target_user.id == current_user_id:
        return jsonify({'error': 'use a opcao sair do grupo para remover a si mesmo'}), 400

    membership = get_membership(conversation_id, target_user.id)
    if not membership:
        return jsonify({'error': 'usuario nao esta no grupo'}), 404

    if membership.is_admin:
        admin_count = ConversationMember.query.filter_by(conversation_id=conversation_id, is_admin=True).count()
        if admin_count <= 1:
            return jsonify({'error': 'o grupo precisa de ao menos um administrador'}), 400

    db.session.delete(membership)
    db.session.commit()
    emit_group_members_updated(conversation_id)
    # Notify the removed user
    try:
        create_notification(user_id=target_user.id, sender_name=User.query.get(current_user_id).username, action_type='foi removido do grupo', category='group')
    except Exception:
        pass
    return jsonify({'ok': True})


@app.route('/api/direct/conversations/<int:conversation_id>/leave', methods=['POST'])
def api_direct_leave_group(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    conversation = Conversation.query.get_or_404(conversation_id)
    if not conversation.is_group:
        return jsonify({'error': 'conversa nao e grupo'}), 400

    membership = get_membership(conversation_id, current_user_id)
    if not membership:
        return jsonify({'error': 'usuario nao esta no grupo'}), 404

    other_members = ConversationMember.query.filter(
        ConversationMember.conversation_id == conversation_id,
        ConversationMember.user_id != current_user_id
    ).order_by(ConversationMember.joined_at.asc(), ConversationMember.id.asc()).all()

    if membership.is_admin:
        has_other_admin = any(member.is_admin for member in other_members)
        if not has_other_admin and other_members:
            other_members[0].is_admin = True

    db.session.delete(membership)

    if not other_members:
        db.session.delete(conversation)
        db.session.commit()
        return jsonify({'ok': True, 'redirect_url': url_for('direct')})

    db.session.commit()
    emit_group_members_updated(conversation_id)
    # Notify remaining members that this user left (batch notifications)
    try:
        leaving_user = User.query.get(current_user_id)
        for m in other_members:
            # Add notifications to the session without committing each time
            create_notification(user_id=m.user_id, sender_name=leaving_user.username if leaving_user else '', action_type='saiu do grupo', category='group', commit=False)
        # commit the pending notifications
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        # Non-fatal: ignore notification failures
        pass
    return jsonify({'ok': True, 'redirect_url': url_for('direct')})


@app.route('/api/direct/conversations/<int:conversation_id>/members/<username>/admin', methods=['PATCH'])
def api_direct_set_member_admin(conversation_id, username):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    conversation = Conversation.query.get_or_404(conversation_id)
    if not conversation.is_group:
        return jsonify({'error': 'conversa nao e grupo'}), 400
    if not can_manage_group(conversation_id, current_user_id):
        return jsonify({'error': 'apenas administrador do grupo pode gerenciar membros'}), 403

    target_user = User.query.filter_by(username=(username or '').strip().lower()).first()
    if not target_user:
        return jsonify({'error': 'usuario nao encontrado'}), 404

    membership = get_membership(conversation_id, target_user.id)
    if not membership:
        return jsonify({'error': 'usuario nao esta no grupo'}), 404

    payload = request.get_json(silent=True) or {}
    next_is_admin = bool(payload.get('is_admin'))

    if membership.is_admin and not next_is_admin:
        admin_count = ConversationMember.query.filter_by(conversation_id=conversation_id, is_admin=True).count()
        if admin_count <= 1:
            return jsonify({'error': 'o grupo precisa de ao menos um administrador'}), 400

    membership.is_admin = next_is_admin
    db.session.commit()
    emit_group_members_updated(conversation_id)
    return jsonify({'ok': True, 'username': target_user.username, 'is_admin': membership.is_admin})

@app.route('/direct/conversa/<username>')
def direct_conversation(username):
    if 'user_id' not in session:
        return redirect(url_for('welcome'))
    if is_direct_blocked_for_system_admin():
        flash('Conta administradora do sistema nao possui acesso ao Direct.')
        return redirect(url_for('feed'))

    import time
    t0 = time.time()
    clean_username = (username or '').strip().lower()
    if not clean_username:
        return redirect(url_for('direct'))

    # Canonical URL: conversation mode is resolved server-side, not via query params.
    if request.args:
        return redirect(url_for('direct_conversation', username=clean_username), code=302)

    current_user = User.query.get(session.get('user_id'))
    if not current_user:
        session.clear()
        return redirect(url_for('welcome'))

    group_conversation = ensure_group_conversation(clean_username)
    is_group_chat = bool(group_conversation)
    current_username = (session.get('username') or '').strip().lower()

    if is_group_chat:
        conversation = group_conversation
        membership = get_membership(conversation.id, current_user.id)
        if not membership or not can_user_access_group_conversation(conversation, current_user):
            flash('Voce nao participa deste grupo.')
            return redirect(url_for('direct'))
        is_group_admin = bool(membership.is_admin)
        target_username = conversation.title or conversation.slug or clean_username
        creator_membership = ConversationMember.query.filter_by(conversation_id=conversation.id).order_by(
            ConversationMember.joined_at.asc(),
            ConversationMember.id.asc()
        ).first()
        group_creator_username = creator_membership.user.username if creator_membership and creator_membership.user else ''
    else:
        target_user = User.query.filter_by(username=clean_username).first()
        if not target_user:
            flash('Conversa nao encontrada.')
            return redirect(url_for('direct'))
        conversation = get_or_create_dm_conversation(current_user.id, target_user.id)
        is_group_admin = False
        target_username = target_user.username
        group_creator_username = ''

    target_initial = target_username[0].upper() if target_username else 'U'

    # Opening the conversation marks all current messages as read for this user.
    mark_conversation_read(conversation.id, current_user.id)

    members = get_group_members(conversation.id)
    participant_usernames = [member.user.username for member in members if member.user]

    participant_cards = []
    for member in members:
        user_obj = member.user
        if not user_obj:
            continue
        participant_cards.append({
            'username': user_obj.username,
            'profile_pic': user_obj.profile_pic if user_obj else None,
            'is_admin': bool(member.is_admin)
        })

    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    resp = render_template(
        'direct_conversation.html',
        unread_count=unread,
        conversation_id=conversation.id,
        current_user_id=current_user.id,
        target_username=target_username,
        target_initial=target_initial,
        is_group_chat=is_group_chat,
        is_group_admin=is_group_admin,
        group_creator_username=group_creator_username,
        participant_usernames=participant_usernames,
        participant_cards=participant_cards
        , direct_enabled=app.config.get('DIRECT_ENABLED', True)
    )
    t1 = time.time()
    print(f"[PERF] /direct/conversa/{{username}} total: {{(t1-t0)*1000:.1f}}ms")
    return resp
    # NOTE: render_template already returns the response above; ensure direct_enabled passed via context

# Register blueprints
from routes.feed import feed_bp
from routes.perfil import perfil_bp
from routes.direct import direct_bp

app.register_blueprint(feed_bp)
app.register_blueprint(perfil_bp)
app.register_blueprint(direct_bp)

@socketio.on('connect')
def handle_socket_connect():
    user_id = session.get('user_id')
    # Deny socket connections when Direct is globally disabled, or when the
    # session is invalid or access is blocked by maintenance/admin rules.
    if (not user_id
            or is_direct_globally_disabled()
            or is_direct_blocked_for_system_admin()
            or is_direct_temporarily_disabled_for_users()):
        return False

    online_user_connections[user_id] = online_user_connections.get(user_id, 0) + 1
    if online_user_connections[user_id] == 1:
        user = User.query.get(user_id)
        emit_presence_for_user(user, True)
    # Join a personal room so we can push user-specific notifications
    try:
        join_room(f'user:{user_id}')
    except Exception:
        pass
    emit('direct:connected', {'ok': True})


@socketio.on('disconnect')
def handle_socket_disconnect():
    user_id = session.get('user_id')
    if not user_id:
        return
    current = online_user_connections.get(user_id, 0)
    if current <= 1:
        online_user_connections.pop(user_id, None)
        user = User.query.get(user_id)
        emit_presence_for_user(user, False)
    else:
        online_user_connections[user_id] = current - 1


@socketio.on('direct:join')
def handle_direct_join(payload):
    user_id = session.get('user_id')
    if (not user_id
            or is_direct_globally_disabled()
            or is_direct_blocked_for_system_admin()
            or is_direct_temporarily_disabled_for_users()):
        emit('direct:error', {'error': 'acesso negado'})
        return

    data = payload or {}
    try:
        conversation_id = int(data.get('conversation_id'))
    except (TypeError, ValueError):
        emit('direct:error', {'error': 'conversa invalida'})
        return

    membership = get_membership(conversation_id, user_id)
    user = User.query.get(user_id)
    conversation = Conversation.query.get(conversation_id)
    if not membership or not can_user_access_group_conversation(conversation, user):
        emit('direct:error', {'error': 'acesso negado'})
        return

    room = conversation_room_name(conversation_id)
    join_room(room)
    emit('direct:joined', {'conversation_id': conversation_id})


@socketio.on('direct:leave')
def handle_direct_leave(payload):
    # If Direct is globally disabled there's nothing to do here.
    if is_direct_globally_disabled():
        return

    data = payload or {}
    try:
        conversation_id = int(data.get('conversation_id'))
    except (TypeError, ValueError):
        return
    leave_room(conversation_room_name(conversation_id))


@socketio.on('direct:typing')
def handle_direct_typing(payload):
    user_id = session.get('user_id')
    if (not user_id
            or is_direct_globally_disabled()
            or is_direct_blocked_for_system_admin()
            or is_direct_temporarily_disabled_for_users()):
        return

    data = payload or {}
    try:
        conversation_id = int(data.get('conversation_id'))
    except (TypeError, ValueError):
        return

    membership = get_membership(conversation_id, user_id)
    user = User.query.get(user_id)
    conversation = Conversation.query.get(conversation_id)
    if not membership or not can_user_access_group_conversation(conversation, user):
        return

    if not user:
        return

    socketio.emit('direct:typing', {
        'conversation_id': conversation_id,
        'username': user.username,
        'is_typing': bool(data.get('is_typing'))
    }, room=conversation_room_name(conversation_id))


def get_message_reaction_summary(message_id):
    rows = db.session.query(MessageReaction.reaction, func.count(MessageReaction.id)).filter(MessageReaction.message_id == message_id).group_by(MessageReaction.reaction).all()
    reactions = {r[0]: r[1] for r in rows}
    reactors = {}
    for reaction in reactions.keys():
        users = db.session.query(User.username).join(MessageReaction, User.id == MessageReaction.user_id).filter(MessageReaction.message_id == message_id, MessageReaction.reaction == reaction).all()
        reactors[reaction] = [u[0] for u in users]
    return {'reactions': reactions, 'reactors': reactors}


@socketio.on('direct:react')
def handle_direct_react(payload):
    user_id = session.get('user_id')
    if (not user_id
            or is_direct_globally_disabled()
            or is_direct_blocked_for_system_admin()
            or is_direct_temporarily_disabled_for_users()):
        emit('direct:error', {'error': 'acesso negado'})
        return

    data = payload or {}
    try:
        conversation_id = int(data.get('conversation_id'))
        message_id = int(data.get('message_id'))
    except (TypeError, ValueError):
        emit('direct:error', {'error': 'dados inválidos'})
        return
    reaction = (data.get('reaction') or '').strip()
    if not reaction:
        emit('direct:error', {'error': 'reação invalida'})
        return

    membership = get_membership(conversation_id, user_id)
    user = User.query.get(user_id)
    conversation = Conversation.query.get(conversation_id)
    if not membership or not can_user_access_group_conversation(conversation, user):
        emit('direct:error', {'error': 'acesso negado'})
        return

    message = DirectChatMessage.query.get(message_id)
    if not message or message.conversation_id != conversation_id:
        emit('direct:error', {'error': 'mensagem nao encontrada'})
        return

    try:
        existing = MessageReaction.query.filter_by(message_id=message_id, user_id=user_id).first()
        if existing and existing.reaction == reaction:
            db.session.delete(existing)
        elif existing:
            existing.reaction = reaction
        else:
            db.session.add(MessageReaction(message_id=message_id, user_id=user_id, reaction=reaction))
        db.session.commit()
    except Exception:
        db.session.rollback()
        emit('direct:error', {'error': 'falha ao registrar reacao'})
        return

    summary = get_message_reaction_summary(message_id)
    socketio.emit('direct:reaction-updated', {
        'conversation_id': conversation_id,
        'message_id': message_id,
        'reactions': summary['reactions'],
        'reactors': summary['reactors']
    }, room=conversation_room_name(conversation_id))

@app.route('/eventos')
def eventos():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    all_events = Event.query.order_by(Event.created_at.desc()).all()
    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    return render_template('eventos.html', events=all_events, unread_count=unread)

@app.route('/criar_evento', methods=['POST'])
def criar_evento():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    title = request.form.get('title')
    description = normalize_event_description(request.form.get('description'))
    date = request.form.get('date')
    time = request.form.get('time')
    location = request.form.get('location')

    if not (title or '').strip() or not description or not (location or '').strip():
        flash('Preencha todos os campos obrigatorios do evento.')
        return redirect(url_for('eventos'))

    _, datetime_error = parse_event_datetime(date, time)
    if datetime_error:
        flash(datetime_error)
        return redirect(url_for('eventos'))
    
    file = request.files.get('file'); filename = None
    if file and file.filename != '':
        ext = os.path.splitext(file.filename)[1]
        filename = str(uuid.uuid4()) + ext
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    full_date = f"{date} às {time}"
    new_event = Event(title=title, description=description, event_date=full_date, location=location, media_url=filename, user_id=session['user_id'])
    db.session.add(new_event)
    
    # Criar postagem no feed automaticamente
    event_content = build_event_post_content(title, location, full_date, description, session['username'])
    feed_post = Post(content=event_content, media_url=filename, user_id=session['user_id'], is_anonymous=False)
    db.session.add(feed_post)
    
    db.session.commit()
    return redirect(url_for('eventos'))


@app.route('/editar_evento/<int:event_id>', methods=['POST'])
def editar_evento(event_id):
    if 'user_id' not in session:
        return redirect(url_for('welcome'))

    event = Event.query.get_or_404(event_id)
    if event.user_id != session.get('user_id') and not session.get('is_admin'):
        return redirect(url_for('eventos'))

    old_title = event.title
    old_location = event.location
    old_event_date = event.event_date
    old_description = event.description

    title = (request.form.get('title') or '').strip()
    description = normalize_event_description(request.form.get('description'))
    date = (request.form.get('date') or '').strip()
    time = (request.form.get('time') or '').strip()
    location = (request.form.get('location') or '').strip()

    if not title or not description or not date or not time or not location:
        flash('Preencha todos os campos obrigatorios do evento.')
        return redirect(url_for('eventos'))

    _, datetime_error = parse_event_datetime(date, time)
    if datetime_error:
        flash(datetime_error)
        return redirect(url_for('eventos'))

    event.title = title[:100]
    event.description = description
    event.location = location[:100]
    event.event_date = f"{date} às {time}"

    sync_event_feed_post(event, old_title, old_location, old_event_date, old_description)
    db.session.commit()
    return redirect(url_for('eventos'))

@app.route('/excluir_evento/<int:event_id>')
def excluir_evento(event_id):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    event = Event.query.get_or_404(event_id)
    if event.user_id == session['user_id'] or session.get('is_admin'):
        db.session.delete(event)
        db.session.commit()
    return redirect(url_for('eventos'))

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('welcome'))

if __name__ == '__main__':
    socketio.run(app, debug=False)
