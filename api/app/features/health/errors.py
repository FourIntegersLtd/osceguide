"""The errors this slice's routes declare. Each `code` is a contract clients branch on, never `message`."""

from __future__ import annotations

# Re-exported: the console's mail retry is refused with notifications' own
# error, and the router may only name this slice's errors.
from app.features.notifications.errors import MessageNotRetryable as MessageNotRetryable
