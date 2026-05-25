"""Data access layer for price-watch."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from price_watch.db.connection import get_db


# ── Users / Auth ──────────────────────────────────────────────────────────

import hashlib
import os
import secrets


def _hash_password(password: str) -> str:
    """Hash a password with a random salt (sha256 + salt)."""
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${h}"


def _check_password(password: str, stored: str) -> bool:
    """Verify a password against a stored hash (salt$hash)."""
    try:
        salt, h = stored.split("$", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except (ValueError, AttributeError):
        return False


async def create_user(username: str, password: str, chat_id: int | None = None) -> int:
    """Create a new user. Raises ValueError if username taken."""
    db = await get_db()
    password_hash = _hash_password(password)
    try:
        cursor = await db.execute(
            "INSERT INTO users (username, password_hash, chat_id) VALUES (?, ?, ?)",
            (username, password_hash, chat_id),
        )
        await db.commit()
        return cursor.lastrowid
    except Exception as exc:
        raise ValueError("El nombre de usuario ya existe") from exc


async def authenticate_user(username: str, password: str) -> dict | None:
    """Verify credentials and return user dict or None."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    user = dict(row)
    if _check_password(password, user["password_hash"]):
        return user
    return None


async def get_user_by_chat(chat_id: int) -> dict | None:
    """Find a user linked to a Telegram chat."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM users WHERE chat_id = ?", (chat_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_user_by_id(user_id: int) -> dict | None:
    """Get user by primary key."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def link_chat_to_user(user_id: int, chat_id: int) -> None:
    """Link a Telegram chat to an existing user."""
    db = await get_db()
    await db.execute(
        "UPDATE users SET chat_id = ? WHERE id = ?",
        (chat_id, user_id),
    )
    await db.commit()


# ── Products ──────────────────────────────────────────────────────────────


async def add_product(
    item_id: str,
    site_id: str,
    title: str,
    permalink: str,
    thumbnail: str | None,
    currency_id: str,
    price: float,
    chat_id: int = 0,
) -> int:
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO products (item_id, site_id, title, permalink, thumbnail,
                                 currency_id, chat_id, initial_price, min_price, max_price)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (item_id, site_id, title, permalink, thumbnail, currency_id, chat_id, price, price, price),
    )
    await db.commit()
    return cursor.lastrowid


async def get_products(chat_id: int) -> list[dict[str, Any]]:
    """Get active products for a specific chat."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM products WHERE is_active = 1 AND chat_id = ? ORDER BY created_at DESC",
        (chat_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_all_products() -> list[dict[str, Any]]:
    """Get ALL active products (for scheduler/global operations)."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM products WHERE is_active = 1 ORDER BY created_at DESC"
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_product(product_id: int) -> dict[str, Any] | None:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_product_by_item_id(item_id: str, chat_id: int = 0) -> dict[str, Any] | None:
    """Get a product by item_id for a specific chat."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM products WHERE item_id = ? AND chat_id = ?",
        (item_id, chat_id),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def deactivate_product(product_id: int, chat_id: int = 0) -> None:
    """Deactivate a product. If chat_id is provided, only deactivate if owned by that chat."""
    db = await get_db()
    if chat_id:
        await db.execute(
            "UPDATE products SET is_active = 0, updated_at = datetime('now') WHERE id = ? AND chat_id = ?",
            (product_id, chat_id),
        )
    else:
        await db.execute(
            "UPDATE products SET is_active = 0, updated_at = datetime('now') WHERE id = ?",
            (product_id,),
        )
    await db.commit()


async def update_price_extremes(product_id: int, price: float) -> None:
    db = await get_db()
    await db.execute(
        """UPDATE products
           SET min_price = CASE WHEN ? < min_price THEN ? ELSE min_price END,
               max_price = CASE WHEN ? > max_price THEN ? ELSE max_price END,
               updated_at = datetime('now')
           WHERE id = ?""",
        (price, price, price, price, product_id),
    )
    await db.commit()


# ── Price History ─────────────────────────────────────────────────────────


async def save_price_snapshot(
    product_id: int,
    price: float,
    original_price: float | None = None,
    available_qty: int | None = None,
    sold_qty: int | None = None,
) -> int:
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO price_history (product_id, price, original_price,
                                       available_qty, sold_qty)
           VALUES (?, ?, ?, ?, ?)""",
        (product_id, price, original_price, available_qty, sold_qty),
    )
    await db.commit()
    return cursor.lastrowid


async def get_price_history(
    product_id: int, limit: int = 50
) -> list[dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        """SELECT * FROM price_history
           WHERE product_id = ?
           ORDER BY fetched_at DESC
           LIMIT ?""",
        (product_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_latest_price(product_id: int) -> dict[str, Any] | None:
    db = await get_db()
    cursor = await db.execute(
        """SELECT * FROM price_history
           WHERE product_id = ?
           ORDER BY fetched_at DESC
           LIMIT 1""",
        (product_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


# ── Alerts ────────────────────────────────────────────────────────────────


async def save_alert(
    product_id: int,
    alert_type: str,
    old_price: float | None = None,
    new_price: float | None = None,
    drop_percent: float | None = None,
) -> int:
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO alerts (product_id, alert_type, old_price, new_price, drop_percent)
           VALUES (?, ?, ?, ?, ?)""",
        (product_id, alert_type, old_price, new_price, drop_percent),
    )
    await db.commit()
    return cursor.lastrowid


async def get_recent_alerts(limit: int = 20) -> list[dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        """SELECT a.*, p.title, p.permalink, p.thumbnail
           FROM alerts a
           JOIN products p ON a.product_id = p.id
           ORDER BY a.sent_at DESC
           LIMIT ?""",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]
