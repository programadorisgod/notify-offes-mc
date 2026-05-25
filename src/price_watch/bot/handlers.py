"""Telegram bot command handlers for NotifyOffersMc."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from price_watch.bot.notifier import register_chat, register_product_chat
from price_watch.db.repository import (
    add_product,
    authenticate_user,
    create_user,
    deactivate_product,
    get_product,
    get_product_by_item_id,
    get_products,
    get_user_by_chat,
    link_chat_to_user,
)
from price_watch.scraper.ml_api import extract_price_data, fetch_item
from price_watch.scraper.url_parser import extract_item_id

logger = logging.getLogger(__name__)


async def _auth_guard(update: Update) -> int | None:
    """Return chat_id if the chat is linked to a user, else None and send a message."""
    chat_id = update.effective_chat.id if update.effective_chat else 0
    user = await get_user_by_chat(chat_id) if chat_id else None
    if user is None:
        await update.message.reply_text(
            "⚠️ Primero tenés que iniciar sesión.\n"
            "Registrate: /register <usuario> <contraseña>\n"
            "O ingresá: /login <usuario> <contraseña>"
        )
    return user["id"] if user else None


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message and register chat for notifications."""
    if update.effective_chat:
        register_chat(update.effective_chat.id)

    user = await get_user_by_chat(update.effective_chat.id) if update.effective_chat else None
    status = f"✅ Logueado como *{user['username']}*" if user else "❌ No has iniciado sesión"

    await update.message.reply_text(
        f"👋 Hola! Soy NotifyOffersMc — te aviso cuando bajan los precios en "
        f"MercadoLibre.\n\n{status}\n\n"
        "Comandos:\n"
        "/register <user> <pass> — crear cuenta\n"
        "/login <user> <pass> — iniciar sesión\n"
        "/add <url> — agregar producto\n"
        "/list — ver productos\n"
        "/remove <id> — dejar de trackear\n"
        "/price <id> — ver historial"
    )


