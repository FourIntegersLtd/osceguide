"""Coverage is provisional evidence, never an assessment result."""

import uuid
from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AttemptLiveCoverage(Base):
    __tablename__ = "attempt_live_coverage"

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
