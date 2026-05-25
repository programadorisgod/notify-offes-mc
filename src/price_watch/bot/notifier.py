"""Notification dispatcher — forwards alerts to Telegram and stores locally."""

from __future__ import annotations

import logging

from telegram.ext import Application

logger = logging.getLogger(__name__)

# In-memory: product_id → list of chat_ids for price-drop notifications
_product_chats: dict[int, list[int]] = {}
_default_chat_id: int | None = None


def register_chat(chat_id: int) -> None:
    """Register a chat to receive notifications."""
    global _default_chat_id
    _default_chat_id = chat_id
    logger.info("Chat %d registered for notifications.", chat_id)


def register_product_chat(product_id: int, chat_id: int) -> None:
    """Associate a product with a Telegram chat for notifications."""
    _product_chats.setdefault(product_id, []).append(chat_id)


async def _notify_price_drop(
    bot_app: Application,
    product_title: str,
    old_price: float,
    new_price: float,
    drop_pct: float,
    permalink: str,
    chat_id: int,
) -> None:
    """Send a price-drop notification to a specific chat."""
    text = (
        f"\U0001f4c9 **BAJ\u00d3 DE PRECIO!**\n\n"
        f"{product_title}\n\n"
        f"Antes: ${old_price:,.2f}\n"
        f"Ahora: ${new_price:,.2f}\n"
        f"Baj\u00f3: -{drop_pct}% \U0001f389\n\n"
        f"{permalink}"
    )
    await bot_app.bot.send_message(chat_id=chat_id, text=text)


async def dispatch_alert(
    bot_app: Application | None,
    product_id: int,
    product_title: str,
    old_price: float,
    new_price: float,
    drop_pct: float,
    permalink: str,
) -> None:
    """Dispatch an alert to all registered notification channels."""
    if bot_app is None:
        return

    # Collect target chat IDs
    targets = _product_chats.get(product_id, [])
    if _default_chat_id is not None:
        targets.append(_default_chat_id)

    for chat_id in set(targets):
        try:
            await _notify_price_drop(
                bot_app, product_title, old_price, new_price, drop_pct, permalink, chat_id
            )
        except Exception:
            logger.exception("Failed to send notification to chat %d", chat_id)
