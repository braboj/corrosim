# ADR 0013 — Cognitive-complexity ratchet (complexipy)

- Status: Accepted
- Date: 2026-07-04
- Extends: ADR 0012 (API contract and readability standard)

## Context

ADR 0012 gates cyclomatic complexity (ruff `C90`, threshold 15). McCabe counts
branch points, not structure: it flags flat, linear section-emitters while
passing deeply nested logic — the opposite of what the readability standard
("split by complexity") is after. Cognitive complexity (the SonarQube metric)
counts nesting depth and control-flow interruptions instead, which tracks how
hard a function is to *read*.

A 2026-07-04 measurement with complexipy 6.0 confirmed the two metrics
genuinely disagree on this codebase. Nine functions exceed cognitive 15, led
by `run_dft.analyse_matrix` at 47 — which the `C901` gate passes cleanly.
Conversely, `report_docx.build_docx_report`, excused from `C901` (16) as a
"linear section emitter, high cyclomatic / low cognitive", actually measures
cognitive 26 — the measurement corrects that ADR 0012 assumption.

ruff has no cognitive-complexity rule (a long-open upstream request), so
adding the metric means adding a tool.

## Decision

Adopt **complexipy** as a quality gate in **snapshot-ratchet** mode:

- `[tool.complexipy]` in `pyproject.toml` scopes the scan to `src/corrosim`
  with `max-complexity-allowed = 15` (SonarQube's Python default; matches the
  `C901` threshold). Tests stay out of scope, mirroring their `C901` exemption.
- The committed `complexipy-snapshot.json` is the watermark: it records every
  currently-over-threshold function (nine at adoption). A run fails only when
  an over-threshold function is **new** or has **increased** relative to the
  snapshot — pre-existing offenders are frozen at their recorded values, not
  exempted. A successful run rewrites the snapshot, so the watermark tightens
  as offenders shrink; the refreshed snapshot is committed in the same change
  (the standing regenerate-dependent-artifacts rule).
- CI runs `complexipy --color no` in the lint job, pinned `complexipy==6.0.*`
  because the snapshot file format is version-sensitive (older snapshots are
  rejected across upgrades). `complexipy` also joins the dev extras and the
  pre-PR local check list (CLAUDE.md §5.2).

## Alternatives considered

- **Plain threshold gate (fail on all nine now)** — rejected: it would demand
  an up-front refactor of the three largest drivers before the gate could
  turn on. The ratchet blocks regressions immediately and lets epic #70 burn
  the backlog down incrementally.
- **Git-diff ratchet (`--diff main --ratchet`)** — rejected: it needs a base
  ref (fetch-depth games in CI), does nothing useful on a clean local tree,
  and is ambiguous on push-to-`main`. The snapshot behaves identically
  everywhere and the baseline is reviewable in the repo.
- **`flake8-cognitive-complexity`** — rejected: drags a second linter
  framework in alongside ruff for one rule.
- **SonarQube / SonarCloud** — rejected for now: a hosted platform for one
  missing metric; its other value (duplication detection, dashboards) is a
  separate decision if wanted later.

## Consequences

- New and edited code is effectively capped at cognitive complexity 15; the
  gate cannot regress silently because any increase of a frozen offender
  fails CI.
- The snapshot doubles as a measured priority list for the epic #70
  per-module refactors: `analyse_matrix` 47, `make_report.main` 38,
  `read_input_csv` 31, `build_docx_report` 26, `run_md` 24,
  `make_figures.main` 18, `render_orbital` 17, `_scientific_basis` 16,
  `run_dft.main` 16.
- The `build_docx_report` `# noqa: C901` justification is weakened by the
  cognitive-26 measurement — revisit splitting it when the function next
  changes.
- One more pinned tool in the lint job; upgrading complexipy across a minor
  requires recreating the snapshot (`complexipy --snapshot-create`) in the
  same change.
