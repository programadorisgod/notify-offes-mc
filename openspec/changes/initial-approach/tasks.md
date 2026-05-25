# Tasks: Price-Watch — Implementación Inicial

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,200–1,500 |
| 800-line budget risk | High |
| Chained PRs recommended | Yes |
| Delivery strategy | single-pr-default |
| Chain strategy | size-exception (personal project, single maintainer) |

Decision needed before apply: **Yes** (proceed with size:exception)
Chained PRs recommended: Yes
Chain strategy: size-exception
400-line budget risk: High

> **Nota**: El presupuesto es 800 líneas (opción D2) pero el proyecto completo estima ~1,200–1,500 líneas nuevas. Para un proyecto personal mono-usuario con un solo mantenedor, se recomienda proceder como `size:exception` en un solo PR. No hay reviewers que proteger.

---

## Phase 1: Foundation

- [x] 1.1 `src/price_watch/__init__.py` — package init
- [x] 1.2 `src/price_watch/config.py` — config desde env vars: `BOT_TOKEN`, `DATABASE_PATH`, `CHECK_INTERVAL`
- [x] 1.3 `src/price_watch/db/schema.py` — esquema SQLite: tablas `products`, `price_history`, `alerts`
- [x] 1.4 `src/price_watch/db/connection.py` — pool async (`aiosqlite`), init DB on startup
- [x] 1.5 `src/price_watch/db/repository.py` — CRUD: `add_product`, `get_products`, `save_price_snapshot`, `get_price_history`, `save_alert`, `get_recent_alerts`

## Phase 2: Core — Scraper + Scheduler

- [x] 2.1 `src/price_watch/scraper/__init__.py` — package init
- [x] 2.2 `src/price_watch/scraper/url_parser.py` — extraer `item_id` de URLs de ML (soporta `/p/MLA...` y `/{title}-MLA...`)
- [x] 2.3 `src/price_watch/scraper/ml_api.py` — cliente httpx async para `GET /items/{id}` y batch `GET /items?ids=...`
- [x] 2.4 `src/price_watch/scheduler/__init__.py` — package init
- [x] 2.5 `src/price_watch/scheduler/service.py` — APScheduler: `check_prices()` cada 1 hora, itera productos activos, consulta API, guarda snapshot, dispara alertas si bajó el precio

## Phase 3: Integration — Server + Bot + UI

- [x] 3.1 `src/price_watch/bot/__init__.py` — package init
- [x] 3.2 `src/price_watch/bot/handlers.py` — comandos Telegram: `/start`, `/add <url>`, `/list`, `/remove <id>`, `/price <id>`
- [x] 3.3 `src/price_watch/bot/notifier.py` — enviar mensaje cuando se detecta baja de precio
- [x] 3.4 `src/price_watch/web/__init__.py` — package init
- [x] 3.5 `src/price_watch/web/server.py` — FastAPI app con rutas: `GET /` (dashboard), `POST /products` (agregar link), `DELETE /products/{id}`, `GET /products/{id}/history`
- [x] 3.6 `src/price_watch/web/templates/` — Jinja2 templates: `base.html`, `dashboard.html`, `product_detail.html`
- [x] 3.7 `src/price_watch/web/static/` — CSS mínimo + vanilla JS para UX

## Phase 4: Entrypoint + Tests

- [x] 4.1 `src/main.py` — entrypoint: crear app FastAPI, registrar startup/shutdown (iniciar scheduler, init DB, configurar bot)
- [x] 4.2 `pyproject.toml` — dependencias + config de proyecto Python
- [x] 4.3 `tests/test_url_parser.py` — unit tests para extracción de item_id (varios formatos de URL)
- [x] 4.4 `tests/test_ml_api.py` — integration tests contra API real (mockeable)
- [x] 4.5 `tests/test_db_repository.py` — tests de CRUD con SQLite in-memory
- [x] 4.6 `tests/test_scheduler.py` — test de lógica de `check_prices()` con mock API

## Summary

| Phase | Tasks | Focus |
|-------|-------|-------|
| 1 — Foundation | 5 | Package, config, DB schema, repository |
| 2 — Core | 5 | URL parser, ML API client, scheduler |
| 3 — Integration | 7 | FastAPI server, bot handlers, web UI |
| 4 — Entrypoint + Tests | 6 | main.py, pyproject.toml, 4 test files |
| **Total** | **23** | |
