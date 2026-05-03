"""Configuração do banco de dados SQLAlchemy (assíncrono).

Este arquivo centraliza a criação do:
  - Engine (motor de conexão com o banco)
  - SessionLocal (fábrica de sessões)
  - Base (classe base para os modelos declarativos)
  - get_db (dependência FastAPI para injetar sessões nas rotas)
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import settings

# 1. Engine: Objeto que gerencia a conexão com o banco de dados.
#    A URL de conexão é lida das configurações (variáveis de ambiente).
engine = create_async_engine(
    settings.DATABASE_URL,
    # echo=True,  # Descomente para ver os comandos SQL gerados pelo SQLAlchemy
)

# 2. Session Factory: Fábrica para criar novas sessões de banco de dados.
#    Usamos async_sessionmaker para sessões assíncronas.
async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,  # Importante para FastAPI
    class_=AsyncSession,
)

# 3. Base: Classe base para todos os modelos ORM (ex: User, Post).
#    Todos os seus modelos (em models/) devem herdar desta classe.
class Base(DeclarativeBase):
    pass

# 4. get_db: Dependência do FastAPI para gerenciar o ciclo de vida da sessão.
#    - Abre uma sessão para cada requisição.
#    - Faz commit se a requisição for bem-sucedida.
#    - Faz rollback se ocorrer um erro.
#    - Fecha a sessão ao final, liberando a conexão.
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get a DB session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
