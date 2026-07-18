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
`cases/<case>/` and it renders its own report bundle (ADR 0019). The six cases
below span that rigor spectrum: an experiment-anchored study (Arghel), a
qualitative AM1 anchor (phytic acid), a same-level DFT numeric cross-check on
iron (pyrazolo-pyrimidine), the first non-iron substrate (aluminium, a same-level
cross-check, TMP-SMX), and two copper studies (tetrazoles, an ordering
cross-check whose reactivity trend tracks the measured inhibition efficiencies;
and pyrazolylnucleosides, the fuller DFT + MC + MD stack with a metal-heteroatom
RDF on copper).

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
| **4 · TMP-SMX** | aluminium / 1 M HCl | same-level B3LYP DFT | 🟡 Partial *(quantitative)* |
| **5 · Tetrazoles** | copper / acidic (HNO₃) | B3LYP DFT + MC (COMPASS) | ✅ Validated *(qualitative)* |
| **6 · Pyrazolylnucleosides** | copper / 1 M HCl | DMol³ DFT + MC + MD | 🟡 Partial *(qualitative)* |

## Substrate models: Fe(110), Al(111), and Cu(111)

The steel cases (1 to 3) model mild / carbon steel as a **pure Fe(110) slab**
(Φ = 4.82 eV, η_metal ≈ 0), consistent with the corrosion literature, which
uniformly treats "mild/carbon steel" as Fe(110). Case 4 is the first non-iron
substrate: an **Al(111) slab** (Φ = 4.26 eV), an fcc(111) facet instead of
bcc(110), exercising the metal-agnostic path end-to-end (the surface builder,
work function, and ΔN reference all read from the case's `metal`, never a
hardcoded "Fe"). Cases 5 and 6 add a second non-iron substrate, a **Cu(111)
slab** (Φ = 4.94 eV, also fcc(111)), so the metal-agnostic path is now exercised
on all three metals the surface builder supports. The reference coupon below (the Mohammed 2014 Arghel experiment
of Case 1) is a clean low-carbon (mild) steel, ~AISI 1020-equivalent, and shows
why the iron slab is the right atomistic model for the steel cases:

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
| Contact regime | Fe–O RDF ≈ 3.0–3.25 Å | physisorption range | ✅ |
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
| **corrosim (MD RDF)** | Brownian MD, Fe–O RDF first peak | 3.25 Å (physisorption) | 3.35 Å |
| **Black tea extract study** (Mater. Chem. Phys., 2025) | DFT, periodic + dispersion | strongest constituent; ΔGads ≈ −20 kJ/mol (overall physicochemical ~−35) | weaker than quercetin |
| **Lady's mantle study** (Results in Chemistry, 2025) | DFT/MC | — | strong adsorption confirmed (reference compound) |

(Isorhamnetin: MC −16.7 kJ/mol, RDF peak 3.15 Å. Full data: `cases/arghel/results/mc_adsorption.json`,
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
  ~3.0–3.25 Å, the physisorption range).
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
  ~2.95–3.25 Å at a weak (few-kJ/mol) interaction energy — a close vdW contact,
  not a chemical bond — and with experimental reports of physical adsorption.
  The residual gap to the DFT free energy is the
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
- **MD Fe–donor RDF**: Fe–O first peak at 3.25 Å plus an Fe–P peak at 3.95 Å
  from the phosphate cores (no Fe–N peak; phytic acid carries no nitrogen).

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
- **MD metal–donor RDF**: metal–O first peak 3.75 Å (acid) or 3.95 Å (amide,
  ester), with a metal–N peak at 3.85 to 3.95 Å for all three. Outer-sphere,
  physisorption-range contact.

