"""
Centraliza a importacao de todos os modelos SQLAlchemy.
"""

from .associations import followers, post_likes
from .user import User
from .post import Post, Comment
from .notification import Notification
from .message import Conversation, ConversationMember, DirectChatMessage, Message, MessageReaction
from .coupon import Coupon
from .mural import MuralPost
from .event import Event
