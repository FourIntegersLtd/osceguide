from __future__ import annotations

from app.core.errors import Conflict, NotFound


class TraineeNotFound(NotFound):
    code = "trainee_not_found"
    default_message = "No such trainee"


class TraineeExists(Conflict):
    code = "trainee_exists"
    default_message = "Someone with that email is already on this roster"


class CohortNotFound(NotFound):
    code = "cohort_not_found"
    default_message = "No such cohort"


class GroupNotFound(NotFound):
    code = "group_not_found"
    default_message = "No such group"


class GroupExists(Conflict):
    code = "group_exists"
    default_message = "A group with that label already exists"


class TraineeRevokedError(Conflict):
    code = "trainee_revoked"
    default_message = "That trainee's access has been revoked"
