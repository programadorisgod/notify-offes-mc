"""Price Watch — MercadoLibre price tracker entrypoint."""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
import uvicorn

# Load .env before anything else
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from telegram.ext import Application

from price_watch.bot.handlers import build_bot
from price_watch.config import settings
from price_watch.db.connection import close_db, init_db
from price_watch.scheduler.service import start_scheduler, stop_scheduler
from price_watch.web.server import app

logger = logging.getLogger(__name__)
bot_app: Application | None = None
_started = False


@app.on_event("startup")
async def on_startup():
    """Initialize DB, scheduler, and Telegram bot on server start."""
    global bot_app, _started
    if _started:
        return
    _started = True

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Starting Price Watch...")

    # Database
    await init_db()
    logger.info("Database initialized at %s", settings.database_path)

    # Scheduler
    start_scheduler()

    # Telegram bot (polling mode)
    if settings.bot_token:
        bot_app = build_bot(settings.bot_token)
        await bot_app.initialize()
        await bot_app.updater.start_polling()
        await bot_app.start()
        logger.info("Telegram bot started (polling)")
    else:
        logger.warning("BOT_TOKEN not set — Telegram bot disabled.")


@app.on_event("shutdown")
async def on_shutdown():
    """Clean shutdown."""
    if not _started:
        return
    stop_scheduler()
    if bot_app:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
    await close_db()
    logger.info("Price Watch stopped.")


def main():
    """Run the Price Watch server."""
    uvicorn.run(
        "price_watch.web.server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
