"""Shared utility functions – no circular dependencies."""

from datetime import datetime, timedelta


def br_time() -> datetime:
    """Brazilian time (UTC-3) helper. Safe to import from anywhere."""
    return datetime.utcnow() - timedelta(hours=3)
