"""A membership is revoked only through the functions that also spend its invitations.

An emailed invitation is a credential (`confirm_password_reset` signs the holder in). Revoking
the seat without spending it leaves a way in for someone who has no seat. The two functions in
`tenancy/service_memberships.py` do both; a third writer would not.
"""

from __future__ import annotations

import ast

from tests.guards._scan import APP_ROOT, python_files, rel

WRITER = "set_membership_revoked"
SPENDING = "app/features/tenancy/service_memberships.py"
REPOSITORY = "app/features/tenancy/repository.py"


def _calls(path) -> list[ast.Call]:  # type: ignore[no-untyped-def]
    return [
        node
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == WRITER
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "repository"
    ]


def _restores(call: ast.Call) -> bool:
    return any(
        k.arg == "at" and isinstance(k.value, ast.Constant) and k.value.value is None for k in call.keywords
    )


def test_only_the_spending_functions_revoke_a_membership_row() -> None:
    """Outside `service_memberships.py` the repository write may only restore (`at=None`)."""
    offenders = [
        f"{rel(path)}:{call.lineno}"
        for path in python_files(APP_ROOT / "features")
        if rel(path) != SPENDING
        for call in _calls(path)
        if not _restores(call)
    ]
    assert offenders == [], f"revoke through service_memberships so invitations are spent: {offenders}"


def test_nothing_else_updates_membership_rows() -> None:
    offenders = [
        rel(path)
        for path in python_files(APP_ROOT / "features")
        if rel(path) != REPOSITORY and "update(Membership)" in path.read_text()
    ]
    assert offenders == [], f"membership writes belong in tenancy/repository.py: {offenders}"