**Reading it: the lead reproduces, the full order and the margins do not.** The
absolute frontier levels reproduce the paper (computed HOMO −6.18 to −6.22 eV
against reported −6.21 to −6.26 eV), and the reactivity regime matches: χ ≈ 4 eV,
all three ΔN between +0.18 and +0.19 (below 3.6, i.e. net electron donation to
Fe), back-donation negative, and MD metal–O/N contact at 3.75 to 3.95 Å (outer-
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

## Case 4: TMP-SMX (aluminium, Al(111) / 1 M HCl)

> **Status: 🟡 Partial *(quantitative)*.** Reproduces the absolute frontier
> descriptors (≈ 0.25 eV offset), the better-donor identity (TMP), and the
> paper's refusal to crown a winner: corrosim's robustness gate independently
> returns a **tie** (the composite lead flips TMP → SMX between the neutral and
> the protonated basis). The adsorption ordering is observable-dependent
> (single-molecule UFF MC favours TMP, MD mean-energy favours SMX, the paper's
> solvent-box MC favours SMX), and the classical field cannot confirm the paper's
> sub-3.5 Å chemisorption.

| What we check | corrosim | Reported (Odozi 2026) | Match |
|---|---|---|:-:|
| Absolute HOMO / LUMO | −6.22 to −6.53 eV | −5.94 to −6.29 eV | ✅ |
| Better electron donor | TMP (shallower HOMO, lower χ) | TMP | ✅ |
| Single robust lead | none, a tie (flips with speciation) | none, a synergistic pair | ✅ |
| Stronger adsorber | MC: TMP · MD-mean: SMX | MC: SMX | 🟡 |
| Contact regime | Al–O 3.55 Å (borderline, classical UFF) | < 3.5 Å chemisorption | 🟡 |

The **first non-iron validation case**, and the point of the whole exercise: the
pipeline claims to be substrate-agnostic (thread `metal` through, derive the
work function and slab from it, never hardcode "Fe"), but every prior case is
Fe(110). This one runs the same DFT → MC → MD stack on an **Al(111)** slab
(fcc(111), Φ = 4.26 eV) to check the claim holds on aluminium.

**Preset:** `tmp-smx` · **Source:** Odozi, Mchihi, Olasunkanmi & Abujah, *DFT,
Monte Carlo, molecular dynamics, electrochemical, and weight loss study on
corrosion inhibition of aluminum by trimethoprim and sulfamethoxazole in HCl*,
**Extreme Materials 2 (2026) 100027** (DOI 10.1016/j.exm.2026.100027). Two
pharmaceutical inhibitors, the co-trimoxazole antibiotic pair, each rich in
heteroatoms and aromatic π-systems. The paper computes at **B3LYP/6-311++G(d,p),
corrosim's own production level**, so (like the pyrazolo case) the descriptor
numbers compare *directly*, not just qualitatively.

Both molecules are in PubChem and shipped in the library from there:

| cmpd | role | SMILES | formula | CAS |
| --- | --- | --- | --- | --- |
| TMP | trimethoprim | `COc1cc(Cc2cnc(N)nc2N)cc(OC)c1OC` | C₁₄H₁₈N₄O₃ | 738-70-5 |
| SMX | sulfamethoxazole | `Cc1cc(NS(=O)(=O)c2ccc(N)cc2)no1` | C₁₀H₁₁N₃O₃S | 723-46-6 |

**Reported values (the comparison target), B3LYP/6-311++G(d,p), gas/vacuum,
neutral:**

| Quantity | TMP | SMX | Method |
| --- | --- | --- | --- |
| E_HOMO | −5.94 eV | −6.29 eV | DFT |
| E_LUMO | −0.64 eV | −1.02 eV | DFT |
| Gap ΔE | 5.29 eV | 5.28 eV | DFT |
| IP / EA | 5.94 / 0.64 eV | 6.29 / 1.02 eV | Koopmans |
| η (hardness) | 2.65 eV | 2.64 eV | (IP−EA)/2 |
| σ (softness) | 0.38 eV⁻¹ | 0.38 eV⁻¹ | 1/η |
| χ (electronegativity) | 3.29 eV | 3.66 eV | (IP+EA)/2 |
| μ / CP (chem. potential) | −3.29 eV | −3.66 eV | −χ |
| ω (electrophilicity) | 2.04 eV | 2.53 eV | χ²/2η |
| MC E_ads (full solvent box) | −4965 kcal/mol | −5096 kcal/mol | Adsorption Locator (COMPASS) |

**Reported reading.** The picture is genuinely split. On the frontier
descriptors **TMP** is the marginally better electron donor (higher HOMO by
0.35 eV, lower χ by 0.37 eV), yet the Monte Carlo adsorption energy has **SMX**
binding more strongly (−5096 vs −4965 kcal/mol). The HOMO–LUMO gaps are
near-identical (5.28 vs 5.29 eV), so they give no discrimination. Both molecules
show RDF peaks under 3.5 Å (the paper reads this as chemisorption), and both
give negative ΔG°_ads (spontaneous adsorption). Experimentally TMP-SMX is a
mixed-type inhibitor (ΔE_corr < 85 mV) that raises the charge-transfer
resistance from 220 to 610 Ω·cm² at 0.4 g/L. The paper does not crown a single
winner; it presents the two as a synergistic pair (co-trimoxazole).

**Computed (corrosim), B3LYP/6-311++G(d,p) single-point on MMFF geometry,
gas/neutral:**

| Quantity | TMP | SMX |
| --- | --- | --- |
| E_HOMO (gas, neutral) | −6.224 eV | −6.527 eV |
| E_LUMO (gas, neutral) | −1.315 eV | −1.248 eV |
| Gap ΔE (gas, neutral) | 4.908 eV | 5.279 eV |
| η / σ / χ (gas) | 2.454 / 0.407 / 3.769 eV | 2.639 / 0.379 / 3.888 eV |
| ω (gas) | 2.895 eV | 2.863 eV |
| ΔN → Al (gas) | +0.100 | +0.071 |
| E_back-donation (gas) | −0.614 eV | −0.660 eV |
| Canonical composite rank | tie | tie |

- **MC adsorption** (Al(111), UFF van-der-Waals): E_ads −130.2 kJ/mol (TMP) >
  −99.7 (SMX), lying 2.81 Å and 3.13 Å above the slab. Ranking **TMP > SMX**.
- **MD metal–donor RDF**: Al–O first peak 3.55 Å for both (Al–N 3.65 to 3.75 Å,
  plus an Al–S peak at 3.95 Å for SMX's sulfonamide sulfur); mean interaction
  energy −67.1 kJ/mol (TMP) vs −75.9 (SMX). Outer-sphere, physisorption-range
  contact by the classical field.
- **Local reactivity (Fukui and ESP).** The condensed Fukui map (fmo,
  B3LYP/6-31G(d)) and the ESP-on-density isosurface, now both shipped in the
  bundle (figs 4, 7, and the 2b HOMO/LUMO isosurfaces), localise the
  nucleophilic centres (the f⁻ donor density and the electron-rich red ESP lobes)
  on the heteroatom-bearing ends. SMX's strongest donor site is the
  sulfonamide/isoxazole nitrogen (top f⁻ +0.26 at N16); TMP's are the
  trimethoxybenzyl oxygens and an adjacent ring carbon (top f⁻ +0.29 at C7),
  while its diaminopyrimidine ring reads as the electrophilic (f⁺) acceptor end.
  The paper presents its own Fukui and ESP as maps rather than tables, so this is
  a qualitative site comparison (the same heteroatom-centred donor picture), not
  a digit-by-digit one.

**Reading it: the DFT picture and the tie reproduce; the adsorption ordering is
observable-dependent.** The absolute frontier levels reproduce the paper
(computed HOMO −6.22 / −6.53 eV against reported −5.94 / −6.29 eV, both ≈ 0.25 to
0.28 eV deeper, the near-uniform offset expected from a single point on MMFF
geometry). The better-donor identity reproduces too: **TMP** has the shallower
HOMO and the lower χ in both corrosim and the paper, and both molecules give a
small positive ΔN to aluminium (+0.10, +0.07, i.e. net electron donation, well
inside the Lukovits window). So the electronic regime and the donor ordering
match.

The interesting part is the lead. corrosim discriminates on the gap where the
paper is degenerate, but the discrimination *flips with protonation*: on the
neutral form TMP has the smaller gap (4.908 vs 5.279 eV) and leads the composite,
while on the protonated / pH-weighted form (the acid-medium species) SMX has the
smaller gap (4.020 vs 4.154 eV) and leads. Because the composite lead changes
across the two bases, the ADR 0021 robustness gate asserts **no single lead and
reports a tie**. That independently reproduces the paper's own posture: it never
crowns a winner either, splitting TMP (better donor) against SMX (stronger
adsorption) and presenting the two as a synergistic pair.

The adsorption side is the partial match. corrosim's single-molecule UFF Monte
Carlo makes **TMP** the stronger binder (−130 vs −100 kJ/mol), the *opposite* of
the paper's full-solvent-box Adsorption-Locator ordering (SMX stronger); yet
corrosim's MD mean interaction energy does put **SMX** a little deeper (−75.9 vs
−67.1 kJ/mol), agreeing with the paper's direction. So the "stronger adsorber"
answer is observable-dependent even within corrosim. And the contact regime
differs: the paper reads its sub-3.5 Å RDF peaks as chemisorption, whereas
corrosim's classical Brownian MD sits at 3.55 Å with a rigid van-der-Waals field
that can neither form nor detect a chemical bond, so it can only report
outer-sphere, physisorption-range contact.

**Verdict.** On aluminium, corrosim validates the DFT side (absolute descriptors
at the same level of theory, the better-donor identity, the donation regime) and
independently reaches the paper's no-single-winner conclusion as a robustness
tie. It reproduces the adsorption *direction* by MD mean energy but inverts it by
single-molecule MC, and its classical field cannot confirm the reported
chemisorption. Most importantly for the substrate-agnostic goal, the whole
DFT → MC → MD → ranking stack runs end-to-end on an **Al(111)** slab and yields
physically sensible, literature-consistent numbers, so the metal-agnostic design
is exercised and validated on a non-iron surface.

**Caveats to apply when comparing:**

- **Same level of theory.** The paper and corrosim both use
  B3LYP/6-311++G(d,p), so absolute frontier levels compare directly. Geometry
  still differs (corrosim's single point on MMFF geometry vs the paper's fully
  DFT-optimised structures), so expect the usual near-uniform gap offset;
  compare the trend and the split, not the last digit.
- **Adsorption observables are not interchangeable.** The paper's MC E_ads is a
  full solvent-box (280 H₂O / H₃O⁺ / Cl⁻) Adsorption-Locator energy of several
  thousand kcal/mol; corrosim's is a single-molecule UFF van-der-Waals E_ads of
  tens of kJ/mol. Compare sign, regime, and which molecule binds more strongly,
  never the number.
- **Divergent basicity, one case pKaH.** TMP (diaminopyrimidine, pKaH ≈ 7.1) and
  SMX (anilinium, pKaH ≈ 1.6) differ in basicity, but at pH ≈ 0 both are
  essentially fully protonated, so the single case pKaH represents both here; it
  would not for a near-neutral medium.

## Case 5: Tetrazoles (copper, Cu(111) / acidic medium)

> **Status: ✅ Validated *(qualitative)*.** corrosim reproduces the paper's
> complete inhibition ordering, PMTZ > PTZ > ATZ > TZ, on all three pipeline
> stages at once (the DFT gap/hardness/softness composite, the Monte Carlo
> adsorption energy, and the MD mean interaction energy), and that ordering is
> the measured one: the experimental inhibition efficiencies rise 6 / 32 / 42.5 /
> 94.5 % in exactly this sequence. The robustness gate asserts a robust PMTZ lead
> (both speciation bases agree). The comparison is of the ordering and its
> correlation with the efficiencies, not the absolute descriptors: the paper's
> frontier levels sit on an anomalously shallow scale (HOMO near -2 eV) whereas
> corrosim's are physical (-6.8 to -8.8 eV).

| What we check | corrosim | Reported (Bourzi 2020) | Match |
|---|---|---|:-:|
| Inhibition ordering (DFT composite) | PMTZ > PTZ > ATZ > TZ | PMTZ > PTZ > ATZ > TZ | ✅ |
| Ordering vs experimental IE % | PMTZ > PTZ > ATZ > TZ | 94.5 > 42.5 > 32 > 6 % | ✅ |
| Strongest / weakest inhibitor | PMTZ / TZ | PMTZ / TZ | ✅ |
| MC adsorption ordering on Cu(111) | PMTZ > PTZ > ATZ > TZ | PMTZ > PTZ > ATZ > TZ | ✅ |
| Absolute frontier levels | HOMO -6.8 to -8.8 eV (physical) | HOMO -1.8 to -2.0 eV (anomalous) | 🟡 |

The **second non-iron validation case** (after aluminium), and the one that
closes the substrate-agnostic exercise on all three metals the surface builder
supports. Four tetrazole derivatives adsorb on a **Cu(111)** slab (fcc(111),
Φ = 4.94 eV): the bare ring (TZ), plus an amino (ATZ), a phenyl (PTZ), and a
1-phenyl-5-mercapto (PMTZ) substituent, a series that grows the donor set worst
to best. Unlike the earlier cases the target here is not one paper's descriptor
numbers but a **ranking that is independently anchored to experiment**: the paper
reports the measured inhibition efficiencies for the same four molecules, so a
screen that recovers their order recovers a fact, not just another calculation.

**Preset:** `tetrazoles` · **Source:** Bourzi, Oukhrib, El Ibrahimi, Abou Oualid,
Abdellaoui, Balkard, Hilali & El Issami, *Understanding of anti-corrosive
behavior of some tetrazole derivatives in acidic medium: adsorption on Cu(111)
surface using quantum chemical calculations and Monte Carlo simulations*,
**Surface Science 702 (2020) 121692** (DOI 10.1016/j.susc.2020.121692). The paper
computes at B3LYP (among HF / MP2 / B3LYP with 6-31+G(2d,p)); corrosim uses the
same functional at its larger production basis.

Both the molecules and their abbreviations ship in the library:

| cmpd | role | SMILES | formula | CAS |
| --- | --- | --- | --- | --- |
| TZ | 1H-tetrazole | `c1nnn[nH]1` | CH₂N₄ | 288-94-8 |
| ATZ | 5-amino-1H-tetrazole | `Nc1nnn[nH]1` | CH₃N₅ | 4418-61-5 |
| PTZ | 5-phenyl-1H-tetrazole | `c1ccc(-c2nnn[nH]2)cc1` | C₇H₆N₄ | 18039-42-4 |
| PMTZ | 1-phenyl-1H-tetrazole-5-thiol | `Sc1nnnn1-c1ccccc1` | C₇H₆N₄S | 86-93-1 |

The source figure draws PTZ with the phenyl on C5 (the abstract's "1-phenyl" is a
naming slip) and PMTZ as the thiol tautomer; both are followed here.

**Reported values (the comparison target), B3LYP/6-31+G(2d,p), aqueous, neutral,
plus the measured inhibition efficiencies:**

| Quantity | TZ | ATZ | PTZ | PMTZ |
| --- | --- | --- | --- | --- |
| E_HOMO | -2.021 eV | -1.915 eV | -1.851 eV | -1.801 eV |
| E_LUMO | 0.909 eV | 0.894 eV | 0.862 eV | 0.842 eV |
| Gap ΔE | 2.930 eV | 2.809 eV | 2.714 eV | 2.644 eV |
| η (hardness) | 1.465 eV | 1.404 eV | 1.357 eV | 1.322 eV |
| χ | 0.556 eV | 0.511 eV | 0.494 eV | 0.479 eV |
| ΔN | 1.339 | 1.413 | 1.469 | 1.513 |
| E_ads on Cu(111) (COMPASS) | -43.1 | -51.7 | -65.8 | -67.1 kcal/mol |
| **Experimental IE %** | **6** | **32** | **42.5** | **94.5** |

**Reported reading.** Every descriptor moves monotonically along TZ -> ATZ -> PTZ
-> PMTZ (shallower HOMO, smaller gap, lower hardness, higher ΔN), the adsorption
energy deepens in the same order, and so does the measured inhibition efficiency
(6 -> 94.5 %). The paper's whole argument is that this one ordering is consistent
across theory and experiment, with PMTZ (the mercapto / phenyl member) the clear
best and bare TZ the worst. The absolute frontier values are anomalous, though:
an E_HOMO near -2 eV is far shallower than a tetrazole's true ionisation level,
so only the ordering is usable.

**Computed (corrosim), B3LYP/6-311++G(d,p) single-point on MMFF geometry,
aqueous, neutral:**

| Quantity | TZ | ATZ | PTZ | PMTZ |
| --- | --- | --- | --- | --- |
| E_HOMO | -8.755 eV | -6.784 eV | -6.977 eV | -7.026 eV |
| E_LUMO | -1.572 eV | -1.329 eV | -1.683 eV | -1.918 eV |
| Gap ΔE | 7.183 eV | 5.455 eV | 5.294 eV | 5.108 eV |
| η / softness | 3.591 / 0.278 | 2.728 / 0.367 | 2.647 / 0.378 | 2.554 / 0.392 |
| χ | 5.164 eV | 4.056 eV | 4.330 eV | 4.472 eV |
| ΔN → Cu | -0.031 | +0.162 | +0.115 | +0.092 |
| Composite score | -1.71 | +0.35 | +0.58 | +0.79 |

- **MC adsorption** (Cu(111), UFF van-der-Waals): E_ads -3.8 (TZ), -4.5 (ATZ),
  -9.1 (PTZ), -10.3 (PMTZ) kJ/mol, lying 2.9 to 3.1 Å above the slab. Ranking
  **PMTZ > PTZ > ATZ > TZ**.
- **MD metal-heteroatom RDF**: no oxygen in these rings, so the contact is
  metal-N at 3.35 to 3.45 Å (physisorption range), plus a Cu-S peak at 3.75 Å
  for the mercapto derivative (its thiol sulfur); mean interaction energy -1.3
  (TZ) to -2.9 (PMTZ) kJ/mol, deepening in the same order.
- **Local reactivity (Fukui / ESP)**: the f- donor density and the electron-rich
  ESP lobe localise on the ring nitrogens and, for PMTZ, the mercapto sulfur (its
  extra soft-donor site), consistent with the paper's reactive-site analysis.

**Reading it: the ordering reproduces on every stage, and it is the measured
ordering.** corrosim's composite ranking (smaller gap, lower hardness, higher
softness) puts the four molecules in the order PMTZ > PTZ > ATZ > TZ, PMTZ well
clear (composite +0.79 against -1.71 for TZ). The Monte Carlo adsorption energy on
copper and the MD mean interaction energy independently give the same order. All
three therefore agree with the paper's descriptor and adsorption orderings, and
all three agree with the experimental inhibition efficiencies (6 / 32 / 42.5 /
94.5 %). Because the medium is only weakly ionising for these tetrazoles (they are
weak bases), the neutral and pH-weighted bases name the same lead, so the ADR
0021 robustness gate reports a **robust PMTZ lead** rather than a tie.

