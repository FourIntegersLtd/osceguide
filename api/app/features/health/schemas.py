from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

CheckState = Literal["ok", "error", "disabled"]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    version: str
    checks: dict[str, CheckState]
