# syntax=docker/dockerfile:1.7
# One image, two Railway services: `web` (default CMD) and `worker`
# (start command overridden to `python -m app.worker.main`).
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.1.4 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# `git` is here because the marking engine is a git dependency, not a
# published package: without it `poetry install` fails with "git executable
# not found", which reads like a poetry bug rather than a missing tool.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev curl git \
    && pip install --no-cache-dir "poetry==${POETRY_VERSION}" \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

# SEC-009: read access to the private repository holding `osce_assessment`.
# The token now arrives as a BuildKit secret, so it is never written to the
# image or shown by `docker history`. Supply it at build time with:
#   DOCKER_BUILDKIT=1 docker build --secret id=engine_token,env=ENGINE_REPO_TOKEN .
# On Railway, add ENGINE_REPO_TOKEN as a build-time secret of that id.
#
# The ARG remains only as a migration fallback for a builder that cannot mount
# secrets: passing it with `--build-arg` reintroduces the `docker history`
# exposure this fix removes, so use the secret. Make the token read-only,
# single-repository and expiring in every case.
ARG ENGINE_REPO_TOKEN=""

COPY pyproject.toml poetry.lock* ./

# The credential is read from the secret mount (or the fallback ARG), used, and
# left behind in nothing: `git config` writes to /root/.gitconfig, so the same
# layer removes the URL rewrite and deletes the file. All of it is one layer,
# so the token never lands in a layer of its own.
#
# Each step is its own command rather than one `&&` chain ending in `|| true`.
# That is how the first version of this file shipped an image with no marking
# engine in it and reported success: the `|| true` was swallowing the install's
# exit code, not just the cleanup's.
RUN --mount=type=secret,id=engine_token,required=false set -eux; \
    TOKEN="$(cat /run/secrets/engine_token 2>/dev/null || true)"; \
    TOKEN="${TOKEN:-$ENGINE_REPO_TOKEN}"; \
    if [ -n "$TOKEN" ]; then \
        git config --global url."https://x-access-token:${TOKEN}@github.com/".insteadOf "https://github.com/"; \
    fi; \
    poetry install --only main --no-root; \
    git config --global --unset-all url."https://x-access-token:${TOKEN}@github.com/".insteadOf 2>/dev/null || true; \
    rm -f /root/.gitconfig

# The build fails here rather than at the first candidate's session.
#
# `poetry install` prints "Installing osce-assessment" and exits zero even when
# the clone produced nothing, so its own exit code is not evidence the engine
# is present. Without the engine this image starts, answers its health check,
# serves every page, and refuses the one thing it exists to do.
RUN python -c "import osce_assessment; print('engine', osce_assessment.__version__)"

COPY . .

# SEC-009: run as an unprivileged user, not root. Dependencies live in the
# system site-packages (POETRY_VIRTUALENVS_CREATE=false) and are read-only at
# runtime; the app logs to stdout and writes nothing under /srv.
RUN useradd --system --uid 10001 --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /srv
USER appuser

EXPOSE 8000
# Schema is migrated before deploy with `alembic upgrade head`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
