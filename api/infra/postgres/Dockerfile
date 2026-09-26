# platform-api's database on Railway: Postgres 17 with pgvector added.
#
# Why this image exists: Railway's official Postgres image has no pgvector, and
# platform-api needs it for tutor memory and media search (ADR 0019). The
# marketplace pgvector templates either drop Railway's point-in-time restore or are
# built by strangers, so we add the one package ourselves.
#
# What we keep from the base image, untouched:
# - SSL on every connection (Railway's init-ssl.sh).
# - pgBackRest, which Railway's Backups tab turns on for point-in-time restore.
# - The official Postgres entrypoint and start command.
#
# Keeping it patched: Railway republishes the `:17` base every week with the latest
# Postgres 17 minor release. Redeploying this database service rebuilds the image on
# top of it (a few seconds of database restart), so redeploy it about once a month.
#
# Why 17 and not 18: Supabase also runs 17, which keeps a way back open.
FROM ghcr.io/railwayapp-templates/postgres-ssl:17

# Install pgvector from the PostgreSQL project's own Debian repository, which the
# official Postgres image already trusts. `PG_MAJOR` (17) comes from the base image,
# so the package always matches the server. Clearing the apt lists keeps the image small.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends "postgresql-${PG_MAJOR}-pgvector" \
    && rm -rf /var/lib/apt/lists/*

# platform-api's migrations run `CREATE EXTENSION vector` (and `citext`, which ships
# with Postgres itself) in its own database; nothing here switches them on.
#
# Checked locally on 2026-09-26: Postgres 17.11, pgvector 0.8.6, citext, SSL on,
# pgBackRest present.
