# NotifyOffersMc

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

**Telegram bot + web dashboard** para trackear precios de productos de MercadoLibre y recibir notificaciones cuando bajan de precio.

## Features

- Agregá productos de MercadoLibre por URL y trackeá su precio automáticamente
- Recibí notificaciones en Telegram cuando un producto baja de precio
- Web dashboard para ver todos los productos y alertas
- Historial de precios por producto
- Scraping via Apify (sin necesidad de tokens de MercadoLibre)

## Stack

- **Runtime:** Python 3.12+
- **Framework web:** FastAPI + Uvicorn
- **Bot:** python-telegram-bot (long polling)
- **Base de datos:** SQLite via aiosqlite
- **Scraping:** Apify MercadoLibre Scraper
- **Scheduler:** APScheduler (cada 1 hora por defecto)
- **Frontend:** Jinja2 templates + Bootstrap

## Arquitectura

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Telegram   │◄───►│  FastAPI App │────►│  Apify Scraper  │
│   Bot       │     │  (bot + web) │     │  (MercadoLibre) │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                           │
                    ┌──────▼───────┐
                    │   SQLite DB  │
                    │ price_watch  │
                    └──────────────┘
```

La app corre como un **proceso local** con long polling. No expone una API pública — es para uso personal/deploy propio.

### ¿Es multi-usuario o single-usuario?

**Single-usuario con soporte de múltiples chats de Telegram.**

Todos los chats que interactúan con el bot comparten la misma base de datos de productos. No hay aislamiento por usuario ni permisos diferenciados. Cualquier persona que agregue el bot a un grupo o chat privado ve los mismos productos trackeados.

### ¿Es una API o una app local?

Es una **app local** que:
- Corre un bot de Telegram mediante long polling (no webhooks)
- Tiene un web dashboard accesible en `http://localhost:8000`
- No expone una API REST pública
- Todo corre en tu máquina/servidor

## Setup

### 1. Clonar e instalar

```bash
git clone git@github.com:programadorisgod/notify-offes-mc.git
cd notify-offes-mc
uv sync
```

### 2. Variables de entorno

Crear un archivo `.env` en la raíz:

```bash
# Telegram Bot Token (obligatorio)
BOT_TOKEN=tu_token_de_botfather

# Apify (obligatorio)
APIFY_TOKEN=tu_apify_token
APIFY_TASK_ID=nurturing_author~mercadolibre-scraper-espanol-castellano-task

# Opcional
DATABASE_PATH=price_watch.db
CHECK_INTERVAL=3600
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
```

### 3. Correr la app

```bash
uv run python src/main.py
```

Esto inicia:
- El bot de Telegram (polling)
- El web dashboard en `http://localhost:8000`
- El scheduler que checkea precios cada hora

## Comandos del Bot

| Comando | Descripción |
|---------|-------------|
| `/start` | Registrar el chat y ver ayuda |
| `/add <url>` | Agregar producto de MercadoLibre |
| `/list` | Ver todos los productos trackeados |
| `/remove <id>` | Dejar de trackear un producto |
| `/price <id>` | Ver historial de precios |

## Web Dashboard

Disponible en `http://localhost:8000`:
- Lista de productos trackeados con precios min/max
- Alertas de bajas de precio recientes
- Agregar productos desde el navegador
- Ver historial de precios por producto

## Estrategia de Scraping

La app usa el actor de Apify `mercadolibre-scraper-espanol-castellano` para obtener datos de productos. Estrategia de dos pasos:

1. **startUrls:** busca el producto por URL en los resultados de búsqueda de ML
2. **Keyword fallback:** si no aparece, extrae keywords del path de la URL y vuelve a buscar

Esto cubre productos que no rankean en las búsquedas (nuevos, con poco movimiento, etc.).

## Licencia

MIT
