# ADR 0033 — Editor type-checking defers to mypy

- Status: Accepted
- Date: 2026-07-18
- Relates to: ADR 0007 (mypy non-strict as the chosen type bar); the `[tool.mypy]`
  overrides that treat the scientific stack as untyped

## Context

mypy (non-strict) is corrosim's type gate, deliberately configured to treat the
scientific stack as untyped (`ignore_missing_imports`, `follow_imports = "skip"`
for rdkit/numpy/pandas/pyscf/tblite/…) so it catches real type errors without
drowning in stub friction. Pylance — the pyright-based language server most
contributors run in VS Code — had no matching configuration, so it fell back to
its default "standard" mode and flagged ~85 diagnostics across `src/`: ~79 from
pandas/numpy inline types being stricter than the runtime needs, and 6 from
imports that do not resolve in the venv (the Docker-only QM engines pyscf/tblite,
and rdkit's stub-less `Chem.Draw`). None are real defects — mypy, ruff, and the
full test suite are clean.

The failure mode is a split brain: the editor contradicts CI, and a contributor
cannot tell a real problem from stub noise. Running two type-checkers at two
strictness levels is the root cause.

## Decision

**The editor's type-checker defers to mypy; mypy is the single type authority in
both the editor and CI.**

- `pyproject.toml [tool.pyright]`: `typeCheckingMode = "off"` (pyright stops its
  own type evaluation) and `reportMissingImports = "none"` (the known-absent
  imports mypy already ignores). Pylance's IntelliSense — completion, hover,
  go-to-definition, rename — is untouched; only its diagnostics layer defers.
- mypy is surfaced live in the editor through the Mypy Type Checker extension,
  wired in a tracked `.vscode/settings.json` (`fromEnvironment` mypy, workspace
  scope, daemon) and recommended via `.vscode/extensions.json`, so the Problems
  panel shows exactly the CI gate.
- Those two `.vscode/` files are shared via a gitignore allowlist (`.vscode/*`
  plus `!settings.json` and `!extensions.json`), the same selective-tracking
  idiom already used for `.claude/settings.json`; all other per-user editor
  state stays ignored.

## Consequences

- The editor Problems panel matches CI: pyright reports 0 errors, and mypy is the
  only type feedback in both places.
- A fresh checkout gets the setup with no manual configuration; VS Code prompts
  to install the recommended extension on first open. Contributors who decline
  the extension still get the quiet editor (the pyright config alone clears the
  85 diagnostics).
- Trade-off: with pyright's type evaluation off, a genuine type error surfaces
  only through mypy (the extension, a terminal run, or CI), not through Pylance.
  Acceptable because mypy is the gate; the daemon + workspace scope keep the
  editor feedback near-live.

## Upstream

The transferable rule is domain-free tooling engineering: *when a project runs a
type-checker as a CI gate at a chosen strictness, the editor's bundled
type-checker should defer to that gate rather than run a second, stricter
analysis that contradicts CI; surface the gate's own diagnostics live in the
editor instead.* Plus the sub-pattern *share only the CI-mirroring editor-config
files via a gitignore allowlist, keeping per-user editor state ignored.* Filed
upstream against `base/workflow/quality-gates.md` (and `base/core/git.md` for the
allowlist) as `solid-ai-templates#826`.
