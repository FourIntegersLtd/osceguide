from __future__ import annotations

from app.core.errors import Conflict, NotFound


class UnknownExamError(NotFound):
    code = "unknown_exam"
    default_message = "No such exam"


class ProgrammeExists(Conflict):
    code = "programme_exists"
    default_message = "That exam is already on this organisation's programme"


class ProgrammeNotFound(NotFound):
    code = "programme_not_found"
    default_message = "No such programme"
