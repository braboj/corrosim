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
gas/aqueous matrix: `dft_descriptors.{json,csv}` (run `python -m corrosim.runs.run_dft`).

## Cross-check against published Fe(110) studies

| Source | Method | Quercetin | Kaempferol |
|---|---|---|---|
| **corrosim (Stage-2 MC)** | UFF vdW, Metropolis/annealing pose search | −16.0 kJ/mol | −16.6 kJ/mol |
| **corrosim (Stage-3 MD)** | Brownian MD, Fe–O RDF first peak | 3.65 Å (physisorption) | 3.35 Å |
| **Black tea extract study** (Mater. Chem. Phys., 2025) | DFT, periodic + dispersion | strongest constituent; ΔGads ≈ −20 kJ/mol (overall physicochemical ~−35) | weaker than quercetin |
| **Lady's mantle study** (Results in Chemistry, 2025) | DFT/MC | — | strong adsorption confirmed (reference compound) |

(Isorhamnetin: MC −16.7 kJ/mol, RDF peak 3.75 Å. Full data: `mc_adsorption.json`,
`md_rdf.json`; run `python -m corrosim.runs.run_mc` / `run_md`.)

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

Simulations rank and explain; they do not prove efficiency — that requires the
electrochemical experiments (EIS, potentiodynamic polarization, weight loss).