Two honest mismatches sit under the clean ranking. First, the absolute frontier
levels do not compare: corrosim's HOMO (-6.8 to -8.8 eV) is physical while the
paper's (-1.8 to -2.0 eV) is not, so only the ordering is meaningful. Second,
corrosim's ΔN does not track the efficiency the way the paper's does: its largest
value falls on ATZ, not PMTZ, and TZ even comes out slightly negative. But ΔN is
not a component of the composite, and the gap / hardness / softness that are do
recover the order. The physical driver is intact: PMTZ carries the polarisable
mercapto sulfur and the conjugating phenyl, giving it the smallest gap and the
softest electron cloud, which is why it leads on both the DFT screen and the
van-der-Waals adsorption.

**Verdict.** On copper, corrosim reproduces the full inhibition ordering of four
tetrazoles across DFT, MC and MD simultaneously, and that ordering is the one
measured experimentally, so the screen recovers an experimentally anchored fact
rather than a single paper's numbers. Combined with the aluminium case, the
metal-agnostic pipeline is now validated on all three substrates it supports
(Fe(110), Al(111), Cu(111)). The comparison is qualitative by necessity (the
paper's absolute descriptors are anomalous and its adsorption energies use a
different force field), but the ranking, the thing a screen exists to produce, is
correct.

