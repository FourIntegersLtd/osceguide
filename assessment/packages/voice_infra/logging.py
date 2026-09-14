"""Process logging for voice workers: one setup, module loggers everywhere."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

_configured = False


def is_production() -> bool:
    return bool(os.getenv("RAILWAY_PROJECT_ID")) or os.getenv("PRODUCTION", "false").lower() == "true"


def configure_logging(*, log_file: str | None = None) -> None:
    """Idempotent. INFO in production, DEBUG otherwise; file plus stream handlers."""
    global _configured
    if _configured:
        return
    log_dir = os.getenv("LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)
    production = is_production()
    fmt = (
        "%(asctime)s | %(levelname)-8s | %(message)s"
        if production
        else "\n═══════════════════════════════════════════\n%(asctime)s | %(levelname)-8s | %(name)s\n───────────────────────────────────────────\n%(message)s\n"
    )
    logging.basicConfig(
        level=logging.INFO if production else logging.DEBUG,
        format=fmt,
        handlers=[
            RotatingFileHandler(os.path.join(log_dir, log_file or os.getenv("LOG_FILE", "voice_worker.log")), maxBytes=10_000_000, backupCount=3),
            logging.StreamHandler(),
        ],
    )
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
