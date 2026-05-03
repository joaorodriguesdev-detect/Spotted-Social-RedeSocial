"""MuralPost model (classified ads / mural de avisos)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base
from utils import br_time
from .enums import MuralCategory


class MuralPost(Base):
    __tablename__ = "mural_post"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, default=MuralCategory.GERAL.value)
    contact_info = Column(String(200), nullable=False)
    timestamp = Column(DateTime, default=br_time)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    author = relationship("User", back_populates="mural_posts")