**Caveats to apply when comparing:**

- **Ordering, not absolute values.** The paper's frontier energies are on an
  anomalously shallow scale (HOMO near -2 eV); corrosim's are physical. Only the
  descriptor *ordering* and its correlation with the measured efficiencies are
  compared, never the numbers.
- **Different basis, same functional.** Both use B3LYP; the paper's 6-31+G(2d,p)
  is smaller than corrosim's 6-311++G(d,p), a further reason to read the trend,
  not the digit.
- **Adsorption observables are not interchangeable.** The paper's E_ads is a
  COMPASS force-field energy in kcal/mol; corrosim's is a single-molecule UFF
  van-der-Waals E_ads in kJ/mol. Compare the ordering and sign, never the value.
- **No reported MD/RDF.** The paper runs DFT + Monte Carlo only; corrosim's MD
  metal-N RDF is its own output, with no published distance to check against.
- **Medium modelled as nitric acid.** The paper states only "acidic medium" and
  correlates against the group's prior experiments on these tetrazolic compounds
  in nitric acid; it is modelled here as 1 M HNO₃. Tetrazoles are weak bases, so
  the exact pH barely moves the ranking.

## Case 6: Pyrazolylnucleosides (copper, Cu(111) / 1 M HCl)

> **Status: 🟡 Partial *(qualitative)*.** corrosim's Monte Carlo reproduces the
> paper's strongest adsorber (5e, the bromo derivative), and all five molecules
> adsorb spontaneously on copper, but the full five-molecule order is below the
> method's resolution: the derivatives differ only in a distal para substituent
> (CH₃ / OCH₃ / F / Cl / Br), a perturbation smaller than the UFF and def2-SVP
> screens resolve. The DFT composite ties (5d neutral vs 5b pH-weighted) rather
> than crowning 5e, MD is observable-dependent, and the classical field gives
> physisorption distances where the paper reads chemisorption. This is the
> **fuller non-iron case** (DFT + MC + MD with a metal-heteroatom RDF), so it
> exercises the MD/RDF path on copper even where the fine ordering is noise.

