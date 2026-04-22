from datetime import datetime, timedelta

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint


db = SQLAlchemy()


followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id')),
)


post_likes = db.Table(
    'post_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('post_id', db.Integer, db.ForeignKey('post.id')),
)


def br_time():
    return datetime.now() - timedelta(hours=3)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    university = db.Column(db.String(50), nullable=True)
    bio = db.Column(db.String(150), default="Estudante no Spotted University")
    profile_pic = db.Column(db.String(200), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=br_time, nullable=True)

    posts = db.relationship('Post', backref='author', lazy=True)
    notifications = db.relationship('Notification', backref='receiver', lazy=True, cascade='all, delete-orphan')
    followed = db.relationship(
        'User',
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic',
    )
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
    comments = db.relationship('Comment', backref='post', cascade='all, delete-orphan')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    content = db.Column(db.String(200), nullable=False)
    username = db.Column(db.String(80), default='Anonimo')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref='comments')
    timestamp = db.Column(db.DateTime, default=br_time)
    is_edited = db.Column(db.Boolean, default=False)


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


class MuralPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='Geral')
    contact_info = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=br_time)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref='mural_posts')

