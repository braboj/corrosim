# ADR 0012 — Full public API contract + readability standard

- Status: Accepted
- Date: 2026-07-04
- Amends: ADR 0007 (scoped quality gates)

## Context

ADR 0007 wired the `python-lib` quality gates but recorded two deferrals in the
spirit of "adopt now, tighten later": `mypy --strict` was postponed and the
ruff `D205` docstring rule relaxed, alongside a deferred `ruff format`. In
practice corrosim also shipped a **relaxed API surface**: `mypy` runs
non-strict (untyped public defs allowed), most public docstrings are
one-liners without `Args:`/`Returns:`/`Raises:`, and the line length is 100.

A 2026-07-04 review measured the gap: of 117 public functions/methods, 54 were
not fully type-annotated and 60 had a single-line docstring; 660 lines exceed
80 columns, 92 comments trail code on the right, 10 comments cite a ticket/ADR
number, and 19 functions exceed 40 lines. `templates/stack/python-lib.md`
makes the full contract a MUST (PEP 484 "all public members annotated" + PEP
257 Google "every public symbol has a docstring"), so these are deviations to
close, not preferences.

## Decision

Adopt two codebase-wide standards and enforce them (issues #51, #52).

**Full public API contract (#51).** Every public (non-`_`) function/method
carries complete type hints (all params + return; prefer `collections.abc`
types; no `Any` in the public API except a justified, `# noqa: ANN401`-marked
case such as a JSON payload) **and** a Google docstring with explicit `Args:`,
`Returns:`, and `Raises:` sections where applicable. The unit-in-name/-docstring
contract (CLAUDE.md §2.2) and the `D205` long-summary relaxation are kept.

**Readability standard (#52).** (1) Organize each function into logical blocks,
each introduced by a short comment on the line *above* it; (2) no right-side /
trailing comments (tool directives like `# noqa` / `# nosec` excepted); (3) max
line length **80** (down from 100); (4) split functions driven by complexity,
not raw line count; (5) comments are self-sufficient — no ticket/PR/ADR
*numbers* in comments (scientific source names — Koopmans, Lukovits ΔN, Rappé
1992 — stay); (6) one parameter per line for wrapped signatures, with a
trailing comma.

**Enforcement, staged so CI never half-breaks.** The sweep runs module by
module (types + docstrings + readability in one pass per file, since both
standards rewrite the same functions). Enforcement grows with it:

- `tests/test_docstrings.py` carries a `CONTRACTED` allowlist of swept modules
  and asserts, over them, full annotations, `Args:`/`Returns:` completeness,
  ≤80 columns, no trailing comments, and no ticket-number comments. The list
  grows one entry per sweep PR. (This file's package path was also corrected —
  it pointed at the pre-`src/` `corrosim/` and had silently become a no-op.)
- Once every module is in the allowlist, a final PR flips the global ruff gate
  — `line-length = 80`, `select += ["ANN", "C90"]`, `extend-select = ["D417"]`,
  `[tool.ruff.lint.mccabe] max-complexity` — and the allowlist checks retire in
  favour of it. `D205` stays relaxed; `ANN401` stays on with justified `noqa`s.

## Alternatives considered

- **One big-bang sweep PR** — rejected: a 700+-violation diff across ~30 files
  is unreviewable and risks silently changing numeric code (mc/md trajectories).
- **Flip the global gate first, exempt every dirty file via `per-file-ignores`**
  — rejected: with no module yet clean, the exempt list would name nearly every
  file, and the gate would enforce nothing until the last PR anyway. The
  allowlist test gives real, growing enforcement without that noise.
- **Keep the relaxed one-liner style** — rejected: it is the documented
  `python-lib.md` MUST that ADR 0007 left open, and the review showed concrete
  readability debt.

## Consequences

- The full contract + readability standard is the corrosim baseline; CLAUDE.md
  §2.2 states it, and new/edited code is held to it immediately (ahead of the
  sweep reaching its module).
- Enforcement is incremental and always-green: the `CONTRACTED` allowlist is the
  live contract until the global ruff gate replaces it.
- ADR 0007's `D205` relaxation and scoped coverage stand; its `mypy --strict`
  deferral is partially advanced — the "public defs annotated" subset is
  enforced now (via the allowlist, then ruff `ANN`), short of full `--strict`.
- The staged rollout is tracked by the #51/#52 checklists; the first increment
  (this ADR + `presets.py` + `runs/_cli.py`) proves the enforcement pipeline.
