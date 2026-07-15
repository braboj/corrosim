# corrosim

*Density-functional-theory reactivity, adsorption dynamics, and a shareable
report for green corrosion inhibitors. Free software, end to end.*

corrosim screens corrosion inhibitors end to end: from a molecule and a
metal, it computes reactivity descriptors, estimates adsorption, ranks
candidates, and writes a self-contained report, all on free, open-source
software. It began as a case study of the **Arghel (*Solenostemma argel*)
flavonoids** on mild steel in 1 M HCl, and now screens any molecule on any
supported substrate.

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

Prerequisites: Docker. The DFT/xTB engines have no Windows wheels, so the
published image is the cross-platform way to run the whole pipeline: it bundles
corrosim with rdkit, pyscf, and tblite, so with only Docker installed you go
from DFT to report with no Python, wheels, or compiler on your side. Outputs
land in `./cases/` on your host.

```bash
# a shipped validation case
docker run --rm -v "$PWD/cases:/work/cases" \
    ghcr.io/braboj/corrosim corrosim-run-study --case arghel

# your own study: bring-your-own inhibitors / metal / medium
docker run --rm -v "$PWD/cases:/work/cases" \
    ghcr.io/braboj/corrosim corrosim-run-study --name my-screen \
        --molecules "quercetin,benzotriazole,CCO" --metal Cu(111)
```

Add `--plan` to preview the ordered steps without computing. The image is
published per release (`ghcr.io/braboj/corrosim:<version>`, and `:latest`); the
`docker compose` path under [Development setup](#development-setup) builds it
locally from source instead.

## Usage

Besides the full study, the image runs a fast `corrosim` screen: it ranks a set
of molecules and writes a one-page report. The quantum engine lives in the
image, so the command runs through Docker (mount a directory for the outputs):

```bash
docker run --rm -v "$PWD:/work/out" -w /work/out ghcr.io/braboj/corrosim \
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
van-der-Waals physisorption estimate as an `e_ads_kjmol` column. (On Linux or
macOS you can install the engines natively with the `qm` extra and drop the
`docker run` prefix; see [Development setup](#development-setup).)

## Modes

The screen is fast triage (ranking only); the full study runs the whole
pipeline. ✓ = on by default, a flag = opt-in, ✗ = not in this mode.

| Capability | `corrosim` (screen) | `corrosim-run-study` (full study) |
| --- | --- | --- |
| Geometry | MMFF force field | MMFF, or DFT-relaxed (`--optimize`) |
| Descriptors (gap, hardness, ΔN) | xTB single-point (or DFT) | DFT (B3LYP) |
| Fukui indices | ✗ | ✓ |
| ESP / orbital maps | ✗ | `--with-cubes` |
| Adsorption estimate | UFF scan (`--adsorption`) | ✓ Monte Carlo pose |
| Binding distance (MD RDF) | ✗ | ✓ |
| pKa / speciation | ✗ | `--with-pka` |
| Output | one-page HTML + ranking | report bundle with figures |
| Speed | seconds | minutes to hours |

## Project structure

| Path | Contents |
| --- | --- |
| **src/corrosim/** | Core package: CLI, molecules, medium, presets, and the fetch tool, plus the subsystem packages below. |
| **src/corrosim/qm/** | Quantum layer: the DFT and xTB engines, reactivity descriptors, Fukui, pKa, speciation, and cube writers. |
| **src/corrosim/adsorption/** | Metal surface, Monte Carlo pose search, and Brownian MD. |
| **src/corrosim/report/** | Report builders (HTML and Word), ranking, figures, and the Pages gallery. |
| **src/corrosim/data/** | Shipped inhibitor library (`inhibitors.json`), grown by the fetch tool. |
| **src/corrosim/runs/** | Stage drivers and the `run-study` orchestrator that chains them end to end. |
| **cases/** | One subtree per case study (shipped: `arghel`), each split into `results/` (data) and `report/` (bundle). |
| **examples/** | Runnable CLI and Python examples with expected output. |
| **tests/** | pytest suite (QM-light, fast). |
| **docs/** | Pipeline, validation, onboarding, playbook, ADRs, and diagram sources. |
| **Dockerfile, docker-compose.yml** | The `corrosim-qm` quantum environment. |

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
  E_ads**. This is a deliberate boundary: a bond-capable E_ads needs an
  HPC-scale periodic-DFT or classical-MD run that would break the free, $0,
  runs-on-a-workstation premise (see ADR 0029; the external recipe is kept in
  `LAMMPS_HANDOFF_NOTE`).
- Simulations **screen and explain**; they do not prove efficiency. Validate with
  electrochemistry (EIS, polarization, weight loss).

## Links

- [Validation gallery](https://braboj.github.io/corrosim/): browse the case
  reports in the browser, no install
- [Pipeline: scientific basis](docs/pipeline.md)
- [Validation: computational and experimental](docs/validation.md)
- [Architecture decisions (ADRs)](docs/decisions/)
- [Onboarding guide](docs/ONBOARDING.md): setup for new contributors
- [Operational playbook](docs/PLAYBOOK.md): day-to-day tasks and workflows
- [Development journal](docs/dev-journal.md): session history
- [Issue tracker](https://github.com/braboj/corrosim/issues)

## License

MIT. See [LICENSE](LICENSE). © 2026 Branimir Georgiev.
