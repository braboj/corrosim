# Validation

corrosim's job is to **rank and explain** candidate inhibitors from first
principles; proving that a molecule actually inhibits is an experimental
question. So validation cross-checks each computed result against an
independently published study of the same or a comparable system, and reads the
agreement only at the level the methods allow:

- **Level of theory sets the ceiling.** Published descriptors come from many
  methods (AM1 semi-empirical, B3LYP DFT, periodic DFT, xTB) whose orbital
  energies sit on different scales. A comparison is only as quantitative as the
  method match: most cases are read for the *qualitative* picture (oxygen- vs
  ring-localised frontier orbitals, soft vs hard, the direction of electron
  donation), and only a same-level source supports a direct numeric comparison.
- **Geometry matters.** A force-field (MMFF) single point and a fully
  DFT-optimised geometry give descriptors that differ by a near-uniform offset
  (gaps ≈ 0.2 to 0.5 eV); compare the trend and the ranking, not the last digit.
- **Adsorption observables are not interchangeable.** A single-molecule UFF
  van-der-Waals `E_ads`, an isotherm-fitted `ΔG°_ads`, and a periodic COMPASS
  binding energy `E_bind` are three different quantities. Compare their **sign,
  regime (physi- vs chemisorption), and order of magnitude**, never the number.
- **A screening result is a hypothesis, not a measurement.** Which molecule
  leads is a prediction; confirming it needs isolated-compound electrochemistry.

Each reproduced paper ships as a **validation preset** (`presets.CASE_STUDIES`,
one `CaseStudy` per study, each with a `source` citation); its outputs live under
`cases/<case>/` and it renders its own report bundle (ADR 0019). The three cases
below span that rigor spectrum: an experiment-anchored study (Arghel), a
qualitative AM1 anchor (phytic acid), and a same-level DFT numeric cross-check
(pyrazolo-pyrimidine).

The pipeline produces four things; each is checked against a published quantity,
and *how* it is read depends on the method gap:

```text
   corrosim computes          checked against (published)
   ─────────────────          ───────────────────────────
   DFT descriptors     ──►     HOMO / LUMO / gap / ΔN
        │            → numbers if same level of theory, else the picture
        ▼
   MC adsorption pose  ──►     E_ads  vs  ΔG°ads  vs  E_bind
        │            → three observables: compare sign + regime, not value
        ▼
   MD metal–O RDF      ──►     adsorption distance & contact regime
        │            → physisorption vs chemisorption range
        ▼
   composite ranking   ──►     reported lead / ordering
                     → a screening prediction, not experimental proof
```

Each case carries a **validation status** for how its computed result compares to
the published target:

| Status | Meaning |
|---|---|
| ✅ **Validated** | agrees with the independent target across every claim the methods can compare |
| 🟡 **Partial** | reproduces some claims, not all |
| ❌ **Rejected** | contradicts the independent target |
| ⏳ **Pending** | not yet assessed |

A *(qualitative)* tag marks a regime-and-picture comparison only (the published
method differs too much for a numeric check); *(quantitative)* marks a direct
same-level numeric comparison.

| Case | System | Published method | Status |
|---|---|---|---|
| **1 · Arghel flavonoids** | mild steel / 1 M HCl | experiment + independent DFT | ✅ Validated |
| **2 · Phytic acid** | Q235 / 0.5 M H₂SO₄ | AM1 semi-empirical | ✅ Validated *(qualitative)* |
| **3 · Pyrazolo-pyrimidine** | carbon steel / HCl | same-level B3LYP DFT | 🟡 Partial *(quantitative)* |

## Substrate model: Fe(110) slab

Every case models mild / carbon steel as a **pure Fe(110) slab** (Φ = 4.82 eV,
η_metal ≈ 0), consistent with the corrosion literature, which uniformly treats
"mild/carbon steel" as Fe(110). The reference coupon below (the Mohammed 2014
Arghel experiment of Case 1) is a clean low-carbon (mild) steel, ~AISI
1020-equivalent, and shows why the slab is the right atomistic model:

| C | Si | Mn | P | S | Cu | Ni | Cr | V | Fe |
|---|----|----|---|---|----|----|----|---|----|
| 0.204 | 0.089 | 0.59 | 0.001 | 0.001 | 0.170 | 0.028 | 0.029 | 0.0062 | rest |

