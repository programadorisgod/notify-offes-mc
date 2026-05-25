"""Tests for MercadoLibre URL parsing."""

from price_watch.scraper.url_parser import extract_item_id


def test_extract_catalog_url():
    """/p/MLA15485496 → MLA15485496"""
    url = "https://www.mercadolibre.com.ar/p/MLA15485496"
    assert extract_item_id(url) == "MLA15485496"


def test_extract_direct_listing():
    """/{title}-MLM3000123456 → MLM3000123456"""
    url = "https://www.mercadolibre.com/iphone-15-MLM3000123456"
    assert extract_item_id(url) == "MLM3000123456"


def test_extract_direct_with_query():
    """URL con query params → MLM3000123456"""
    url = "https://www.mercadolibre.com/iphone-15-MLM3000123456?quantity=1"
    assert extract_item_id(url) == "MLM3000123456"


def test_extract_raw_id():
    """Solo el item_id → MLA15485496"""
    assert extract_item_id("MLA15485496") == "MLA15485496"


def test_extract_brazil_id():
    """MLB prefix → MLB1234567890"""
    url = "https://www.mercadolibre.com.br/p/MLB1234567890"
    assert extract_item_id(url) == "MLB1234567890"


def test_extract_mexico_direct():
    """MLM prefix direct listing"""
    url = "https://www.mercadolibre.com.mx/samsung-galaxy-MLM987654321"
    assert extract_item_id(url) == "MLM987654321"


def test_invalid_url_returns_none():
    """URL sin ID de ML → None"""
    assert extract_item_id("https://www.google.com") is None


def test_empty_string_returns_none():
    assert extract_item_id("") is None


def test_whitespace_handling():
    """URL con espacios alrededor → funciona"""
    url = "  https://www.mercadolibre.com.ar/p/MLA15485496  "
    assert extract_item_id(url) == "MLA15485496"
