FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /uvx /bin/

WORKDIR /app

# Install project deps (layer is cached unless pyproject.toml or uv.lock changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# Copy source code
COPY src/ src/

EXPOSE 8000

ENV HOST=0.0.0.0 \
    PORT=8000 \
    DATABASE_PATH=/data/price_watch.db

VOLUME ["/data"]

CMD ["uv", "run", "--no-dev", "python", "src/main.py"]
