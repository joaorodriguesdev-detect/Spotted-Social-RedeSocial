"""Compatibility wrapper: import models from the new `models` package."""

from models import (
    db,
    User,
    Post,
    Comment,
    Notification,
    Message,
    Conversation,
    ConversationMember,
    DirectChatMessage,
    MessageReaction,
    Event,
    MuralPost,
    followers,
    post_likes,
    br_time,
)

