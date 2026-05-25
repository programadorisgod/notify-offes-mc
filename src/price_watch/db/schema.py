"""SQLite schema for price-watch."""

CREATE_PRODUCTS = """
CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id         TEXT    NOT NULL,
    site_id         TEXT    NOT NULL,
    title           TEXT    NOT NULL,
    permalink       TEXT    NOT NULL,
    thumbnail       TEXT,
    currency_id     TEXT    NOT NULL,
    chat_id         INTEGER NOT NULL DEFAULT 0,
    initial_price   REAL,
    min_price       REAL,
    max_price       REAL,
    is_active       INTEGER NOT NULL DEFAULT 1,
    alert_enabled   INTEGER NOT NULL DEFAULT 1,
    check_interval  INTEGER NOT NULL DEFAULT 3600,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(item_id, chat_id)
);
"""

CREATE_PRICE_HISTORY = """
CREATE TABLE IF NOT EXISTS price_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES products(id),
    price           REAL    NOT NULL,
    original_price  REAL,
    available_qty   INTEGER,
    sold_qty        INTEGER,
    fetched_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_PRICE_HISTORY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_price_history_product
    ON price_history(product_id, fetched_at);
"""

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL UNIQUE,
    password_hash   TEXT    NOT NULL,
    chat_id         INTEGER UNIQUE,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_ALERTS = """
CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES products(id),
    alert_type      TEXT    NOT NULL,
    old_price       REAL,
    new_price       REAL,
    drop_percent    REAL,
    sent_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

SCHEMA_STATEMENTS = [
    CREATE_USERS,
    CREATE_PRODUCTS,
    CREATE_PRICE_HISTORY,
    CREATE_PRICE_HISTORY_INDEX,
    CREATE_ALERTS,
]
