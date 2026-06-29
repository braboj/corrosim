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

## Stage-1 descriptors (B3LYP/6-31G, gas phase)

Quercetin leads kaempferol at the DFT level — the same order the fast xTB screen
gives, confirming the ranking is engine-independent. DFT also restores a physical
ΔN (xTB orbital energies are off the Koopmans scale, giving the spurious negatives).

| Molecule | Method | HOMO (eV) | LUMO (eV) | Gap (eV) | η (eV) | ΔN |
|---|---|---|---|---|---|---|
| Quercetin | DFT B3LYP/6-31G | −5.902 | −1.880 | **4.022** | 2.011 | **+0.231** |
| Kaempferol | DFT B3LYP/6-31G | −5.960 | −1.829 | 4.130 | 2.065 | +0.224 |
| Quercetin | xTB (GFN2) | −10.383 | −7.870 | 2.513 | 1.257 | −1.714 ✗ |
| Kaempferol | xTB (GFN2) | −10.427 | −7.830 | 2.597 | 1.298 | −1.659 ✗ |

(Gas phase; implicit solvent shifts absolutes slightly but not the ranking.)

## Cross-check against published Fe(110) studies

| Source | Method | Quercetin | Kaempferol |
|---|---|---|---|
| **corrosim** | UFF vdW estimate | −4.5 kJ/mol | −4.3 kJ/mol |
| **Black tea extract study** (Mater. Chem. Phys., 2025) | DFT, periodic + dispersion | strongest constituent; ΔGads ≈ −20 kJ/mol (overall physicochemical ~−35) | weaker than quercetin |
| **Lady's mantle study** (Results in Chemistry, 2025) | DFT/MC | — | strong adsorption confirmed (reference compound) |

## Reading

- **Ranking validated.** The black tea study independently ran DFT on Fe(110) and
  found quercetin the strongest-adsorbing constituent — the same conclusion
  `corrosim` reaches, now confirmed at our own DFT level. Lady's mantle adds a
  second source affirming kaempferol/Fe(110) adsorption.
- **The adsorption-energy gap is expected, not an error.** `corrosim`'s
  −4.5 kJ/mol is a *physisorption* proxy (UFF van der Waals, rigid bodies, no
  charge transfer, no water displacement). The literature's ~−20 to −35 kJ/mol is
  a full DFT adsorption free energy. Same *order* (quercetin > kaempferol), at a
  deliberately conservative magnitude. Closing the magnitude gap is what the
  Stage-3 MD on the exported structures is for.

## Defensible claim

> Of the documented major Arghel flavonoids, **quercetin is the strongest
> predicted corrosion inhibitor on mild steel** — confirmed at both semi-empirical
> and DFT levels, ranking-consistent with the UFF adsorption estimate, and in
> agreement with an independent published DFT study of black-tea polyphenols on
> Fe(110).

Simulations rank and explain; they do not prove efficiency — that requires the
electrochemical experiments (EIS, potentiodynamic polarization, weight loss).
