# Proposal: Price-Watch — MercadoLibre Price Tracker

## Intent

Crear un tracker personal de precios de MercadoLibre. El usuario pega un link de producto, el sistema extrae el precio vía API pública de ML, lo monitorea cada 1 hora, y notifica vía Telegram y web cuando hay una baja de precio.

## Scope

### In Scope
- Parseo de URLs de MercadoLibre para extraer item ID
- Consulta a la API pública de MercadoLibre (`/items/{id}`) para obtener precio, título, stock
- Base de datos SQLite con productos, historial de precios y alertas
- Web UI mínima (Jinja2 + vanilla JS) para gestionar links y ver historial
- Scheduler cada 1 hora vía APScheduler en el mismo proceso
- Notificación por Telegram cuando el precio baja (bot NotifyOffersMc)
- Notificación en web UI (timeline de alertas)
- API key del bot configurable sin hardcodear

### Out of Scope
- Scraping con Playwright/BeautifulSoup (no hace falta, tenemos API)
- Reviews, Q&A, o datos no-precio de MercadoLibre
- Autenticación de usuarios (proyecto personal, single-user)
- Dashboard con gráficos complejos (tabla + timeline es suficiente)
- Modo multi-idioma
- Despliegue en producción con Docker (se puede agregar después)

## Capabilities

### New Capabilities
- `product-link-management`: agregar, listar, y eliminar productos trackeados desde web UI y Telegram
- `price-tracking`: consulta periódica a la API de ML, almacenamiento de snapshots, cálculo de precio mínimo/máximo
- `telegram-notifications`: bot NotifyOffersMc que alerta cuando un precio baja y permite comandos `/add`, `/list`, `/remove`
- `web-dashboard`: interfaz web para ver productos, precios actuales, historial, y últimas alertas

### Modified Capabilities
None — proyecto nuevo, sin capacidades previas.

## Approach

**Python + FastAPI + MercadoLibre API pública**. Sin scraping. Sin Playwright.

La API de MercadoLibre devuelve JSON limpio con `price`, `original_price`, `title`, etc. Extraemos el `item_id` de la URL ingresada, consultamos la API cada hora vía APScheduler, almacenamos en SQLite.

El bot de Telegram recibe comandos (`/add <url>`, `/list`, `/remove <id>`) y también recibe notificaciones push cuando detectamos una baja de precio.

La web UI permite pegar links, ver productos trackeados con precio actual, gráfico simple de historial, y timeline de alertas.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/scraper/` | New | Cliente HTTP para API de MercadoLibre |
| `src/db/` | New | Modelos SQLite + esquema |
| `src/scheduler/` | New | APScheduler con check cada 1h |
| `src/bot/` | New | Bot de Telegram (NotifyOffersMc) |
| `src/web/` | New | FastAPI + Jinja2 templates |
| `src/config.py` | New | Config desde env vars (API keys, etc.) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| ML API deja de ser pública | Low | Registro gratis como developer, OAuth read-only trivial |
| ML cambia formato de URLs | Low | Parseo con regex + fallback a ingreso manual de item_id |
| SQLite corrupción | Very Low | Backup automático antes de cada ciclo de check |
| Rate limiting | Very Low | ~1 req/hora por producto — no llega ni a 1 req/min |

## Rollback Plan

1. Detener el proceso (Ctrl+C o `systemctl stop price-watch`)
2. Restaurar SQLite desde backup automático
3. Si hay cambios de esquema, borrar DB y recargar desde el último backup
4. Revertir código con `git checkout HEAD~1`

## Dependencies

- Python 3.12+
- `fastapi`, `uvicorn`, `httpx`, `apscheduler`, `python-telegram-bot`, `jinja2`
- Cuenta de Telegram con bot NotifyOffersMc creado vía @BotFather

## Success Criteria

- [ ] Pegar un link de ML → se extrae item_id correctamente y se guarda en DB
- [ ] El scheduler corre cada 1 hora y guarda snapshot de precio
- [ ] Cuando el precio baja, llega notificación a Telegram
- [ ] La web UI muestra productos, precio actual, historial y alertas
- [ ] El bot responde a `/add`, `/list`, `/remove`
