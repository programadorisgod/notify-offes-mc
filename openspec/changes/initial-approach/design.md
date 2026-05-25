# Design: Price-Watch — MercadoLibre Price Tracker

## Technical Approach

Greenfield Python 3.12+ project. FastAPI serves REST API + Jinja2 web UI in one process. APScheduler runs hourly price checks in-process via `BackgroundScheduler`. httpx calls `api.mercadolibre.com/items/{id}` (no auth, no scraping). SQLite via aiosqlite stores products, snapshots, and alerts. python-telegram-bot with polling handles commands `/add`, `/list`, `/remove` and push notifications. Single-user, zero-config, no external infra.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|---|---|---|---|
| **Database** | SQLite / PostgreSQL | SQLite: zero-config, single file, no server. PG: overkill for single-user. | **SQLite via aiosqlite** |
| **Scheduler** | APScheduler / Celery / cron | APScheduler: in-process, no infra. Celery needs Redis. Cron: external, no programmatic control. | **APScheduler BackgroundScheduler** |
| **Telegram mode** | Polling / Webhook | Polling: no public URL. Webhook needs HTTPS endpoint. | **Polling** |
| **Frontend** | Jinja2+vanilla JS / React+Svelte | Jinja2: no build step, ships with FastAPI. React adds npm+bundler for a dashboard. | **Jinja2 + vanilla JS** |
| **HTTP client** | httpx / requests | httpx: async-native, non-blocking. requests: sync, blocks event loop. | **httpx** |
| **DB access** | aiosqlite / sqlite3 | aiosqlite: async, no thread-pool needed. sqlite3: sync, must use `run_in_executor`. | **aiosqlite** |
| **Package layout** | flat / namespaced | Namespaced (`src/price_watch/`): clear boundaries, import isolation. | **src/price_watch/** |

## Data Flow

```
Browser ──→ FastAPI ──→ repository ──→ SQLite
                │
                └── Jinja2 templates

Telegram ──→ python-telegram-bot ──→ repository ──→ SQLite

APScheduler (1h) ──→ scraper (httpx) ──→ api.mercadolibre.com
                        │
                        ├──→ repository ──→ SQLite
                        └──→ notifier ──→ Telegram
```

## Module Structure

```
src/price_watch/
├── __init__.py
├── __main__.py              # uvicorn.run() + scheduler.start()
├── config.py                # pydantic-settings: env vars → typed config
├── db/
│   ├── database.py          # aiosqlite connection + schema init
│   ├── models.py            # DB schema as dataclasses
│   └── repository.py        # CRUD: products, price_history, alerts
├── scraper/
│   ├── client.py            # httpx.AsyncClient → /items & /items?ids=
│   └── url_parser.py        # Regex: ML URL → item_id extraction
├── scheduler/
│   └── jobs.py              # check_prices(): scrape → store → alert
├── bot/
│   ├── handlers.py          # Command handlers: /add, /list, /remove
│   └── notifier.py          # send_alert(): drop % formatting + send
├── web/
│   ├── routes.py            # FastAPI: /, /api/products, /api/history
│   ├── templates/           # base.html, index.html, product.html
│   └── static/              # style.css, app.js (vanilla)
└── tests/
    ├── conftest.py          # test DB + httpx mock transport
    ├── test_url_parser.py
    ├── test_scraper.py
    ├── test_repository.py
    ├── test_scheduler.py
    ├── test_bot.py
    └── test_routes.py
```

Key conventions:
- API calls share one `httpx.AsyncClient` session
- DB uses single aiosqlite connection with WAL mode for concurrency
- `check_prices()` is async; APScheduler runs via `AsyncIOScheduler`
- All config via env (pydantic-settings reads `.env` automatically)
- Bot runs polling with `Application.run_polling()` in a background task

## File Changes

| File | Action | Description |
|---|---|---|
| `pyproject.toml` | Create | Project metadata, deps, entry point `price-watch` |
| `.env.example` | Create | `TELEGRAM_TOKEN=`, `DB_PATH=`, `CHECK_INTERVAL=` |
| `src/price_watch/` | Create | 18 files across 6 modules + tests |

## Testing Strategy

| Layer | What | How |
|---|---|---|
| Unit | `url_parser` — all ML URL patterns + edge cases | Parametrized pytest, no DB |
| Unit | `repository` — CRUD, duplicate detection, min/max | In-memory aiosqlite, fresh DB per test |
| Unit | `scraper/client` — response parsing, API errors | respx mock on `api.mercadolibre.com` |
| Integration | `scheduler/jobs` — full cycle: scrape→store→alert | Test DB + mocked ML + captured Telegram calls |
| Integration | `bot/handlers` — commands, invalid input | PTB Mock/ApplicationBuilder |
| Integration | `web/routes` — dashboard, API endpoints | TestClient with test DB dependency override |

## Migration / Rollout

No migration. First run auto-creates schema via `database.py`. No data to migrate.

## Open Questions

None.
