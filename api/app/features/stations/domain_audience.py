"""Building a station's document into what one audience may read of it.

A template's structure names each section's audience — `candidate`, `patient`
or `examiner` — and each block's role. This turns a station's content (already
lifted onto block ids by `domain_content.content_for_template`) into the
sections one audience may see, in the order the template lists them.

Pure functions, no session: the peer to `attempts/domain_definition.py`'s
role-driven prompt, which answers the same "who is this block for" question
for the live persona rather than for a screen. Unlike the legacy per-exam key
lists in `attempts/domain_material.py` and `stations/domain_content.py`, this
reads the template's own audience and role fields, so a block with a custom id
— one that is not `management_plan` or `doctor_information` — still reaches
the reader its template says it is for.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# A block carrying this role is the patient's own material — their ICE, the
# question they hold back, the history they only reveal expanded — written for
# the patient persona to play. It is dropped from every audience projection
# unless the caller asks for it explicitly (`include_hidden`), which only the
# roleplay script and the peer-practice patient actor do.
_HIDDEN_ROLE = "hidden"
_EXAMINER_ROLE = "examiner"


@dataclass(frozen=True)
class AudienceBlock:
    """One block of a section, as this audience may read it."""

    id: str
    label: str
    type: str
    role: str
    value: Any
    fields: list[dict[str, str]] | None = None


@dataclass(frozen=True)
class AudienceSection:
    """One section of the document, filtered to a single audience."""

    id: str
    title: str
    audience: str
    blocks: list[AudienceBlock]


def _is_empty(value: Any) -> bool:
    """Whether a block's value is worth showing at all.

    An author who left a field blank should not see a heading over nothing on
    the other side, so an empty string, list or mapping is dropped the same as
    `None`. `0` and `False` are not empty — a duration of zero minutes or a
    checkbox left off is still an authored answer.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    return False


def sections_for(
    sections: list[Any],
    content: Mapping[str, Any],
    audience: str,
    *,
    include_hidden: bool = False,
) -> list[AudienceSection]:
    """The sections written for this audience, in template order, with content filled in.

    A section whose audience does not match is skipped entirely. Within a
    matching section, a block with nothing written for it is dropped, and a
    `hidden`-role block is dropped unless `include_hidden` — the patient's own
    material, kept off the candidate's and the examiner's reads. A section
    that ends up with no blocks is dropped too, rather than rendered as an
    empty heading.
    """
    result: list[AudienceSection] = []
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        section_audience = str(section.get("audience") or "")
        blocks: list[AudienceBlock] = []
        for block in section.get("blocks") or []:
            if not isinstance(block, Mapping):
                continue
            block_id = str(block.get("id") or "")
            if not block_id:
                continue
            role = str(block.get("role") or "")
            if not _visible(role, section_audience, audience, include_hidden=include_hidden):
                continue
            value = content.get(block_id)
            if _is_empty(value):
                continue
            blocks.append(
                AudienceBlock(
                    id=block_id,
                    label=str(block.get("label") or ""),
                    type=str(block.get("type") or ""),
                    role=role,
                    value=value,
                    fields=_record_fields(block.get("fields")),
                )
            )
        if not blocks:
            continue
        result.append(
            AudienceSection(
                id=str(section.get("id") or ""),
                title=str(section.get("title") or ""),
                audience=audience,
                blocks=blocks,
            )
        )
    return result


def _record_fields(fields: Any) -> list[dict[str, str]] | None:
    """A `records` block's `{key, label}` columns, keeping only well-formed ones."""
    if not isinstance(fields, list):
        return None
    columns = [
        {"key": str(column["key"]), "label": str(column.get("label") or column["key"])}
        for column in fields
        if isinstance(column, Mapping) and column.get("key")
    ]
    return columns or None


def _visible(role: str, section_audience: str, audience: str, *, include_hidden: bool) -> bool:
    """Whether one block reaches one audience: its role decides first, then its section.

    An `examiner`-role block is the model answer wherever an author filed it —
    the Ortho prioritisation template keeps its suggested order inside a
    candidate section — so it reaches the examiner audience and nobody else.
    """
    if role == _EXAMINER_ROLE:
        return audience == _EXAMINER_ROLE
    if section_audience != audience:
        return False
    return role != _HIDDEN_ROLE or include_hidden


def sections_as_text(sections: list[AudienceSection]) -> str:
    """The sections rendered as plain text: the worker's `candidate_brief` contract.

    One paragraph per section — its title as a heading line, then each block
    as a `label: value` line — separated by a blank line. Prose, not JSON: the
    worker's prompt formatter reads a brief as text a candidate would read on
    screen, not a structure it has to walk.
    """
    paragraphs: list[str] = []
    for section in sections:
        lines = [section.title] if section.title else []
        for block in section.blocks:
            rendered = _render_value(block.value)
            if not rendered:
                continue
            lines.append(f"{block.label or block.id}: {rendered}")
        # A section whose title is the only line has nothing under it.
        if len(lines) > (1 if section.title else 0):
            paragraphs.append("\n".join(lines))
    return "\n\n".join(paragraphs)


def _render_value(value: Any) -> str:
    """A block's value as one line of text, whatever shape it was authored in."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        rendered_pairs = [
            f"{key}: {text}" for key, sub_value in value.items() if (text := _render_value(sub_value))
        ]
        return ", ".join(rendered_pairs)
    if isinstance(value, (list, tuple)):
        rendered_items = [text for item in value if (text := _render_value(item))]
        return "; ".join(rendered_items)
    return str(value)
