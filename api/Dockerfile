# One image, two Railway services: `platform-api` (the default CMD below) and
# `platform-worker` (its start command is `python -m app.worker.main`). Their
# Railway settings live in the dashboard: docs/ENVIRONMENT.md, "Railway service
# settings".
#
# Built from the repository root, not from `api/`: the marking engine is a
# path dependency on `assessment/packages/osce_assessment`, so the build
# context must hold both. `/.dockerignore` lets in only those two folders.
#   docker build -f api/Dockerfile .
#
# Two stages. `dependencies` holds the build tools and installs every package
# into /opt/venv. The final stage starts again from a clean base and copies
# only /opt/venv, so the build tools never reach the image that ships.

# ---- Stage 1: install the dependencies (throwaway) ------------------------
FROM python:3.11-slim AS dependencies

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.1.4 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Poetry goes into the system Python so it stays out of /opt/venv.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && pip install --no-cache-dir "poetry==${POETRY_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

# The virtualenv the final stage copies. Poetry installs into whichever
# environment `VIRTUAL_ENV` names when it is told not to create its own.
RUN python -m venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

# The same relative layout as the repository, so the lock file's
# `../assessment/packages/osce_assessment` resolves. `develop = false` copies
# the engine into /opt/venv, so nothing under /build is needed at run time.
WORKDIR /build/api
COPY assessment/packages/osce_assessment /build/assessment/packages/osce_assessment
COPY api/pyproject.toml api/poetry.lock ./
RUN poetry install --only main --no-root

# ---- Stage 2: the image that ships ----------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

# Every Python package, the marking engine included. Nothing else crosses over:
# psycopg ships its own libpq (the `binary` extra) and MoviePy its own ffmpeg,
# so the runtime needs no system packages beyond the base image.
COPY --from=dependencies /opt/venv /opt/venv

# The build fails here rather than at the first candidate's session.
#
# `poetry install` exiting zero is not evidence the engine is present: an
# earlier version of this file shipped an image with no engine and reported
# success. Without the engine this image starts, answers its health check,
# serves every page, and refuses the one thing it exists to do. It runs in this
# stage so it proves the engine is in the image that ships.
RUN python -c "import osce_assessment; print('engine', osce_assessment.__version__)"

WORKDIR /srv
COPY api/ .

# SEC-009: run as an unprivileged user, not root. Dependencies in /opt/venv
# stay root-owned and read-only at runtime; the app logs to stdout and writes
# nothing under /srv.
RUN useradd --system --uid 10001 --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /srv
USER appuser

EXPOSE 8000
# Schema is migrated before deploy with `alembic upgrade head`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
