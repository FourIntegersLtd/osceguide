"""Turns the JSON an LLM returns, still shaped like the old B2C service's models, into the
keys the platform's media and authoring code expects.
"""

from __future__ import annotations

from typing import Any


def _as_str_list(raw_value: Any) -> list[str]:
    """The blank and non-string entries stripped out, or an empty list if raw_value is not a list at all."""
    if not isinstance(raw_value, list):
        return []
    return [str(item) for item in raw_value if item is not None and str(item).strip()]


def normalize_summary_response(raw: dict[str, Any]) -> dict[str, Any]:
    """B2C ScaSummaryModel fields → platform summary draft keys."""
    if "title" in raw and "name" not in raw:
        return raw
    name = str(raw.get("name") or raw.get("title") or "Untitled")
    red_flags = _as_str_list(raw.get("red_flags"))
    examinations = _as_str_list(raw.get("examinations"))
    brief_management = _as_str_list(raw.get("brief_management"))
    psychosocial = _as_str_list(raw.get("psychosocial_aspects"))

    sections: list[str] = []
    if red_flags:
        sections.append("## Red flags\n" + "\n".join(f"- {line}" for line in red_flags))
    if examinations:
        sections.append("## Examinations\n" + "\n".join(f"- {line}" for line in examinations))
    if brief_management:
        sections.append("## Brief management\n" + "\n".join(f"- {line}" for line in brief_management))
    if psychosocial:
        sections.append("## Psychosocial aspects\n" + "\n".join(f"- {line}" for line in psychosocial))

    body_md = "\n\n".join(sections)
    summary_line = red_flags[0] if red_flags else (examinations[0] if examinations else name)

    return {
        "title": name,
        "summary": summary_line,
        "body_md": body_md,
        "red_flags": red_flags,
        "examinations": examinations,
        "brief_management": brief_management,
        "psychosocial_aspects": psychosocial,
    }


def _first_paragraph(markdown: str) -> str:
    """The first non-heading paragraph of a Markdown body, trimmed to 500 characters, for use as a summary."""
    for block in markdown.split("\n\n"):
        line = block.strip()
        if line and not line.startswith("#"):
            return line[:500]
    stripped = markdown.strip()
    return stripped[:500] if stripped else ""


def normalize_blog_response(raw: dict[str, Any]) -> dict[str, Any]:
    """B2C blog fields to platform blog draft keys, deriving a summary from the body when none was given."""
    if "body_md" in raw and "content" not in raw:
        return raw
    title = str(raw.get("title") or "Untitled")
    content = str(raw.get("content") or raw.get("body_md") or "")
    url = str(raw.get("url") or "")
    summary = str(raw.get("summary") or _first_paragraph(content))
    normalized: dict[str, Any] = {
        "title": title,
        "summary": summary,
        "body_md": content,
    }
    if url:
        normalized["url"] = url
    return normalized


def normalize_slide_deck_response(raw: dict[str, Any]) -> dict[str, Any]:
    """B2C slide fields to platform slide deck draft keys. Passes raw through unchanged if it isn't shaped
    like either a platform deck or a B2C one.
    """
    if "topic" in raw and "slides" in raw:
        return raw
    title = str(raw.get("title") or "Untitled")
    slides = raw.get("slides")
    if isinstance(slides, list):
        return {"topic": title, "about": str(raw.get("summary") or ""), "slides": slides}
    return raw


def normalize_podcast_response(raw: dict[str, Any]) -> dict[str, Any]:
    """B2C podcast fields to a platform podcast draft's `script` key, falling back to dumping the whole
    response as JSON if neither a script nor a content field is present.
    """
    if "script" in raw:
        return raw
    title = {"title": str(raw["title"])} if raw.get("title") else {}
    if "content" in raw:
        return {**title, "script": str(raw["content"])}
    return {**title, "script": json_dumps_safe(raw)}


def json_dumps_safe(value: Any) -> str:
    """Any JSON-serialisable value, dumped without escaping non-ASCII characters."""
    import json

    return json.dumps(value, ensure_ascii=False)
