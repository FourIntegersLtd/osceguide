"""Errors are exceptions, and the type carries the HTTP status.

Services raise an `AppError` subclass. One handler turns it into an
`ErrorResponse`. Routers never inspect messages to pick a status code, and the
frontend switches on `code`, never on `message`.

Slices subclass these for their own vocabulary, for example
`class SlotLocked(Conflict): code = "slot_locked"`.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, NoReturn

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

log = logging.getLogger(__name__)


# The shape of every AppError response; clients switch on `code`, never `message`.
class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class AppError(Exception):

    status: int = 500
    code: str = "internal_error"
    default_message: str = "Something went wrong"

    # Normally a failed request leaves no trace: the transaction rolls back.
    # A few failures must record something anyway — e.g. revoking a refresh
    # chain proven to have leaked, while still answering 401. Such an error
    # sets this, and `core.db.get_session` commits instead of rolling back.
    persist_effects: bool = False

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


def raise_mapped(exc: Exception, mapping: Mapping[type[Exception], type[AppError]]) -> NoReturn:
    """Translate a domain refusal into the API error that carries its status.

    Matched with `isinstance`, in the mapping's order, so a subclass of a
    mapped refusal is not silently dropped. An exception the mapping does not
    name is re-raised as-is, rather than falling back to some arbitrary error
    that would misreport an unexpected failure as a plausible one.
    """
    for refusal, app_error in mapping.items():
        if isinstance(exc, refusal):
            raise app_error(str(exc)) from exc
    raise exc


class InvalidInput(AppError):

    status = 422
    code = "invalid_input"
    default_message = "The request was not valid"


class Unauthenticated(AppError):

    status = 401
    code = "unauthenticated"
    default_message = "Authentication required"


class Forbidden(AppError):

    status = 403
    code = "forbidden"
    default_message = "You do not have access to this resource"


class NotFound(AppError):

    status = 404
    code = "not_found"
    default_message = "Resource not found"


class Conflict(AppError):

    status = 409
    code = "conflict"
    default_message = "The request conflicts with the current state"


class Gone(AppError):

    status = 410
    code = "gone"
    default_message = "This resource is no longer available"


class Unavailable(AppError):

    status = 503
    code = "unavailable"
    default_message = "A dependency is unavailable"


def error_codes() -> list[str]:
    """Every `code` any `AppError` in the app can carry, sorted.

    Published as the enum of `ErrorResponse.code` so the generated TypeScript
    is a closed union rather than `string`, and a typo becomes a compile error
    instead of a silently broken `message.includes(...)` check.

    Walked from the class hierarchy rather than kept as a list, which would be
    a second place to forget. Every feature module is imported by the time the
    document is built, so the walk sees all of them.
    """
    found: set[str] = set()

    def walk(cls: type[AppError]) -> None:
        for sub in cls.__subclasses__():
            found.add(sub.code)
            walk(sub)

    found.add(AppError.code)
    walk(AppError)
    return sorted(found)


# The code every bearer route can answer with once an account is deactivated:
# `core.auth` refuses the token on its next request, whatever the route. Named
# here rather than in `auth` because this module cannot import that one, and
# `error_responses` declares it wherever `Unauthenticated` is declared.
ACCOUNT_DEACTIVATED_CODE = "account_suspended"


def error_responses(*errors: type[AppError]) -> dict[int | str, dict[str, Any]]:
    """Build the `responses=` mapping for a route so OpenAPI documents its errors.

    Declaring `Unauthenticated` also declares the deactivated-account refusal,
    so the frontend's generated types know the code to sign the person out
    cleanly.
    """
    responses: dict[int | str, dict[str, Any]] = {}
    for err in errors:
        entry = responses.setdefault(err.status, {"model": ErrorResponse, "description": ""})
        codes = entry.setdefault("x-codes", [])
        codes.append(err.code)
        if err is Unauthenticated and ACCOUNT_DEACTIVATED_CODE not in codes:
            codes.append(ACCOUNT_DEACTIVATED_CODE)
        entry["description"] = ", ".join(codes)
    return responses


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error_response(request: Request, status: int, body: ErrorResponse) -> JSONResponse:
    body.request_id = _request_id(request)
    return JSONResponse(status_code=status, content=body.model_dump())


def register_error_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(
            request, exc.status, ErrorResponse(code=exc.code, message=exc.message, details=exc.details)
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = {"errors": [dict(error, ctx=None) for error in exc.errors()]}
        return _error_response(
            request,
            422,
            ErrorResponse(code="invalid_input", message="The request was not valid", details=details),
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error", extra={"request_id": _request_id(request)})
        return _error_response(
            request, 500, ErrorResponse(code="internal_error", message="Something went wrong")
        )
