# Examples

Runnable examples for the `corrosim` CLI and the Python API, ordered from the
fastest screen to the full multiscale study. Each one lists the exact command and
what it prints.

Everything here runs against the bundled inhibitor library
(`src/corrosim/data/inhibitors.json`), so no network is needed. The quantum
engines (`xtb`, `pyscf`) have no Windows wheels: on Linux/macOS install the `qm`
extra (`pip install -e .[qm]`) and run in the venv; on Windows prefix each
compute command with `docker compose run --rm qm`. The `--plan` dry runs shown
below need no engine and run anywhere.

## 1. Quick screen (xTB)

A sub-second reactivity ranking. Names resolve against the library, so you can
pass either a name or a SMILES:

```bash
corrosim --inhibitors "kaempferol,quercetin,isorhamnetin" --engine xtb \
         --out report.html --csv results.csv
```

It embeds a force-field geometry per molecule, computes GFN2-xTB descriptors,
ranks by a composite z-score, and writes a self-contained HTML report plus the
results CSV. The ranking prints best-first; see the root
[`README.md`](../README.md) for a sample table and [`docs/validation.md`](../docs/validation.md)
for the validated leads.

Add `--plan` to see the steps without computing (works with no engine
installed):

```text
$ corrosim --inhibitors "kaempferol,quercetin" --engine xtb --plan
Plan - quick screen of 2 molecule(s) on Fe(110), medium '1 M HCl':
  1. geometry    MMFF force-field 3D embed (RDKit), per molecule
  2. descriptors single-point GFN2-xTB (tblite)
  3. rank        composite z-score of gap / hardness / softness / delta_n
  4. report      self-contained HTML -> corrosion_report.html
  ...
Not run here: Fukui, ESP, Monte Carlo pose search, MD RDF, pKa.
```

## 2. Batch from a CSV

[`molecules.csv`](molecules.csv) is a batch input (columns `name[,smiles]`):

```csv
name,smiles
kaempferol,
quercetin,
isorhamnetin,
benzotriazole,
gallic acid,OC(=O)c1cc(O)c(O)c(O)c1
```

The `smiles` column is blank for the first four rows on purpose. A bare `name`
is resolved against the bundled library, so SMILES is optional; you only supply
it for a molecule that is not in the library (here, `gallic acid`). This is the
"name **or** SMILES" demonstration: mix both forms freely in one file.

```bash
corrosim --input molecules.csv --engine xtb --adsorption \
         --out report.html --csv results.csv
```

`--adsorption` adds a fast UFF van-der-Waals physisorption estimate as an
`e_ads_kjmol` column. Dry run:

```text
$ corrosim --input molecules.csv --engine xtb --adsorption --plan
Plan - quick screen of 5 molecule(s) on Fe(110), medium '1 M HCl':
  1. geometry    MMFF force-field 3D embed (RDKit), per molecule
  2. descriptors single-point GFN2-xTB (tblite)
  3. adsorption  UFF van-der-Waals height-scan -> e_ads_kjmol
  4. rank        composite z-score of gap / hardness / softness / delta_n
  5. report      self-contained HTML -> corrosion_report.html
```

## 3. A custom metal and medium

The substrate and medium are flags; the descriptors and the report adapt (the
metal sets the work function used for the charge-transfer term):

```bash
corrosim --inhibitors "benzotriazole,gallic acid" \
         --metal Cu(111) --medium "0.5 M H2SO4" --engine xtb --out report.html
```

## 4. The full multiscale study

The quick screen is one single-point per molecule. The full study runs the whole
pipeline (DFT descriptors, Fukui, ESP, Monte Carlo adsorption, Brownian-MD RDF)
into a `cases/<case>/report/` bundle, orchestrated by one command:

```bash
docker compose run --rm qm corrosim-run-study --case arghel
```

Enrichments are opt-in (`--optimize`, `--with-pka`, `--with-cubes`); `--plan`
lists the ordered steps first:

```text
$ corrosim-run-study --case arghel --plan
Plan - full multiscale study of 3 molecule(s) on Fe(110), medium '1 M HCl':
  QM container (pyscf/tblite):
    1. dft      DFT descriptor matrix B3LYP/6-311++G(d,p) + ddCOSMO water -> results/dft_descriptors_ff.csv
    2. fukui    condensed Fukui / dual descriptor, B3LYP/6-31G(d)    -> results/<name>_fukui.json
  venv (classical):
    3. mc       Monte Carlo adsorption pose search                   -> results/mc_adsorption.json
    4. md       Brownian MD -> metal-X RDF                           -> results/md_rdf.json
    5. figures  render the manuscript figure set                     -> report/figures/
    6. report   assemble the self-contained bundle                   -> cases/arghel/report/ (html + docx + tables)
  Skipped enrichments: pka (add --with-pka), cubes (add --with-cubes).
```

Full-pipeline operations (detached runs, per-stage drivers) live in
[`docs/PLAYBOOK.md`](../docs/PLAYBOOK.md).

## 5. Your own study (bring-your-own inhibitors, metal, medium)

The built-in `--case` names screen the shipped validation studies. To screen
*your own* set, declare a study as data and hand it to the same one-command
runner, with no source edit and no rebuild. Copy
[`study.template.json`](study.template.json) and edit it:

```json
{
  "name": "my-study",
  "molecules": ["quercetin", "benzotriazole", "CCO"],
  "metal": "Fe(110)",
  "medium": "1 M HCl",
  "pkah": -1.5,
  "basis": "6-311++G(d,p)",
  "xc": "b3lyp"
}
```

`name` and `molecules` are required; the rest fall back to the defaults shown.
Molecules are library names or SMILES, so a novel compound needs no library
edit. Run the full pipeline against the file:

```bash
docker compose run --rm qm corrosim-run-study --case ./my-study.json
```

Prefer flags for a one-off? Giving `--molecules` builds the study inline and
writes `cases/<name>/study.json` as a reproducible side effect, so the two forms
are interchangeable:

```bash
corrosim-run-study --name my-study --molecules "quercetin,benzotriazole,CCO" \
    --metal Fe(110) --medium "1 M HCl" --plan
```

The supported envelope is checked up front, so an out-of-range study fails
immediately with a clear message rather than three stages deep: the metal must be
one the slab builder knows (`Fe`, `Cu`, `Al`) and every atom must have a UFF
parameter (`H, C, N, O, S, F, Cl, Br, P`). For a bromine-containing set, declare
`"basis": "def2-SVP"` (the Pople sets lack bromine).

## 6. From Python

corrosim is a library as well as a CLI. The same quick screen from a script:

```python
import corrosim

df, html = corrosim.screen(
    ["kaempferol", "quercetin", "isorhamnetin"],
    metal="Fe(110)", engine="xtb", out_html="report.html",
)
print(corrosim.rank_inhibitors(df).iloc[0]["name"])
```

```text
quercetin
```