async def cmd_register(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Register a new user and link this chat."""
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text("Usá: /register <usuario> <contraseña>")
        return

    username, password = ctx.args[0], " ".join(ctx.args[1:])
    try:
        await create_user(username, password, chat_id=chat_id)
        # Register for notifications
        register_chat(chat_id)
        await update.message.reply_text(
            f"✅ Cuenta *{username}* creada con éxito.\n"
            "Ya podés usar /add, /list, etc.\n\n"
            "También podés ingresar desde la web con las mismas credenciales."
        )
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_login(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Login and link this chat to an existing user."""
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text("Usá: /login <usuario> <contraseña>")
        return

    username, password = ctx.args[0], " ".join(ctx.args[1:])
    user = await authenticate_user(username, password)
    if user is None:
        await update.message.reply_text("❌ Usuario o contraseña incorrectos.")
        return

    await link_chat_to_user(user["id"], chat_id)
    register_chat(chat_id)
    await update.message.reply_text(
        f"✅ Sesión iniciada como *{username}*.\n"
        "Este chat queda vinculado a tu cuenta."
    )


async def cmd_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a MercadoLibre product URL to track."""
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if not await _auth_guard(update):
        return

    if not ctx.args:
        await update.message.reply_text(
            "Usá: /add <url de MercadoLibre>\n"
            "Ej: /add https://www.mercadolibre.com.ar/p/MLA15485496"
        )
        return

    url = " ".join(ctx.args)
    item_id = extract_item_id(url)
    if not item_id:
        await update.message.reply_text(
            "No pude extraer el ID de producto de esa URL. "
            "Asegurate que sea una URL válida de MercadoLibre."
        )
        return

    # Check if already tracked by THIS chat
    existing = await get_product_by_item_id(item_id, chat_id=chat_id)
    if existing:
        await update.message.reply_text(
            f"⚠️ Ese producto ya está siendo trackeado (ID: {existing['id']}).\n"
            f"Usá /list para ver tus productos."
        )
        return

    # Send feedback immediately — Apify tarda ~20-60s
    msg = await update.message.reply_text(
        "🔍 Buscando producto en MercadoLibre... "
        "Puede tardar hasta 1 minuto."
    )

    # Fetch using the FULL URL, not just the item_id
    data = await fetch_item(url)
    if data is None:
        await msg.edit_text(
            "❌ No encontré ese producto en MercadoLibre. "
            "Revisá que el link sea correcto."
        )
        return

    info = extract_price_data(data)
    pid = await add_product(
        item_id=info["item_id"],
        site_id=info["site_id"],
        title=info["title"],
        permalink=info["permalink"],
        thumbnail=info.get("thumbnail"),
        currency_id=info["currency_id"],
        price=info["price"],
        chat_id=chat_id,
    )

    # Register for notifications
    register_product_chat(pid, chat_id)

    # Format price nicely
    price_str = f"${info['price']:,.0f}".replace(",", ".")
    orig = info.get("original_price")
    discount = ""
    if orig and orig > info["price"]:
        pct = round((orig - info["price"]) / orig * 100)
        discount = f"  (antes ${orig:,.0f} — {pct}% OFF)".replace(",", ".")

    await msg.edit_text(
        f"✅ Agregado!\n\n"
        f"{info['title']}\n"
        f"Precio actual: {price_str} {info['currency_id']}{discount}\n"
        f"ID: {pid}\n\n"
        f"Te voy a avisar si baja de precio."
    )


async def cmd_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """List products tracked by this chat."""
    if not await _auth_guard(update):
        return
    chat_id = update.effective_chat.id if update.effective_chat else 0
    products = await get_products(chat_id)
    if not products:
        await update.message.reply_text(
            "No tenés productos trackeados todavía.\n"
            "Agregá uno con: /add <url>"
        )
        return

    lines = ["📋 Productos trackeados:\n"]
    for p in products:
        min_p = f"${p['min_price']:,.0f}".replace(",", ".")
        max_p = f"${p['max_price']:,.0f}".replace(",", ".")
        title = p["title"][:60] + "..." if len(p["title"]) > 60 else p["title"]
        lines.append(f"  {p['id']}. {title}")
        lines.append(f"     Precio: {min_p} — {max_p} {p['currency_id']}")
        if p.get("permalink"):
            lines.append(f"     {p['permalink']}")
        lines.append("")
    await update.message.reply_text("\n".join(lines))


async def cmd_remove(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop tracking a product."""
    if not await _auth_guard(update):
        return
    chat_id = update.effective_chat.id if update.effective_chat else 0

    if not ctx.args:
        await update.message.reply_text("Usá: /remove <id>")
        return

    try:
        pid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("El ID debe ser un número.")
        return

    product = await get_product(pid)
    if not product or product.get("chat_id", 0) != chat_id:
        await update.message.reply_text(
            "No encontré un producto con ese ID. Usá /list para ver tus IDs."
        )
        return

    await deactivate_product(pid, chat_id=chat_id)
    await update.message.reply_text(f"🗑️ Dejé de trackear: {product['title'][:50]}...")


async def cmd_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Show price history for a product."""
    if not await _auth_guard(update):
        return
    chat_id = update.effective_chat.id if update.effective_chat else 0

    if not ctx.args:
        await update.message.reply_text("Usá: /price <id>")
        return

    try:
        pid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("El ID debe ser un número.")
        return

    from price_watch.db.repository import get_price_history

    product = await get_product(pid)
    if not product or product.get("chat_id", 0) != chat_id:
        await update.message.reply_text("Producto no encontrado.")
        return

    history = await get_price_history(pid, limit=10)
    if not history:
        await update.message.reply_text(
            f"{product['title'][:50]}...\n"
            "Todavía no hay historial de precios."
        )
        return

    title = product["title"][:60] + "..." if len(product["title"]) > 60 else product["title"]
    min_p = f"${product['min_price']:,.0f}".replace(",", ".")
    max_p = f"${product['max_price']:,.0f}".replace(",", ".")

    lines = [
        f"📊 {title}\n"
        f"Rango: {min_p} — {max_p}\n"
    ]
    for h in history:
        p = f"${h['price']:,.0f}".replace(",", ".")
        lines.append(f"  {p} ({h['fetched_at']})")
    await update.message.reply_text("\n".join(lines))


def build_bot(token: str) -> Application:
    """Create and configure the Telegram bot application."""
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("register", cmd_register))
    app.add_handler(CommandHandler("login", cmd_login))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("price", cmd_price))

    return app
