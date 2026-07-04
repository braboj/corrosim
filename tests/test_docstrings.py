"""Public-API contract enforcement (issues #6, #51, #52).

Enforced across the *whole* package, complementing the ruff gate. Ruff owns
line length (80), Google docstring format (D + D417) and complexity (C90);
these tests own what ruff has no rule for:

* every public symbol carries a docstring (#6);
* every public function/method is fully type-annotated — all params + the
  return (#51). This is the public-API contract, enforced here rather than via
  ruff `ANN` so private QM helpers that take un-stubbed pyscf objects need no
  annotations;
* public functions with params carry an ``Args:`` section and non-None returns
  carry a ``Returns:`` section (#51);
* no comment trails code on the same line, and no comment cites a ticket / PR /
  ADR number (#52 rules 2 and 5). Tool directives (``# noqa`` / ``# nosec``)
  are exempt.
"""
from __future__ import annotations

import ast
import io
import pathlib
import re
import tokenize

PKG = pathlib.Path(__file__).resolve().parent.parent / "src" / "corrosim"

# Ticket/PR/ADR/issue references that rot — banned from comments (rule 5).
TICKET_RE = re.compile(r"#\d+|\bADR[-\s]?\d+|\bissue[-\s]?#?\d+|\bPR[-\s]?#?\d+", re.IGNORECASE)
# Tool directives are machine-readable and must sit inline, so they are exempt
# from the human-comment rules (no trailing, no ticket numbers).
DIRECTIVE_RE = re.compile(r"^#\s*(noqa|type:|pragma:|nosec)")


def _modules() -> list[pathlib.Path]:
    return sorted(PKG.rglob("*.py"))


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


def test_public_api_symbols_have_docstrings():
    """Every public top-level symbol + public method carries a docstring."""
    missing: list[str] = []
    for f in _modules():
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
    assert not missing, "Public symbols missing docstrings:\n  " + "\n  ".join(missing)


def test_public_defs_are_fully_annotated():
    """Every public def has all params + a return typed (the #51 contract)."""
    bad: list[str] = []
    for f in _modules():
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


def test_public_defs_document_args_and_returns():
    """Public defs with params carry ``Args:``; non-None returns carry ``Returns:``."""
    bad: list[str] = []
    for f in _modules():
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


def test_comments_are_clean():
    """No trailing comments and no ticket-number comments (rules 2, 5)."""
    bad: list[str] = []
    for f in _modules():
        src = f.read_text(encoding="utf-8")
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
    assert not bad, "Comment-rule violations:\n  " + "\n  ".join(bad)
