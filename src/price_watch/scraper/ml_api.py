"""MercadoLibre product data via Apify actor task.

Uses a pre-configured Apify task to scrape MercadoLibre product pages.
No OAuth or API tokens needed — all scraping complexity is handled by Apify.

Strategy:
  1. First try ``startUrls`` with the product URL → search results → match by SKU
  2. If not found, extract keywords from the URL path → ``keyword`` search → match by SKU
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from price_watch.config import settings

logger = logging.getLogger(__name__)

APIFY_TOKEN = settings.apify_token
APIFY_TASK_ID = settings.apify_task_id
APIFY_RUN_TIMEOUT = 120  # seconds to wait for task completion


async def fetch_item(url: str) -> dict[str, Any] | None:
    """Scrape a MercadoLibre product page via Apify.

    Args:
        url: Full MercadoLibre product URL.

    Returns a flat dict with keys matching our DB schema, or None on failure.
    """
    if not APIFY_TOKEN or not APIFY_TASK_ID:
        logger.error("APIFY_TOKEN or APIFY_TASK_ID not set.")
        return None

    from price_watch.scraper.url_parser import extract_item_id

    target_id = extract_item_id(url)
    headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}

    async with httpx.AsyncClient(headers=headers, timeout=APIFY_RUN_TIMEOUT) as client:
        # --- Attempt 1: startUrls search ---
        items = await _apify_search(client, {"startUrls": [url]})
        match = _find_product(items, target_id, url) if items else None

        # --- Attempt 2: keyword search from URL path ---
        if not match:
            keywords = _extract_keywords_from_url(url)
            if keywords:
                logger.info("Retrying with keywords: %s", keywords)
                items = await _apify_search(client, {"keyword": keywords, "maxPages": 1})
                match = _find_product(items, target_id, url) if items else None

        if not match:
            logger.warning("Product not found in Apify results: %s", url)
            return None

        return _apify_item_to_dict(match, target_id, url)


async def _apify_search(
    client: httpx.AsyncClient, input_data: dict[str, Any]
) -> list[dict[str, Any]] | None:
    """Run the Apify task with given input and return result items."""
    resp = await client.post(
        f"https://api.apify.com/v2/actor-tasks/{APIFY_TASK_ID}/run-sync-get-dataset-items",
        params={"format": "json"},
        json=input_data,
    )

    if resp.status_code not in (200, 201):
        logger.error("Apify task failed: %s %s", resp.status_code, resp.text[:300])
        return None

    items = resp.json()
    if not isinstance(items, list):
        logger.warning("Unexpected Apify response type: %s", type(items).__name__)
        return None

    return items


def _extract_keywords_from_url(url: str) -> str:
    """Extract search keywords from a MercadoLibre product URL path.

    Example:
      ``/escritorio-electrico-cougar-e-star-140-color-negro/p/MCO53975362``
      → ``escritorio electrico cougar e star 140``
    """
    path = urlparse(url).path
    # Remove trailing /p/ITEM_ID or /up/... segment
    path = re.sub(r"/(p|up)/\w+$", "", path)
    # Remove leading slash, convert dashes to spaces, trim
    keywords = path.lstrip("/").replace("-", " ").strip()
    # Keep the most significant part (first 50 chars)
    return keywords[:60] if keywords else ""


def _find_product(
    items: list[dict[str, Any]], target_id: str | None, url: str
) -> dict[str, Any] | None:
    """Find the matching product in Apify results by SKU or URL."""
    # Prefer exact SKU match
    if target_id:
        for item in items:
            sku = item.get("SKU", "")
            if sku == target_id:
                return item

    # Fallback: URL match in zdireccion
    for item in items:
        product_url = item.get("zdireccion", "")
        if product_url and (product_url == url or product_url.rstrip("/") == url.rstrip("/")):
            return item

    return None


def _parse_price(text: str | None) -> float:
    """Parse a price string like '653427' or '670.209' into a float."""
    if not text:
        return 0.0
    cleaned = re.sub(r"[^\d]", "", text)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _extract_currency(moneda: str | None) -> str:
    """Extract currency code from Moneda field like 'COP $' or 'ARS $'."""
    if not moneda:
        return ""
    return moneda.split()[0] if moneda.split() else ""


def _apify_item_to_dict(
    item: dict[str, Any], item_id: str | None, url: str
) -> dict[str, Any]:
    """Convert Apify output format to our DB schema dict."""
    price = _parse_price(item.get("nuevoPrecio"))
    original_price = _parse_price(item.get("precioAnterior")) or None

    site_id = _extract_site_id(url)

    return {
        "item_id": item.get("SKU") or item_id or "",
        "site_id": site_id,
        "title": item.get("articuloTitulo", "").strip(),
        "permalink": item.get("zdireccion") or url,
        "thumbnail": item.get("imgDireccion"),
        "currency_id": _extract_currency(item.get("Moneda")),
        "price": price,
        "original_price": original_price,
        "available_quantity": None,  # not available from Apify
        "sold_quantity": None,
    }


def _extract_site_id(url: str) -> str:
    """Guess the MercadoLibre site ID from the URL domain."""
    match = re.search(r"mercadolibre\.([a-z.]+)", url)
    if match:
        tld = match.group(1).rstrip("/")
        tld_to_site = {
            "com.ar": "MLA",
            "com.bo": "MBO",
            "com.br": "MLB",
            "cl": "MLC",
            "com.co": "MCO",
            "com.cr": "MCR",
            "com.do": "MRD",
            "com.ec": "MEC",
            "com.gt": "MGT",
            "hn": "MHN",
            "com.mx": "MLM",
            "com.ni": "MNI",
            "com.pa": "MPA",
            "com.py": "MPY",
            "com.pe": "MPE",
            "com.sv": "MSV",
            "com.uY": "MLU",
            "com.ve": "MLV",
        }
        return tld_to_site.get(tld, "")
    return ""


def extract_price_data(data: dict[str, Any]) -> dict[str, Any]:
    """Passthrough — the scraper already returns the right shape."""
    return data
