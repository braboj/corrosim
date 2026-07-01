# corrosim

*Density-functional-theory reactivity, adsorption dynamics, and a shareable
report for green corrosion inhibitors — on free software, end to end.*

corrosim screens green corrosion inhibitors end to end: from a molecule and a
metal, it computes reactivity descriptors, estimates adsorption, ranks
candidates, and emits a self-contained report — all on free, open-source
software. It is built around the **Arghel (*Solenostemma argel*) flavonoids** on
mild steel in 1 M HCl, but accepts any molecule and supported substrate.

![CI](https://github.com/braboj/corrosim/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

## Features

- Screen any molecule — by name or SMILES (Simplified Molecular-Input Line-Entry
  System) — against a metal surface, and rank a candidate set best-first with a
  transparent score
- Compute global reactivity descriptors — HOMO–LUMO gap, chemical
  hardness/softness, and the Lukovits electron-transfer ΔN — with xTB (extended
  tight-binding) or DFT (density-functional theory)
- Map local reactivity — Fukui and dual-descriptor indices, plus
  electrostatic-potential (ESP) isosurfaces
- Estimate the adsorption pose — a Monte Carlo search over a rigid metal slab,
  then Brownian molecular dynamics for the metal–oxygen radial distribution
  function (RDF)
- Emit one self-contained HTML report with every figure embedded
- Run end to end on free, open-source engines (xTB, PySCF)

The multiscale pipeline — how each stage works, the diagram, and the science
behind it — is documented in [`docs/pipeline.md`](docs/pipeline.md).

## Quick start

Prerequisites: Python 3.10+ with `pip`. No quantum engines needed for this path —
it rebuilds the report from the committed result data.

```bash
git clone https://github.com/braboj/corrosim
cd corrosim
pip install -e ".[viz]"                # core + figure rendering
python -m corrosim.runs.make_report    # rebuild report.html from results/
```

Expected output:

```text
report written to report.html (3931 kB, self-contained)
```

Open `report.html` in any browser. To run the DFT/xTB stages yourself, see
[Development setup](#development-setup).

## Usage

corrosim has two modes: a command-line screen and a Python API.

**Command line** — screen the case-study set, rank it, and write a report + CSV:

```bash
corrosim --inhibitors kaempferol,quercetin,isorhamnetin \
         --engine pyscf --out report.html --csv results/screen.csv
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
screen a batch (columns `name[,smiles]`), and `--adsorption` to add the Stage-2
physisorption estimate as an `e_ads_kjmol` column.

**Python** — the same screen from a script:

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

Quercetin is the robust lead across engines and geometries — see
[`docs/validation.md`](docs/validation.md). The quantum engines (`xtb`, `pyscf`)
run natively on Linux/macOS via the `qm` extra, or in the Docker image on
Windows (see [Development setup](#development-setup)).

## Project structure

```text
corrosim/        core package — molecules, engines, descriptors, fukui, mc,
                 md, adsorption, surface, medium, speciation, pka, figures,
                 report, cli, presets
corrosim/runs/   stage drivers — run_dft, run_fukui, run_mc, run_md, run_pka,
                 make_cubes, make_figures, make_report, compare_geometry
results/         tracked output data (descriptors, Fukui, MC/MD, pKa)
figures/         curated figure set (PNG); fig0 is the pipeline diagram
report.html      self-contained pipeline report (from make_report)
examples/        sample batch CSV
tests/           pytest suite (QM-light, no DFT — fast)
docs/            pipeline.md, validation.md, ONBOARDING.md, PLAYBOOK.md,
                 dev-journal.md, decisions/ (ADRs)
Dockerfile              the corrosim-qm QM environment (PySCF + tblite)
docker-compose.yml
```

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
```

**External tool — Docker (for the quantum stages).** The DFT/xTB engines
(`pyscf`, `tblite`, `geometric`) have no native-Windows wheels and run only in
the bundled `corrosim-qm` image; everything else runs in the venv.

```bash
docker compose build qm                           # build once
docker compose run --rm qm pytest -q              # smoke test in the container
docker compose run --rm qm \
    python -m corrosim.runs.run_dft --out-csv results/dft_descriptors.csv
```

The repo is bind-mounted at `/work`, so outputs land back in `results/` /
`figures/` and code edits need no rebuild. Long jobs (geometry-opt, MEP cubes)
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
| `--adsorption` | flag | off | Add the Stage-2 UFF physisorption estimate. |
| `--out` | path | `corrosion_report.html` | HTML report output path. |
| `--csv` | path | *(none)* | Also write the ranked results table to this CSV. |

## Limitations & roadmap

- The adsorption stages (Monte Carlo pose search + Brownian MD) use a **UFF
  van-der-Waals model** (rigid bodies, no charge transfer): bounded and good for
  ranking and the physisorption distance, but **not a quantitative chemisorption
  E_ads**. That last step is the LAMMPS (EAM+GAFF) or periodic-DFT hand-off —
  *roadmap*.
- Geometry optimisation covers the **neutral** forms; a vibrational-frequency
  check (confirm true minima) and optimised **protonated** cations are *roadmap*.
- The flavonoids are **documented major constituents** of *S. argel*, simulated
  as representatives — confirm a specific extract with LC-MS/GC-MS.
- Simulations **screen and explain**; they do not prove efficiency. Validate with
  electrochemistry (EIS, polarization, weight loss).

## Links

- [Pipeline — scientific basis](docs/pipeline.md)
- [Validation — computational and experimental](docs/validation.md)
- [Architecture decisions (ADRs)](docs/decisions/)
- [Onboarding guide](docs/ONBOARDING.md) — setup for new contributors
- [Operational playbook](docs/PLAYBOOK.md) — day-to-day tasks and workflows
- [Development journal](docs/dev-journal.md) — session history
- [Issue tracker](https://github.com/braboj/corrosim/issues)

## License

MIT — see [LICENSE](LICENSE). © 2026 Branimir Georgiev.
