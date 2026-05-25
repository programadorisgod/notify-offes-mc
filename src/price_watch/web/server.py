"""FastAPI web server — routes and dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from price_watch.db.repository import (
    add_product,
    deactivate_product,
    get_price_history,
    get_product,
    get_product_by_item_id,
    get_products,
    get_recent_alerts,
)
from price_watch.scraper.ml_api import extract_price_data, fetch_item
from price_watch.scraper.url_parser import extract_item_id

HERE = Path(__file__).resolve().parent

app = FastAPI(title="Price Watch")
templates = Jinja2Templates(directory=str(HERE / "templates"))
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")


@app.get("/")
async def dashboard(request: Request):
    """Main dashboard — list tracked products and recent alerts."""
    products = await get_products()
    alerts = await get_recent_alerts(limit=10)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"products": products, "alerts": alerts},
    )


@app.post("/products")
async def add_product_route(request: Request, url: str = Form(...)):
    """Add a new product by MercadoLibre URL."""
    item_id = extract_item_id(url)
    if not item_id:
        raise HTTPException(400, "No se pudo extraer el ID de producto de la URL.")

    # Check if already tracked
    existing = await get_product_by_item_id(item_id)
    if existing:
        raise HTTPException(409, "Ese producto ya está siendo trackeado.")

    # Scrape the page
    data = await fetch_item(url)
    if data is None:
        raise HTTPException(404, "Producto no encontrado en MercadoLibre.")

    await add_product(
        item_id=data["item_id"],
        site_id=data["site_id"],
        title=data["title"],
        permalink=data["permalink"],
        thumbnail=data.get("thumbnail"),
        currency_id=data["currency_id"],
        price=data["price"],
    )

    return RedirectResponse(url="/", status_code=303)


@app.get("/products/{product_id}")
async def product_detail(request: Request, product_id: int):
    """Show price history for a single product."""
    product = await get_product(product_id)
    if not product:
        raise HTTPException(404, "Producto no encontrado.")

    history = await get_price_history(product_id, limit=100)
    return templates.TemplateResponse(
        request,
        "product_detail.html",
        {"product": product, "history": history},
    )


@app.post("/products/{product_id}/delete")
async def delete_product(product_id: int):
    """Deactivate a tracked product."""
    product = await get_product(product_id)
    if not product:
        raise HTTPException(404, "Producto no encontrado.")

    await deactivate_product(product_id)
    return RedirectResponse(url="/", status_code=303)
