"""Point a script at a Railway Postgres without copying its secret.

Run the script under the database's own service, from api/, so Railway injects its variables:

    railway run -s platform-postgres -e staging \
        poetry run python scripts/<script>.py --database-url-env RAILWAY_PROXY
    (production: -s platform-postgres-production -e production)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote

API_ROOT = Path(__file__).resolve().parents[1]

RAILWAY_PROXY = "RAILWAY_PROXY"  # use_database_env(RAILWAY_PROXY): the proxy of the service run under


def bootstrap_app() -> None:
    """Make `app` importable and load api/.env, as every maintenance script needs before importing it."""
    from dotenv import load_dotenv

    sys.path.insert(0, str(API_ROOT))
    os.environ.setdefault("APP_ENV", "local")
    load_dotenv(API_ROOT / ".env")


def _railway_proxy_url() -> str:
    """The public TCP-proxy URL of the Postgres service this process runs under."""
    needed = (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "RAILWAY_TCP_PROXY_DOMAIN",
        "RAILWAY_TCP_PROXY_PORT",
    )
    env = {key: os.environ.get(key, "").strip() for key in needed}
    missing = [key for key, value in env.items() if not value]
    if missing:
        sys.exit(
            f"missing {', '.join(missing)}; run under `railway run -s <postgres service> -e <environment>`"
        )
    return (
        f"postgresql://{quote(env['POSTGRES_USER'], safe='')}:{quote(env['POSTGRES_PASSWORD'], safe='')}"
        f"@{env['RAILWAY_TCP_PROXY_DOMAIN']}:{env['RAILWAY_TCP_PROXY_PORT']}/{env['POSTGRES_DB']}"
    )


def use_database_env(name: str) -> None:
    """Points the app's DATABASE_URL at the connection string held in env var `name`,
    or at the Railway proxy address when `name` is RAILWAY_PROXY."""
    url = _railway_proxy_url() if name == RAILWAY_PROXY else (os.environ.get(name) or "").strip()
    if not url:
        sys.exit(f"{name} is not set")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    os.environ["DATABASE_URL"] = url
