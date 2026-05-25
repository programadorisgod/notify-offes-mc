"""Tests for the scheduler service."""

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_check_prices_no_products():
    """check_prices no debe fallar cuando no hay productos activos."""
    with patch("price_watch.scheduler.service.get_products", return_value=[]):
        from price_watch.scheduler.service import check_prices
        # Should not raise any exception
        await check_prices()


@pytest.mark.asyncio
async def test_check_prices_with_product():
    """check_prices procesa un producto activo correctamente."""
    fake_product = {
        "id": 1,
        "item_id": "MLA123",
        "title": "Test",
    }
    fake_item = {
        "id": "MLA123",
        "site_id": "MLA",
        "title": "Test Product",
        "permalink": "https://ml.com/test-MLA123",
        "currency_id": "ARS",
        "price": 150.0,
        "original_price": 200.0,
        "available_quantity": 10,
        "sold_quantity": 5,
    }

    with (
        patch("price_watch.scheduler.service.get_products", return_value=[fake_product]),
        patch("price_watch.scheduler.service.fetch_item", return_value=fake_item),
        patch("price_watch.scheduler.service.save_price_snapshot", return_value=1),
        patch("price_watch.scheduler.service.update_price_extremes"),
        patch("price_watch.scheduler.service.get_latest_price", return_value=None),
    ):
        from price_watch.scheduler.service import check_prices
        await check_prices()
