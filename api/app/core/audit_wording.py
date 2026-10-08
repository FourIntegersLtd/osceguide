"""The words audit summaries end with when an admin seats or adds someone.

`tenancy` reads them back to tell an account that began with a password somebody else chose from
one whose owner chose it, so every writer and that reader build the text here.
"""

RELAYED_PASSWORD_NOTE = " (temporary password)"  # noqa: S105 -- audit wording, not a secret
INVITED_NOTE = " (invited)"


def seating_note(*, relayed: bool) -> str:
    """The suffix for a seat or roster add that created the account: how the person is to get in."""
    return RELAYED_PASSWORD_NOTE if relayed else INVITED_NOTE


def roster_added_summary(email: str, note: str = "") -> str:
    """The `trainee.added` summary; `note` is empty when the address already had an account."""
    return f"Added {email} to the roster{note}"
