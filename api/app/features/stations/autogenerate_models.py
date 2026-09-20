"""Pydantic models for OpenAI structured parse in station autogeneration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StationContentBlockModel(BaseModel):
    """One template block value in AI autogenerate output."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    block_id: str = Field(
        alias="blockId",
        description="Template block id from templateStructure",
    )
    value: str | list[str] | int | float | bool = Field(
        description="Block value: text, option string, list of strings, checklist ids, or scale number",
    )


class StationContentAutogenerateModel(BaseModel):
    """AI output for station instance content autogenerate."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    title: str = Field(description="Suggested station title")
    blocks: list[StationContentBlockModel] = Field(
        description="One entry per template blockId with a populated value",
    )

    def content_map(self) -> dict[str, str | list[str] | int | float | bool]:
        return {block.block_id: block.value for block in self.blocks}
