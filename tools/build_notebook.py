"""Build corrosion_inhibitor_tool.ipynb"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s))
code = lambda s: cells.append(nbf.v4.new_code_cell(s))

md(r"""# Corrosion-inhibitor screening tool

Automated pipeline for screening green corrosion inhibitors (built around the
**Arghel / *Solenostemma argel*** flavonoids, but it accepts any molecule).

**Inputs:** a list of inhibitors (built-in names *or* SMILES), a metal substrate,
and an engine choice.
**Outputs:** a reactivity-descriptor table, comparison plots, a ranking, a
self-contained **HTML report**, and ready-to-run **adsorption structures** for the
Stage-2 MD step.

```
 name/SMILES ─▶ 3D geometry (RDKit) ─▶ quantum engine ─▶ descriptors ─▶ report
                                       (xTB or DFT)        (HOMO/LUMO,      + ranking
                                                            gap, η, σ, ω, ΔN)   + HTML
        └────────────────────────────▶ metal slab + molecule (ASE) ─▶ MD handoff
```

Everything here runs on **free, open-source** software (RDKit, tblite/xTB, PySCF,
ASE). No paid licenses, no network.""")

md("## 0. Setup")
code(r"""# Install the package first (from the repo root):  pip install -e ".[qm,notebook]"

%matplotlib inline
import sys, pathlib
try:
    import corrosim
except ModuleNotFoundError:                 # not installed -> add repo root to path
    sys.path.insert(0, str(pathlib.Path.cwd().parent))
    import corrosim
import pandas as pd
pd.set_option("display.width", 200)
print("corrosim ready. Built-in molecules:", ", ".join(corrosim.LIBRARY))""")

md(r"""## 1. Inputs — *edit this cell*

- `INHIBITORS`: built-in names (`kaempferol`, `quercetin`, `isorhamnetin`,
  `benzotriazole`, `caffeine`) or any SMILES string.
- `METAL`: `Fe(110)`, `Cu(111)`, or `Al(111)`.
- `ENGINE`: `"xtb"` (sub-second, great for ranking) or `"pyscf"` (real DFT,
  minutes/molecule — use for final numbers). For `pyscf` you can also set
  `BASIS` and `SOLVENT`.""")
code(r"""INHIBITORS = ["kaempferol", "quercetin", "isorhamnetin"]   # the Arghel flavonoids
METAL      = "Fe(110)"      # mild-steel surface
MEDIUM     = "1 M HCl"      # label only (used in the report header)
ENGINE     = "xtb"          # "xtb" fast | "pyscf" DFT | "orca"/"gaussian" (need the binary)
ADSORPTION = True           # add the Stage-2 UFF vdW physisorption estimate

# Only used when ENGINE == "pyscf":
BASIS   = "6-31g"           # production: "6-311++G(d,p)"
SOLVENT = "water"           # implicit solvation (ddCOSMO); None for gas phase
XC      = "b3lyp"

engine_kwargs = {} if ENGINE == "xtb" else dict(basis=BASIS, solvent=SOLVENT, xc=XC)""")

md("## 2. Run the screening")
code(r"""df, _ = corrosim.screen(INHIBITORS, metal=METAL, medium=MEDIUM,
                        engine=ENGINE, adsorption=ADSORPTION, **engine_kwargs)
df""")

md(r"""## 3. Ranking & plots

The composite score favours a **smaller energy gap, lower hardness, higher
softness** — the directions associated with stronger adsorption. Higher = better.""")
code(r"""ranked = corrosim.rank_inhibitors(df)
ranked[["name", "gap_ev", "hardness_ev", "softness_inv_ev", "delta_n", "score"]]""")
code(r"""from corrosim.report import plot_homo_lumo, plot_descriptor_bars
plot_homo_lumo(df)""")
code(r"""plot_descriptor_bars(df)""")

md(r"""> **Engine note on ΔN.** xTB orbital energies sit on a different scale than
> DFT Koopmans values, so the **gap / hardness / softness ranking from xTB is
> reliable, but the absolute ΔN and χ can look off** (even negative). For the
> ΔN descriptor and any publication numbers, re-run the shortlist with
> `ENGINE = "pyscf"`.""")

md("## 4. HTML report")
code(r"""report_path = corrosim.build_html_report(df, metal=METAL, medium=MEDIUM,
                                         level=df["level"].iloc[0],
                                         out_path="corrosion_report.html")
