"""Every seam the composition root is supposed to tie is tied.

A slice that sits below another cannot import it, so the two meet at a seam:
one side declares `bind_x(...)` and `main.create_app` calls it. The failure
mode is silence — nobody calls `bind_x`, the code that needs it raises at
runtime, and only on the route that happens to use it. `identity.register`
grew one of these in the same week `sittings` did; a missing call would have
been found by whoever registered an account in production.

Two checks, because each catches what the other cannot: that `main.py` calls
every `bind_*` that exists, and that a built app actually has each one filled
in. The first is structural and catches a new seam nobody wired; the second
catches a call that was written but is never reached.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.guards._scan import APP_ROOT, parse, python_files, rel

MAIN = APP_ROOT / "main.py"


def declared_seams(root: Path = APP_ROOT) -> dict[str, str]:
    """Every `bind_*` function under `root`, and the file that declares it."""
    found: dict[str, str] = {}
    for path in python_files(root):
        for node in ast.walk(parse(path)):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("bind_"):
                found[node.name] = path.name if root is not APP_ROOT else rel(path)
    return found


def unbound(root: Path = APP_ROOT, main: Path = MAIN) -> list[str]:
    called = calls_in(main)
    return sorted(
        f"{name} (declared in {where})" for name, where in declared_seams(root).items() if name not in called
    )


def calls_in(path: Path) -> set[str]:
    return {
        node.func.id
        for node in ast.walk(parse(path))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def test_there_are_seams_to_check() -> None:
    assert declared_seams(), "no bind_* seams found; the guard would pass vacuously"


def test_the_composition_root_binds_every_seam() -> None:
    missing = unbound()
    assert not missing, (
        f"seams declared but never bound in app/main.py: {missing}. "
        "A seam nobody ties raises at runtime, on whichever route reaches it first."
    )


def test_the_guard_would_catch_a_seam_nobody_tied(tmp_path: Path) -> None:
    """The planted violation: two seams, one of them forgotten."""
    (tmp_path / "slice.py").write_text(
        "def bind_tied(x): ...\ndef bind_forgotten(x): ...\n", encoding="utf-8"
    )
    main = tmp_path / "main.py"
    main.write_text("def create_app():\n    bind_tied(1)\n", encoding="utf-8")

    assert unbound(tmp_path, main) == ["bind_forgotten (declared in slice.py)"]


def test_a_built_app_has_every_seam_filled_in() -> None:
    """The structural check above passes if the call is written but unreachable."""
    from app.core import audience, auth, memberships, role_policy, tenancy
    from app.features.growth import service as growth
    from app.features.identity import service as identity
    from app.features.identity import service_sessions
    from app.features.sittings import service_circuit
    from app.main import create_app

    create_app()

    filled = {
        "password gate": auth._password_gate,
        "org lookup": [tenancy._org_lookup] if tenancy._org_lookup else [],
        "org access policy": role_policy._access_policy,
        "role policies": list(role_policy._policies),
        "viewer audiences": audience._lookup,
        "membership lookup": [memberships._lookup] if memberships._lookup else [],
        "default workspace": service_sessions._default_workspace,
        "registration hook": identity._on_registered,
        "purchase counter": growth._purchase_counter,
        "feedback lookup": service_circuit._slot_has_review,
    }
    empty = sorted(name for name, bound in filled.items() if not bound)
    assert not empty, f"seams that create_app left empty: {empty}"
