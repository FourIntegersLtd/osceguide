"""The FAQ answers rendered straight into the help instructions.

The whole pack fits in a few thousand tokens, so the model reads every entry
itself instead of a keyword search choosing a handful for it.
"""

from __future__ import annotations

from ..models import ContentPack

FAQ_BLOCK_HEADER = "FAQ ANSWERS — the ONLY source for questions about using the app."


def render_faq_block(pack: ContentPack) -> str:
    lines = [FAQ_BLOCK_HEADER, f"If no entry fits the question: {pack.no_match_message}".rstrip(": "), ""]
    for entry in pack.faq:
        lines += [f"[{entry.section}]", f"QUESTION: {entry.question}", f"ANSWER: {entry.answer}", ""]
    return "\n".join(lines).strip()
