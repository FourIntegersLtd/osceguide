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

# Read access to the private repository holding `osce_assessment`. The same
# value as the `ENGINE_REPO_TOKEN` secret CI uses; make it a read-only,
# single-repository, expiring token, because a build argument is recorded in
# the image's metadata and `docker history` will show it. If your builder
# supports BuildKit secrets, prefer
# `RUN --mount=type=secret,id=engine_token` over this and nothing is recorded
# at all.
ARG ENGINE_REPO_TOKEN=""

COPY pyproject.toml poetry.lock* ./

# The credential is written, used and removed inside one layer, so it is never
# committed to a layer of its own.
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
    git config --global --remove-section url."https://x-access-token:${ENGINE_REPO_TOKEN}@github.com/" 2>/dev/null || true

# The build fails here rather than at the first candidate's session.
#
# `poetry install` prints "Installing osce-assessment" and exits zero even when
# the clone produced nothing, so its own exit code is not evidence the engine
# is present. Without the engine this image starts, answers its health check,
# serves every page, and refuses the one thing it exists to do.
RUN python -c "import osce_assessment; print('engine', osce_assessment.__version__)"

COPY . .

EXPOSE 8000
# Schema is migrated before deploy with `alembic upgrade head`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
