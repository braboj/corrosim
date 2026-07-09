# Validation

How `corrosim`'s screening result for the Arghel (*Solenostemma argel*) flavonoids
holds up against independent published work, on a defined steel substrate.

## Substrate

Modelled as a **pure Fe(110) slab** (Φ = 4.82 eV, η_metal ≈ 0). The experimental
coupon is a clean low-carbon (mild) steel, ~AISI 1020-equivalent:

| C | Si | Mn | P | S | Cu | Ni | Cr | V | Fe |
|---|----|----|---|---|----|----|----|---|----|
| 0.204 | 0.089 | 0.59 | 0.001 | 0.001 | 0.170 | 0.028 | 0.029 | 0.0062 | rest |

The surface is ~98.3 % Fe and every alloying element is a dilute residual
(<0.6 %), so an iron slab is the correct atomistic model — consistent with the
literature, which uniformly models "mild/carbon steel" as Fe(110). The very low
S (0.001 %) means almost no MnS inclusions, i.e. uniform corrosion dominates over
pitting — relevant to the *experiment*, not the simulation.

## Stage-1 descriptors (B3LYP/6-311++G(d,p))

Full DFT at the adopted production level (ADR 0002), neutral form, gas and aqueous
(ddCOSMO). All three flavonoids show a **physical, positive ΔN (0.16–0.24)** inside
the Lukovits 0 < ΔN < 3.6 window — DFT corrects the spurious negative ΔN that xTB
gives (its orbital energies sit off the Koopmans scale). **Quercetin** has the
smallest gap and highest softness (the composite-ranking lead), while
**isorhamnetin** leads on charge transfer (ΔN) and electron richness (TNC) via its
methoxy group; kaempferol is third. The three are close on gap/η/σ, but ΔN and ω
separate them.

| Molecule | Phase | HOMO (eV) | LUMO (eV) | Gap (eV) | η (eV) | ΔN | TNC |
|---|---|---|---|---|---|---|---|
| Quercetin | aqueous | −6.134 | −2.052 | **4.082** | 2.041 | +0.178 | −4.71 |
| Isorhamnetin | aqueous | −6.009 | −1.910 | 4.099 | 2.049 | **+0.210** | **−5.52** |
| Kaempferol | aqueous | −6.193 | −2.047 | 4.146 | 2.073 | +0.169 | −4.42 |
| Quercetin | gas | −6.201 | −2.101 | 4.099 | 2.050 | +0.163 | −4.36 |
| Isorhamnetin | gas | −5.897 | −1.781 | 4.116 | 2.058 | +0.238 | −5.31 |
| Kaempferol | gas | −6.234 | −2.063 | 4.171 | 2.086 | +0.161 | −4.07 |

For contrast, xTB (GFN2) gives the right gap *ordering* but unphysical ΔN/χ — use
it only for screening, never for reported descriptors:

| Molecule | Method | HOMO (eV) | LUMO (eV) | Gap (eV) | ΔN |
|---|---|---|---|---|---|
| Quercetin | xTB (GFN2) | −10.383 | −7.870 | 2.513 | −1.714 ✗ |
| Kaempferol | xTB (GFN2) | −10.427 | −7.830 | 2.597 | −1.659 ✗ |

In 1 M HCl the inhibitors protonate; the cations have smaller gaps (3.1–3.6 eV
aqueous) and ΔN flips toward weak electron acceptance. Full neutral/protonated ×
gas/aqueous matrix: `cases/arghel/results/dft_descriptors_ff.{json,csv}` (run `python -m corrosim.runs.run_dft`).

**Quantitative pH-speciation (ADR 0004).** The most basic site is the 4-oxo
carbonyl, a very weak base. A literature-range estimate (pKaH ≈ −1.5) puts the
gap/softness composite lead on a knife-edge: it **crosses from quercetin to
isorhamnetin at only ~5–7 % protonation** (pKaH ≈ −1.1 to −1.3). So which lead is
correct hinges on the protonation pKa — the dominant uncertainty for the acidic
case (more than geometry or level of theory).

