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

### ¿Multi-usuario?

Sí. Cada usuario se registra con usuario y contraseña (compartido entre Telegram y web).

- **Telegram:** `/register user pass` → crea cuenta y vincula el chat
- **Web:** se registra con las mismas credenciales
- **Telegram:** `/login user pass` → vincula un chat existente a tu cuenta
- Cada usuario ve **solamente sus productos**, tanto en Telegram como en la web

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
CHECK_INTERVAL=43200   # 12 horas en segundos
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
SESSION_SECRET=un-secreto-seguro
```

### 3. Correr la app

```bash
uv run python src/main.py
```

Esto inicia:
- El bot de Telegram (polling)
- El web dashboard en `http://localhost:8000`
- El scheduler que checkea precios cada 12 horas

### 4. O con Docker

```bash
# Buildear la imagen
docker build -t notify-offes-mc .

# Correr (reemplazar variables de entorno)
docker run -d \
  --name price-watch \
  -p 8000:8000 \
  -v price-watch-data:/data \
  -e BOT_TOKEN=tu_token \
  -e APIFY_TOKEN=tu_apify_token \
  -e SESSION_SECRET=un-secreto-seguro \
  notify-offes-mc
```

> La base de datos se persiste en el volumen `price-watch-data`.

## Comandos del Bot

| Comando | Descripción |
|---------|-------------|
| `/start` | Ver estado y ayuda |
| `/register <user> <pass>` | Crear cuenta y vincular este chat |
| `/login <user> <pass>` | Iniciar sesión y vincular este chat |
| `/add <url>` | Agregar producto de MercadoLibre |
| `/list` | Ver mis productos trackeados |
| `/remove <id>` | Dejar de trackear un producto |
| `/price <id>` | Ver historial de precios |

## Web Dashboard

Disponible en `http://localhost:8000`:
- Login/registro con las mismas credenciales que Telegram
- Lista de **mis** productos con precios min/max
- Agregar productos (con spinner de carga)
- Alertas de bajas de precio recientes
- Ver historial de precios por producto

## Estrategia de Scraping

La app usa el actor de Apify `mercadolibre-scraper-espanol-castellano` para obtener datos de productos. Estrategia de dos pasos:

1. **startUrls:** busca el producto por URL en los resultados de búsqueda de ML
2. **Keyword fallback:** si no aparece, extrae keywords del path de la URL y vuelve a buscar

Esto cubre productos que no rankean en las búsquedas (nuevos, con poco movimiento, etc.).

## Licencia

MIT
