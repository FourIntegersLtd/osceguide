# 0005. Errors are typed exceptions; one handler; one error shape

Date: 2026-09-15
Status: accepted

## Context
b2b services returned `(ok, result)` tuples and every handler re-derived the HTTP status by matching substrings of the error message (`if "locked" in msg.lower(): return 409`). Rewording a message silently changed the API. b2c returned `{"error": str(e)}` with 500, leaking internal detail.

## Decision
Services raise subclasses of `AppError`. The class carries `status` and `code`; slices define their own subclasses (`class SlotLocked(Conflict): code = "slot_locked"`). A single exception handler renders `ErrorResponse{code, message, details, request_id}`. Request validation and unhandled exceptions render the same shape. Routes declare their error responses so OpenAPI documents them.

## Consequences
- Handlers contain no status logic.
- The frontend switches on `code` and never on `message`.
- Unhandled errors are logged with the request id and never expose internals.
