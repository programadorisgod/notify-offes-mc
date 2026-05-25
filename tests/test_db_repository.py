"""Tests for the SQLite repository layer."""

import pytest
import aiosqlite

from price_watch.db.connection import init_db, get_db
from price_watch.db.schema import SCHEMA_STATEMENTS


@pytest.fixture
async def db():
    """In-memory SQLite database for testing."""
    # Override path before any connection is created
    import price_watch.db.connection as conn
    conn._db = await aiosqlite.connect(":memory:")
    conn._db.row_factory = aiosqlite.Row

    for stmt in SCHEMA_STATEMENTS:
        await conn._db.execute(stmt)
    await conn._db.commit()

    yield conn._db

    await conn._db.close()
    conn._db = None


@pytest.mark.asyncio
async def test_add_and_get_product(db):
    from price_watch.db.repository import add_product, get_product

    pid = await add_product(
        item_id="MLA123",
        site_id="MLA",
        title="Test Product",
        permalink="https://mercadolibre.com/test-MLA123",
        thumbnail=None,
        currency_id="ARS",
        price=100.0,
    )
    assert pid > 0

    product = await get_product(pid)
    assert product is not None
    assert product["title"] == "Test Product"
    assert product["item_id"] == "MLA123"


@pytest.mark.asyncio
async def test_get_products_returns_active_only(db):
    from price_watch.db.repository import add_product, deactivate_product, get_products

    pid = await add_product("MLA1", "MLA", "Active", "url", None, "ARS", 50)
    await add_product("MLA2", "MLA", "Inactive", "url", None, "ARS", 60)
    await deactivate_product(pid + 1)

    products = await get_products()
    assert len(products) == 1
    assert products[0]["item_id"] == "MLA1"


@pytest.mark.asyncio
async def test_price_snapshot_and_history(db):
    from price_watch.db.repository import add_product, save_price_snapshot, get_price_history

    pid = await add_product("MLA99", "MLA", "History Test", "url", None, "ARS", 200)
    sid = await save_price_snapshot(pid, 180, original_price=200)
    assert sid > 0

    history = await get_price_history(pid)
    assert len(history) == 1
    assert history[0]["price"] == 180
