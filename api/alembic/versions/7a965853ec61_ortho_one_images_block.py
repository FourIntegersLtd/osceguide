"""Give the Ortho clinical station one images field instead of two.

The template had "Radiograph Image URL" and "Additional Image URLs", both media
blocks, and a media block already holds any number of images with captions. The
one block keeps the key `radiograph_image_url`, relabelled "Images". Each
station version's `additional_image_urls` is appended to it (a lone URL string
becomes a one-item list) and the old key dropped; each template version loses
the second block.

Revision ID: 7a965853ec61
Revises: 7d3e9c1a5b42
Create Date: 2026-10-09
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa

from alembic import op

revision = "7a965853ec61"
down_revision = "7d3e9c1a5b42"
branch_labels = None
depends_on = None

KEPT = "radiograph_image_url"
DROPPED = "additional_image_urls"
LABEL = "Images"
PLACEHOLDER = "Radiographs, classification diagrams, post-op X-rays, etc."


def _items(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, dict):
        return [value]
    return []


def merged_content(content: dict[str, Any]) -> dict[str, Any]:
    """The station content with its additional images appended to the one images key."""
    merged = {key: value for key, value in content.items() if key != DROPPED}
    items = _items(content.get(KEPT)) + _items(content.get(DROPPED))
    if items or KEPT in content:
        merged[KEPT] = items
    return merged


def merged_structure(structure: dict[str, Any]) -> dict[str, Any]:
    """The template structure without the additional-images block, its radiograph block relabelled."""
    sections = []
    for section in structure.get("sections", []):
        blocks = []
        for block in section.get("blocks", []):
            if block.get("id") == DROPPED:
                continue
            if block.get("id") == KEPT:
                block = {**block, "label": LABEL, "placeholder": PLACEHOLDER}
            blocks.append(block)
        sections.append({**section, "blocks": blocks})
    return {**structure, "sections": sections}


def upgrade() -> None:
    connection = op.get_bind()
    contents = connection.execute(
        sa.text("SELECT id, content FROM station_versions WHERE content ? :key"), {"key": DROPPED}
    ).all()
    for row_id, content in contents:
        connection.execute(
            sa.text("UPDATE station_versions SET content = CAST(:content AS jsonb) WHERE id = :id"),
            {"content": json.dumps(merged_content(content)), "id": row_id},
        )
    structures = connection.execute(
        sa.text("SELECT id, structure FROM station_template_versions WHERE structure::text LIKE :pattern"),
        {"pattern": f'%"{DROPPED}"%'},
    ).all()
    for row_id, structure in structures:
        connection.execute(
            sa.text(
                "UPDATE station_template_versions SET structure = CAST(:structure AS jsonb) WHERE id = :id"
            ),
            {"structure": json.dumps(merged_structure(structure)), "id": row_id},
        )


def downgrade() -> None:
    # Nothing to undo: which images were "additional" is not recorded once merged.
    pass
