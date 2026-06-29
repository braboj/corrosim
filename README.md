# corrosim

Automated screening of green corrosion inhibitors: take a molecule (name or
SMILES) and a metal, get reactivity descriptors, an adsorption estimate, a
ranking, and a report — all on free, open-source software.

Built around the **Arghel (*Solenostemma argel*) flavonoids** (kaempferol,
quercetin, isorhamnetin), but it accepts any molecule.

![CI](https://github.com/braboj/corrosim/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

## Pipeline

```
 name / SMILES ─▶ 3D geometry (RDKit) ─▶ quantum engine ─▶ descriptors ─▶ report
                                          xTB | PySCF |       HOMO, LUMO,     + ranking
                                          ORCA | Gaussian      gap, η, σ, ω, ΔN  + HTML
         └───────────────────────────▶ slab + molecule (ASE) ─▶ UFF E_ads est. + MD handoff
```

| Stage | What | Tool | Status |
|---|---|---|---|
| 1 | DFT/QM reactivity descriptors | tblite (xTB), PySCF, ORCA/Gaussian | ✅ global; ⏳ local (Fukui) |
| 2a | Fast adsorption-energy estimate | UFF van der Waals (built-in) | ✅ screening proxy |
| 2b | Adsorption structure prep | ASE (Fe(110)/Cu(111)/Al(111)) | ✅ |
| 2c | Monte Carlo pose search | — | ⏳ roadmap |
| 3 | Full adsorption-energy MD | LAMMPS | 🔌 hand-off (runs outside) |

The scientific basis — the three-stage methodology, the descriptor equations, the
engine choices, and how each stage maps to the code — is in
[`docs/pipeline.md`](docs/pipeline.md). Results vs. published Fe(110) studies are
in [`docs/validation.md`](docs/validation.md).

## Install

```bash
git clone https://github.com/braboj/corrosim
cd corrosim
pip install -e ".[qm,notebook]"     # core + quantum engines + notebook tooling
```

`rdkit`, `ase`, `tblite`, `pyscf` ship pip wheels on Linux/macOS; if a wheel is
missing on your platform, install that one via conda
(`conda install -c conda-forge rdkit pyscf tblite`).

## Use

**Command line / batch CSV**
```bash
corrosim --input examples/molecules.csv --metal "Fe(110)" \
         --engine xtb --adsorption --out report.html --csv results.csv
```
CSV columns: `name` (and optional `smiles`).

**Python**
```python
import corrosim
df, html = corrosim.screen(
    ["kaempferol", "quercetin", "isorhamnetin"],
    metal="Fe(110)", engine="xtb", adsorption=True,
    out_html="corrosion_report.html",
)
print(corrosim.rank_inhibitors(df))
```

**Notebook** — edit the Inputs cell and run:
```bash
jupyter notebook notebooks/corrosion_inhibitor_tool.ipynb
```

### Engines
- `xtb` — GFN2-xTB, sub-second, for ranking (open-source).
- `pyscf` — real DFT (B3LYP etc.), minutes/molecule, for final numbers (open-source).
- `orca` / `gaussian` — write input, run your local binary, parse HOMO/LUMO:
  ```python
  corrosim.analyse_one("kaempferol", engine="orca",
                       keywords="B3LYP def2-TZVP", solvent="water",
                       orca_cmd="/path/to/orca")     # or set $ORCA_CMD
  ```
  ORCA is free for academic use; for the fully open path use `pyscf`.

## Project structure

```
corrosim/        package (molecules, engines, descriptors, adsorption, report, cli)
notebooks/       the interactive front end
examples/        sample batch CSV
tests/           pytest suite (no DFT — fast)
docs/adr/        architecture decision records
tools/           notebook builder + HTML renderer
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests are deliberately QM-light (descriptor math, parsers, CSV reader, slab/UFF,
one xTB smoke test) so CI stays fast. See `docs/adr/` for design decisions — e.g.
why cluster-xTB was rejected for the adsorption energy.

## Limitations & roadmap

- Stage-1 descriptors are **global**; **local reactivity (Fukui / dual descriptor /
  ESP)** is not computed yet — *roadmap*.
- Stage-2a is a **UFF van-der-Waals physisorption estimate** (rigid bodies, no
  charge transfer): bounded and good for ranking, not a quantitative E_ads. A real
  Monte Carlo pose search is *roadmap*; the full chemisorption-capable E_ads needs
  Stage-3 MD on the exported structure.
- The flavonoids are **documented major constituents** of *S. argel*, simulated as
  representatives — confirm a specific extract with LC-MS/GC-MS.
- Simulations **screen and explain**; they don't prove efficiency. Validate with
  electrochemistry (EIS, polarization, weight loss).

## License

MIT © 2026 Branimir Georgiev
