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
        chat_id=12345,
    )
    assert pid > 0

    product = await get_product(pid)
    assert product is not None
    assert product["title"] == "Test Product"
    assert product["item_id"] == "MLA123"
    assert product["chat_id"] == 12345


@pytest.mark.asyncio
async def test_get_products_by_chat(db):
    from price_watch.db.repository import add_product, get_products, get_all_products

    pid1 = await add_product("MLA1", "MLA", "Chat A", "url", None, "ARS", 50, chat_id=111)
    await add_product("MLA2", "MLA", "Chat B", "url", None, "ARS", 60, chat_id=222)

    chat_a_products = await get_products(111)
    assert len(chat_a_products) == 1
    assert chat_a_products[0]["item_id"] == "MLA1"

    chat_b_products = await get_products(222)
    assert len(chat_b_products) == 1
    assert chat_b_products[0]["item_id"] == "MLA2"

    all_products = await get_all_products()
    assert len(all_products) == 2


@pytest.mark.asyncio
async def test_get_products_returns_active_only(db):
    from price_watch.db.repository import add_product, deactivate_product, get_products

    pid = await add_product("MLA1", "MLA", "Active", "url", None, "ARS", 50, chat_id=111)
    await add_product("MLA2", "MLA", "Inactive", "url", None, "ARS", 60, chat_id=111)
    await deactivate_product(pid + 1, chat_id=111)

    products = await get_products(111)
    assert len(products) == 1
    assert products[0]["item_id"] == "MLA1"


@pytest.mark.asyncio
async def test_chat_cannot_see_other_chat_products(db):
    from price_watch.db.repository import add_product, get_products

    await add_product("MLA1", "MLA", "Chat A", "url", None, "ARS", 50, chat_id=111)
    await add_product("MLA2", "MLA", "Chat B", "url", None, "ARS", 60, chat_id=222)

    assert len(await get_products(111)) == 1
    assert len(await get_products(333)) == 0


@pytest.mark.asyncio
async def test_price_snapshot_and_history(db):
    from price_watch.db.repository import add_product, save_price_snapshot, get_price_history

    pid = await add_product("MLA99", "MLA", "History Test", "url", None, "ARS", 200, chat_id=111)
    sid = await save_price_snapshot(pid, 180, original_price=200)
    assert sid > 0

    history = await get_price_history(pid)
    assert len(history) == 1
    assert history[0]["price"] == 180
