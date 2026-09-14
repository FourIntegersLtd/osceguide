FROM python:3.11-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    HF_HOME=/app/.cache/huggingface \
    TORCH_HOME=/app/.cache/torch

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry==2.1.3"

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-ansi

COPY . .

RUN poetry install --only main --no-ansi

# Bake plugin models and native assets into the image instead of downloading
# them during every container startup.
RUN .venv/bin/python -m livekit.agents download-files


FROM python:3.11-slim-bookworm AS runtime

ARG UID=10001
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONPATH=/app:/app/packages \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PRODUCTION=true \
    HF_HOME=/app/.cache/huggingface \
    TORCH_HOME=/app/.cache/torch

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates make \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos "" --home /home/appuser \
        --shell /usr/sbin/nologin --uid "${UID}" appuser

WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app /app

RUN chmod +x hosting/container_entry.sh

USER appuser

CMD ["hosting/container_entry.sh"]
