"""Tables owned by `health`. These classes never leave this slice's repository."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import BigInteger, Date, SmallInteger, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class DatabaseSizeReading(Base, UUIDPrimaryKey, Timestamps):
    """How big the database was on one day: the history the Ops forecast is fitted to."""

    __tablename__ = "database_size_readings"
    __table_args__ = (UniqueConstraint("taken_on", name="uq_database_size_readings_taken_on"),)

    taken_on: Mapped[date] = mapped_column(Date, nullable=False)
    total_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # The biggest relations that day: [{"name", "total_bytes", "rows"}], largest first.
    relations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    # 0 below 60% of the budget, 1 from 60%, 2 from 80%, as it stood when this was written. The next
    # reading compares against it, so a threshold raises its alarm once per crossing, not once per run.
    alert_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
