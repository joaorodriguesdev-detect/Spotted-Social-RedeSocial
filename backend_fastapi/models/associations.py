"""Association tables for many-to-many relationships.

Centralizado aqui para evitar duplicação de tabelas em Base.metadata
e quebras de circular import entre models/user.py e models/post.py.
"""

from sqlalchemy import Column, ForeignKey, Integer, Table

from database import Base


# ── Seguidores (User → User) ────────────────────────────────────────────
followers = Table(
    "followers",
    Base.metadata,
    Column("follower_id", Integer, ForeignKey("user.id")),
    Column("followed_id", Integer, ForeignKey("user.id")),
    extend_existing=True
)


# ── Likes em posts (User → Post) ────────────────────────────────────────
post_likes = Table(
    "post_likes",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("post_id", Integer, ForeignKey("post.id"), primary_key=True),
)
