# ADR 0006 — Consolidate pipeline outputs into a tracked report/ bundle

- Status: Accepted
- Date: 2026-07-01

## Context

The shipped artifacts were scattered: `report.html` at the repo root, the curated
figure set in `figures/`, and the data tables in `results/`. Worse, `results/`
mixed tracked data (`*.csv`/`*.json`) with gitignored preview PNGs that the stage
drivers (`run_mc`/`run_md`/`run_fukui`) dropped there — a "some files tracked,
others not, unclear why" state. There was no single directory a user could point
at as "the report and everything it is built from".

## Decision

Consolidate the shipped deliverable into one tracked `report/` bundle:

- `report/report.html` — the self-contained report (figures embedded as base64).
- `report/figures/` — the curated PNG set (moved from `./figures/`).
- `report/tables/` — the report's source CSV/JSON copied at build time, plus a
  derived `ranking.csv`.

`make_report`, `make_figures`, and `compare_geometry` default their outputs under
`report/`. The stage drivers (`run_mc`/`run_md`/`run_fukui`) no longer write
preview PNGs; **`results/` now holds only tracked data**, and figures come solely
from `make_figures`. `.gitignore` tracks `report/report.html` (dropping the moot
`results/*.png` rule); `.pre-commit` excludes the machine-written `report/` from
the whitespace hooks.

## Alternatives considered

- **On-demand gitignored bundle** — keep sources in place, add `make_report
  --bundle` that copies into a derived `report/`. Rejected: duplicates files
  without consolidating, and the report stops being tracked.
- **Full reorg** — move `results/` CSV/JSON under `report/tables/` too. Rejected:
  `results/` is also the drivers' working-data input; churning every driver path
  was more disruption than the consolidation warranted.

## Consequences

- One shippable, self-describing `report/` directory; `results/` is unambiguously
  all-tracked data.
- `report/tables/` intentionally duplicates the source CSVs from `results/` so the
  bundle stands alone — the accepted trade-off.
- Running a single stage no longer emits a quick-look figure; regenerate figures
  with `make_figures`. The ad-hoc `corrosim` CLI (`--out`) is unchanged — only the
  case-study `make_report` targets the tracked bundle.
