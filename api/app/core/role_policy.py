"""The registry where a slice's role rules meet core's dependencies.

The predicates themselves belong to `features/tenancy/domain.py` — who counts
as an admin is a tenancy rule. The place that *applies* them is core, which
may not import a feature. They meet here, bound once by `main.py`, so every
slice can write `workspace: OrgAdmin` without importing another slice's
service.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

RolePredicate = Callable[[str | None], bool]

_policies: dict[str, RolePredicate] = {}


def bind_role_policy(**predicates: RolePredicate) -> None:
    """Wire a slice's named role predicates in, once, at start-up."""
    _policies.update(predicates)


@dataclass(frozen=True)
class Policy:
    """A late-bound predicate, so an annotation can name a rule before `main.py` ties it.

    Looked up per call, not at import, so `OrgAdmin` can be declared at module
    level and still fail loudly, naming the missing binding, if the
    composition root forgot it. The name is kept so the OpenAPI document can
    say which rung a route enforces.
    """

    name: str

    def __call__(self, role: str | None) -> bool:
        """Look the bound rule up now, so a late binding still takes effect."""
        try:
            return _policies[self.name](role)
        except KeyError as exc:
            raise RuntimeError(
                f"No {self.name!r} role policy bound. app.main.create_app must call bind_role_policy."
            ) from exc


def policy(name: str) -> Policy:
    """The named rule, applied by whatever `main.py` binds to that name."""
    return Policy(name)
