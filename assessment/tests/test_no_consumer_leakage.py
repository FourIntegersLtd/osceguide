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
APP_TYPE_SPELLINGS = ("app_type", "apptype")


def python_files() -> list[Path]:
    """Every source file in the package, excluding build artefacts.

    ``build/`` is a gitignored copy setuptools leaves behind; scanning it makes
    the guard report on code that was deleted from the source tree.
    """
    return sorted(
        path
        for path in PACKAGE_ROOT.rglob("*.py")
        if "build" not in path.relative_to(PACKAGE_ROOT).parts
    )


def engine_files() -> list[Path]:
    """Every module in the package. There is no longer a quarantine to exclude.

    ``compat/`` held a legacy product-string translation and was the one place
    allowed to speak that vocabulary. It has been deleted: nothing resolves an
    exam by string any more, so the exception it needed goes with it.
    """
    return python_files()


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
        f"{_module_id(path)} uses {offenders}. An exam is resolved by the caller; "
        "the engine takes a framework id and never a product string."
    )


def test_the_migration_shim_is_gone() -> None:
    """It named four products, so it could only ever have described four exams."""
    with pytest.raises(ModuleNotFoundError):
        import osce_assessment.compat  # noqa: F401


def test_the_engine_ships_no_frameworks_of_its_own() -> None:
    """A rubric is authored and stored; the package holds machinery, not content."""
    with pytest.raises(ModuleNotFoundError):
        import osce_assessment.catalog  # noqa: F401


@pytest.mark.parametrize("path", python_files(), ids=lambda p: str(p.name))
def test_engine_imports_no_vendor_sdks(path: Path) -> None:
    offenders = sorted(imported_roots(path) & BANNED_IMPORT_ROOTS)
    assert not offenders, (
        f"{path.relative_to(PACKAGE_ROOT)} imports {offenders}. "
        "The engine depends on pydantic only; clients and adapters are injected."
    )


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
