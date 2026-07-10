# corrosim

*Density-functional-theory reactivity, adsorption dynamics, and a shareable
report for green corrosion inhibitors. Free software, end to end.*

corrosim screens corrosion inhibitors end to end: from a molecule and a
metal, it computes reactivity descriptors, estimates adsorption, ranks
candidates, and writes a self-contained report, all on free, open-source
software. It is built for green, plant-derived inhibitors: the **Arghel
(*Solenostemma argel*) flavonoids** on mild steel in 1 M HCl. It also accepts
any molecule and supported substrate.

![CI](https://github.com/braboj/corrosim/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

## Features

- Screen any molecule (by name or SMILES) against a metal surface
- Rank your candidates best-first with a transparent score
- Compute quantum reactivity descriptors (HOMO–LUMO gap, hardness, ΔN) with
  xTB or DFT
- Map where a molecule is reactive: Fukui indices and ESP isosurfaces
- Estimate how it adsorbs: Monte Carlo pose search plus Brownian-dynamics RDF
- Write one self-contained HTML report, every figure embedded
- Run end to end on free, open-source engines (xTB, PySCF)

## Quick start

Prerequisites: Python 3.10+ with `pip`. No quantum engines needed for this path:
it rebuilds the report from the committed result data.

```bash
git clone https://github.com/braboj/corrosim
cd corrosim

# core + figure rendering + Word output
pip install -e ".[viz,report]"

# rebuild cases/arghel/report/ from cases/arghel/results/
python -m corrosim.runs.make_report    
```

Expected output:

```text
report written to cases/arghel/report/report.html (4248 kB, self-contained)
word report written to cases/arghel/report/report.docx (3101 kB)
tables in cases/arghel/report/tables/ (per-stage subfolders)
```

## Usage

**Command line.** Screen the case-study set, rank it, and write a report + CSV:

```bash
corrosim --inhibitors kaempferol,quercetin,isorhamnetin \
         --engine pyscf --out report.html --csv screen.csv
```

Output (the ranking prints best-first, then the report path):

```text
Ranking (best first):
        name   gap_ev  hardness_ev  softness_inv_ev  delta_n  score
   quercetin 4.082368     2.041184         0.489912 0.178078  0.995
isorhamnetin 4.098977     2.049489         0.487927 0.209973  0.373
  kaempferol 4.145686     2.072843         0.482429 0.168912 -1.368

HTML report: report.html
```

Use `--engine xtb` for a sub-second ranking pass, `--input molecules.csv` to
screen a batch (columns `name[,smiles]`), and `--adsorption` to add a fast UFF
van-der-Waals physisorption estimate as an `e_ads_kjmol` column.

**Python.** The same screen from a script:

```python
import corrosim

df, html = corrosim.screen(
    ["kaempferol", "quercetin", "isorhamnetin"],
    metal="Fe(110)", engine="xtb", out_html="report.html",
)
print(corrosim.rank_inhibitors(df).iloc[0]["name"])
```

Output:

```text
quercetin
```

## How it fits together

| | `corrosim` (screen) | `runs/*` → `make_report` (report) |
| --- | --- | --- |
| Per molecule | MMFF geometry, single-point descriptors | DFT (optionally relaxed), Fukui, ESP, MC, MD, pKa |
| Produces | one-page HTML + ranking | `cases/<case>/report/` bundle with figures |
| Speed | seconds | minutes to hours |

`corrosim --plan` lists the steps a screen will run without computing them. On
Windows the engines (`xtb`, `pyscf`) run in the `corrosim-qm` container; the venv
does everything else. Full pipeline commands: [`docs/PLAYBOOK.md`](docs/PLAYBOOK.md).

## Project structure

| Path | Contents |
| --- | --- |
| `src/corrosim/` | Core package facade: `__init__`, `cli`, `molecules`, `medium`, `presets`, `fetch`; subsystem sub-packages below (ADR 0011). |
| `src/corrosim/qm/` | `engines`, `descriptors`, `fukui`, `pka`, `speciation`, `protonation`, `cubes`; `_backend_pyscf`/`_tblite` hold the deferred pyscf/tblite imports (ADR 0015). |
| `src/corrosim/adsorption/` | `surface`, `adsorption`, `mc`, `md`. |
| `src/corrosim/report/` | `report`, `report_docx`, `report_content`, `report_layout`, `figures` (renders cubes; `qm.cubes` writes them). |
| `src/corrosim/data/` | `inhibitors.json`: the shipped inhibitor library (name → SMILES + provenance), loaded by `molecules`; grown by the fetch tool. |
| `src/corrosim/runs/` | Stage drivers: `run_dft`, `run_fukui`, `run_mc`, `run_md`, `run_pka`, `make_cubes`, `make_figures`, `make_report`, `compare_geometry` (+ `_cli`: shared CLI plumbing). |
| `cases/<case>/` | One co-located subtree per case study (the shipped one is `cases/arghel/`), split into `results/` and `report/`. |
| `cases/<case>/results/` | Tracked pipeline data: descriptors, Fukui, MC/MD, pKa. |
| `cases/<case>/report/` | Report bundle (`make_report`): `report.html` + `report.docx` + `figures/<stage>/` + `tables/<stage>/`. |
| `examples/` | Sample batch CSV. |
| `tests/` | pytest suite (QM-light, no DFT, fast). |
| `docs/` | `pipeline.md`, `validation.md`, `ONBOARDING.md`, `PLAYBOOK.md`, `dev-journal.md`, `decisions/` (ADRs), `diagrams/` (.drawio sources). |
| `Dockerfile`, `docker-compose.yml` | The `corrosim-qm` QM environment (PySCF + tblite). |

## Development setup

Clone with the quality-template submodule, create a virtual environment, and
install with the dev extras:

```bash
git clone --recurse-submodules https://github.com/braboj/corrosim
cd corrosim

python -m venv .venv
# Windows:  .venv\Scripts\activate    |  POSIX:  source .venv/bin/activate
pip install -e ".[dev]"       # runtime + tests + figure rendering

pytest -q                     # test suite (QM-light; no Docker)
ruff check .                  # lint
mypy                          # type-check (non-strict; CI gate)
complexipy                    # cognitive-complexity ratchet (CI gate)
```

**External tool: Docker (for the quantum stages).** The DFT/xTB engines
(`pyscf`, `tblite`, `geometric`) have no native-Windows wheels and run only in
the bundled `corrosim-qm` image; everything else runs in the venv.

```bash
docker compose build qm                           # build once
docker compose run --rm qm pytest -q              # smoke test in the container
docker compose run --rm qm \
    python -m corrosim.runs.run_dft --out-csv cases/arghel/results/dft_descriptors_ff.csv
```

The repo is bind-mounted at `/work`, so outputs land back in `cases/<case>/results/` /
`cases/<case>/report/` and code edits need no rebuild. Long jobs (geometry-opt, MEP cubes)
should run detached (`docker compose run -d --name <job> qm …`) so they survive
a shell exit. On Linux/macOS you may instead install the engines natively with
the `qm` extra (`pip install -e ".[qm]"`).

## Configuration reference

corrosim reads no secrets and needs no `.env`. The only environment variables
are the paths to the optional external ORCA/Gaussian binaries:

| Variable | Type | Default | Description |
| --- | --- | --- | --- |
| `ORCA_CMD` | path | `orca` | ORCA executable used by `--engine orca`. |
| `GAUSSIAN_CMD` | path | `g16` | Gaussian executable used by `--engine gaussian`. |

The screening run is configured through CLI options (`corrosim --help`):

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `--input` / `--inhibitors` | path / list | *(one required)* | Molecules: a CSV (`name[,smiles]`) or a comma-separated list of names/SMILES. |
| `--metal` | str | `Fe(110)` | Substrate: `Fe(110)`, `Cu(111)`, or `Al(111)`. |
| `--medium` | str | `1 M HCl` | Medium label for the report header. |
| `--engine` | choice | `xtb` | Quantum engine: `xtb`, `pyscf`, `orca`, `gaussian`. |
| `--basis` | str | `6-311++G(d,p)` | PySCF basis set (ADR 0002 production level). |
| `--xc` | str | `b3lyp` | PySCF exchange–correlation functional. |
| `--solvent` | str | `water` | Implicit solvent (`none` for gas phase). |
| `--adsorption` | flag | off | Add a fast UFF van-der-Waals physisorption estimate (`e_ads_kjmol`), scanned over heights at a flat orientation. |
| `--out` | path | `corrosion_report.html` | HTML report output path. |
| `--csv` | path | *(none)* | Also write the ranked results table to this CSV. |

## Limitations

- The adsorption stages (Monte Carlo pose search + Brownian MD) use a **UFF
  van-der-Waals model** (rigid bodies, no charge transfer): bounded and good for
  ranking and the physisorption distance, but **not a quantitative chemisorption
  E_ads**.
- Simulations **screen and explain**; they do not prove efficiency. Validate with
  electrochemistry (EIS, polarization, weight loss).

## Links

- [Pipeline: scientific basis](docs/pipeline.md)
- [Validation: computational and experimental](docs/validation.md)
- [Architecture decisions (ADRs)](docs/decisions/)
- [Onboarding guide](docs/ONBOARDING.md): setup for new contributors
- [Operational playbook](docs/PLAYBOOK.md): day-to-day tasks and workflows
- [Development journal](docs/dev-journal.md): session history
- [Issue tracker](https://github.com/braboj/corrosim/issues)

## License

MIT. See [LICENSE](LICENSE). © 2026 Branimir Georgiev.
