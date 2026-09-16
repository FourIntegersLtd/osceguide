"""Every domain rule has a caller, or is listed here as debt.

This is the guard whose absence cost the most. 20 of 101 domain rules were
written, unit-tested, documented in a slice README, and never called from any
service — including `should_freeze`, so no attempt could run, and
`trial_available`, so no free trial could be granted. Every other guard checks
*structure*: file shape, layering, no SQL outside a repository. None checked
whether the code runs, and a green suite with a high test count read as
working software.

A rule with no caller is worse than no rule. It passes its tests, it appears
in the README, its error is advertised in the OpenAPI document — and the
behaviour it describes does not happen.

`KNOWN_UNWIRED` is a debt list, not an exemption list. It may only shrink:
`test_the_debt_list_has_no_stale_entries` fails when something on it becomes
reachable, which forces the entry to be deleted rather than left to rot.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.guards._scan import APP_ROOT, FEATURES_ROOT, python_files

# Rules with no production caller, and why. Each is a real gap with a phase
# that closes it — see docs/STATUS.md. Removing the last entry deletes this
# list, not the guard.
KNOWN_UNWIRED: dict[tuple[str, str], str] = {
    ("attempts", "is_terminal"): "helper; status checks compare the enum directly",
    ("attempts", "required_reference"): "the CHECK constraint enforces this; the rule mirrors it",
    ("community", "apply_like"): "likes are counted in SQL, not recomputed in Python",
    ("community", "apply_unlike"): "as apply_like",
    ("growth", "format_ref_id"): "referral codes are generated in the service; unify or delete",
    ("identity", "may_call"): "rate limiting is not built yet",
    ("notifications", "is_due"): "the SKIP LOCKED claim query does the due check in SQL",
    ("reviews", "combine_rag"): "Phase D: the server should own RAG aggregation, not the browser",
    ("roster", "ensure_rosterable"): "Phase D",
    ("roster", "memberships_from_labels"): "import helper for the migration; move to app/migration",
    (
        "sittings",
        "ensure_editable",
    ): "asserts C3; no structural-edit route to assert it at yet (edit_block reports it)",
    ("stations", "ensure_bindable"): "Phase D: T3 is not enforced",
    ("stations", "ensure_brief_editable"): "Phase D: T5, no brief-edit route",
    ("stations", "ensure_deletable"): "Phase D: no delete-version route",
    ("stations", "ensure_usable_in_circuit"): "Phase D: T4, a circuit may reference a draft station",
    ("tenancy", "pick_default_workspace"): "Phase C: login uses memberships[0] instead",
}


def _public_functions(tree: ast.Module) -> list[str]:
    return [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith("_")
    ]


def _used_names(node: ast.AST) -> set[str]:
    """Every name this code uses, called or merely referred to.

    References count, not just calls: a predicate handed to
    `bind_org_access_policy(org_permits_access)` is wired even though no call
    site names it. Counting calls alone reported that rule as dead the moment
    it was fixed, which would have taught people to ignore this guard.

    An import that goes nowhere would also count, but ruff's F401 catches those
    first.
    """
    found: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = getattr(child.func, "attr", None) or getattr(child.func, "id", None)
            if name:
                found.add(name)
        elif isinstance(child, ast.Attribute):
            found.add(child.attr)
        elif isinstance(child, ast.Name):
            found.add(child.id)
        elif isinstance(child, ast.alias):
            found.add(child.asname or child.name.rsplit(".", 1)[-1])
    return found


def unreachable_rules(features_root: Path | None = None) -> dict[tuple[str, str], None]:
    """Domain rules not reachable from any non-domain production module.

    Reachability, not a bare grep: a rule called only by another rule in the
    same `domain.py` is reachable exactly when *that* one is. Counting direct
    call sites alone reports helpers as dead and misses the real orphans.
    """
    root = features_root or FEATURES_ROOT
    defined: dict[tuple[str, str], None] = {}
    edges: dict[tuple[str, str], set[tuple[str, str]]] = {}

    for path in sorted(root.glob("*/domain.py")):
        slice_name = path.parent.name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for name in _public_functions(tree):
            defined[(slice_name, name)] = None
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                edges[(slice_name, node.name)] = {
                    (slice_name, called)
                    for called in _used_names(node)
                    if (slice_name, called) in defined or called in _public_functions(tree)
                }

    entry: set[tuple[str, str]] = set()
    for path in python_files(root if features_root else APP_ROOT):
        if path.name == "domain.py":
            continue
        slice_name = path.parent.name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for called in _used_names(tree):
            if (slice_name, called) in defined:
                entry.add((slice_name, called))

    seen: set[tuple[str, str]] = set()
    stack = list(entry)
    while stack:
        key = stack.pop()
        if key in seen:
            continue
        seen.add(key)
        stack.extend(edges.get(key, set()))

    return {key: None for key in defined if key not in seen}


def test_every_domain_rule_is_reachable_from_production() -> None:
    orphans = sorted(set(unreachable_rules()) - set(KNOWN_UNWIRED))
    assert not orphans, (
        f"These domain rules have no production caller: {orphans}. A rule that never "
        "runs still passes its tests and still appears in the README, which is how "
        "an attempt came to be unrunnable. Wire it, or delete it."
    )


def test_the_debt_list_has_no_stale_entries() -> None:
    """The ratchet: fixing a rule forces its entry off the list."""
    fixed = sorted(set(KNOWN_UNWIRED) - set(unreachable_rules()))
    assert not fixed, (
        f"These are wired now: {fixed}. Remove them from KNOWN_UNWIRED so the list "
        "keeps meaning what it says."
    )


def test_the_guard_catches_a_rule_nobody_calls(tmp_path: Path) -> None:
    """The planted violation, run through the guard itself.

    `test_org_scoped_repositories` walked `ast.ClassDef` in a codebase whose
    repositories are all module-level functions: 21 files scanned, nothing
    inspected, green throughout. Its meta-test passed because it built a class
    to check — a shape that exists nowhere here. So this one plants its
    violation in a tree shaped like `app/features/<slice>/`, and runs the real
    function over it.
    """
    slice_dir = tmp_path / "billing"
    slice_dir.mkdir()
    (slice_dir / "domain.py").write_text(
        "def wired():\n    return 1\n\n\n"
        "def helper():\n    return 2\n\n\n"
        "def reached_via_helper():\n    return helper()\n\n\n"
        "def orphan():\n    return 3\n",
        encoding="utf-8",
    )
    (slice_dir / "service.py").write_text(
        "from app.features.billing import domain\n\n\n"
        "def run():\n    return domain.wired() + domain.reached_via_helper()\n",
        encoding="utf-8",
    )

    found = set(unreachable_rules(tmp_path))

    assert ("billing", "orphan") in found, "the guard missed a rule nobody calls"
    assert ("billing", "wired") not in found
    # The distinction a bare grep gets wrong: `helper` has no direct call site
    # outside domain.py, but it is reached through a rule that does.
    assert ("billing", "helper") not in found
