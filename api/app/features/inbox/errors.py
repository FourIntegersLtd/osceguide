"""The refusals an inbox route can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import NotFound
from app.features.identity.errors import UserNotFound

__all__ = ["AnnouncementNotFound", "InboxMessageNotFound", "UserNotFound"]


class InboxMessageNotFound(NotFound):
    """No such message, or one that is not yours to see."""

    code = "inbox_message_not_found"
    default_message = "We couldn't find that message"


class AnnouncementNotFound(NotFound):
    """No such announcement."""

    code = "announcement_not_found"
    default_message = "We couldn't find that announcement"
