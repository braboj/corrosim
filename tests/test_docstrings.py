"""Public-API docstring + contract enforcement (issues #6, #51, #52).

Two layers:

* :func:`test_public_api_symbols_have_docstrings` — every public, top-level
  function/class and the public methods of public classes must carry a
  docstring, across the whole package. Pins the #6 acceptance criterion so it
  can't silently regress.
* The ``_CONTRACTED`` allowlist — modules already swept to the full standard
  (issues #51 full API contract + #52 readability) are held to it here:
  complete type hints, Google ``Args:``/``Returns:`` sections, 80-column
  lines, no trailing/right-side comments, and no ticket/ADR numbers in
  comments. The list grows one module per sweep PR; the global ruff gate takes
  over once every module is in.
"""
from __future__ import annotations

import ast
import io
import pathlib
import re
import tokenize

PKG = pathlib.Path(__file__).resolve().parent.parent / "src" / "corrosim"

# Modules swept to the full #51/#52 contract; enforced by the contract tests
# below. Grows per sweep PR until it covers the package, then the ruff gate
# (line-length 80 + ANN + D417 + C901) replaces this allowlist.
CONTRACTED = [
    "presets.py",
    "runs/_cli.py",
    "adsorption/__init__.py",
    "adsorption/surface.py",
    "adsorption/adsorption.py",
    "adsorption/mc.py",
    "adsorption/md.py",
    "qm/__init__.py",
    "qm/descriptors.py",
    "qm/engines.py",
    "qm/fukui.py",
    "qm/pka.py",
    "qm/speciation.py",
]

MAX_LINE = 80
# Ticket/PR/ADR/issue references that rot — banned from comments (rule 5).
TICKET_RE = re.compile(r"#\d+|\bADR[-\s]?\d+|\bissue[-\s]?#?\d+|\bPR[-\s]?#?\d+", re.IGNORECASE)
# Tool directives are machine-readable and must sit inline, so they are exempt
# from the human-comment rules (no trailing, no ticket numbers).
DIRECTIVE_RE = re.compile(r"^#\s*(noqa|type:|pragma:|nosec)")


def _contracted_files() -> list[pathlib.Path]:
    return [PKG / rel for rel in CONTRACTED]


def _public_defs(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Public top-level functions + public methods of public classes."""
    defs: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                defs.append(node)
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            for m in node.body:
                if (isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and not m.name.startswith("_")):
                    defs.append(m)
    return defs


def _missing_docstrings() -> list[str]:
    missing: list[str] = []
    for f in sorted(PKG.rglob("*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if node.name.startswith("_"):
                continue
            if ast.get_docstring(node) is None:
                missing.append(f"{f.name}:{node.lineno} {node.name}")
            if isinstance(node, ast.ClassDef):
                for m in node.body:
                    if (isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and not m.name.startswith("_")
                            and ast.get_docstring(m) is None):
                        missing.append(f"{f.name}:{m.lineno} {node.name}.{m.name}")
    return missing


def test_public_api_symbols_have_docstrings():
    missing = _missing_docstrings()
    assert not missing, "Public symbols missing docstrings:\n  " + "\n  ".join(missing)


def test_contracted_modules_are_fully_annotated():
    """Every public def in a contracted module has all params + a return typed."""
    bad: list[str] = []
    for f in _contracted_files():
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for fn in _public_defs(tree):
            a = fn.args
            params = [*a.posonlyargs, *a.args, *a.kwonlyargs]
            for p in params:
                if p.arg in ("self", "cls"):
                    continue
                if p.annotation is None:
                    bad.append(f"{f.name}:{fn.lineno} {fn.name}({p.arg}) untyped")
            if a.vararg and a.vararg.annotation is None:
                bad.append(f"{f.name}:{fn.lineno} {fn.name}(*{a.vararg.arg}) untyped")
            if a.kwarg and a.kwarg.annotation is None:
                bad.append(f"{f.name}:{fn.lineno} {fn.name}(**{a.kwarg.arg}) untyped")
            if fn.returns is None:
                bad.append(f"{f.name}:{fn.lineno} {fn.name} missing return type")
    assert not bad, "Incomplete type hints:\n  " + "\n  ".join(bad)


def test_contracted_modules_document_args_and_returns():
    """Public defs with params carry ``Args:``; non-None returns carry ``Returns:``."""
    bad: list[str] = []
    for f in _contracted_files():
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for fn in _public_defs(tree):
            doc = ast.get_docstring(fn) or ""
            real = [p.arg for p in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs)
                    if p.arg not in ("self", "cls")]
            if real and "Args:" not in doc:
                bad.append(f"{f.name}:{fn.lineno} {fn.name} params but no Args:")
            returns_value = not (fn.returns is None
                                 or (isinstance(fn.returns, ast.Constant)
                                     and fn.returns.value is None))
            if returns_value and "Returns:" not in doc:
                bad.append(f"{f.name}:{fn.lineno} {fn.name} returns but no Returns:")
    assert not bad, "Incomplete Google docstrings:\n  " + "\n  ".join(bad)


def test_contracted_modules_are_clean_comments_and_width():
    """Contracted modules: <=80 cols, no trailing comments, no ticket-number refs."""
    bad: list[str] = []
    for f in _contracted_files():
        src = f.read_text(encoding="utf-8")
        for i, line in enumerate(src.splitlines(), 1):
            if len(line) > MAX_LINE:
                bad.append(f"{f.name}:{i} line {len(line)} > {MAX_LINE}")
        tokens = tokenize.generate_tokens(io.StringIO(src).readline)
        code_rows: set[int] = set()
        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                if DIRECTIVE_RE.match(tok.string):
                    continue
                if TICKET_RE.search(tok.string):
                    bad.append(f"{f.name}:{tok.start[0]} ticket ref in comment")
                if tok.start[0] in code_rows:
                    bad.append(f"{f.name}:{tok.start[0]} trailing comment")
            elif tok.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                                  tokenize.DEDENT, tokenize.ENCODING):
                code_rows.add(tok.start[0])
    assert not bad, "Readability violations:\n  " + "\n  ".join(bad)
