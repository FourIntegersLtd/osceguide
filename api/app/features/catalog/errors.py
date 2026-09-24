from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound


class UnknownExamError(NotFound):
    code = "unknown_exam"
    default_message = "No such exam"


class ExamNotOwned(NotFound):
    """An exam that exists, but belongs to a different owner.

    Deliberately the same `unknown_exam` a missing exam gets. An institution
    must not be able to learn what the platform is drafting by trying ids, and
    the platform must not learn what an institution is drafting either.
    """

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


class ExamInUse(Conflict):
    """Refused by the database, not by a pre-check this slice ran itself.

    `catalog` sits near the bottom of the layer contract — nearly every other
    slice imports it, not the reverse — so it cannot ask "does anything
    reference this exam" the way `station_sets` asks about its own attempts.
    A `RESTRICT` foreign key somewhere above answers instead: retire an exam
    with real history, this is what the delete becomes.
    """

    code = "exam_in_use"
    default_message = (
        "This exam has stations, sittings or attempts recorded against it. Retire it instead of deleting it."
    )


class RubricVersionNotFound(NotFound):
    """Mirrors `rubrics.errors.RubricVersionNotFound`.

    Declared here as well so this slice's routes can document the refusal
    without importing another slice's error class into their signature.
    """

    code = "rubric_version_not_found"
    default_message = "No such rubric version"
