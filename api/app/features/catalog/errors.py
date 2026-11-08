"""The refusals a catalog route can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound


class UnknownExamError(NotFound):
    """No exam matches: missing, unpublished, retired, or the wrong owner."""

    code = "unknown_exam"
    default_message = "We couldn't find that exam"


class ExamNotOwned(NotFound):
    """An exam that exists, but belongs to a different owner.

    Deliberately the same `unknown_exam` a missing exam gets. An institution
    must not be able to learn what the platform is drafting by trying ids, and
    the platform must not learn what an institution is drafting either.
    """

    code = "unknown_exam"
    default_message = "We couldn't find that exam"


class ProgrammeExists(Conflict):
    """This organisation is already running the exam it just tried to add."""

    code = "programme_exists"
    default_message = "That exam is already on this organisation's programme"


class ExamAlreadyImported(Conflict):
    """This organisation already runs the platform exam it asked to import, whether it
    imported it before or added it as a programme by code."""

    code = "exam_already_imported"
    default_message = "That exam is already in this organisation"


class ProgrammeNotFound(NotFound):
    """No programme with that id in this organisation."""

    code = "programme_not_found"
    default_message = "We couldn't find that programme"


class ExamCodeTaken(Conflict):
    """Another exam already has this code in the same owner's namespace."""

    code = "exam_code_taken"
    default_message = "An exam with that code already exists"


class InvalidExamCodeError(InvalidInput):
    """The code does not fit the pattern a URL or ref id can carry."""

    code = "invalid_exam_code"
    default_message = "That exam code can't be used. Choose a different code."


class ExamNotPublishable(Conflict):
    """The exam is retired, or it names no rubric to be marked against."""

    code = "exam_not_publishable"
    default_message = "That exam isn't ready to publish yet. Fix the problems listed and try again."


class ExamInUse(Conflict):
    """Refused by the database, not by a pre-check this slice ran itself.

    Other slices hold the stations, sittings and attempts that reference an
    exam, so `catalog` cannot ask "does anything reference this exam" itself.
    A `RESTRICT` foreign key answers instead: this is what deleting an exam
    with real history becomes.
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
    default_message = "We couldn't find that version of the marking scheme"


class InvalidExamSettings(InvalidInput):
    """The exam's settings name a generation prompt or profile that does not exist."""

    code = "invalid_exam_settings"
    default_message = (
        "These exam settings point to something that doesn't exist. Check the settings and try again."
    )


class ProgrammeNotActive(Conflict):
    """A sitting was scheduled against a programme that is not running, or whose exam is retired."""

    code = "programme_not_active"
    default_message = "That programme is not active, so nothing can be scheduled against it"
