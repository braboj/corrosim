# ADR 0011 — Adopt a src/ layout and regroup modules into subsystem sub-packages

- Status: Accepted
- Date: 2026-07-04

## Context

corrosim uses a **flat layout** (`corrosim/` at the repo root, not
`src/corrosim/`) — an early, informal choice noted in CLAUDE.md §1.2. Spike #73
asked whether to revisit it, on two axes: the `src/` layout, and regrouping the
22 flat modules into subsystem sub-packages.

Two forces make this worth deciding now, and deciding **before** the per-module
refactor epic #70:

- **Packaging correctness.** We are heading to PyPI/GHCR publishing (#67) and a
  data-driven inhibitor library shipped as package-data (#54). Under a flat
  layout, `import corrosim` can silently resolve to the **working-tree** package
  instead of the **installed** one, so tests can pass against un-packaged code
  (e.g. a `data/` file missing from the wheel). A `src/` layout makes the
  working-tree package un-importable, forcing tests to exercise the installed
  build. `python-lib.md` recommends `src/` for exactly this reason.
- **Sequencing.** A structural move reshapes the very lines epic #70 refactors.
  Doing it first means each per-module PR lands in the file's final home; doing
  it after would churn the same lines twice.

Exploration confirmed the move is mechanical and low-risk:

- The intra-package import graph is a clean DAG — no circular imports; `surface`
  and `presets` are leaves; `report_docx` sits atop `report`.
- Tests are layout-agnostic: no `sys.path` hacks; every test imports the
  editable install, so they work unchanged once the package is reinstalled.
- Only **path-based** references need editing — `pyproject.toml`
  (`packages.find`, coverage `source`/`omit`, `mypy.files`, bandit
  `exclude_dirs`), `Dockerfile` COPY, `ci.yml` `bandit -r`, and stale
  `corrosim/...` paths in the docs. Import-name references
  (`[project.scripts]`, `--cov=corrosim`, `python -m corrosim.runs.*`) are
  unaffected.

## Decision

Two decisions, one concern (project structure):

**1. Adopt the `src/` layout.** Move `corrosim/` to `src/corrosim/`.

**2. Regroup the flat modules into three subsystem sub-packages**, keeping the
input/facade/config modules and the drivers at the package top level:

```
src/corrosim/
  __init__.py  __main__.py  cli.py       # facade + entry (public API stable)
  molecules.py  medium.py  presets.py    # input parsing + shared case-study config
  qm/          engines  descriptors  fukui  pka  speciation     # Stage-1 electronic structure
  adsorption/  surface  adsorption  mc  md                      # Stage-2/3 classical
  report/      report  report_content  report_docx  report_layout  figures  equations
  runs/        run_dft  run_mc  run_md ...                      # drivers, unchanged
```

The boundaries follow the pipeline stages and the observed import clusters:
`qm` is the electronic-structure cluster (`engines` is its heavy leaf);
`adsorption` is the self-contained classical cluster rooted at the shared
`surface` primitives; `report` is the reporting/visualisation cluster (`figures`
renders orbitals/ESP and belongs with the report it feeds). `molecules`,
`medium`, and `presets` stay at the top as cross-cutting leaves.

**Public API stays stable.** The top-level `__init__.py` keeps its `__all__`
re-export facade, so `import corrosim; corrosim.build_html_report(...)` is
unchanged. One collision must be handled: `from corrosim import figures` /
`report` work today because those are *modules*; after the move `corrosim/report/`
is a *package*, so `from corrosim import figures` breaks and `from corrosim
import report` resolves to the package `__init__`. Mitigation — `report/__init__.py`
re-exports the public report names, and the three consumers
(`runs/make_cubes.py`, `runs/make_figures.py`, `runs/compare_geometry.py`, plus
any tests) switch to `from corrosim.report import figures`.

This ADR supersedes the informal flat-layout note in CLAUDE.md §1.2. The move
itself is **not** performed here — it is captured as migration ticket #78,
sequenced strictly before epic #70.

## Rationale

- The `src/` half carries the entire packaging-correctness payoff (#54, #67) on
  its own and is nearly free given the layout-agnostic tests.
- The sub-package half is an organisational-clarity choice, not a
  correctness one. Its only real cost — import churn on the same lines #70
  touches — is neutralised by doing the move first (ticket #78 before #70), so
  refactors land in the final home and nothing is churned twice. Grouping 22
  modules by pipeline stage makes the tree self-describing and gives #54's
  `data/` and future stage-local assets an obvious home.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| **`src/` layout, keep modules flat** (no sub-packages) | The lower-churn option and fully sufficient for #54/#67 — the packaging payoff comes entirely from `src/`. Rejected in favour of the sub-package grouping for organisational clarity: 22 flat modules obscure the stage boundaries, and the churn objection is removed by sequencing the move before #70. Recorded here as the honest fallback if the migration proves costlier than expected. |
| **Keep the flat layout** (status quo) | Rejected: forfeits the import-hygiene that makes `pip install` + test-against-installed reliable, which is the whole point of the #67/#54 push. Leaves the working-tree/installed ambiguity that lets a missing package-data file pass CI. |
| **Subsystem sub-packages without `src/`** | Rejected: adds the churn of regrouping without the packaging-correctness benefit that motivated revisiting the structure at all. |

## Consequences

| Area | What follows |
| --- | --- |
| Packaging | `pyproject.toml` `packages.find` gains `where = ["src"]`; coverage `source`/`omit`, `mypy.files`, and bandit `exclude_dirs` re-point under `src/corrosim/` (ticket #78). |
| Docker / CI | `Dockerfile` COPYs `src/corrosim`; `ci.yml` runs `bandit -r src/corrosim`. `python -m corrosim.runs.*` and `--cov=corrosim` (import-name) are untouched, so the QM image and coverage gate keep working. |
| Public API | Stable via the `__init__` facade. The one break — `from corrosim import figures`/`report` — is contained by re-exports in `report/__init__.py` and three consumer edits. |
| Internal imports | Intra-cluster imports become relative (`adsorption`/`mc`/`md` → `from .surface`, `report_docx` → `from .report`). Behaviour-preserving. |
| Docs | `README.md` layout tree, `docs/pipeline.md` module-path table, ONBOARDING, PLAYBOOK, and CLAUDE.md §1.2's physical-layout description refresh to `src/corrosim/...` when the move lands. |
| Sequencing | Migration ticket #78 executes this and MUST precede epic #70; the spike #73 closes when this ADR merges. |
| Tests | Layout-agnostic today; after the move they exercise the reinstalled package, closing the working-tree/installed gap. |