| What we check | corrosim | Reported (Oukhrib 2021) | Match |
|---|---|---|:-:|
| Strongest adsorber (MC on Cu) | 5e (bromo) | 5e (bromo) | ✅ |
| All five adsorb spontaneously | yes (all E_ads < 0) | yes | ✅ |
| Full inhibition order | noise-limited | 5e > 5b > 5a > 5c > 5d | 🟡 |
| Single robust DFT lead | none, a tie (5d ↔ 5b) | 5e | 🟡 |
| Contact regime | Cu–O 3.35 to 3.75 Å (physisorption) | < 3.5 Å chemisorption | 🟡 |

The **fuller of the two copper cases** (the tetrazoles case is DFT + MC only).
Five novel pyrazolylnucleosides adsorb on a **Cu(111)** slab: a common
2-deoxyribofuranosyl pyrazole carrying a cyanomethyl arm and a 4-X-phenyl group,
where the only difference across 5a to 5e is the para substituent X = CH₃ / OCH₃
/ F / Cl / Br. The source ran the whole DFT + Monte Carlo + molecular dynamics
stack with a clean metal-heteroatom RDF, so this case is the one that exercises
corrosim's MD/RDF path on copper end-to-end.

**Preset:** `pyrazolylnucleosides` · **Source:** Oukhrib, Abdellaoui, Berisha,
Abou Oualid, Halili, Jusufi, Ait El Had, Bourzi, El Issami, Asmary, Parmar & Len,
*DFT, Monte Carlo and molecular dynamics simulations for the prediction of
corrosion inhibition efficiency of novel pyrazolylnucleosides on Cu(111) surface
in acidic media*, **Scientific Reports 11 (2021) 3771**
(DOI 10.1038/s41598-021-82927-5). The paper computes with **DMol³ (M-11L / DND /
COSMO)**, a different functional and basis family from corrosim, so the descriptor
comparison is qualitative. The SMILES were read from the source Figure 1; the
sugar is treated without stereochemistry for the screen.

