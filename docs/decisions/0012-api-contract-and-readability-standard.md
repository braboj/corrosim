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

**Enforcement, staged so CI never half-breaks.** The sweep ran module by
module (types + docstrings + readability in one pass per file, since both
standards rewrite the same functions), and enforcement grew with it via a
`CONTRACTED` allowlist in `tests/test_docstrings.py`. Once every module was in,
the final PR flipped the **global** gate and retired the allowlist. The end
state:

- **ruff** (whole package): `line-length = 80`, `extend-select = ["D417"]`
  (documented args complete), `select += ["C90"]` with
  `[tool.ruff.lint.mccabe] max-complexity = 15`. `D205` stays relaxed. The
  `report.py` embedded-CSS `E501` per-file-ignore stays; `tests/**` are exempt
  from `E501`/`C901`/`D` (not public API). One linear section-by-section report
  builder carries a documented `# noqa: C901` (high cyclomatic, low cognitive).
- **`tests/test_docstrings.py`** (whole package) owns what ruff has no rule
  for: every public def is fully type-annotated (params + return), public defs
  with params carry `Args:` and non-None returns carry `Returns:`, and comments
  neither trail code nor cite ticket/ADR numbers (tool directives exempted).
- **No ruff `ANN`.** #51 is the *public* contract, so annotation completeness
  is enforced by the test (public-only). This keeps private QM helpers that
  take un-stubbed pyscf objects annotation-free rather than forcing
  `Any`/`attr-defined` friction — a deliberate narrowing of the `mypy --strict`
  path ADR 0007 deferred.
- The `test_docstrings.py` package path was also corrected en route — it
  pointed at the pre-`src/` `corrosim/` and had silently become a no-op since
  the layout move.

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

- The full contract + readability standard is the corrosim baseline, enforced
  package-wide by ruff (line-length 80 + D417 + C90) and `test_docstrings.py`
  (public annotations + Args/Returns + comment rules). CLAUDE.md §2.2 states it;
  new/edited code is held to it by CI.
- ADR 0007's `D205` relaxation and scoped coverage stand; its `mypy --strict`
  deferral is partially advanced — the "public defs annotated" subset is
  enforced now (via `test_docstrings.py`), short of full `--strict`.
- The rollout landed as eight PRs (foundation + one per subsystem/batch + the
  gate flip), each behaviour-preserving and green; the numeric mc/md modules
  were verified bit-identical by a full-precision golden and the report/
  narrative by a string-value golden, so no results/report artifacts changed.
