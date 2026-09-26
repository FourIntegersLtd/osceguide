"""What the public site may send us, and what it may be told.

Two unrelated things that happen to share a caller: an anonymous visitor
writing to us, and an anonymous visitor reading a number off the landing page.
They are together because they have the same threat model — nobody is signed
in — and the rules below are all about that.
"""

from __future__ import annotations

from enum import StrEnum

MAX_NAME = 120
MAX_SUBJECT = 200
MAX_BODY = 5_000


class MessageKind(StrEnum):
    """Why somebody wrote.

    Separate kinds rather than one "message" because they are read by different people: a contact
    message wants answering, and product feedback wants collating.
    """

    CONTACT = "contact"
    PRODUCT_FEEDBACK = "product_feedback"


class InvalidMessage(Exception):
    pass


def normalise_kind(raw_kind: str) -> MessageKind:
    try:
        return MessageKind((raw_kind or "").strip().lower())
    except ValueError as exc:
        raise InvalidMessage(f"{raw_kind!r} is not something this form sends.") from exc


def clean(raw: str | None) -> str:
    return (raw or "").strip()


def ensure_sendable(*, name: str, email: str, body: str, kind: MessageKind) -> None:
    """What a message needs before it is worth keeping.

    An address is required for contact and not for feedback: somebody telling
    us a button is confusing should not have to identify themselves, and
    somebody asking a question has to be answerable.
    """
    if not clean(body):
        raise InvalidMessage("There is nothing to send.")
    if len(clean(body)) > MAX_BODY:
        raise InvalidMessage(f"A message is at most {MAX_BODY} characters.")
    if len(clean(name)) > MAX_NAME:
        raise InvalidMessage(f"A name is at most {MAX_NAME} characters.")
    if kind is MessageKind.CONTACT:
        address = clean(email)
        if not address or "@" not in address:
            raise InvalidMessage("An email address is required so we can reply.")
