"""One map from a lifecycle refusal to the API error that carries its status.

Shared by every module that drives the state machine — stations, their versions, station templates
and rubrics all publish, edit and archive the same way. A copy per module risks mapping a refusal to
a plausible but wrong status code.
"""

from __future__ import annotations

from app.core.errors import AppError
from app.features.stations import domain, errors

REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.NotEditable: errors.NotEditableError,
    domain.NotDeletable: errors.NotDeletableError,
    domain.AlreadyPublished: errors.AlreadyPublishedError,
    domain.DraftExists: errors.DraftExistsError,
    domain.NotArchivable: errors.NotArchivableError,
    domain.TemplateNotPublished: errors.TemplateNotPublishedError,
    domain.StationNotPublished: errors.StationNotPublishedError,
}
