# corrosim

Automated screening of green corrosion inhibitors: a molecule (name or
SMILES) and a metal in, DFT/QM reactivity descriptors + an adsorption
estimate + a ranking + a self-contained HTML report out. Free software only.

- Owner: Branimir Georgiev
- Repo: github.com/braboj/corrosim
- Model: reference

This file inlines corrosim-specific rules and **defers generic Python,
quality, git, and review rules to the template submodule** under
`docs/solid-ai-templates/`. If that directory is empty, run
`git submodule update --init docs/solid-ai-templates`.

Defer to (read in full; do not summarize):

- `docs/solid-ai-templates/templates/stack/python-lib.md` — Python library
  conventions, packaging, quality gates.
- `docs/solid-ai-templates/templates/base/core/git.md` — git workflow
  (overridden where noted in 2.1).
- `docs/solid-ai-templates/templates/base/core/quality.md`, `oop.md`,
  `testing.md`, `review.md` — quality, design, testing, review rules.

Where this file and a template disagree, **this file wins**: it records the
project's actual, current state.

## 1. Project

### 1.1 Overview

- Python >= 3.10 scientific library + CLI (`corrosim`), MIT.
- Multiscale pipeline: Stage 1 DFT/xTB descriptors + Fukui + ESP ->
  Stage 2 Monte Carlo adsorption pose -> Stage 3 Brownian MD (metal-O RDF)
  -> a self-contained HTML report. Scientific basis: `docs/pipeline.md`.
- Core deps: numpy, rdkit, ase, pandas, matplotlib.
- The QM engines (pyscf, tblite, geometric) have no Windows wheels and run
  ONLY in the `corrosim-qm` Docker image. Everything else runs in a venv.
- Layout is FLAT (`corrosim/`, not `src/`). This OVERRIDES the `src/` rule
  in python-lib.md; do not restructure.

### 1.2 Project structure

```
corrosim/        package: molecules, engines, descriptors, fukui, mc, md,
                 adsorption, surface, figures, report, cli, presets
corrosim/runs/   stage drivers (run_dft/fukui/mc/md, make_cubes/figures/
                 report, compare_geometry)
tools/           static-notebook build/render (build_notebook, render_notebook)
notebooks/       exploratory notebook (corrosion_inhibitor_tool.ipynb)
results/         tracked output data (descriptors, Fukui, MC/MD, comparison)
figures/         curated figure set (PNG, tracked); fig0 = pipeline diagram
cubes/           volumetric .cube files (regenerable, gitignored)
report.html      self-contained pipeline report (tracked)
docs/            pipeline.md, validation.md, adr/, *.local.md (gitignored)
docs/solid-ai-templates/   CLAUDE.md template submodule
tests/           pytest suite (no DFT/Docker - fast)
Dockerfile, docker-compose.yml   the corrosim-qm QM environment
```

### 1.3 Commands

```bash
pytest -q                              # test suite (venv; no QM)
ruff check .                           # lint
docker compose build qm                # build the QM image once
docker compose run --rm qm pytest -q   # run anything needing pyscf/tblite
python -m corrosim.runs.run_dft   --out-csv results/dft_descriptors.csv
python -m corrosim.runs.make_report    # -> report.html
```

Long QM jobs (geometry-opt, MEP cubes) MUST run detached so a shell or
session exit does not kill them mid-run:

```bash
docker compose run -d --name corrosim_job qm \
    python -m corrosim.runs.run_dft --optimize ...
docker logs -f corrosim_job            # poll; then: docker rm corrosim_job
```

## 2. Code conventions

Follow `docs/solid-ai-templates/templates/stack/python-lib.md` and
`.../base/core/quality.md`, `oop.md`. corrosim additions and overrides:

### 2.1 Git

- Conventional commits: `<type>(<scope>): <summary>`, types
  feat/fix/chore/docs/refactor/style/test; subject imperative, < 80 chars.
- End every commit message with this trailer:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Branch off `main` for nontrivial work. Commit and push ONLY when asked.
- `*.local.md` are private working notes: gitignored, never committed.
- `report.html` and `results/*.{csv,json}` ARE tracked; `cubes/` and
  `*.log` are not.

### 2.2 Python

- `from __future__ import annotations`; type-hint public functions.
- Units are part of the contract: energies in eV, distances in Å,
  adsorption energies in kJ/mol. Put the unit in the name or docstring
  (`e_ads_kjmol`, `first_peak_metal_O`); never leave a bare number.
- Scientific-comment exception to "a name that needs a comment is wrong":
  non-obvious physics or derivations MUST carry a short comment naming the
  descriptor or source (Koopmans, Lukovits ΔN, the relevant ADR).
- Single source of truth: the case study (molecule set + substrate +
  medium) lives in `corrosim/presets.py` (`ARGHEL`). Drivers import
  `ARGHEL.molecule_list()` / `ARGHEL.metal`; never re-declare the list.
- Substrate-agnostic: thread the `metal` parameter through; derive labels
  and output keys from the actual metal, never hardcode "Fe".
- Linter/formatter: ruff + `ruff format` (line length 100). Keep new and
  edited code ruff-clean; do not bulk-reformat untouched files.

### 2.3 Data and artifacts

- Generated data -> `results/`; figures -> `figures/`; cubes -> `cubes/`.
- When a change alters an input, regenerate the dependent artifact in the
  SAME change: descriptors / `md_rdf.json` -> `make_figures` +
  `make_report` -> `report.html`. Verify the diff (spot-check values, not
  just file size).

## 3. Quality

### 3.1 Testing

- pytest, deliberately QM-light: NO DFT/xTB/Docker in the suite so CI stays
  fast. Run `pytest -q`. CI matrix is py3.10-3.12 with `pip install -e
  .[dev]`.
- Every new feature or module ships a test (see `tests/test_*.py`).
- Naming: `test_<unit>_<state>_<expected>`.

### 3.2 Scientific validity

- Cross-check ranking / descriptor claims against `docs/validation.md`
  before stating them as results.
- After a geometry or level-of-theory change, confirm the lead ranking is
  robust: `python -m corrosim.runs.compare_geometry`.

## 5. Review process

Follow `docs/solid-ai-templates/templates/base/core/review.md` priority
order (security > correctness > clarity > conventions). corrosim-specific
checks: units stated; outputs metal-agnostic (no stray "Fe"); the case
study read from `presets.ARGHEL`, not re-declared; dependent artifacts
regenerated in the same change.

## 6. Session protocol

### 6.1 Start

- Read `MEMORY.md` (the auto-memory index) and
  `docs/SESSION-HANDOFF.local.md`; run `git status`.

### 6.2 During

- Run long QM jobs DETACHED (see 1.3); they survive a session teardown.
  Docker Desktop may be down after a host restart - start it and wait for
  `docker info` to answer before launching containers.
- Keep `results/`, `figures/`, and `report.html` regenerated as you go.

### 6.3 End

- Run `pytest -q`. Update `docs/SESSION-HANDOFF.local.md` and `MEMORY.md`.
- Commit (conventional, with the trailer) and push only when asked.
