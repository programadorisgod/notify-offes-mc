"""APScheduler service for periodic price checks."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from price_watch.config import settings
from price_watch.scraper.ml_api import extract_price_data, fetch_item
from price_watch.db.repository import (
    get_all_products,
    get_latest_price,
    save_price_snapshot,
    save_alert,
    update_price_extremes,
)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def check_prices() -> None:
    """Check current prices for all active products and save snapshots.

    If a price dropped below the minimum, create an alert.
    """
    products = await get_all_products()
    if not products:
        logger.info("No active products to check.")
        return

    for product in products:
        # Use the original product URL for Apify scraping
        url = product.get("permalink") or f"https://www.mercadolibre.com/{product['item_id']}"
        logger.debug("Checking %s (%s)", product["title"], product["item_id"])

        data = await fetch_item(url)
        if data is None:
            logger.warning("Item %s not found or API error, skipping.", item_id)
            continue

        info = extract_price_data(data)
        current_price = info["price"]

        # Save price snapshot
        await save_price_snapshot(
            product_id=product["id"],
            price=current_price,
            original_price=info.get("original_price"),
            available_qty=info.get("available_quantity"),
            sold_qty=info.get("sold_quantity"),
        )

        # Update min/max
        await update_price_extremes(product["id"], current_price)

        # Check for price drop alert
        latest = await get_latest_price(product["id"])
        previous_price = latest["price"] if latest else None

        if previous_price is not None and current_price < previous_price:
            drop_pct = round(
                (previous_price - current_price) / previous_price * 100, 2
            )
            logger.info(
                "Price DROP for %s: %s → %s (-%s%%)",
                product["title"],
                previous_price,
                current_price,
                drop_pct,
            )
            await save_alert(
                product_id=product["id"],
                alert_type="price_drop",
                old_price=previous_price,
                new_price=current_price,
                drop_percent=drop_pct,
            )


def start_scheduler() -> None:
    """Start the APScheduler with the price-check job."""
    scheduler.add_job(
        check_prices,
        "interval",
        seconds=settings.check_interval_seconds,
        id="check_prices",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started — checking prices every %d seconds",
        settings.check_interval_seconds,
    )


def stop_scheduler() -> None:
    """Shut down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
