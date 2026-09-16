"""The error vocabulary is the frontend's contract, so it is machine-checked.

b2b decides control flow by substring-matching English prose — whether a
trainee retries or is told the facilitator ended the session turns on
`message.includes("not live")`. Rewording a message changes behaviour. The
replacement is `ErrorResponse.code`, which only helps if the codes are
stable, distinct and known in advance.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core import errors as core_errors
from app.core.errors import AppError, error_codes, error_responses, register_error_handlers
from app.main import create_app
from tests.support.declared_codes import UndeclaredErrorCode
from tests.support.declared_codes import install as install_declared_code_check

# The generic classes are the vocabulary's base and carry codes of their own.
_BASES = {
    core_errors.InvalidInput,
    core_errors.Unauthenticated,
    core_errors.Forbidden,
    core_errors.NotFound,
    core_errors.Conflict,
    core_errors.Gone,
    core_errors.Unavailable,
}

# `RefreshTokenReused` deliberately answers with its parent's code: a client
# behaves identically and an attacker learns nothing from being told that the
# chain was detected as leaked. See `identity/errors.py`.
_MAY_INHERIT = {"RefreshTokenReused"}


def _subclasses() -> list[type[AppError]]:
    out: list[type[AppError]] = []

    def walk(cls: type[AppError]) -> None:
        for sub in cls.__subclasses__():
            out.append(sub)
            walk(sub)

    create_app()  # imports every slice, so the hierarchy is complete
    walk(AppError)
    return out


def test_every_error_declares_its_own_code() -> None:
    """An inherited code reports `conflict` where the client needed `slot_locked`."""
    inherited = [
        f"{cls.__module__}.{cls.__name__} (inherits {cls.code!r})"
        for cls in _subclasses()
        if cls not in _BASES and "code" not in cls.__dict__ and cls.__name__ not in _MAY_INHERIT
    ]
    assert inherited == []


def test_the_published_catalogue_covers_every_error() -> None:
    catalogue = set(error_codes())
    missing = sorted({cls.code for cls in _subclasses()} - catalogue)
    assert missing == []


def test_the_catalogue_reaches_the_document_as_an_enum() -> None:
    """Without this the generated TypeScript types `code` as `string`."""
    spec = create_app().openapi()
    published = spec["components"]["schemas"]["ErrorResponse"]["properties"]["code"]
    assert published.get("enum") == error_codes()


@pytest.mark.asyncio
async def test_the_declared_code_check_catches_an_undeclared_code() -> None:
    """The planted violation: a route that raises what it does not document.

    Without this, `tests/support/declared_codes.py` could be inert and the
    suite would look like it proved something.
    """

    class Planted(core_errors.Conflict):
        code = "planted_violation"

    app = FastAPI()
    register_error_handlers(app)
    install_declared_code_check(app)

    @app.get("/planted", responses=error_responses(core_errors.NotFound))
    async def planted() -> None:
        raise Planted

    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        with pytest.raises(UndeclaredErrorCode, match="planted_violation"):
            await http.get("/planted")
