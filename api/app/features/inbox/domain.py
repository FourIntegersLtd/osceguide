"""What a message says and who may see it. Pure: no I/O."""

from __future__ import annotations

from typing import Literal

Kind = Literal["report_answer", "reply", "note", "announcement"]

FROM_LABEL = "OSCE Guide team"
DEFAULT_ANSWER_BODY = "We have looked at your report and closed it. Thank you for telling us."


def report_answer_subject(station_title: str | None) -> str:
    """The subject of the answer to a station report, naming the station when we know it."""
    return f"About your report: {station_title}" if station_title else "About your station report"


def reply_subject(original: str | None) -> str:
    """The subject of a reply: the original, prefixed once with "Re:"."""
    subject = (original or "").strip()
    if not subject:
        return "Re: your message to us"
    return subject if subject.lower().startswith("re:") else f"Re: {subject}"


def report_answer_body(note: str | None) -> str:
    """The staff note, or a plain default when they closed the report without one."""
    return (note or "").strip() or DEFAULT_ANSWER_BODY
