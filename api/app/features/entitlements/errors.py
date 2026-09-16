from __future__ import annotations

from app.core.errors import Forbidden


class NotEntitled(Forbidden):
    """No live grant and no trial left.

    One code whatever the reason, with the detail in `details`: the client shows
    an upgrade prompt either way, and the distinction between "expired" and
    "never had one" is for us, not for them.
    """

    code = "not_entitled"
    default_message = "You do not have access to this exam"
