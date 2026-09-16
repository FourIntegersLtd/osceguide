from __future__ import annotations

from pydantic import BaseModel


class PlanRead(BaseModel):
    code: str
    amount_pence: int
    currency: str
    duration_days: int
    exam_code: str | None


class WebhookResult(BaseModel):
    status: str
