"""Startup database migrations – ensures missing columns exist.

Mirrors backend/services/startup_service.py but with async SQLAlchemy.

This is a lightweight alternative to Alembic for development.
In production, use proper migration tools.
"""

import logging
from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


# List of (table, column, type) to add if missing
_COLUMNS_TO_ENSURE: List[Tuple[str, str, str]] = [
    ("user", "social_link", "VARCHAR(200)"),
    ("user", "is_banned", "BOOLEAN DEFAULT 0"),
]


async def run_startup_migrations(engine: AsyncEngine) -> None:
    """Check and add missing columns to existing tables."""
    for table, column, col_type in _COLUMNS_TO_ENSURE:
        try:
            async with engine.connect() as conn:
                # Check if column exists (SQLite compatible)
                result = await conn.execute(
                    text(f"PRAGMA table_info({table})")
                )
                columns = [row[1] for row in result]
                if column not in columns:
                    await conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                    )
                    await conn.commit()
                    logger.info("Added column %s.%s (%s)", table, column, col_type)
        except Exception as exc:
            logger.warning("Could not add column %s.%s: %s", table, column, exc)
