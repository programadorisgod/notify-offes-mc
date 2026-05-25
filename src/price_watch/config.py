"""Configuration via environment variables with sensible defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))

    # Apify — used to scrape MercadoLibre product data
    apify_token: str = field(default_factory=lambda: os.getenv("APIFY_TOKEN", ""))
    apify_task_id: str = field(
        default_factory=lambda: os.getenv(
            "APIFY_TASK_ID",
            "nurturing_author~mercadolibre-scraper-espanol-castellano-task",
        )
    )

    database_path: str = field(
        default_factory=lambda: os.getenv("DATABASE_PATH", "price_watch.db")
    )
    check_interval_seconds: int = int(os.getenv("CHECK_INTERVAL", "43200"))

    session_secret: str = field(
        default_factory=lambda: os.getenv("SESSION_SECRET", "change-me-in-production")
    )
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))


settings = Settings()
