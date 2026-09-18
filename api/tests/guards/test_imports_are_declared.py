"""Everything the app imports must be a dependency it declares.

The hole this closes: `voice/adapter.py` imports the LiveKit SDK inside each
call and turns an ImportError into `VoiceUnavailable`, so the SDK went missing
from `pyproject.toml` for the life of the project without one test failing.
No deployment could mint a room token or dispatch a patient; the API simply
reported that voice was unavailable.

A lazy import is still a dependency. This walks every import in `app/` —
module level or not — and insists the distribution behind it is declared.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from importlib.metadata import packages_distributions

from tests.guards._scan import PROJECT_ROOT, python_files, rel

# Imported from production code but deliberately undeclared, each with the
# open question that tracks it. Anything else here is a bug.
KNOWN_UNDECLARED = {
    # E-1: the engine is installed from a sibling checkout by `make engine-dev`
    # until `engine-v0.7.0` is tagged. The commented line is in `pyproject.toml`.
    "osce_assessment",
}


def _declared_distributions() -> set[str]:
    data = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    names: set[str] = set()
    specs = list(data["project"]["dependencies"])
    for group in data["tool"]["poetry"].get("group", {}).values():
        specs.extend(group["dependencies"])
    for spec in specs:
        name = spec.split("(")[0].split("[")[0].split(">")[0].split("=")[0].split("@")[0]
        names.add(name.strip().lower().replace("_", "-"))
    return names


def _imported_roots() -> dict[str, str]:
    """Top-level module name → the first file that imports it."""
    found: dict[str, str] = {}
    for path in python_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                roots = [node.module.split(".")[0]] if node.level == 0 and node.module else []
            else:
                continue
            for root in roots:
                found.setdefault(root, rel(path))
    return found


def test_every_third_party_import_is_a_declared_dependency() -> None:
    declared = _declared_distributions()
    provided = packages_distributions()

    undeclared: list[str] = []
    for root, first_use in sorted(_imported_roots().items()):
        if root in sys.stdlib_module_names or root in {"app", "tests"} or root in KNOWN_UNDECLARED:
            continue
        dists = {name.lower().replace("_", "-") for name in provided.get(root, [])}
        if not dists:
            undeclared.append(f"{root} (imported by {first_use}) is not installed at all")
        elif not dists & declared:
            undeclared.append(f"{root} (imported by {first_use}) comes from {sorted(dists)}, none declared")

    assert not undeclared, (
        "These imports are not declared in pyproject.toml: "
        + "; ".join(undeclared)
        + ". A lazy import inside a function is still a dependency — and one that "
        "degrades to a 503 instead of an ImportError will never fail a test."
    )
