# One image, two Railway services: `platform-api` (the default CMD below,
# configured by railway.toml) and `platform-worker` (railway.worker.toml starts
# it as `python -m app.worker.main`).
#
# Two stages. `dependencies` holds the build tools and the private-repo token
# and installs every package into /opt/venv. The final stage starts again from
# a clean base and copies only /opt/venv, so neither the token nor the build
# tools reach the image that ships.

# ---- Stage 1: install the dependencies (throwaway) ------------------------
FROM python:3.11-slim AS dependencies

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.1.4 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# `git` is here because the marking engine is a git dependency, not a
# published package: without it `poetry install` fails with "git executable
# not found", which reads like a poetry bug rather than a missing tool.
# Poetry goes into the system Python so it stays out of /opt/venv.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev git \
    && pip install --no-cache-dir "poetry==${POETRY_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

# The virtualenv the final stage copies. Poetry installs into whichever
# environment `VIRTUAL_ENV` names when it is told not to create its own.
RUN python -m venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /srv

# SEC-009: read access to the private repository holding `osce_assessment`.
# Railway hands every service variable to the build as a build argument, so
# ENGINE_REPO_TOKEN on the service is all it needs. Locally:
#   docker build --build-arg ENGINE_REPO_TOKEN="$ENGINE_REPO_TOKEN" .
# A build argument is recorded in the history of the stage that declares it,
# which is why it is declared only here: the final stage is built from a fresh
# base and its `docker history` never mentions it. Railway's builder does not
# support BuildKit secret mounts (`--mount=type=secret`), which is what this
# file used before; every build failed on it. Keep the token read-only,
# single-repository and expiring.
ARG ENGINE_REPO_TOKEN=""

COPY pyproject.toml poetry.lock* ./

# The credential is written, used and removed inside one command.
#
# Each step is its own command rather than one `&&` chain ending in `|| true`.
# That is how the first version of this file shipped an image with no marking
# engine in it and reported success: the `|| true` was swallowing the install's
# exit code, not just the cleanup's.
RUN set -eux; \
    if [ -n "$ENGINE_REPO_TOKEN" ]; then \
        git config --global url."https://x-access-token:${ENGINE_REPO_TOKEN}@github.com/".insteadOf "https://github.com/"; \
    fi; \
    poetry install --only main --no-root; \
    rm -f /root/.gitconfig

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
# `poetry install` prints "Installing osce-assessment" and exits zero even when
# the clone produced nothing, so its own exit code is not evidence the engine
# is present. Without the engine this image starts, answers its health check,
# serves every page, and refuses the one thing it exists to do. It runs in this
# stage so it proves the engine is in the image that ships.
RUN python -c "import osce_assessment; print('engine', osce_assessment.__version__)"

WORKDIR /srv
COPY . .

# SEC-009: run as an unprivileged user, not root. Dependencies in /opt/venv
# stay root-owned and read-only at runtime; the app logs to stdout and writes
# nothing under /srv.
RUN useradd --system --uid 10001 --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /srv
USER appuser

EXPOSE 8000
# Schema is migrated before deploy with `alembic upgrade head`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
