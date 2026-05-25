"""Telegram bot command handlers for NotifyOffersMc."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from price_watch.bot.notifier import register_chat
from price_watch.db.repository import (
    add_product,
    deactivate_product,
    get_product,
    get_product_by_item_id,
    get_products,
)
from price_watch.scraper.ml_api import extract_price_data, fetch_item
from price_watch.scraper.url_parser import extract_item_id

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message and register chat for notifications."""
    if update.effective_chat:
        register_chat(update.effective_chat.id)
    await update.message.reply_text(
        "👋 Hola! Soy NotifyOffersMc — te aviso cuando bajan los precios en "
        "MercadoLibre.\n\n"
        "Comandos:\n"
        "/add <url> — agregar producto a trackear\n"
        "/list — ver productos trackeados\n"
        "/remove <id> — dejar de trackear\n"
        "/price <id> — ver historial de precios"
    )


async def cmd_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a MercadoLibre product URL to track."""
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

    # Check if already tracked
    existing = await get_product_by_item_id(item_id)
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
    )

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
    """List all tracked products."""
    products = await get_products()
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
    if not ctx.args:
        await update.message.reply_text("Usá: /remove <id>")
        return

    try:
        pid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("El ID debe ser un número.")
        return

    product = await get_product(pid)
    if not product:
        await update.message.reply_text(
            "No encontré un producto con ese ID. Usá /list para ver tus IDs."
        )
        return

    await deactivate_product(pid)
    await update.message.reply_text(f"🗑️ Dejé de trackear: {product['title'][:50]}...")


async def cmd_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Show price history for a product."""
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
    if not product:
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
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("price", cmd_price))

    return app
