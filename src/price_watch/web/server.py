"""FastAPI web server — routes and dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from price_watch.config import settings
from price_watch.db.repository import (
    add_product,
    authenticate_user,
    create_user,
    deactivate_product,
    get_all_products,
    get_price_history,
    get_product,
    get_product_by_item_id,
    get_products,
    get_recent_alerts,
    get_user_by_id,
)
from price_watch.scraper.ml_api import extract_price_data, fetch_item
from price_watch.scraper.url_parser import extract_item_id

HERE = Path(__file__).resolve().parent

app = FastAPI(title="Price Watch")
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
templates = Jinja2Templates(directory=str(HERE / "templates"))
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")


def _get_user(request: Request) -> dict | None:
    """Return the logged-in user from session, or None."""
    user_id = request.session.get("user_id")
    return None if user_id is None else {"id": user_id, "username": request.session.get("username")}


# ── Auth routes ───────────────────────────────────────────────────────────


@app.get("/login")
async def login_page(request: Request, error: str = ""):
    """Show login form."""
    user = _get_user(request)
    if user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": error})


@app.post("/login")
async def login_action(request: Request, username: str = Form(...), password: str = Form(...)):
    """Authenticate and set session."""
    user = await authenticate_user(username, password)
    if user is None:
        return RedirectResponse(url="/login?error=Usuario+o+contrase%C3%B1a+incorrectos", status_code=303)
    request.session["user_id"] = user["id"]
    request.session["username"] = user["username"]
    return RedirectResponse(url="/", status_code=303)


@app.get("/register")
async def register_page(request: Request, error: str = ""):
    """Show registration form."""
    user = _get_user(request)
    if user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request, "register.html", {"error": error})


@app.post("/register")
async def register_action(
    request: Request, username: str = Form(...), password: str = Form(...)
):
    """Create a new user and set session."""
    try:
        user_id = await create_user(username, password, chat_id=None)
    except ValueError as e:
        return RedirectResponse(url=f"/register?error={str(e)}", status_code=303)

    request.session["user_id"] = user_id
    request.session["username"] = username
    return RedirectResponse(url="/", status_code=303)


@app.get("/logout")
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


# ── Dashboard ─────────────────────────────────────────────────────────────


@app.get("/")
async def dashboard(request: Request):
    """Main dashboard — list my products and recent alerts."""
    user = _get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    # If user has no chat linked yet, show empty state
    full_user = await get_user_by_id(user["id"])
    chat_id = full_user["chat_id"] if full_user else None

    products = []
    alerts = []
    if chat_id:
        products = await get_products(chat_id)
        alerts = await get_recent_alerts(limit=10)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "products": products,
            "alerts": alerts,
            "user": user,
            "has_chat": chat_id is not None,
        },
    )


# ── API routes ────────────────────────────────────────────────────────────


@app.post("/api/products")
async def add_product_route(request: Request, url: str = Form(...)):
    """Add a new product by MercadoLibre URL (authenticated)."""
    user = _get_user(request)
    if user is None:
        raise HTTPException(401, "Not authenticated")

    full_user = await get_user_by_id(user["id"])
    chat_id = full_user["chat_id"] if full_user else None
    if chat_id is None:
        raise HTTPException(400, "Vinculá tu cuenta desde Telegram con /login <user> <pass>")

    item_id = extract_item_id(url)
    if not item_id:
        raise HTTPException(400, "No se pudo extraer el ID de producto de la URL.")

    # Check if already tracked by this user
    existing = await get_product_by_item_id(item_id, chat_id=chat_id)
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
        chat_id=chat_id,
    )

    return {"ok": True}


@app.get("/products/{product_id}")
async def product_detail(request: Request, product_id: int):
    """Show price history for a single product."""
    user = _get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    product = await get_product(product_id)
    if not product:
        raise HTTPException(404, "Producto no encontrado.")

    # Verify ownership
    full_user = await get_user_by_id(user["id"])
    if full_user and product.get("chat_id", 0) != full_user.get("chat_id", 0):
        raise HTTPException(403, "Ese producto no te pertenece.")

    history = await get_price_history(product_id, limit=100)
    return templates.TemplateResponse(
        request,
        "product_detail.html",
        {"product": product, "history": history, "user": user},
    )


@app.post("/products/{product_id}/delete")
async def delete_product_route(request: Request, product_id: int):
    """Deactivate a tracked product."""
    user = _get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    full_user = await get_user_by_id(user["id"])
    product = await get_product(product_id)
    if not product:
        raise HTTPException(404, "Producto no encontrado.")

    if full_user and product.get("chat_id", 0) != full_user.get("chat_id", 0):
        raise HTTPException(403, "Ese producto no te pertenece.")

    await deactivate_product(product_id, chat_id=product["chat_id"])
    return RedirectResponse(url="/", status_code=303)