The surface is ~98.3 % Fe and every alloying element is a dilute residual
(<0.6 %), so an iron slab is the correct atomistic model. The very low
S (0.001 %) means almost no MnS inclusions, i.e. uniform corrosion dominates over
pitting (relevant to the *experiment*, not the simulation).

## Case 1: Arghel flavonoids (mild steel / 1 M HCl)

> **Status: ✅ Validated.** Mechanism, regime, efficacy, and ranking all
> consistent with experiment (Mohammed 2014) and independent Fe(110) DFT. The
> per-molecule lead remains a prediction pending isolated-compound assay.

| What we check | corrosim | Independent evidence | Match |
|---|---|---|:-:|
| Mechanism | physisorption (MC + MD) | Langmuir, physical adsorption (Mohammed 2014) | ✅ |
| Contact regime | Fe–O RDF ≈ 3.5 Å | physisorption range | ✅ |
| Efficacy | strong adsorber | IE up to 99.62 % (experiment) | ✅ |
| Lead compound | quercetin | quercetin strongest (black-tea Fe(110) DFT) | ✅ |
| Per-molecule order | quercetin > iso > kaempferol | not tested (extract only, no LC-MS) | ⏳ |

The default study: *Solenostemma argel* flavonoids (quercetin, isorhamnetin,
kaempferol) on mild steel in 1 M HCl, and the only case with a direct experiment
on the exact system (Mohammed 2014). It is corrosim's default preset, but a
validation case like the others, not a privileged reference.

### DFT descriptors (B3LYP/6-311++G(d,p))

Full DFT at the adopted production level (ADR 0002), neutral form, gas and aqueous
(ddCOSMO). All three flavonoids show a **physical, positive ΔN (0.16–0.24)** inside
the Lukovits 0 < ΔN < 3.6 window; DFT corrects the spurious negative ΔN that xTB
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

For contrast, xTB (GFN2) gives the right gap *ordering* but unphysical ΔN/χ. Use
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
correct hinges on the protonation pKa, the dominant uncertainty for the acidic
case (more than geometry or level of theory).

