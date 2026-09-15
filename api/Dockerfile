# One image, two Railway services: `web` (default CMD) and `worker`
# (start command overridden to `python -m app.worker.main`).
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.1.4 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && pip install --no-cache-dir "poetry==${POETRY_VERSION}" \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
