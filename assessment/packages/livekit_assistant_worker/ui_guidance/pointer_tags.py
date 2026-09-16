"""Pointer tags the model writes inline in its own reply.

Instead of spending a second tool call to place a highlight, the model writes
``[POINT:840,210:AI Practice]`` in the sentence that names the control. The tag
is taken out before the words reach the speaker, and the highlight is published
as the stream passes it — so the pointer appears exactly as the user hears the
control named, and the turn costs one model round trip instead of two.

The stream arrives a few tokens at a time, so a tag routinely straddles two
chunks. The filter holds back only text that could still turn into a tag, and
anything that stops looking like one is released as ordinary speech.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

__all__ = ["PointerTag", "PointerTagFilter", "strip_pointer_tags", "POINTER_TAG_SYNTAX"]

POINTER_TAG_SYNTAX = "[POINT:x,y:Label]"

_OPENER = "[point:"

# A label runs to the closing bracket, so it cannot contain one.
_TAG = re.compile(
    r"\[POINT\s*:\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*(?::\s*([^\]]*?))?\s*\]",
    re.IGNORECASE,
)

# Past this, an unclosed bracket is not a tag being typed — it is prose. Releasing
# it keeps a stray "[" from swallowing the rest of the sentence.
_MAX_TAG_CHARS = 120


@dataclass(frozen=True)
class PointerTag:
    x: float
    y: float
    label: str


class PointerTagFilter:
    """Incremental removal of pointer tags from a text stream."""

    def __init__(self) -> None:
        self._buffer = ""
        # A tag sits next to the space that separated it from the words. Removing
        # the tag would otherwise leave that space doubled mid-sentence, or
        # stranded at the head of the reply where it reaches the transcript.
        self._drop_next_space = True
        self._last_emitted = ""

    def feed(self, chunk: str) -> tuple[str, list[PointerTag]]:
        """Text safe to speak now, and any tags completed by this chunk."""
        self._buffer += chunk
        return self._drain(final=False)

    def flush(self) -> tuple[str, list[PointerTag]]:
        """Everything left at the end of the stream, tags included."""
        text, tags = self._drain(final=True)
        remainder, self._buffer = self._buffer, ""
        return text + remainder, tags

    def _drain(self, *, final: bool) -> tuple[str, list[PointerTag]]:
        out: list[str] = []
        tags: list[PointerTag] = []

        def emit(text: str) -> None:
            if self._drop_next_space:
                text = text.lstrip(" ")
                if not text:
                    return
                self._drop_next_space = False
            out.append(text)
            self._last_emitted = text[-1]

        while self._buffer:
            start = self._buffer.find("[")
            if start == -1:
                emit(self._buffer)
                self._buffer = ""
                break
            if start:
                emit(self._buffer[:start])
                self._buffer = self._buffer[start:]

            match = _TAG.match(self._buffer)
            if match:
                tags.append(
                    PointerTag(
                        x=float(match.group(1)),
                        y=float(match.group(2)),
                        label=(match.group(3) or "").strip(),
                    )
                )
                self._buffer = self._buffer[match.end():]
                # Swallow the separator only when the words either side would
                # otherwise collide with a space that no longer separates anything.
                self._drop_next_space = self._last_emitted in ("", " ")
                continue

            if not final and self._may_still_close(self._buffer):
                break

            # Not a tag after all: let the bracket through and keep looking.
            emit(self._buffer[0])
            self._buffer = self._buffer[1:]

        return "".join(out), tags

    @staticmethod
    def _may_still_close(buffer: str) -> bool:
        if len(buffer) > _MAX_TAG_CHARS:
            return False
        lowered = buffer.lower()
        if len(lowered) < len(_OPENER):
            return _OPENER.startswith(lowered)
        if not lowered.startswith(_OPENER):
            return False
        # The opener is there; only keep waiting while the tag is still unclosed.
        # A closed tag that did not match the pattern is malformed, and is spoken.
        return "]" not in buffer


OnPointer = Callable[[PointerTag], Awaitable[None] | None]


async def strip_pointer_tags(
    stream: AsyncIterable[Any], on_pointer: OnPointer | None = None
) -> AsyncIterator[Any]:
    """Yield the stream without its pointer tags, reporting each one as it passes.

    Chunks containing no tag machinery are yielded unchanged, so a ``TimedString``
    keeps its word timings on every turn that does not point at anything.
    """
    tag_filter = PointerTagFilter()

    async for chunk in stream:
        text, tags = tag_filter.feed(str(chunk))
        for tag in tags:
            await _report(on_pointer, tag)
        if text == chunk:
            yield chunk  # untouched, so keep the original object and its metadata
        elif text:
            yield text

    text, tags = tag_filter.flush()
    for tag in tags:
        await _report(on_pointer, tag)
    if text:
        yield text


async def _report(on_pointer: OnPointer | None, tag: PointerTag) -> None:
    if on_pointer is None:
        return
    result = on_pointer(tag)
    if result is not None:
        await result