print("Saved:", report_path)
from IPython.display import IFrame
IFrame(report_path, width="100%", height=520)""")

md(r"""## 5. Stage 2 — adsorption energy + structure prep

Two things here: a **fast vdW physisorption energy estimate** (rigid-body UFF,
runs in seconds), and the **metal slab + molecule** exported for a full
molecular-dynamics adsorption study (LAMMPS, run outside the notebook).""")
code(r"""best = ranked["name"].iloc[0]
metal_symbol = METAL.split("(")[0]            # 'Fe(110)' -> 'Fe'
mol = corrosim.build_molecule(best)

# Stage-2a: fast adsorption-energy estimate (UFF van der Waals, physisorption)
ads_e = corrosim.estimate_adsorption_energy(mol, metal=metal_symbol)
print(f"Top inhibitor: {best}")
print(f"Estimated adsorption energy ({ads_e['method']}):")
print(f"  E_ads = {ads_e['e_ads_ev']:.3f} eV  ({ads_e['e_ads_kjmol']:.1f} kJ/mol) "
      f"at {ads_e['best_height_A']} Å")

# Stage-2b: export slab + molecule for the full MD run
adss = corrosim.build_adsorption_system(mol, metal=metal_symbol, size=(6, 6, 4))
paths = adss.write_files(f"{best}_{metal_symbol}_slab")
print(f"\nSystem: {adss.metal}{adss.surface}, {len(adss.combined)} atoms, "
      f"box {tuple(round(b,1) for b in adss.box)} Å")
print("Exported:", paths)
print()
print(corrosim.LAMMPS_HANDOFF_NOTE)""")

md(r"""> **On the adsorption number.** The UFF estimate is a *physisorption-scale*
> screening proxy (van der Waals only, rigid bodies, no charge transfer). It is
> bounded and good for ranking, but a quantitative, chemisorption-capable E_ads
> needs the full MD on the exported structure. A cluster-xTB shortcut was tried
> and rejected — small bare metal clusters give unphysical (tens-of-eV) energies.""")

md(r"""## 6. Beyond the notebook

**Production DFT engines.** Set `ENGINE = "orca"` or `"gaussian"` to use a locally
installed binary. The tool writes the input, runs it, and parses HOMO/LUMO:
```python
row = corrosim.analyse_one("kaempferol", engine="orca",
                           keywords="B3LYP def2-TZVP", solvent="water",
                           orca_cmd="/path/to/orca")
```
ORCA is free for academic use; for the genuinely open path use `engine="pyscf"`.

**Command line / batch.** Screen a whole CSV without Jupyter:
```bash
python -m corrosim --input molecules.csv --metal "Fe(110)" \
                   --engine xtb --adsorption --out report.html --csv results.csv
```
CSV columns: `name` (and optional `smiles`).""")


md(r"""## Caveats & next steps

1. **Representative constituents, not your exact extract.** The flavonoids are
   *documented* major compounds of *S. argel*; confirm your sample with
   LC-MS/GC-MS for a publication-grade claim.
2. **Stage 1 is screening.** Descriptors rank candidates; they do **not** prove
   inhibition efficiency. The adsorption energy (Stage 2 MD) and the
   electrochemical experiments (EIS, polarization, weight loss) are what validate.
3. **To scale up:** add molecules/SMILES to `INHIBITORS`, switch `METAL`, or point
   the engine at ORCA/Gaussian by adding a wrapper in `corrosim/engines.py`
   following the existing `EngineResult` interface.""")

nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.12"},
}
with open("corrosion_inhibitor_tool.ipynb", "w") as f:
    nbf.write(nb, f)
print("notebook written:", len(cells), "cells")
