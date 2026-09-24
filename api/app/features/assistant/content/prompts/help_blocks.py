"""The reusable pieces of the help prompt: writing rules, phrasing, navigation.

Split out of `help.py` only because the two together are past this repo's file
size cap. The wording is b2c's, verbatim: it is what the FAQ voice has been
tuned against, and rewriting it would quietly change every answer.
"""

from __future__ import annotations

from ..models import ClientProfile

"""
Curated short phrases for help-worker UI navigation (TTS-friendly, no markdown).
Injected into help_instructions so the model varies wording and avoids repetition.
"""

# After show_pointer in guided mode — combine with FAQ label in the same breath.
GUIDED_CLOSING_PATTERNS: tuple[str, ...] = (
    "Tap {label}, then say next.",
    "{label} — tap it, then next.",
    "There — {label}. Tap when ready, then say next.",
    "That's {label}. Tap, then next.",
    "{label} in the UI — tap, then next.",
)

# Hands-off: after perform_click + verify screenshot succeeds.
HANDS_OFF_ACKS: tuple[str, ...] = (
    "Done.",
    "Next.",
    "Opened.",
    "There.",
    "Got it.",
    "Continuing.",
    "Okay, next.",
)

# If tools fail or user must scroll manually — vary these.
MANUAL_SCROLL_PROMPTS: tuple[str, ...] = (
    "Scroll a bit to find {label}.",
    "Try scrolling to locate {label}.",
    "{label} may be off screen — scroll to find it.",
)


def format_phrase_lists_for_prompt() -> str:
    """Single block appended to system instructions (plain text for the LLM)."""
    guided = "\n        ".join(f"- {p}" for p in GUIDED_CLOSING_PATTERNS)
    hands = " | ".join(HANDS_OFF_ACKS)
    manual = "\n        ".join(f"- {p}" for p in MANUAL_SCROLL_PROMPTS)

    return f"""
        VARIED WORDING — rotate; do not repeat the same phrase twice in a row during one help session.

        After guided step (pointer on screen), use ONE line under 12 words. Vary the template; replace
        {{label}} with the exact FAQ control name. Examples:
        {guided}

        After a successful hands-off click, use ONE short ack under 6 words, varying each step:
        {hands}

        If the user must scroll manually, vary wording; replace {{label}} with the FAQ name:
        {manual}
        """


def instruction_header(*, screen_ui_guidance: bool = False) -> str:
    """TTS-safe writing rules plus the FAQ tool contract, shared by every help prompt."""
    computer_note = ""
    if screen_ui_guidance:
        computer_note = """
        When you use the computer tool, the user sees a progress panel and hears the tool's own
        waiting line, so the pause is covered without you. After tools finish, give at most one
        short sentence with the answer or next step.
        """

    return f"""
        CRITICAL TTS WRITING INSTRUCTIONS FOR ALL RESPONSES:
        1. NEVER use markdown formatting: NO **bold**, NO *italics*, NO __underlines__
        2. NEVER use hashtags (#), dashes (-), underscores (_), or brackets ([], {{}})
        3. To emphasize words, just write them normally - do NOT use asterisks or any symbols
        4. Write conversationally as if speaking to someone face-to-face
        5. Use only plain letters, periods, commas, and question marks

        EXAMPLES OF WHAT NOT TO DO:
        BAD: Click on **Dashboard** to see your progress
        BAD: The *important* thing is to practice
        BAD: You have **3 options**: practice, review, or flag

        EXAMPLES OF CORRECT FORMAT:
        GOOD: Click on Dashboard to see your progress
        GOOD: The important thing is to practice
        GOOD: You have 3 options: practice, review, or flag

        If a user asks for help, needs guidance on how to use a feature, or asks a question
        not related to the clinical scenario, answer ONLY from the FAQ ANSWERS section at the
        end of these instructions. Read the whole list and pick the entries that fit; they are
        your only source of information for these questions. Do not answer from your own
        knowledge. If no entry fits, say you cannot answer from the help articles and direct
        the user to the contact option named there.
        {computer_note}
        """


def navigation_block(profile: ClientProfile) -> str:
    """What the client says the user can see right now; omitted when the client sent no catalog."""
    if not profile.navigation and not profile.route:
        return ""
    lines = [
        f"        - {item.label} ({item.path})" if item.path else f"        - {item.label}"
        for item in profile.navigation
    ]
    current = f"        Current page: {profile.route}\n" if profile.route else ""
    listing = "\n".join(lines) + "\n" if lines else ""
    return f"""
        CLIENT NAVIGATION (the left navigation as this user sees it right now):
{listing}{current}        Only these items exist for this user. Never mention a menu item that is not listed.
        """