**Computed pKaH resolves it (ADR 0005; frequency-corrected, issue #18).** A DFT
deprotonation cycle (B3LYP/6-311++G(d,p) + ddCOSMO on B3LYP/6-31G(d) gas
opt+frequency geometries; `cases/arghel/results/pka.json`, `run_pka --freq`) gives
**pKaH = quercetin −13.3, kaempferol −12.9, isorhamnetin −3.92**, all far below
the crossover, so every flavonoid is **< 0.1 % protonated in 1 M HCl**. The
neutral form is therefore the physically dominant species, not just the
conventional choice, and the **quercetin lead is robust**. The ZPE/thermal/entropy
correction pushes every value *more* negative (more neutral) than the
electronic-only estimate, deepening the conclusion.

*Clean minima (issue #34, resolved).* All six species (each neutral and its cation)
are clean minima with no imaginary frequencies. The isorhamnetin cation had earlier
kept one imaginary mode (its nearly-flat 3'-OMe torsion tips slightly negative under
the default integration grid), so it was re-optimised at a **finer grid (level 4)**
with an **imaginary-mode displacement** (`run_pka --tight`) to a true minimum
(`n_imag = 0`). That refines its pKaH −5.12 → **−3.92** (*less* negative: the old
saddle inflated the cation's Gibbs correction, and stabilising the cation raises its
basicity). The conclusion is unchanged (isorhamnetin is still ~0.01 % protonated and
is not the lead), and it remains the most geometry-sensitive of the three (its
electronic-only pKaH on the DFT-optimised geometry is +1.7, pulled firmly neutral
only by the correction).

### Geometry refinement (FF vs DFT-optimised)

The matrix above uses force-field (MMFF) geometries with a DFT single point. Re-running
the neutral set with a **DFT geometry optimisation** first (B3LYP/6-31G(d), gas phase;
`run_dft --optimize`, data in `cases/arghel/results/dft_descriptors_opt.{json,csv}`) shifts every descriptor
in the same direction but **leaves both rankings unchanged**, the lead assignments are
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

### Adsorption cross-check against published Fe(110) studies

| Source | Method | Quercetin | Kaempferol |
|---|---|---|---|
| **corrosim (MC adsorption)** | UFF vdW, Metropolis/annealing pose search | −16.0 kJ/mol | −16.6 kJ/mol |
| **corrosim (MD RDF)** | Brownian MD, Fe–O RDF first peak | 3.65 Å (physisorption) | 3.35 Å |
| **Black tea extract study** (Mater. Chem. Phys., 2025) | DFT, periodic + dispersion | strongest constituent; ΔGads ≈ −20 kJ/mol (overall physicochemical ~−35) | weaker than quercetin |
| **Lady's mantle study** (Results in Chemistry, 2025) | DFT/MC | — | strong adsorption confirmed (reference compound) |

(Isorhamnetin: MC −16.7 kJ/mol, RDF peak 3.75 Å. Full data: `cases/arghel/results/mc_adsorption.json`,
`cases/arghel/results/md_rdf.json`; run `python -m corrosim.runs.run_mc` / `run_md`.)

### Experimental validation (Mohammed 2014)

The one direct experiment on *this exact system* (Arghel extract on mild steel in
1 M HCl) is the MSc thesis of E. M. Mohammed (*Corrosion Inhibition of Steel in
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

- **Medium and substrate** (1 M HCl on mild steel) match the corrosim model exactly.
- **Mechanism** (physisorption with a Langmuir isotherm) is exactly what corrosim
  predicts independently (MC E_ads ≈ −16 kJ/mol; MD Fe–O RDF at
  ~3.5 Å, the physisorption range).
- **Efficacy:** the extract is a genuinely strong inhibitor (up to 99.62 %),
  supporting Arghel flavonoids as effective mild-steel inhibitors in acid.

**What it does not settle.** The study uses a bulk methanolic extract with **no
LC-MS/GC-MS**, so it validates the *extract*, not the individual flavonoids; it
neither confirms nor refutes the quercetin > isorhamnetin > kaempferol ranking.
That per-molecule claim still needs LC-MS plus isolated-compound electrochemistry.

**On comparing ΔG°_ads with the MC E_ads.** The experimental ΔG°_ads
(−32.5/−34.5 kJ/mol) and the corrosim MC E_ads (−16 kJ/mol) are **different
observables and must not be equated**: the MC value is a single-molecule van der
Waals interaction energy on Fe(110) in vacuum, whereas ΔG°_ads is a standard
adsorption *free* energy fitted from an isotherm for the *whole extract*, carrying
entropic, solvent-displacement and coverage terms. They agree on regime
(physisorption/borderline) and order of magnitude, not on a number. The
experimental value sits at the upper edge of the physisorption window (|ΔG| ≳
32 kJ/mol borders the mixed physi-/chemisorption zone), consistent with the
residual charge-transfer contribution that corrosim's classical vdW level omits
(the EAM+GAFF/periodic-DFT hand-off would add it).

### Reading

- **Ranking validated.** The black tea study independently ran DFT on Fe(110) and
  found quercetin the strongest-adsorbing constituent, the same conclusion
  `corrosim` reaches, now confirmed at our own DFT level. Lady's mantle adds a
  second source affirming kaempferol/Fe(110) adsorption.
- **The adsorption-energy gap is now small.** The crude single-orientation height
  scan gave only ≈ −4.5 kJ/mol; the **Metropolis/annealing pose search (MC
  adsorption) reaches ≈ −16 kJ/mol**, at the lower edge of the published black-tea DFT band
  (−20 to −35 kJ/mol); full rotational sampling finds the high-contact poses the
  height scan missed. It remains a *physisorption* proxy (UFF van der Waals, no
  charge transfer / water displacement), consistent with the Fe–O RDF peaking at
  ~3.3–3.8 Å (the > 3.5 Å physisorption range) and with experimental reports of
  physical adsorption. The residual gap to the DFT free energy is the
  charge-transfer/chemisorption contribution, which the LAMMPS EAM+GAFF
  hand-off (or periodic DFT) would add.

### Defensible claim

> Of the documented major Arghel flavonoids, **quercetin is the strongest
> predicted corrosion inhibitor on mild steel**, confirmed at both semi-empirical
> and DFT levels, ranking-consistent with the UFF adsorption estimate, and in
> agreement with an independent published DFT study of black-tea polyphenols on
> Fe(110).

Simulations rank and explain; they do not by themselves prove efficiency. For the
Arghel *extract* that proof now exists: the Mohammed (2014) PDP/EIS study above
confirms strong physisorptive inhibition of mild steel in 1 M HCl (IE up to
99.62 %). The per-*molecule* attribution (which flavonoid actually leads) is a
computational **prediction**, not an experimental result. Testing it directly would
need sample-specific LC-MS plus isolated-compound electrochemistry; both are
**out of scope for this study (no laboratory access)**. The constituents are
therefore treated as documented-representative (El-Shiekh et al. 2024, and the
Fe(110) black-tea / lady's-mantle DFT precedents above), and the ranking is offered
as a screening hypothesis rather than a measured result.

## Case 2: Phytic acid (Q235 mild steel, Fe(110) / 0.5 M H₂SO₄)

> **Status: ✅ Validated *(qualitative)*.** corrosim reproduces the charge-dense,
> multidentate oxygen-chelator picture and the flat-lying physisorption regime of
> the AM1 study; the orbital numbers are not comparable across methods.

| What we check | corrosim | Reported (AM1 paper) | Match |
|---|---|---|:-:|
| Frontier picture | O-localised, charge-dense (huge TNC) | O-localised frontier orbitals | ✅ |
| HOMO / LUMO / gap (numeric) | B3LYP/6-31G(d) | AM1 (different scale) | ❌ |
| Adsorption geometry | flat-lying, ≈ 2.3 Å above slab | flat, 553.89 Å² footprint | ✅ |
| Mechanism | physisorption surrogate | chemisorption | 🟡 |

**Preset:** `phytic-acid` · **Source:** Chidiebere, Oguzie, Liu, Li & Wang,
*Corrosion Inhibition of Q235 Mild Steel in 0.5 M H₂SO₄ Solution by Phytic Acid
and Synergistic Iodide Additives*, **Ind. Eng. Chem. Res. 2014, 53, 7670–7679**
(DOI 10.1021/ie404382v). Phytic acid = *myo*-inositol hexakisphosphate
(C₆H₁₈O₂₄P₆, CAS 83-86-3). This is a Tier-1 anchor: a fully experiment-validated
DFT+MD workflow, on a non-flavonoid inhibitor in a sulfuric, not hydrochloric,
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
- **MD Fe–O RDF**: first peak at 3.25 Å (no Fe–N peak; phytic acid carries no
  nitrogen).

**Reading it: a different inhibitor archetype from the flavonoids.** Phytic acid
is *saturated* (no π system), so B3LYP gives it a large gap (7.3 eV) and a modest
ΔN (+0.09, well below the flavonoids' 0.16–0.24): it is not a soft, small-gap
frontier-orbital donor. What stands out instead is the enormous TNC (−14.6), the
summed partial charge of its 24 phosphate oxygens, so corrosim reads phytic acid
as a **charge-dense, multidentate oxygen chelator** that grips through many O atoms
at once. The flat MC pose (≈ 2.3 Å) and the tight 3.25 Å Fe–O RDF peak corroborate
that flat-lying, oxygen-anchored adsorption, the same picture the paper draws (a
flat orientation, 553.89 Å² footprint, chemisorption through the phosphate O's),
reached by a different route. The frontier-orbital "softness" argument that orders
the flavonoids does not apply to this class; the oxygen count (TNC) carries it.

**Caveats to apply when comparing (not oversights, level-of-theory differences):**

- **AM1 ≠ B3LYP.** The reported orbital energies are AM1 semi-empirical and sit
  on a different scale from corrosim's B3LYP, exactly the caution we document for
  xTB. The numeric HOMO/LUMO/gap differ (AM1 also compresses the gap of a
  saturated system like this one); compare the qualitative picture (oxygen-
  localized frontier orbitals and flat-lying, multidentate adsorption), not the
  digits.
- **Basis: 6-31G(d), not the production 6-311++G(d,p).** Phytic acid folds its six
  phosphates inward (radius of gyration ≈ 4 Å), packing its 24 oxygens close
  together; the production basis's diffuse (`++`) functions then drive the overlap
  matrix near-singular and the SCF diverges, while the density-fitting workaround
  exceeds the container's memory. A converged result comes from dropping the
  diffuse augmentation (6-31G(d): no near-linear-dependence, ~450 basis functions,
  low-memory), a common level for large inhibitors in the corrosion literature.
  Because the comparison here is qualitative (against AM1), this is the right
  trade; but the *absolute* LUMO/gap stay basis-sensitive (diffuse functions matter
  most for the virtual orbitals), so lean on the picture, not the last digit.
- **Medium.** 0.5 M H₂SO₄ (a diprotic strong acid), not the Arghel HCl;
  `medium.py` models it as the acidic protonated regime. Phytic acid is itself a
  poly-acid (not a base), so the neutral form is its species in acid; the run is
  neutral-only, and the protonated-cation row the flavonoids carry does not apply.
- **E_bind observable.** The −199 kcal/mol is a COMPASS *periodic* binding energy
  (many metal–adsorbate contacts), a different observable from corrosim's UFF
  single-molecule van-der-Waals E_ads; compare regime and sign, not the number
  (the same distinction drawn for the Arghel MC vs experimental ΔG°_ads above).
- **Chemisorption claim.** The paper argues chemical adsorption; corrosim's
  classical MC/MD is a physisorption surrogate, so it can corroborate strong
  adsorption and a flat pose but not the charge-transfer bond; the periodic-DFT
  hand-off would be needed for that.

## Case 3: Pyrazolo-pyrimidine derivatives (carbon steel, Fe(110) / HCl)

> **Status: 🟡 Partial *(quantitative)*.** Reproduces the absolute frontier
> descriptors and the reported lead (ethyl ester), but not the full 3 > 2 > 1
> order; the separating margins sit below the noise floor. A DFT-geometry rerun
> closes the absolute offset to ≈ 0.05 eV but confirms the order is noise-limited
> (the gap-lead flips ester → acid with geometry), not geometry-limited.

| What we check | corrosim | Reported (Awad 2025) | Match |
|---|---|---|:-:|
| Absolute HOMO / LUMO | −6.18 to −6.22 eV | −6.21 to −6.26 eV | ✅ |
| Reactivity regime | χ ≈ 4 eV, ΔN > 0, physisorption | same | ✅ |
| Lead compound | ester tops composite ranking | ethyl ester | ✅ |
| Full order (3 > 2 > 1) | 3 > 1 > 2 | 3 > 2 > 1 | ❌ |
| Adsorption order | 1 > 2 > 3 (single-molecule MC) | ester max (periodic COMPASS) | ❌ |

**Preset:** `pyrazolo-pyrimidine` · **Source:** Awad, Abdel Halim, Atlam & Fawzy,
*A multiscale computational investigation for protection of carbon steel surface
by pyrazolo-pyrimidine derivatives*, **Sci. Rep. 15:32576 (2025)** (DOI
10.1038/s41598-025-19022-6). Three novel 3-methyl-1-phenyl-1H-pyrazolo[3,4-d]-
pyrimidin-4-yloxy propanoate derivatives sharing one aromatic core, differing
only in the tail: **1** propanoic acid (–COOH), **2** propanamide (–CONH₂), **3**
ethyl ester (–COOEt, the reported **lead**). Unlike the phytic-acid anchor, this
paper computes at **B3LYP/6-311++G(d,p)/IEFPCM, corrosim's own production
level**, so the descriptor numbers compare *directly*, not just qualitatively.

The three compounds are novel (no CAS / not in PubChem); their SMILES were
authored and RDKit-verified (formula + MW exact) and are confirmed by the DFT run
(clean closed-shell SCF, absolute HOMO matching the paper; see the computed
column below):

| cmpd | tail | SMILES | formula |
| --- | --- | --- | --- |
| 1 | –COOH | `Cc1nn(-c2ccccc2)c3ncnc(OCCC(=O)O)c13` | C₁₅H₁₄N₄O₃ |
| 2 | –CONH₂ | `Cc1nn(-c2ccccc2)c3ncnc(OCCC(=O)N)c13` | C₁₅H₁₅N₅O₂ |
| 3 | –COOEt | `Cc1nn(-c2ccccc2)c3ncnc(OCCC(=O)OCC)c13` | C₁₇H₁₈N₄O₃ |

**Reported values (the comparison target), B3LYP/6-311++G(d,p):**

| Quantity | Cmpd 1 | Cmpd 2 | Cmpd 3 (lead) | Method |
| --- | --- | --- | --- | --- |
| E_HOMO (gas, neutral) | −6.261 eV | −6.262 eV | −6.214 eV | DFT |
| E_LUMO (gas, neutral) | −1.611 eV | −1.615 eV | −1.566 eV | DFT |
| Gap ΔE (gas, neutral) | 4.651 eV | 4.647 eV | **4.640 eV** | DFT |
| Gap ΔE (aqueous, neutral) | 4.717 eV | 4.715 eV | **4.713 eV** | DFT + IEFPCM |
| η / σ / χ (cmpd 1, gas) | 2.325 / 0.430 / 3.936 eV | — | — | DFT |
| ΔN → Fe (cmpd 1) | +0.244 | — | — | Lukovits (< 3.6) |
| E_back-donation (cmpd 1) | −0.582 eV | — | — | Gómez (−η/4) |
| E_ads (max, cmpd 3) | — | — | −129.998 kcal/mol | Adsorption Locator (COMPASS) |
| Ranking | \| | 3 > 2 > 1 | \| | gap, softness, TNC, E_ads all agree |

**Computed (corrosim), B3LYP/6-311++G(d,p) single-point on MMFF geometry:**

| Quantity | Cmpd 1 (acid) | Cmpd 2 (amide) | Cmpd 3 (ester) |
| --- | --- | --- | --- |
| E_HOMO (gas, neutral) | −6.224 eV | −6.176 eV | −6.218 eV |
| E_LUMO (gas, neutral) | −1.823 eV | −1.752 eV | −1.817 eV |
| Gap ΔE (gas, neutral) | 4.401 eV | 4.425 eV | 4.401 eV |
| Gap ΔE (aqueous, neutral) | 4.471 eV | 4.480 eV | 4.471 eV |
| η / σ / χ (gas) | 2.200 / 0.454 / 4.023 eV | 2.212 / 0.452 / 3.964 eV | 2.200 / 0.454 / 4.017 eV |
| ΔN → Fe (gas) | +0.181 | +0.194 | +0.182 |
| E_back-donation (gas) | −0.550 eV | −0.553 eV | −0.550 eV |
| Composite rank (aqueous score) | 2nd (+0.66) | 3rd (−1.41) | **1st (+0.76)** |

- **MC adsorption** (Fe(110), UFF van-der-Waals): E_ads −20.4 kJ/mol (acid) >
  −15.6 (amide) > −8.8 (ester), each lying ≈ 2.2 Å above the slab. Ranking
  **1 > 2 > 3**.
- **MD metal–O RDF**: first peak 3.85 Å (acid, amide) or 3.95 Å (ester), with a
  metal–N peak at 3.75 to 3.95 Å for all three. Outer-sphere, physisorption-range
  contact.

**Reading it: the lead reproduces, the full order and the margins do not.** The
absolute frontier levels reproduce the paper (computed HOMO −6.18 to −6.22 eV
against reported −6.21 to −6.26 eV), and the reactivity regime matches: χ ≈ 4 eV,
all three ΔN between +0.18 and +0.19 (below 3.6, i.e. net electron donation to
Fe), back-donation negative, and MD metal–O/N contact at 3.8 to 4.0 Å (outer-
sphere physisorption). On the composite descriptor score (aqueous electro-
negativity, hardness, softness, z-scored), corrosim ranks **3 > 1 > 2** and so
picks the **ethyl ester (cmpd 3) as the lead, matching the paper's reported
lead** (the ester is marginally the softest: lowest η, lowest aqueous gap). It
does *not* reproduce the paper's full **3 > 2 > 1** order, though: corrosim puts
the amide (2) last, not the acid. And every margin here is tiny. The aqueous gaps
span 4.471 to 4.480 eV (ester lowest by 0.4 meV over the acid), the reported gaps
span just 0.011 eV, and the raw gas-phase gap actually orders the acid marginally
ahead of the ester (**1 < 3 < 2**). So corrosim identifies the lead correctly but
on sub-0.01 eV differences that are below the noise floor of an FF-geometry single
point.

Two further mismatches are worth stating plainly. The computed LUMO sits ≈ 0.2 eV
deeper than the reported one, so every gap comes out ≈ 0.24 eV narrower (a near-
uniform offset, consistent with single points on MMFF geometry rather than the
paper's fully B3LYP-optimised structures). And the MC adsorption order inverts to
**1 > 2 > 3** (acid strongest, ester weakest), because a single-molecule UFF
van-der-Waals E_ads does not reward the ester's larger footprint the way the
paper's periodic COMPASS Adsorption-Locator slab does.

**Verdict.** corrosim confirms the authored structures (clean SCF, absolute
descriptors matching the paper), the physisorption regime, and the reported
**lead compound**: the ethyl ester tops the composite descriptor ranking. It
does not reproduce the full **3 > 2 > 1** order (the acid and amide swap), and the
margins separating the three sit below what a single point on MMFF geometry can
resolve, so the lead call is directional rather than robust.

That open test has now been run. A full `--optimize` DFT-geometry rerun
(B3LYP/6-31G(d) relaxation, then descriptors at the production basis;
`dft_descriptors_opt`, `run_dft --optimize`) raises every neutral gap by ≈ 0.19
to 0.20 eV, landing within ≈ 0.05 eV of the reported values (aqueous gaps: acid
4.662, amide 4.669, ester 4.667 eV vs reported 4.717 / 4.715 / 4.713). So
geometry was indeed the cause of the ≈ 0.24 eV offset, and matching it removes
the last confound: the absolute agreement is now excellent. The fine ordering,
however, does *not* sharpen. The optimised gaps span only 0.007 eV (below the
reported 0.011 eV spread), and the gap-lead flips from the ester (FF geometry) to
the acid (DFT geometry). That flip is the finding: the 3 > 2 > 1 order is
noise-limited, not geometry-limited, so no single-method run resolves it (figure
`fig8_geometry_comparison.png`; `compare_geometry` reports the gap ranking
CHANGED, the ΔN ranking PRESERVED).

**Caveats to apply when comparing:**

- **Same level of theory, and now the same geometry.** The paper's
  B3LYP/6-311++G(d,p) with implicit water is corrosim's production level, so the
  comparison is quantitative rather than merely qualitative (the payoff over the
  AM1 phytic-acid anchor), and these ~40-atom aromatics are well-behaved (no
  near-linear-dependence), so the full diffuse basis converges. The shipped
  report's descriptors are single points on MMFF geometry, whose LUMO/gap sit
  ≈ 0.24 eV low; the `--optimize` rerun (above) closes that to ≈ 0.05 eV,
  confirming geometry as the cause. Neither geometry resolves the 0.01 eV gap
  ordering, because it sits below the noise floor.
- **E_ads observable.** The −130 kcal/mol is an Adsorption-Locator (COMPASS
  forcefield) value on a periodic slab, a different observable from corrosim's
  UFF single-molecule van-der-Waals E_ads. Compare the regime (physisorption-range
  adsorption), not the number, and not the order either: the corrosim
  single-molecule ranking inverts to 1 > 2 > 3, because that metric does not
  reward the ester's larger footprint the way a periodic slab does.
- **Novel SMILES.** No CAS/PubChem entry exists; the structures are hand-authored
  from the paper's core + tail description. The DFT run validates them on formula
  and MW (exact) and on absolute frontier levels (computed HOMO −6.18 to −6.22 eV
  against the reported −6.21 to −6.26 eV); the fine gap ordering is a separate
  question the run does not settle (see the verdict above).
- **Medium.** The extracted note records the medium only as acidic HCl (no
  molarity); the preset uses the standard 1 M HCl, which drives the same
  protonated regime; verify the concentration against the paper.
- **FPMD.** The paper's molecular dynamics is periodic Car–Parrinello (Quantum
  ESPRESSO, PBE + DFT-D2), versus corrosim's classical Brownian MD; compare the
  adsorption regime and the metal–heteroatom contact, not the trajectory.
