# Onboarding

Guide for a new contributor to get corrosim running locally. See `README.md`
for the project overview and `docs/PLAYBOOK.md` for day-to-day operations.

## 1. Prerequisites

- Python 3.10 or newer, with `pip` and the ability to create a virtual
  environment.
- Git (with submodule support).
- Docker Desktop — required only for the QM stages (DFT/xTB). The quantum
  engines `pyscf` and `tblite` have no Windows wheels and run only in the
  bundled `corrosim-qm` image; everything else runs in a plain venv. On
  Windows, Docker Desktop uses the WSL2 backend.

## 2. First-time setup

Clone the repository with its template submodule, create a virtual
environment, and install the package in editable mode with the dev extras.

```bash
git clone --recurse-submodules https://github.com/braboj/corrosim
cd corrosim
# if you cloned without --recurse-submodules:
git submodule update --init docs/solid-ai-templates

python -m venv .venv
# Windows:  .venv\Scripts\activate     |  POSIX:  source .venv/bin/activate
pip install -e ".[dev]"
```

The `dev` extra includes the figure-rendering dependencies, so the full test
suite is importable. The QM engines are intentionally excluded from `dev`
(the suite is QM-light). To build the QM image for DFT/xTB work:

```bash
docker compose build qm
```

On Linux or macOS you may instead install the QM engines natively with the
`qm` extra (`pip install -e ".[qm]"`); on Windows use the Docker image.

## 3. Verify the setup

Run the fast checks. The test suite is QM-light, so it needs no Docker.

```bash
pytest -q          # all tests pass; one QM-dependent test is skipped
ruff check .       # lint: clean
mypy               # type-check (non-strict): clean
```

For an end-to-end check that does not need QM, rebuild the report from the
tracked result data — it writes the `report/` bundle (self-contained
`report/report.html` + figures + tables):

```bash
python -m corrosim.runs.make_report
```

If the QM image is built, confirm the container runs:

```bash
docker compose run --rm qm pytest -q
```

## 4. Key files

Read these first to understand the codebase.

| File | Why it matters |
| --- | --- |
| `corrosim/presets.py` | The `ARGHEL` case study — molecule set, substrate, medium. Single source of truth; drivers import it. |
| `corrosim/engines.py` | Uniform wrappers over the quantum engines (xTB, PySCF) plus geometry optimisation and thermochemistry. |
| `corrosim/cli.py` | The `corrosim` command-line entry point. |
| `corrosim/runs/` | Stage drivers (`run_dft`, `run_fukui`, `run_mc`, `run_md`, `run_pka`, `make_figures`, `make_report`, `compare_geometry`). |
| `corrosim/report.py` | Builds the self-contained HTML pipeline report. |
| `docs/pipeline.md` | The scientific basis for the multiscale pipeline. |
| `docs/validation.md` | How the computational results hold up against published and experimental work. |
| `CLAUDE.md` | Project rules and conventions for AI-assisted work. |

## 5. Project context

corrosim screens green corrosion inhibitors with an open-source multiscale
pipeline: Stage 1 DFT/xTB reactivity descriptors (plus Fukui and ESP maps),
Stage 2 a Monte Carlo adsorption-pose search, and Stage 3 a Brownian
molecular-dynamics run yielding the metal–oxygen radial distribution — ending
in one self-contained HTML report. The reference case study is the Arghel
(*Solenostemma argel*) flavonoids against mild steel in 1 M HCl.

The scientific basis is in `docs/pipeline.md`, the result validation in
`docs/validation.md`, and the architectural decisions in `docs/decisions/`.

## 6. Daily workflow

The routine tasks — git flow, running a pipeline stage, regenerating
artifacts, quality checks, and maintenance — live in `docs/PLAYBOOK.md`. Start
there for anything beyond the initial setup above.

<!-- Generated with solid-ai-templates (github.com/braboj/solid-ai-templates) -->
