"""App configuration using pydantic-settings for environment variables."""

import os
from datetime import timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
_profile = (os.getenv("SPOTTED_ENV", "dev") or "dev").strip().lower()
_profile_file = BASE_DIR / f".env.{_profile}"
if _profile_file.exists():
    load_dotenv(_profile_file, override=True)


class Settings(BaseSettings):
    # ── Security ──────────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_DAYS: int = int(os.getenv("SESSION_EXPIRE_DAYS", "7"))
    JWT_COOKIE_NAME: str = "access_token"
    JWT_COOKIE_SECURE: bool = os.getenv("JWT_COOKIE_SECURE", "false").strip().lower() in ("1", "true", "yes")
    JWT_COOKIE_SAMESITE: str = "Lax"

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./instance/spotted.db")

    # ── CORS ──────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"]
    CORS_CREDENTIALS: bool = True

    # ── Uploads ───────────────────────────────────────────────────────
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "static/uploads")
    PUBLIC_FOLDER: str = os.getenv("PUBLIC_FOLDER", "static/public")
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH", str(30 * 1024 * 1024)))

    # ── Feature Flags ─────────────────────────────────────────────────
    DIRECT_ENABLED: bool = True
    FEED_PAGE_SIZE: int = int(os.getenv("FEED_PAGE_SIZE", "8"))
    ADMIN_SEED_ENABLED: bool = False
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = ""

    # ── Logging ───────────────────────────────────────────────────────
    SPOTTED_ERROR_LOG: str = os.getenv("SPOTTED_ERROR_LOG", "instance/error.log")

    # ── Session ──────────────────────────────────────────────────────
    @property
    def ACCESS_TOKEN_EXPIRE_DELTA(self) -> timedelta:
        return timedelta(days=self.JWT_ACCESS_TOKEN_EXPIRE_DAYS)

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


settings = Settings()
