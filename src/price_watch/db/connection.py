"""Async SQLite connection management."""

from __future__ import annotations

import aiosqlite

from price_watch.config import settings
from price_watch.db.schema import SCHEMA_STATEMENTS

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """Return the singleton database connection."""
    global _db
    if _db is None:
        _db = await aiosqlite.connect(settings.database_path)
        _db.row_factory = aiosqlite.Row
    return _db


MIGRATIONS = [
    # v0→v1: add chat_id column for multi-tenant support
    "ALTER TABLE products ADD COLUMN chat_id INTEGER NOT NULL DEFAULT 0",
]


async def init_db() -> None:
    """Create tables if they don't exist and run migrations."""
    db = await get_db()
    for stmt in SCHEMA_STATEMENTS:
        await db.execute(stmt)
    await db.commit()

    # Run migrations (safe to re-run — ALTER ADD COLUMN is a no-op if col exists)
    for migration in MIGRATIONS:
        try:
            await db.execute(migration)
        except Exception:
            pass  # column already exists
    await db.commit()


async def close_db() -> None:
    """Close the database connection."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
