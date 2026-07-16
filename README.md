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

**Install Docker** (Desktop on Windows/macOS, Engine on Linux). It is the only
prerequisite. The DFT/xTB engines have no Windows wheels, so the published image
bundles corrosim with rdkit, pyscf, and tblite: with Docker alone you go from a
molecule to a report, no Python, wheels, or compiler on your side.

Screen a few molecules and write a one-page report in seconds:

```bash
docker run --rm -v "$PWD:/work/out" -w /work/out ghcr.io/braboj/corrosim \
    corrosim screen --inhibitors quercetin,benzotriazole,caffeine \
                    --out report.html --csv screen.csv
```

Open `report.html`, one self-contained file that holds:

- a best-first ranking of the molecules,
- the reactivity descriptors behind it, and
- the charts.

The Docker image is published per release:

- `ghcr.io/braboj/corrosim:<version>` (and `:latest`) from GHCR;
- `docker compose` path under [Development setup](#development-setup) builds
  it locally from source.

## Usage

corrosim is one command with three subcommands: `screen` (fast triage),
`run-study` (the full pipeline), and `add-inhibitor` (grow the library). Every
command runs through the image, so mount a directory for the outputs.

**Quick screen.** Rank a molecule set in seconds; ranks best-first and writes a
one-page HTML report:

```bash
docker run --rm -v "$PWD:/work/out" -w /work/out ghcr.io/braboj/corrosim \
    corrosim screen --inhibitors kaempferol,quercetin,isorhamnetin \
                    --engine pyscf --out report.html --csv screen.csv
```

```text
Ranking (best first):
        name   gap_ev  hardness_ev  softness_inv_ev  delta_n  score
   quercetin 4.082368     2.041184         0.489912 0.178078  0.995
isorhamnetin 4.098977     2.049489         0.487927 0.209973  0.373
  kaempferol 4.145686     2.072843         0.482429 0.168912 -1.368

HTML report: report.html
```

**Full study.** The whole pipeline on your own molecules (minutes to hours):
DFT descriptors + Fukui + ESP + Monte Carlo adsorption + Brownian MD, written as
a report bundle (`report.html`, `report.docx`, figures, and tables) under
`cases/<name>/`:

```bash
docker run --rm -v "$PWD/cases:/work/cases" ghcr.io/braboj/corrosim \
    corrosim run-study --name my-screen \
        --molecules "quercetin,benzotriazole,CCO" --metal Cu(111)
```

Growing the inhibitor library (`add-inhibitor`) is a source-clone task, not a
one-off container run: the library is package data baked into the image. See
[Growing the inhibitor library](docs/PLAYBOOK.md#growing-the-inhibitor-library)
in the PLAYBOOK.

## Modes

The screen is fast triage (ranking only); the full study runs the whole
pipeline. ✓ = on by default, a flag = opt-in, ✗ = not in this mode.

| Capability | `corrosim screen` | `corrosim run-study` |
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

## Configuration reference

corrosim reads no secrets and needs no `.env`. The only environment variables
are the paths to the optional external ORCA/Gaussian binaries:

| Variable | Type | Default | Description |
| --- | --- | --- | --- |
| `ORCA_CMD` | path | `orca` | ORCA executable used by `--engine orca`. |
| `GAUSSIAN_CMD` | path | `g16` | Gaussian executable used by `--engine gaussian`. |

Everything else is per-subcommand CLI options. Run the command's own `--help`,
which is the authoritative, always-current list:

| Command | Purpose |
| --- | --- |
| `corrosim screen --help` | Quick reactivity screen + ranking of a molecule set. |
| `corrosim run-study --help` | Full multiscale study (DFT → MC → MD → report) for a case. |
| `corrosim add-inhibitor --help` | Fetch a compound from PubChem into the inhibitor library. |

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
