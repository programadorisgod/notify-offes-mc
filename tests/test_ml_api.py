"""Tests for the MercadoLibre API client (Apify-based)."""

from __future__ import annotations

import pytest

from price_watch.scraper.ml_api import (
    _apify_item_to_dict,
    _extract_currency,
    _extract_keywords_from_url,
    _extract_site_id,
    _find_product,
    _parse_price,
    extract_price_data,
)


class TestParsePrice:
    def test_integer_string(self):
        assert _parse_price("653427") == 653427.0

    def test_with_currency_prefix(self):
        assert _parse_price("COP 670209") == 670209.0

    def test_none(self):
        assert _parse_price(None) == 0.0

    def test_empty_string(self):
        assert _parse_price("") == 0.0


class TestExtractCurrency:
    def test_cop(self):
        assert _extract_currency("COP $") == "COP"

    def test_ars(self):
        assert _extract_currency("ARS $") == "ARS"

    def test_empty(self):
        assert _extract_currency(None) == ""
        assert _extract_currency("") == ""


class TestExtractSiteId:
    def test_argentina(self):
        assert _extract_site_id("https://www.mercadolibre.com.ar/p/MLA123") == "MLA"

    def test_colombia(self):
        assert _extract_site_id("https://www.mercadolibre.com.co/p/MCO456") == "MCO"

    def test_mexico(self):
        assert _extract_site_id("https://www.mercadolibre.com.mx/p/MLM789") == "MLM"

    def test_chile(self):
        assert _extract_site_id("https://www.mercadolibre.cl/p/MLC111") == "MLC"

    def test_no_match(self):
        assert _extract_site_id("https://example.com/item") == ""


class TestFindProduct:
    def test_sku_match(self):
        items = [
            {"SKU": "MCO123", "articuloTitulo": "Test", "nuevoPrecio": "100"},
            {"SKU": "MCO456", "articuloTitulo": "Other", "nuevoPrecio": "200"},
        ]
        result = _find_product(items, "MCO456", "https://ml.com/test")
        assert result is not None
        assert result["SKU"] == "MCO456"

    def test_url_match(self):
        items = [
            {"SKU": "MCO123", "articuloTitulo": "Test", "zdireccion": "https://ml.com/test-product/p/MCO123"},
        ]
        result = _find_product(items, "MCO123", "https://ml.com/test-product/p/MCO123")
        assert result is not None

    def test_no_match_returns_none(self):
        items = [{"SKU": "MCO123", "articuloTitulo": "Test", "nuevoPrecio": "100"}]
        result = _find_product(items, "MCO999", "https://ml.com/other")
        assert result is None

    def test_empty_items(self):
        assert _find_product([], "MCO123", "https://ml.com/test") is None


class TestExtractKeywords:
    def test_colombia_desk(self):
        url = "https://www.mercadolibre.com.co/escritorio-electrico-cougar-e-star-140-color-negro/p/MCO53975362"
        assert _extract_keywords_from_url(url) == "escritorio electrico cougar e star 140 color negro"

    def test_argentina_samsung(self):
        url = "https://www.mercadolibre.com.ar/samsung-galaxy-s23-128gb-negro/p/MLA123456"
        assert _extract_keywords_from_url(url) == "samsung galaxy s23 128gb negro"

    def test_chile(self):
        url = "https://www.mercadolibre.cl/macbook-air-m2-256gb/p/MLC789012"
        assert _extract_keywords_from_url(url) == "macbook air m2 256gb"

    def test_basic_p_url(self):
        url = "https://www.mercadolibre.com.mx/p/MLM123"
        assert _extract_keywords_from_url(url) == ""

    def test_generic_url(self):
        assert _extract_keywords_from_url("https://example.com") == ""


class TestApifyItemToDict:
    def test_full_conversion(self):
        apify_item = {
            "SKU": "MCO2070727165",
            "articuloTitulo": "Estructura Eléctrica De Escritorio Ergear",
            "nuevoPrecio": "653427",
            "precioAnterior": "787281",
            "Moneda": "COP $",
            "imgDireccion": "https://http2.mlstatic.com/img.jpg",
            "zdireccion": "https://www.mercadolibre.com.co/p/MCO2070727165",
        }
        result = _apify_item_to_dict(apify_item, "MCO2070727165", "https://www.mercadolibre.com.co/p/MCO2070727165")
        assert result["item_id"] == "MCO2070727165"
        assert result["site_id"] == "MCO"
        assert result["title"] == "Estructura Eléctrica De Escritorio Ergear"
        assert result["price"] == 653427.0
        assert result["original_price"] == 787281.0
        assert result["currency_id"] == "COP"
        assert result["thumbnail"] == "https://http2.mlstatic.com/img.jpg"
        assert result["permalink"] == "https://www.mercadolibre.com.co/p/MCO2070727165"

    def test_minimal(self):
        apify_item = {"SKU": "MLA999", "articuloTitulo": "Minimal", "nuevoPrecio": "100"}
        result = _apify_item_to_dict(apify_item, "MLA999", "https://ml.com/p/MLA999")
        assert result["item_id"] == "MLA999"
        assert result["price"] == 100.0
        assert result["original_price"] is None


class TestExtractPriceData:
    def test_passthrough(self):
        data = {"item_id": "MCO123", "price": 100.0}
        assert extract_price_data(data) is data