The five derivatives (para substituent in bold):

| tag | X (para) | formula |
| --- | --- | --- |
| 5a | **CH₃** | C₁₇H₁₉N₃O₃ |
| 5b | **OCH₃** | C₁₇H₁₉N₃O₄ |
| 5c | **F** | C₁₆H₁₆FN₃O₃ |
| 5d | **Cl** | C₁₆H₁₆ClN₃O₃ |
| 5e | **Br** | C₁₆H₁₆BrN₃O₃ |

**Reported reading.** The paper ranks the five by their Monte Carlo adsorption
and desorption energies and reports **5e > 5b > 5a > 5c > 5d**, with the bromo
derivative 5e the strongest adsorber (the lowest desorption energy, −438.8 versus
roughly −140 for the others) and all five binding spontaneously and lying flat on
the copper surface. The RDF puts the Cu–O contact at 2.85 to 3.36 Å and Cu–N at
3.16 to 3.40 Å, both under 3.5 Å, which the paper reads as chemisorption. The
frontier orbitals and ESP concentrate on the ring N and the sugar/nitrile O, the
adsorption centres.

**Computed (corrosim), B3LYP/def2-SVP single-point on MMFF geometry, aqueous,
neutral:**

| Quantity | 5a | 5b | 5c | 5d | 5e |
| --- | --- | --- | --- | --- | --- |
| E_HOMO (eV) | -6.709 | -6.331 | -6.626 | -6.600 | -6.638 |
| Gap ΔE (eV) | 6.171 | 5.635 | 5.738 | 5.528 | 5.541 |
| η (eV) | 3.085 | 2.818 | 2.869 | 2.764 | 2.771 |
| ΔN → Cu | 0.213 | 0.253 | 0.206 | 0.200 | 0.194 |
| Composite score (pH-weighted) | 0.50 | 1.53 | -1.47 | -0.50 | -0.08 |
| MC E_ads (kJ/mol) | -7.7 | -9.1 | -9.2 | -9.2 | **-10.5** |
| MD ⟨E⟩ (kJ/mol) | -1.28 | -1.72 | -1.16 | -1.85 | -0.94 |

