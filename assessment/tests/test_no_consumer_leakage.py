"""The guard that keeps the engine consumer-agnostic.

The engine must never learn who is calling it. Consumer identity lives in the
backends: routing picks a worker, consumer code picks an ``EvaluationPolicy``,
consumer code persists results. If any of those identifiers appear in
``osce_assessment`` code, a B2C/B2B/employer branch has started to grow and
this test fails.

Scanning is deliberately limited to code — identifiers, attributes, keywords
and runtime string literals — because prose that explains what the engine
replaces ("LiveKit today, anything later") is useful and carries no coupling.
Actual dependence on a vendor SDK is caught by the import check below.

The legacy ``app_type`` vocabulary is confined to ``compat/``, which is named
for being temporary and which the engine proper must not import. Everywhere
else the ban is absolute. ``attempt_context`` is allowed by design because it
is opaque pass-through.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import osce_assessment

PACKAGE_ROOT = Path(osce_assessment.__file__).parent

# Consumer identity that must never appear in engine code.
BANNED_IDENTIFIERS = (
    "org_slug",
    "orgslug",
    "tenant_slug",
    "tenantslug",
    "user_email",
    "useremail",
    "mock_id",
    "mockid",
    "slot_id",
    "slotid",
    "circuit_id",
    "circuitid",
    "trainee_id",
    "traineeid",
    "product_surface",
    "productsurface",
    "b2c",
    "b2b",
    "bmj",
    "employer",
    "recruitment",
    "firestore",
    "supabase",
    "livekit",
)

# Vendor SDKs the engine must not depend on; clients and adapters are injected.
BANNED_IMPORT_ROOTS = frozenset(
    {
        "openai",
        "anthropic",
        "instructor",
        "livekit",
        "google",
        "firebase_admin",
        "supabase",
        "redis",
        "flask",
        "fastapi",
        "requests",
        "httpx",
        "aiohttp",
    }
)

# Legacy product vocabulary is quarantined in this package, nowhere else.
COMPAT_PACKAGE = "compat"

APP_TYPE_SPELLINGS = ("app_type", "apptype")


def python_files() -> list[Path]:
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def engine_files() -> list[Path]:
    """Engine modules: everything outside the migration-shim package."""
    return [
        path
        for path in python_files()
        if COMPAT_PACKAGE not in path.relative_to(PACKAGE_ROOT).parts
    ]


def compat_files() -> list[Path]:
    return [path for path in python_files() if path not in set(engine_files())]


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_ROOT))


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """Constant nodes that are docstrings, so prose is excluded from the scan."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def code_tokens(path: Path) -> set[str]:
    """Every identifier and runtime string literal in a module, lowercased."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docstrings = _docstring_nodes(tree)
    tokens: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            tokens.add(node.id)
        elif isinstance(node, ast.Attribute):
            tokens.add(node.attr)
        elif isinstance(node, ast.arg):
            tokens.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            tokens.add(node.name)
        elif isinstance(node, ast.keyword) and node.arg:
            tokens.add(node.arg)
        elif isinstance(node, ast.alias):
            tokens.add(node.name)
            if node.asname:
                tokens.add(node.asname)
        elif isinstance(node, ast.ImportFrom) and node.module:
            tokens.add(node.module)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in docstrings:
                tokens.add(node.value)
    return {token.lower() for token in tokens}


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_the_package_has_modules_to_scan() -> None:
    """Guards against the scan silently passing on an empty package."""
    assert len(python_files()) >= 8


@pytest.mark.parametrize("path", python_files(), ids=lambda p: str(p.name))
def test_no_consumer_identity_in_engine_code(path: Path) -> None:
    tokens = code_tokens(path)
    offenders = sorted(
        {
            banned
            for banned in BANNED_IDENTIFIERS
            for token in tokens
            if banned in token
        }
    )
    assert not offenders, (
        f"{path.relative_to(PACKAGE_ROOT)} uses consumer identity {offenders} in code. "
        "Consumer context belongs in the backends; pass correlation ids through "
        "AssessmentAttempt.attempt_context instead."
    )


@pytest.mark.parametrize("path", engine_files(), ids=_module_id)
def test_engine_code_never_speaks_legacy_exam_vocabulary(path: Path) -> None:
    tokens = code_tokens(path)
    offenders = sorted(
        {
            spelling
            for spelling in APP_TYPE_SPELLINGS
            for token in tokens
            if spelling in token
        }
    )
    assert not offenders, (
        f"{_module_id(path)} uses {offenders}. Translate once via "
        "compat.framework_id_for_app_type and pass a framework id onwards."
    )


def test_the_migration_shim_exists_and_is_where_it_claims_to_be() -> None:
    """The quarantine must hold a real translation, not be a stale exception."""
    from osce_assessment.compat import framework_id_for_app_type

    assert callable(framework_id_for_app_type)
    assert compat_files(), "compat/ is empty; remove the exception from this guard"


@pytest.mark.parametrize("path", engine_files(), ids=_module_id)
def test_the_engine_never_imports_the_migration_shim(path: Path) -> None:
    """Shims are for consumers to call, not for the engine to depend on."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    offending: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".")[0] == COMPAT_PACKAGE or f".{COMPAT_PACKAGE}" in module:
                offending.append(module)
            # A relative "from .compat import x" carries the name in aliases.
            if node.level and any(
                alias.name == COMPAT_PACKAGE for alias in node.names
            ):
                offending.append(f"relative {COMPAT_PACKAGE}")
        elif isinstance(node, ast.Import):
            offending.extend(
                alias.name
                for alias in node.names
                if COMPAT_PACKAGE in alias.name.split(".")
            )
    assert not offending, (
        f"{_module_id(path)} imports the migration shim {sorted(set(offending))}. "
        "Consumers call compat; the engine takes a framework id."
    )


@pytest.mark.parametrize("path", python_files(), ids=lambda p: str(p.name))
def test_engine_imports_no_vendor_sdks(path: Path) -> None:
    offenders = sorted(imported_roots(path) & BANNED_IMPORT_ROOTS)
    assert not offenders, (
        f"{path.relative_to(PACKAGE_ROOT)} imports {offenders}. "
        "The engine depends on pydantic only; clients and adapters are injected."
    )


def test_the_quarantine_is_the_only_place_exam_vocabulary_lives() -> None:
    """Belt and braces: compat really does hold what the engine is denied."""
    vocabulary = {
        spelling
        for path in compat_files()
        for token in code_tokens(path)
        for spelling in APP_TYPE_SPELLINGS
        if spelling in token
    }
    assert vocabulary, "compat/ no longer mentions app_type; the shim may be dead"


def test_the_guard_would_catch_a_real_leak(tmp_path: Path) -> None:
    """The scan must actually fail on code that branches on a consumer."""
    leaky = tmp_path / "leaky.py"
    leaky.write_text(
        '"""A docstring mentioning LiveKit and B2B is fine."""\n'
        "def evaluate(attempt):\n"
        '    if attempt.attempt_context["org_slug"] == "bmj":\n'
        "        return 1\n"
        "    return 2\n",
        encoding="utf-8",
    )
    tokens = code_tokens(leaky)
    assert any("org_slug" in token for token in tokens)
    assert any("bmj" in token for token in tokens)
    assert not any("livekit" in token for token in tokens)
