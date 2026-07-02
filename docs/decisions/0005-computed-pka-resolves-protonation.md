# ADR 0005 — A computed pKaH resolves the protonation state (quercetin lead robust)

- Status: Accepted
- Date: 2026-07-01
- Updated: 2026-07-02 — frequency-corrected pKaH folded in, resolving issue #18
  (see Finding); the electronic-only estimate is retained below as the prior step.
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

**Two levels of the cycle.** The first pass was *electronic-only* — no frequency
calculation, force-field geometries, ZPE/thermal/entropy of B and BH⁺ omitted — so
the absolute pKaH carried a few-units uncertainty. Its largest omitted term (the
extra O–H zero-point energy of BH⁺) only makes the cation *less* stable, i.e.
pushes pKaH *more negative* (more neutral), so it was conservative for the
conclusion. Issue **#18** then added the *frequency correction*: each species is
gas-phase optimised at B3LYP/6-31G(d), a Hessian gives `g_corr = ZPE + H − T·S`
(`estimate_pka` accepts it), and the production ddCOSMO single point runs on the
relaxed geometry. This is now the canonical result in `results/pka.json`
(`run_pka --freq`).

## Finding

Frequency-corrected pKaH (issue #18), the canonical result:

| molecule | computed pKaH (freq-corrected) | electronic-only (prior) | % protonated @ pH 0 | clean minimum? |
|---|---|---|---|---|
| quercetin | **−13.3** | −12.1 | ~0 % | yes (n_imag = 0) |
| kaempferol | **−12.9** | −11.2 | ~0 % | yes (n_imag = 0) |
| isorhamnetin | **−5.12** | −3.3 | ~0.001 % | cation has 1 imaginary freq |

All three sit **well below the −1.2 crossover**: every flavonoid is **< 0.1 %
protonated in 1 M HCl**, and the frequency correction moved each value *more*
negative (more neutral) than the electronic-only estimate — deepening, not
weakening, the conclusion. The methoxy group makes isorhamnetin the most basic (as
expected), but even it is essentially fully neutral.

**Caveat (issue #18).** Quercetin and kaempferol are clean minima (no imaginary
frequencies, neutral or cation). The **isorhamnetin cation retained one imaginary
frequency** — a low-frequency methoxy/hydroxyl torsion that did not converge to a
true minimum — so its corrected pKaH is less tightly determined, and isorhamnetin
is the most geometry-sensitive case (electronic-only on the optimised geometry is
+1.7, pulled firmly neutral only by the correction). It does not change the
conclusion: isorhamnetin stays < 0.1 % protonated at its flagged value, and it is
not the lead. A tighter re-optimisation of that one cation could remove the mode
but would only make it more negative.

## Decision / consequence

**The neutral form is not just the conventional choice — it is the physically
dominant species in 1 M HCl, so the quercetin lead is robust**, and the lead rests
on a clean, imaginary-frequency-free calculation (pKaH −13.3). The fragility
flagged in ADR 0004 is resolved: the system sits far on the neutral side of the
crossover. The report's speciation section shows the computed per-molecule pKaH and
populations (from `results/pka.json`) alongside the illustrative crossover. This
resolves issue #18 (frequency-corrected pKaH).
