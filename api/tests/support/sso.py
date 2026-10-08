"""A single-sign-on configuration body for tests."""

from __future__ import annotations


def a_config(**over: object) -> dict:
    body: dict = {
        "provider": "clerk",
        "issuer": "https://accounts.bmj.com",
        "enabled": True,
        "sso_only": True,
        "sign_in_label": "Sign in with BMJ",
        "hosts": ["https://BMJ.osceguide.com/"],
        "email_domains": ["someone@bmj.com"],
    }
    body.update(over)
    return body