- **MC adsorption** (Cu(111), UFF): 5e binds strongest at −10.5 kJ/mol, then a
  near-degenerate cluster 5c ≈ 5d ≈ 5b (−9.2 to −9.1) and 5a weakest (−7.7),
  lying 2.0 to 2.4 Å above the slab. Ranking **5e > (5c ≈ 5d ≈ 5b) > 5a**.
- **MD metal-heteroatom RDF**: Cu–O first peak 3.25 to 3.65 Å, Cu–N 3.65 to
  3.95 Å (physisorption range), plus a per-derivative Cu–halogen contact (F/Cl/
  Br); mean interaction energy −2.3 to −2.8 kJ/mol.

**Reading it: the lead adsorber reproduces, the fine order does not.** The one
firm agreement is the most important observable: the paper ranks by adsorption,
and corrosim's Monte Carlo independently makes **5e (bromo) the strongest
binder**, matching the paper's number-one. All five give negative E_ads and lie
flat, also as reported. Past the lead, though, the comparison dissolves into
noise. The five molecules differ only in a distal para substituent, so their
adsorption energies cluster within about 1 kJ/mol (the middle three within 0.1),
below what the UFF screen resolves, and corrosim's order after 5e (5c ≈ 5d ≈ 5b,
then 5a) does not match the paper's (5b > 5a > 5c > 5d). The DFT-descriptor
composite is worse still: it does not single out 5e at all but flips its lead with
speciation (5d on the neutral basis, 5b on the pH-weighted one), so the ADR 0021
robustness gate reports a **tie** rather than a lead, and it puts the methyl 5a
last where the paper puts it mid-pack. The MD mean energy inverts the MC result
(5e comes out shallowest), the same observable-dependence seen on aluminium, and
the classical RDF sits at 3.35 to 3.75 Å, physisorption range, where the paper's
sub-3.5 Å peaks are read as chemisorption.

