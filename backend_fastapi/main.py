"""FastAPI application – main entry point.

Migrated from Flask (app.py) with:
  • CORS enabled for localhost:3000
  • JWT authentication via httpOnly cookies
  • APIRouter-based route organisation (instead of Blueprints)
  • async def route handlers
  • Pydantic schemas for request/response (instead of jsonify)
  • Async SQLAlchemy engine
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from database import Base, engine, async_session_factory

# ── Logger setup ───────────────────────────────────────────────────────
def _configure_logger() -> None:
    log_path = Path(settings.SPOTTED_ERROR_LOG)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(str(log_path))
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


_configure_logger()
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan: reset DB schema on every startup.

    WARNING: drop_all + create_all destroys all data.
    Remove drop_all in production; use Alembic migrations instead.
    """
    logger.info("Resetting database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All tables recreated from scratch.")

    # ── Optional: seed admin user ──────────────────────────────────────
    if settings.ADMIN_SEED_ENABLED:
        from passlib.hash import bcrypt
        from sqlalchemy import select

        from models import User # Import from models/__init__.py

        async with async_session_factory() as session:
            result = await session.execute(
                select(User).where(User.username == settings.ADMIN_USERNAME)
            )
            admin = result.scalar_one_or_none()
            if not admin and settings.ADMIN_PASSWORD:
                admin = User(
                    name="Spotted Social",
                    username=settings.ADMIN_USERNAME,
                    password_hash=bcrypt.hash(settings.ADMIN_PASSWORD),
                    is_admin=True,
                    bio="Sistema",
                )
                session.add(admin)
                await session.commit()
                logger.info("Admin user seeded: %s", settings.ADMIN_USERNAME)

    yield  # ── Application runs here ──────────────────────────────────

    logger.info("Shutting down…")
    await engine.dispose()


# ── FastAPI instance ───────────────────────────────────────────────────
app = FastAPI(
    title="Spotted Social – FastAPI Migration",
    description="API backend migrada de Flask para FastAPI, preparada para Next.js.",
    version="1.0.0",
    lifespan=lifespan,
)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  MIDDLEWARES                                                         ║
# ╚══════════════════════════════════════════════════════════════════════╝

# ── CORS – permite o frontend Next.js em localhost:3000 ────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Static files – sirva arquivos enviados (uploads) ───────────────────
UPLOADS_DIR = Path(settings.UPLOAD_FOLDER)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


# ── Optional: global exception handler ─────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Log unhandled exceptions and return a generic 500."""
    logger.exception("Unhandled exception at %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor."},
    )


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  ROUTES (APIRouters)                                                 ║
# ╚══════════════════════════════════════════════════════════════════════╝

from routes.auth import router as auth_router
from routes.cupons import router as cupons_router
from routes.mural import router as mural_router
from routes.feed import router as feed_router
from routes.upload import router as upload_router
from routes.social import router as social_router
from routes.perfil import router as perfil_router
from routes.notifications import router as notifications_router
from routes.chat import router as chat_router
from routes.admin import router as admin_router
from routes.events import router as events_router
from routes.users import router as users_router

app.include_router(auth_router)
app.include_router(cupons_router)
app.include_router(mural_router)
app.include_router(feed_router)
app.include_router(upload_router)
app.include_router(social_router)
app.include_router(perfil_router)
app.include_router(notifications_router)
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(events_router)
app.include_router(users_router)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  ROOT HEALTH-CHECK                                                    ║
# ╚══════════════════════════════════════════════════════════════════════╝

@app.get("/", tags=["health"])
async def root():
    """Health check – the frontend can hit this to verify the API is up."""
    return {
        "status": "ok",
        "app": "Spotted Social API",
        "version": "1.0.0",
        "docs": "/docs",
    }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  ENTRY POINT (for `python main.py`)                                  ║
# ╚══════════════════════════════════════════════════════════════════════╝

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("APP_AUTO_RELOAD", "true").strip().lower() in ("1", "true", "yes")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload_enabled,
        log_level="info",
    )