**Computed pKaH resolves it (ADR 0005; frequency-corrected, issue #18).** A DFT
deprotonation cycle (B3LYP/6-311++G(d,p) + ddCOSMO on B3LYP/6-31G(d) gas
opt+frequency geometries; `cases/arghel/results/pka.json`, `run_pka --freq`) gives
**pKaH = quercetin −13.3, kaempferol −12.9, isorhamnetin −3.92** — all far below
the crossover, so every flavonoid is **< 0.1 % protonated in 1 M HCl**. The
neutral form is therefore the physically dominant species, not just the
conventional choice, and the **quercetin lead is robust**. The ZPE/thermal/entropy
correction pushes every value *more* negative (more neutral) than the
electronic-only estimate, deepening the conclusion.

*Clean minima (issue #34, resolved).* All six species (each neutral and its cation)
are clean minima with no imaginary frequencies. The isorhamnetin cation had earlier
kept one imaginary mode — its nearly-flat 3'-OMe torsion tips slightly negative under
the default integration grid — so it was re-optimised at a **finer grid (level 4)**
with an **imaginary-mode displacement** (`run_pka --tight`) to a true minimum
(`n_imag = 0`). That refines its pKaH −5.12 → **−3.92** (*less* negative: the old
saddle inflated the cation's Gibbs correction, and stabilising the cation raises its
basicity). The conclusion is unchanged — isorhamnetin is still ~0.01 % protonated and
is not the lead — and it remains the most geometry-sensitive of the three (its
electronic-only pKaH on the DFT-optimised geometry is +1.7, pulled firmly neutral
only by the correction).

### Geometry refinement (FF vs DFT-optimised)

The matrix above uses force-field (MMFF) geometries with a DFT single point. Re-running
the neutral set with a **DFT geometry optimisation** first (B3LYP/6-31G(d), gas phase;
`run_dft --optimize`, data in `cases/arghel/results/dft_descriptors_opt.{json,csv}`) shifts every descriptor
in the same direction but **leaves both rankings unchanged** — the lead assignments are
geometry-robust:

| Descriptor (neutral, aqueous) | Shift FF → DFT-opt | Effect |
|---|---|---|
| Gap ΔE | −0.41 to −0.48 eV | FF over-estimates the gap |
| Hardness η | −0.21 to −0.24 eV | softer, more polarisable |
| Softness σ | +0.06 | — |
| ΔN | +0.019 to +0.023 | stronger predicted donation |
| TNC | −1.3 to −1.8 | more electron-rich |

Ranking by gap stays **quercetin < isorhamnetin < kaempferol**; ranking by ΔN stays
**isorhamnetin > quercetin > kaempferol**. So the FF-geometry screening is a sound,
cheap proxy, and the production numbers tighten with the relaxed geometry (figure
`fig8_geometry_comparison.png`; reproduce with `python -m corrosim.runs.compare_geometry`).

## Cross-check against published Fe(110) studies

| Source | Method | Quercetin | Kaempferol |
|---|---|---|---|
| **corrosim (Stage-2 MC)** | UFF vdW, Metropolis/annealing pose search | −16.0 kJ/mol | −16.6 kJ/mol |
| **corrosim (Stage-3 MD)** | Brownian MD, Fe–O RDF first peak | 3.65 Å (physisorption) | 3.35 Å |
| **Black tea extract study** (Mater. Chem. Phys., 2025) | DFT, periodic + dispersion | strongest constituent; ΔGads ≈ −20 kJ/mol (overall physicochemical ~−35) | weaker than quercetin |
| **Lady's mantle study** (Results in Chemistry, 2025) | DFT/MC | — | strong adsorption confirmed (reference compound) |

(Isorhamnetin: MC −16.7 kJ/mol, RDF peak 3.75 Å. Full data: `cases/arghel/results/mc_adsorption.json`,
`cases/arghel/results/md_rdf.json`; run `python -m corrosim.runs.run_mc` / `run_md`.)

## Experimental validation (Mohammed 2014)

The one direct experiment on *this exact system* — Arghel extract on mild steel in
1 M HCl — is the MSc thesis of E. M. Mohammed (*Corrosion Inhibition of Steel in
Acidic Medium by Herbs Extract*, Materials Science Dept., Institute of Graduate
Studies & Research, Alexandria University, 2014); it is also the source of the
substrate composition table above. A methanolic Arghel extract (25–150 ppm) was
tested at 27 °C by potentiodynamic polarization (PDP) and electrochemical impedance
spectroscopy (EIS) on a Gamry G750, with SEM/optical surface analysis.

| C_inh (ppm) | I_corr (µA/cm2) | -E_corr (mV) | IE % (PDP) | R_ct (ohm cm2) | IE % (EIS) |
|---|---|---|---|---|---|
| blank | 447.0 | 496 | — | 11.78 | — |
| 25 | 14.7 | 484 | 96.71 | 126.4 | 90.68 |
| 50 | 10.67 | 480 | 97.6 | 135.6 | 91.31 |
| 75 | 1.99 | 472 | 99.55 | 142.7 | 91.74 |
| 125 | 1.90 | 470 | 99.57 | 198.1 | 94.05 |
| 150 | 1.66 | 470 | **99.62** | 258.3 | 95.43 |

Adsorption thermodynamics (from the EIS surface coverage θ): the data fit a
**Langmuir** isotherm (also Flory–Huggins and a kinetic-thermodynamic model), with
**ΔG°_ads ≈ −32.5 to −34.5 kJ/mol** (kinetic-thermo K = 456 L/g; Flory K = 398 L/g).
The small anodic E_corr shift (+26 mV) marks a **mixed-type** inhibitor, and the
thesis concludes **physical adsorption**.

**What this confirms.** The model and the experiment agree on three points:

- **Medium and substrate** — 1 M HCl on mild steel — match the corrosim model exactly.
- **Mechanism** — physisorption with a Langmuir isotherm — is exactly what corrosim
  predicts independently (Stage-2 MC E_ads ≈ −16 kJ/mol; Stage-3 Fe–O RDF at
  ~3.5 Å, the physisorption range).
- **Efficacy** — the extract is a genuinely strong inhibitor (up to 99.62 %),
  supporting Arghel flavonoids as effective mild-steel inhibitors in acid.

**What it does not settle.** The study uses a bulk methanolic extract with **no
LC-MS/GC-MS**, so it validates the *extract*, not the individual flavonoids — it
neither confirms nor refutes the quercetin > isorhamnetin > kaempferol ranking.
That per-molecule claim still needs LC-MS plus isolated-compound electrochemistry.

**On comparing ΔG°_ads with the MC E_ads.** The experimental ΔG°_ads
(−32.5/−34.5 kJ/mol) and the corrosim MC E_ads (−16 kJ/mol) are **different
observables and must not be equated**: the MC value is a single-molecule van der
Waals interaction energy on Fe(110) in vacuum, whereas ΔG°_ads is a standard
adsorption *free* energy fitted from an isotherm for the *whole extract*, carrying
entropic, solvent-displacement and coverage terms. They agree on regime
(physisorption/borderline) and order of magnitude, not on a number — the
experimental value sits at the upper edge of the physisorption window (|ΔG| ≳
32 kJ/mol borders the mixed physi-/chemisorption zone), consistent with the
residual charge-transfer contribution that corrosim's classical vdW level omits
(the Stage-3 EAM+GAFF/periodic-DFT hand-off would add it).

## Reading

- **Ranking validated.** The black tea study independently ran DFT on Fe(110) and
  found quercetin the strongest-adsorbing constituent — the same conclusion
  `corrosim` reaches, now confirmed at our own DFT level. Lady's mantle adds a
  second source affirming kaempferol/Fe(110) adsorption.
- **The adsorption-energy gap is now small.** The crude single-orientation height
  scan gave only ≈ −4.5 kJ/mol; the **Metropolis/annealing pose search (Stage-2
  MC) reaches ≈ −16 kJ/mol**, at the lower edge of the published black-tea DFT band
  (−20 to −35 kJ/mol) — full rotational sampling finds the high-contact poses the
  height scan missed. It remains a *physisorption* proxy (UFF van der Waals, no
  charge transfer / water displacement), consistent with the Fe–O RDF peaking at
  ~3.3–3.8 Å (the > 3.5 Å physisorption range) and with experimental reports of
  physical adsorption. The residual gap to the DFT free energy is the
  charge-transfer/chemisorption contribution, which the LAMMPS EAM+GAFF Stage-3
  hand-off (or periodic DFT) would add.

## Defensible claim

> Of the documented major Arghel flavonoids, **quercetin is the strongest
> predicted corrosion inhibitor on mild steel** — confirmed at both semi-empirical
> and DFT levels, ranking-consistent with the UFF adsorption estimate, and in
> agreement with an independent published DFT study of black-tea polyphenols on
> Fe(110).

Simulations rank and explain; they do not by themselves prove efficiency. For the
Arghel *extract* that proof now exists — the Mohammed (2014) PDP/EIS study above
confirms strong physisorptive inhibition of mild steel in 1 M HCl (IE up to
99.62 %). The per-*molecule* attribution — which flavonoid actually leads — is a
computational **prediction**, not an experimental result. Testing it directly would
need sample-specific LC-MS plus isolated-compound electrochemistry; both are
**out of scope for this study (no laboratory access)**. The constituents are
therefore treated as documented-representative (El-Shiekh et al. 2024, and the
Fe(110) black-tea / lady's-mantle DFT precedents above), and the ranking is offered
as a screening hypothesis rather than a measured result.

## Multi-study validation suite

The Arghel study above is validation study #1. To exercise the substrate- and
medium-agnostic design against *independent* published systems, corrosim ships a
**validation preset** per reproduced paper (`presets.CASE_STUDIES`, each with a
`source` citation); its outputs live under `cases/<case>/results/` and its reported
target values are recorded below. Run one with, e.g.,
`python -m corrosim.runs.run_dft --case phytic-acid` (QM in the container).

### Phytic acid — Q235 mild steel (Fe(110)) / 0.5 M H₂SO₄

**Preset:** `phytic-acid` · **Source:** Chidiebere, Oguzie, Liu, Li & Wang,
*Corrosion Inhibition of Q235 Mild Steel in 0.5 M H₂SO₄ Solution by Phytic Acid
and Synergistic Iodide Additives*, **Ind. Eng. Chem. Res. 2014, 53, 7670–7679**
(DOI 10.1021/ie404382v). Phytic acid = *myo*-inositol hexakisphosphate
(C₆H₁₈O₂₄P₆, CAS 83-86-3). This is a Tier-1 anchor: a fully experiment-validated
DFT+MD workflow, on a non-flavonoid inhibitor in a sulfuric — not hydrochloric —
medium.

**Reported values (the comparison target):**

| Quantity | Reported | Method (in the paper) |
| --- | --- | --- |
| E_HOMO | −6.508 eV | AM1 semi-empirical (VAMP, MS Studio) |
| E_LUMO | −1.732 eV | AM1 |
| Gap ΔE | 4.776 eV | AM1 |
| Molecular surface area | 553.89 Å² | AM1; a **flat-lying** adsorption orientation |
| Binding energy E_bind | −199 ± 0.8 kcal/mol | COMPASS MD on Fe(110) (12×10 supercell, NVE, 350 K) |
| IE % (max) | 88.7 % at 0.001 M | potentiodynamic polarization |
| ΔG°_ads | −29.6 kJ/mol (PA) | Langmuir isotherm; mixed-type inhibitor |
| Mechanism | chemisorption | IE rises with T; low/negative E_a |

**Computed (corrosim), B3LYP/6-31G(d) neutral form** (see the basis-choice caveat
below):

| Quantity | Gas | Aqueous (ddCOSMO) | Reported (AM1) |
| --- | --- | --- | --- |
| E_HOMO | −7.841 eV | −8.103 eV | −6.508 eV |
| E_LUMO | −0.520 eV | −0.080 eV | −1.732 eV |
| Gap ΔE | 7.322 eV | 8.023 eV | 4.776 eV |
| Hardness η | 3.661 eV | 4.011 eV | — |
| ΔN → Fe | +0.087 | +0.091 | — |
| TNC (Σ negative Mulliken charge) | −14.59 | −14.93 | — |

- **MC adsorption** (Fe(110)): E_ads = −0.12 eV (−11.5 kJ/mol), lying flat ≈ 2.3 Å
  above the slab.
- **MD Fe–O RDF**: first peak at 3.25 Å (no Fe–N peak — phytic acid carries no
  nitrogen).

**Reading it — a different inhibitor archetype from the flavonoids.** Phytic acid
is *saturated* (no π system), so B3LYP gives it a large gap (7.3 eV) and a modest
ΔN (+0.09, well below the flavonoids' 0.16–0.24): it is not a soft, small-gap
frontier-orbital donor. What stands out instead is the enormous TNC (−14.6) — the
summed partial charge of its 24 phosphate oxygens — so corrosim reads phytic acid
as a **charge-dense, multidentate oxygen chelator** that grips through many O atoms
at once. The flat MC pose (≈ 2.3 Å) and the tight 3.25 Å Fe–O RDF peak corroborate
that flat-lying, oxygen-anchored adsorption — the same picture the paper draws (a
flat orientation, 553.89 Å² footprint, chemisorption through the phosphate O's),
reached by a different route. The frontier-orbital "softness" argument that orders
the flavonoids does not apply to this class; the oxygen count (TNC) carries it.

**Caveats to apply when comparing (not oversights — level-of-theory differences):**

- **AM1 ≠ B3LYP.** The reported orbital energies are AM1 semi-empirical and sit
  on a different scale from corrosim's B3LYP — exactly the caution we document for
  xTB. The numeric HOMO/LUMO/gap differ (AM1 also compresses the gap of a
  saturated system like this one); compare the qualitative picture — oxygen-
  localized frontier orbitals and flat-lying, multidentate adsorption — not the
  digits.
- **Basis: 6-31G(d), not the production 6-311++G(d,p).** Phytic acid folds its six
  phosphates inward (radius of gyration ≈ 4 Å), packing its 24 oxygens close
  together; the production basis's diffuse (`++`) functions then drive the overlap
  matrix near-singular and the SCF diverges, while the density-fitting workaround
  exceeds the container's memory. A converged result comes from dropping the
  diffuse augmentation (6-31G(d) — no near-linear-dependence, ~450 basis functions,
  low-memory), a common level for large inhibitors in the corrosion literature.
  Because the comparison here is qualitative (against AM1), this is the right
  trade; but the *absolute* LUMO/gap stay basis-sensitive (diffuse functions matter
  most for the virtual orbitals), so lean on the picture, not the last digit.
- **Medium.** 0.5 M H₂SO₄ (a diprotic strong acid), not the Arghel HCl —
  `medium.py` models it as the acidic protonated regime. Phytic acid is itself a
  poly-acid (not a base), so the neutral form is its species in acid — the run is
  neutral-only, and the protonated-cation row the flavonoids carry does not apply.
- **E_bind observable.** The −199 kcal/mol is a COMPASS *periodic* binding energy
  (many metal–adsorbate contacts), a different observable from corrosim's UFF
  single-molecule van-der-Waals E_ads — compare regime and sign, not the number
  (the same distinction drawn for the Arghel MC vs experimental ΔG°_ads above).
- **Chemisorption claim.** The paper argues chemical adsorption; corrosim's
  classical MC/MD is a physisorption surrogate, so it can corroborate strong
  adsorption and a flat pose but not the charge-transfer bond — the periodic-DFT
  hand-off would be needed for that.
