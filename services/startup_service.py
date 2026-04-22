from flask import current_app
from sqlalchemy import inspect
from werkzeug.security import generate_password_hash

from models import User, db, br_time


def ensure_user_created_at_column():
    inspector = inspect(db.engine)
    user_columns = {col['name'] for col in inspector.get_columns('user')}
    if 'created_at' in user_columns:
        return
    with db.engine.begin() as conn:
        conn.exec_driver_sql('ALTER TABLE user ADD COLUMN created_at DATETIME')


def ensure_user_is_verified_column():
    inspector = inspect(db.engine)
    user_columns = {col['name'] for col in inspector.get_columns('user')}
    if 'is_verified' in user_columns:
        return
    with db.engine.begin() as conn:
        conn.exec_driver_sql('ALTER TABLE user ADD COLUMN is_verified BOOLEAN DEFAULT 0')


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
        conn.exec_driver_sql('ALTER TABLE direct_chat_message ADD COLUMN all_read BOOLEAN DEFAULT 0 NOT NULL')


def ensure_notification_category_column():
    inspector = inspect(db.engine)
    try:
        cols = {col['name'] for col in inspector.get_columns('notification')}
    except Exception:
        cols = set()
    if 'category' in cols:
        return
    with db.engine.begin() as conn:
        conn.exec_driver_sql("ALTER TABLE notification ADD COLUMN category VARCHAR(50) DEFAULT 'general'")


def ensure_comment_is_edited_column():
    inspector = inspect(db.engine)
    try:
        cols = {col['name'] for col in inspector.get_columns('comment')}
    except Exception:
        cols = set()
    if 'is_edited' in cols:
        return
    with db.engine.begin() as conn:
        conn.exec_driver_sql('ALTER TABLE comment ADD COLUMN is_edited BOOLEAN DEFAULT 0 NOT NULL')


def ensure_comment_user_id_column():
    inspector = inspect(db.engine)
    try:
        cols = {col['name'] for col in inspector.get_columns('comment')}
    except Exception:
        cols = set()
    if 'user_id' in cols:
        return
    with db.engine.begin() as conn:
        conn.exec_driver_sql('ALTER TABLE comment ADD COLUMN user_id INTEGER')


def initialize_database():
    db.create_all()
    ensure_user_created_at_column()
    ensure_user_is_verified_column()
    ensure_conversation_member_last_read_column()
    ensure_conversation_pinned_message_column()
    ensure_direct_chat_message_all_read_column()
    ensure_notification_category_column()
    ensure_comment_is_edited_column()
    ensure_comment_user_id_column()

    missing_created_at = User.query.filter(User.created_at.is_(None)).all()
    for user in missing_created_at:
        user.created_at = br_time()

    if current_app.config.get('ADMIN_SEED_ENABLED', False):
        admin_username = current_app.config.get('ADMIN_USERNAME', 'admin')
        admin_password = current_app.config.get('ADMIN_PASSWORD', '')

        admin_master = User.query.filter_by(username=admin_username).first()
        if not admin_master:
            if not admin_password:
                current_app.logger.warning('ADMIN_SEED_ENABLED=true, mas ADMIN_PASSWORD nao foi definido. Seed do admin ignorado.')
            else:
                nova_senha_hash = generate_password_hash(admin_password)
                admin_master = User(
                    name='Spotted Social',
                    username=admin_username,
                    password=nova_senha_hash,
                    is_admin=True,
                    bio='Sistema',
                )
                db.session.add(admin_master)

    db.session.commit()

