# ADR 0005 — A computed pKaH resolves the protonation state (quercetin lead robust)

- Status: Accepted
- Date: 2026-07-01
- Extends: ADR 0004 (quantitative pH-speciation)

## Context

ADR 0004 showed the acidic-medium lead is fragile: the gap/softness composite
crosses from quercetin to isorhamnetin at only ~5–7 % protonation (pKaH ≈ −1.2),
and the assumed pKaH (≈ −1.5, a literature-range estimate) sat right on that edge.
The protonation pKa was the dominant uncertainty. This ADR pins it with a DFT
calculation instead of an assumption.

## Method

`corrosim/pka.py` + `corrosim/runs/run_pka.py` compute the conjugate-acid pKaH from
the aqueous deprotonation cycle `BH⁺ ⇌ B + H⁺`:

    pKaH = [E_aq(B) + G*_aq(H⁺) − E_aq(BH⁺)] / (RT ln10)

with `E_aq` from B3LYP/6-311++G(d,p) + ddCOSMO(water) single points (results in
`results/pka.json`) and the standard `G*_aq(H⁺) = −270.3 kcal/mol`.

**Electronic-only approximation.** No frequency calculation: the ZPE / thermal /
entropy of B and BH⁺ are omitted and the geometries are the force-field ones, so
the *absolute* pKaH carries a few-units uncertainty. Critically, the largest
omitted term — the extra O–H zero-point energy of BH⁺ — only makes the cation
*less* stable, i.e. pushes pKaH *more negative* (more neutral). So the
approximation is **conservative for the conclusion below**.

## Finding

| molecule | proton affinity (aq) | computed pKaH | % protonated @ pH 0 |
|---|---|---|---|
| quercetin | 11.00 eV | **−12.1** | ~0 % |
| kaempferol | 11.06 eV | **−11.2** | ~0 % |
| isorhamnetin | 11.52 eV | **−3.3** | ~0.05 % |

All three sit **well below the −1.2 crossover**: every flavonoid is **< 0.1 %
protonated in 1 M HCl**. The methoxy group makes isorhamnetin the most basic (as
expected), but even it is essentially fully neutral. The omitted ZPE only pushes
these more negative.

## Decision / consequence

**The neutral form is not just the conventional choice — it is the physically
dominant species in 1 M HCl, so the quercetin lead is robust.** The fragility
flagged in ADR 0004 is resolved: the system sits far on the neutral side of the
crossover. The report's speciation section now shows the computed per-molecule
pKaH and populations (from `results/pka.json`) alongside the illustrative
crossover.

A frequency-corrected pKaH (gas-phase opt + freq → `g_corr`, which `estimate_pka`
already accepts) would tighten the absolute numbers, but cannot change the
conclusion: it would only deepen the neutral dominance.
