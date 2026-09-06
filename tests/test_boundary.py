"""Architectural boundary test (AGENTS.md §7): app/core must not import any
LLM or provider module. Walks the source tree and asserts the constraint
syntactically — cheap, fast, and impossible to bypass accidentally."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_PREFIXES = ("app.providers", "app.agents", "google.genai", "google.adk")
CORE_DIR = Path(__file__).resolve().parent.parent / "app" / "core"


def _imports_of(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append(node.module)
    return out


def test_core_imports_no_llm_or_providers():
    violations: list[str] = []
    for path in CORE_DIR.glob("*.py"):
        for module in _imports_of(path):
            if any(module.startswith(p) for p in FORBIDDEN_PREFIXES):
                violations.append(f"{path.name} imports {module}")
    assert violations == [], f"boundary violated: {violations}"
