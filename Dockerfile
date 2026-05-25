FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (layer cached unless pyproject.toml or uv.lock changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project --frozen

# Copy source and install the project itself
COPY src/ src/
RUN uv sync --no-dev --frozen

EXPOSE 8000

ENV HOST=0.0.0.0 \
    PORT=8000 \
    DATABASE_PATH=/data/price_watch.db

VOLUME ["/data"]

CMD ["uv", "run", "--no-dev", "python", "src/main.py"]
