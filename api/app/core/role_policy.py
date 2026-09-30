"""The registry where a slice's role rules meet core's dependencies.

The predicates themselves belong to `features/tenancy/domain.py` — who counts
as an admin is a tenancy rule. The place that *applies* them is core, which
may not import a feature. They meet here, bound once by `main.py`, so every
slice can write `workspace: OrgAdmin` without importing another slice's
service.
"""

from __future__ import annotations

from collections.abc import Callable

RolePredicate = Callable[[str | None], bool]

_policies: dict[str, RolePredicate] = {}


def bind_role_policy(**predicates: RolePredicate) -> None:
    """Wire a slice's named role predicates in, once, at start-up."""
    _policies.update(predicates)


def policy(name: str) -> RolePredicate:
    """A late-bound predicate, so an annotation can name a rule before `main.py` ties it.

    Looked up per call, not at import, so `OrgAdmin` can be declared at module
    level and still fail loudly, naming the missing binding, if the
    composition root forgot it.
    """

    def predicate(role: str | None) -> bool:
        """Look the bound rule up now, so a late binding still takes effect."""
        try:
            return _policies[name](role)
        except KeyError as exc:
            raise RuntimeError(
                f"No {name!r} role policy bound. app.main.create_app must call bind_role_policy."
            ) from exc

    return predicate


# Whether an org's status still permits its members to act. Bound the same way
# and for the same reason: the rule belongs to the slice, the enforcement point
# belongs to core.
_access_policy: list[Callable[[str | None], bool]] = []


def bind_org_access_policy(predicate: Callable[[str | None], bool]) -> None:
    """Wire the slice's org-status rule in, once, at start-up."""
    _access_policy.clear()
    _access_policy.append(predicate)


def org_permits_access(status: str | None) -> bool:
    """Whether an org with this status still permits its members to act."""
    if not _access_policy:
        raise RuntimeError(
            "No org access policy bound. app.main.create_app must call bind_org_access_policy."
        )
    return _access_policy[0](status)
