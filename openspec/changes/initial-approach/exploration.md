# Exploration: Price-Watch Technical Approach

## Current State

This is a greenfield project — no code exists yet. The project directory has `openspec/` initialized with `config.yaml` in hybrid mode (Engram + OpenSpec). The goal is a personal MercadoLibre price tracker with Telegram notifications.

---

## 🔑 Critical Discovery: MercadoLibre Public API

**MercadoLibre has a free, public, no-authentication-required REST API** that returns clean structured product data including price, title, stock, shipping info, and more.

- **Endpoint**: `GET https://api.mercadolibre.com/items/{item_id}`
- **No auth required** for read-only access
- **Returns**: `price`, `original_price`, `base_price`, `currency_id`, `title`, `available_quantity`, `sold_quantity`, `condition`, `permalink`, `shipping`, `category_id`, `attributes`, `variations`, and more — all as clean JSON
- **Batch support**: up to 20 item IDs per request via `GET /items?ids=ID1,ID2,...`
- **Rate limits**: ~1,000 req/min per IP unauthenticated; 5,000–20,000 with free OAuth app registration

**The website itself runs behind Cloudflare** with anti-bot protection. Scraping HTML directly requires Playwright with stealth plugins and residential proxies. **Using the API avoids Cloudflare entirely.**

This means for price tracking, **we do NOT need to scrape or render JavaScript at all**. Playwright would only be needed for optional features like reviews or Q&A.

### Extracting Item ID from URLs

MercadoLibre product URLs contain the item ID in multiple formats:

| URL Pattern | Example | ID to Extract |
|---|---|---|
| `/p/{product_id}` (catalog page) | `.../p/MLA15485496` | `MLA15485496` (catalog product) |
| Direct item listing | `.../iphone-15-MLM3000123456` | `MLM3000123456` (item ID) |

The API is global — item IDs are prefixed by site code (MLA = Argentina, MLM = Mexico, MLB = Brazil, etc.).

---

## Approaches

### 1. Python + MercadoLibre API (RECOMMENDED)

**Description**: Use the official MercadoLibre Items API for all price/product data. No browser automation needed for core functionality. Python stack throughout.

- **Pros**:
  - No scraping needed — clean JSON from the official API
  - No Cloudflare bypass, no stealth plugins, no headless browser
  - Dramatically simpler and more reliable
  - Python ecosystem well-suited: FastAPI, APScheduler, SQLite
  - Telegram bot libraries available (`python-telegram-bot`)
  - The API is free and explicitly allowed for programmatic access