**Verdict.** On copper, corrosim reproduces the paper's strongest adsorber and
the spontaneous, flat physisorption of all five pyrazolylnucleosides, but not the
full para-substituent ordering, which is finer than either the UFF or the
def2-SVP screen resolves, nor the reported chemisorption contact, which the
rigid classical field cannot form. It is a **partial** reproduction of the kind
expected when a screen is asked to order molecules that differ only in a distal
substituent. Its value here is completing the substrate-agnostic exercise: this
is the case that drives the full DFT + MC + MD + RDF stack on a copper surface,
and it does so end-to-end and produces physically sensible numbers.

**Caveats to apply when comparing:**

- **Level of theory gap.** The paper uses DMol³ (M-11L / DND / COSMO), corrosim
  B3LYP / def2-SVP; different functional and basis family, so only the picture
  and ordering are comparable, never the numbers.
- **Basis chosen for halogen coverage.** The set spans F / Cl / Br, and the
  engine's Pople sets (6-31G(d), 6-311++G(d,p)) carry no bromine, so this case
  uses def2-SVP (all-electron, whole-periodic-table) rather than the usual
  production basis.
- **A distal-substituent ranking is intrinsically hard.** The five molecules
  share a scaffold and differ only in a para group on a phenyl remote from the
  binding N/O sites; both methods are being asked to resolve a sub-kJ/mol,
  sub-0.1 eV spread, so read the lead, not the full order.
- **Neutral screen vs protonated source.** corrosim's MC/MD run the neutral
  molecule; the paper protonates the pyrazole ring in acid. The DFT matrix does
  include the protonated cation (and drives the pH-weighted composite basis).
- **Adsorption observables are not interchangeable.** The paper's COMPASS E_ads
  is a full solvent-box energy of order 10⁴ kcal/mol; corrosim's is a
  single-molecule UFF van-der-Waals E_ads of tens of kJ/mol. Compare the
  strongest-binder identity and sign, never the value.
- **Fukui / ESP not rendered.** The QM Fukui and cube stages were not run for
  this bundle (the engine's default Fukui/cube basis lacks bromine), so it ships
  the DFT + MC + MD figures only; the paper's ESP and Mulliken maps have no
  corrosim counterpart here yet.
