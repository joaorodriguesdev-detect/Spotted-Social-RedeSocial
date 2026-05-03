"""Enumeradores padronizados para o projeto.

Usar enum.Enum do Python evita erros de digitação em strings soltas
e garante consistência entre models, schemas e rotas.
"""

import enum


class MuralCategory(str, enum.Enum):
    """Categorias permitidas para anúncios no Mural de Recados."""
    EMPREGO = "Emprego"
    SAUDE = "Saúde"
    GERAL = "Geral"
    EDUCACAO = "Educação"
    MORADIA = "Moradia"
    EVENTOS = "Eventos"
    CARONA = "Carona"


class NotificationCategory(str, enum.Enum):
    """Categorias de notificação."""
    GENERAL = "general"
    MURAL = "mural"
    FOLLOW = "follow"
    DM = "dm"
    LIKE = "like"
    COMMENT = "comment"


class CouponStatus(str, enum.Enum):
    """Status de um cupom."""
    ACTIVE = "active"
    EXPIRED = "expired"
    DISABLED = "disabled"
    DEPLETED = "depleted"  # atingiu o limite de usos


class EventCategory(str, enum.Enum):
    """Categorias para eventos."""
    FESTA = "Festa"
    PALESTRA = "Palestra"
    WORKSHOP = "Workshop"
    ESPORTE = "Esporte"
    CULTURA = "Cultura"
    OUTRO = "Outro"
