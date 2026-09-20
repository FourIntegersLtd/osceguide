from typing import Literal

from pydantic import BaseModel, Field


class CoverageItemRead(BaseModel):
    competency_id: str
    label: str
    state: Literal["partial", "covered"]
    quote: str
    seq: int


class CoverageRead(BaseModel):
    supported: bool
    items: list[CoverageItemRead] = Field(default_factory=list)
    last_seq: int = -1
