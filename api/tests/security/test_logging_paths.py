"""A one-time token in a request path never reaches the logs."""

from app.core.logging import _loggable_path


def test_an_invitation_token_is_blanked_from_the_logged_path() -> None:
    assert _loggable_path("/api/v1/auth/invitation/abc123") == "/api/v1/auth/invitation/[token]"
    assert _loggable_path("/api/v1/me/dashboard") == "/api/v1/me/dashboard"
