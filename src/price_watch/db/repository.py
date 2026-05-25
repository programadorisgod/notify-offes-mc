"""Data access layer for price-watch."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from price_watch.db.connection import get_db


# ── Products ──────────────────────────────────────────────────────────────


async def add_product(
    item_id: str,
    site_id: str,
    title: str,
    permalink: str,
    thumbnail: str | None,
    currency_id: str,
    price: float,
) -> int:
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO products (item_id, site_id, title, permalink, thumbnail,
                                 currency_id, initial_price, min_price, max_price)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (item_id, site_id, title, permalink, thumbnail, currency_id, price, price, price),
    )
    await db.commit()
    return cursor.lastrowid


async def get_products() -> list[dict[str, Any]]:
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


async def get_product_by_item_id(item_id: str) -> dict[str, Any] | None:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM products WHERE item_id = ?", (item_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def deactivate_product(product_id: int) -> None:
    db = await get_db()
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