- **Cons**:
  - Relies on API availability (but it's a public, stable API)
  - API doesn't expose reviews or Q&A (not needed for price tracking)
- **Effort**: Low

### 2. Python + Playwright (HTML Scraping)

**Description**: Scrape MercadoLibre product pages with Playwright for Python, using stealth plugins to bypass Cloudflare.

- **Pros**:
  - Works even if the API changes
  - Can extract reviews, Q&A, and any UI-only data
- **Cons**:
  - Cloudflare actively blocks headless browsers. Stealth plugins alone fail in 2026 without residential proxies
  - Requires `playwright install chromium` (~300MB browser binary)
  - Slower (browser launch per request)
  - Higher maintenance burden (DOM selectors break when ML changes UI)
  - MercadoLibre ToS restricts scraping of the website (though API access is explicitly allowed)
- **Effort**: High

### 3. Python + requests/BeautifulSoup (Static HTML)

**Description**: Send HTTP requests and parse HTML. Would NOT work for MercadoLibre.

- **Pros**: Lightest weight
- **Cons**: MercadoLibre pages are behind Cloudflare — you'd hit a challenge page or 403 immediately. Prices are loaded dynamically in many cases. **Fundamentally unworkable** for this target.
- **Effort**: N/A (infeasible)

---

## Recommendation

**Go with Approach 1: Python + MercadoLibre API.**

The existence of a free public API that returns real-time pricing data eliminates the hardest problem in this project. There's no reason to fight Cloudflare with Playwright when the official API gives you exactly what you need.

Keep Playwright as an **optional fallback** for features not covered by the API (e.g., reviews display in the web UI). But for the core price-checking loop, it's unnecessary.

---

## Architecture Sketch

```
┌──────────────────────────────────────────────────────┐
│                   price-watch                         │
│                                                       │
│  ┌──────────┐    ┌─────────────┐    ┌──────────────┐ │
│  │  Web UI  │    │  FastAPI    │    │  APScheduler  │ │
│  │ (minimal │◄──►│  Server     │◄───│  (every 1h)   │ │
│  │  HTML/   │    │             │    │              │ │
│  │  JS)     │    │ ├─ /api/*   │    │ └──────┬──────┘ │
│  └──────────┘    │ ├─ /webhook │           │         │
│                  │ └─────┬─────┘           │         │
│                  │       │                 │         │
│                  │       ▼                 ▼         │
│                  │  ┌─────────────────────────┐      │
│                  │  │     Scraper Service      │      │
│                  │  │  (httpx → ML API)        │      │
│                  │  └────────────┬────────────┘      │
│                  │               │                    │
│                  │               ▼                    │
│                  │  ┌─────────────────────────┐      │
│                  │  │      SQLite DB           │      │
│                  │  │  ├─ products             │      │
│                  │  │  ├─ price_history        │      │
│                  │  │  └─ alerts               │      │
│                  │  └─────────────────────────┘      │
│                  │                                    │
│                  │  ┌─────────────────────────┐      │
│                  │  │  Telegram Notifier       │      │
│                  │  │  (python-telegram-bot)   │      │
│                  │  │  bot: NotifyOffersMc     │      │
│                  │  └─────────────────────────┘      │
└──────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | Technology | Responsibility |
|---|---|---|
| **Web Server** | FastAPI + Uvicorn | REST API for managing links, serving web UI, Telegram webhook endpoint |
| **Scheduler** | APScheduler (BackgroundScheduler) | Runs price checks every 1 hour. Lives in the same process as FastAPI (simplest for a personal project) |
| **Scraper** | httpx (async HTTP client) | Calls `api.mercadolibre.com/items/{id}`, extracts price data |
| **Storage** | SQLite (via aiosqlite or SQLAlchemy) | Single file, no server needed, perfect for personal use |
| **Web UI** | Minimal HTML + vanilla JS or Jinja2 templates | Form to paste links, table of tracked products + prices |
| **Telegram Notifier** | `python-telegram-bot` (async) | Sends alerts when prices drop; receives `/start`, `/list`, `/add` commands |

### Scheduling Architecture

For a personal project, **in-process scheduling** is the right choice:

1. FastAPI starts → APScheduler starts in the same process
2. Scheduler runs `check_prices()` every hour
3. `check_prices()` queries all tracked products from DB
4. For each product, calls MercadoLibre API, stores price snapshot
5. If price < lowest_known_price → trigger Telegram notification
6. No external cron, Redis, or Celery needed

```
FastAPI process
├── HTTP server (uvicorn)
├── APScheduler (background thread)
│   └── Every hour: check_prices()
└── SQLite DB
```

### Key Design Decisions

1. **SQLite over PostgreSQL**: This is a personal project running on a single machine. SQLite is zero-config, file-based, and more than sufficient for tracking dozens to hundreds of products with hourly snapshots. PostgreSQL would be overkill.

2. **In-process scheduler over Celery/RabbitMQ**: For a single-user personal project, adding a message queue is unnecessary complexity. APScheduler in the same process works perfectly. If the project grows, the scheduler can be extracted later.

3. **Polling-based Telegram bot**: The bot uses webhooks (Telegram pushes updates to FastAPI) rather than polling, which means it needs a public URL (ngrok for dev, a VPS for production).

4. **API-first, Playwright-fallback**: The primary data path uses the MercadoLibre API. If the API ever fails or changes, we can fall back to browser-based extraction, but this is unlikely for the core pricing data.

---

## Data Model

```sql
-- Tracked products
CREATE TABLE products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id         TEXT    NOT NULL UNIQUE,  -- e.g. "MLA1234567890"
    site_id         TEXT    NOT NULL,          -- e.g. "MLA", "MLM", "MLB"
    title           TEXT    NOT NULL,
    permalink       TEXT    NOT NULL,          -- MercadoLibre product URL
    thumbnail       TEXT,
    currency_id     TEXT    NOT NULL,          -- "ARS", "MXN", "BRL"
    initial_price   REAL,                      -- Price when first tracked
    min_price       REAL,                      -- Lowest price ever seen
    max_price       REAL,                      -- Highest price ever seen
    is_active       INTEGER NOT NULL DEFAULT 1, -- Soft delete
    alert_enabled   INTEGER NOT NULL DEFAULT 1, -- Enable/disable notifications
    check_interval  INTEGER NOT NULL DEFAULT 3600, -- Seconds between checks
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Price snapshots (time-series)
CREATE TABLE price_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES products(id),
    price           REAL    NOT NULL,
    original_price  REAL,                      -- Pre-discount price (if on sale)
    available_qty   INTEGER,
    sold_qty        INTEGER,
    fetched_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_price_history_product ON price_history(product_id, fetched_at);

-- Notification alerts sent
CREATE TABLE alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES products(id),
    alert_type      TEXT    NOT NULL,           -- "price_drop", "back_in_stock"
    old_price       REAL,
    new_price       REAL,
    drop_percent    REAL,                       -- e.g. 15.5 for 15.5% drop
    sent_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

---

## Recommended Stack

| Layer | Technology | Version (approx.) | Why |
|---|---|---|---|
| **Language** | Python 3.12+ | >=3.12 | Async-native, rich ecosystem |
| **Web framework** | FastAPI | 0.115+ | Async, auto-docs, lightweight |
| **ASGI server** | Uvicorn | 0.32+ | Standard FastAPI server |
| **HTTP client** | httpx | 0.28+ | Async HTTP, needed for API calls |
| **Scheduler** | APScheduler | 3.10+ | Mature, in-process scheduling |
| **Database** | SQLite (std lib) | Bundled with Python | Zero config, single file |
| **ORM** | SQLAlchemy (optional) | 2.0+ | For cleaner queries; or just aiosqlite |
| **Telegram bot** | python-telegram-bot | 21+ | Best async Telegram library for Python |
| **Templating** | Jinja2 | Bundled with FastAPI | Server-rendered HTML for the UI |
| **Frontend** | Vanilla HTML + JS + CSS | — | Minimal dashboard, no framework needed |
| **Playwright** (optional fallback) | playwright | 1.60+ | Only if API proves insufficient |

### Python vs Node.js Decision

The user seemed inclined toward Python. **Python is the right choice here**:

- MercadoLibre API calls are simple HTTP requests — no advantage to Node.js
- APScheduler is more mature and simpler than node-cron for in-process scheduling
- `python-telegram-bot` is excellent and natively async
- SQLite support is built into Python stdlib
- FastAPI is Python's best web framework — comparable to Express in simplicity
- For a personal project, Python's "batteries included" approach means fewer dependencies

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| **MercadoLibre API changes** | Medium | The API is well-documented and widely used; breaking changes are announced via developer portal. Monitor the changelog. Keep Playwright as a cold fallback. |
| **Rate limiting** | Low | For personal use (tens of products, hourly checks), you won't hit 1,000 req/min. Even at 50 products/hour, that's <1 req/min. |
| **API removes unauthenticated access** | Low-Medium | If ML requires OAuth, registration is free and takes 30 minutes. The OAuth flow for read-only is straightforward. |
| **IP blocking** | Very Low | The API path doesn't trigger Cloudflare. Even without proxies, the rate is so low (1 req/hour per product) that blocking is unlikely. |
| **MercadoLibre ToS** | Low | API access is explicitly allowed. ToS prohibits scraping the website at high volume, but the API is the intended programmatic access path. |
| **Product URL parsing fails** | Low | ML URL formats are stable. If URL parsing fails, user can manually enter the item ID. |
| **SQLite concurrency** | Low | Single-user app; SQLite handles this fine. Even with scheduler + web UI, contention is negligible. |
| **Data loss (no backup)** | Low | SQLite is a single file — periodic backup is trivial (copy the file). |

---

## Ready for Proposal

Yes. The research uncovered that MercadoLibre's public API makes this project simpler than anticipated — no scraping needed. Recommend proceeding with **sdd-propose** for the initial change ("price-tracker-foundation") using the Python + MercadoLibre API approach.

**Key message for the orchestrator to tell the user**: "MercadoLibre has a free public API — you don't need to scrape anything. The price data comes back as clean JSON with no browser, no Cloudflare bypass, no tricks. Python + FastAPI + the ML API is the ideal stack for this project. Playwright would only be needed if you want reviews display, which isn't in scope for the initial version."
