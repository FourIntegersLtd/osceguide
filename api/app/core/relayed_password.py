"""The words an audit row ends with when an admin gave someone a password by hand."""

RELAYED_PASSWORD_NOTE = " (temporary password)"  # noqa: S105 -- audit wording, not a secret
"""Every writer appends this to its audit summary and `tenancy` reads it back, so an account
that began with a relayed password can be told apart from one whose owner chose it."""
