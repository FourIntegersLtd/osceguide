from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound


class UnknownExamError(NotFound):
    code = "unknown_exam"
    default_message = "No such exam"


class ProgrammeExists(Conflict):
    code = "programme_exists"
    default_message = "That exam is already on this organisation's programme"


class ProgrammeNotFound(NotFound):
    code = "programme_not_found"
    default_message = "No such programme"


class ExamCodeTaken(Conflict):
    code = "exam_code_taken"
    default_message = "An exam with that code already exists"


class InvalidExamCodeError(InvalidInput):
    code = "invalid_exam_code"
    default_message = "That is not a usable exam code"


class ExamNotPublishable(Conflict):
    code = "exam_not_publishable"
    default_message = "That exam cannot be published as it stands"


class RubricVersionNotFound(NotFound):
    """Mirrors `rubrics.errors.RubricVersionNotFound`.

    Declared here as well so this slice's routes can document the refusal
    without importing another slice's error class into their signature.
    """

    code = "rubric_version_not_found"
    default_message = "No such rubric version"
