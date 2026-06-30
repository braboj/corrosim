"""Public-API docstring coverage (issue #6).

Every public, module-top-level function/class — and the public methods of public
classes — must carry a docstring. Nested local helpers and underscore/dunder
names are exempt. This pins the acceptance criterion so the coverage can't
silently regress.
"""
from __future__ import annotations

import ast
import pathlib

PKG = pathlib.Path(__file__).resolve().parent.parent / "corrosim"


def _missing_docstrings() -> list[str]:
    missing: list[str] = []
    for f in sorted(PKG.rglob("*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in tree.body:                       # module top level only
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if node.name.startswith("_"):
                continue
            if ast.get_docstring(node) is None:
                missing.append(f"{f.name}:{node.lineno} {node.name}")
            if isinstance(node, ast.ClassDef):       # + public methods of public classes
                for m in node.body:
                    if (isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and not m.name.startswith("_")
                            and ast.get_docstring(m) is None):
                        missing.append(f"{f.name}:{m.lineno} {node.name}.{m.name}")
    return missing


def test_public_api_symbols_have_docstrings():
    missing = _missing_docstrings()
    assert not missing, "Public symbols missing docstrings:\n  " + "\n  ".join(missing)
