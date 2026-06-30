# ADR 0004 — Quantitative pH-speciation of the protonation state

- Status: Accepted
- Date: 2026-06-30
- Extends: ADR 0003 (medium → protonation, selection layer)

## Context

ADR 0003 coupled the `medium` label to protonation by *selection* (acidic medium
→ show the cation alongside the neutral headline) and explicitly deferred a
*quantitative* speciation. This ADR adds that quantitative layer
(`corrosim/speciation.py`): from the medium pH and the inhibitor's conjugate-acid
pKa it computes the neutral/protonated **population** (Henderson–Hasselbalch) and
the **population-weighted descriptors**, so a ranking can reflect the actual
species mix rather than a binary form choice.

    f_protonated = 1 / (1 + 10**(pH − pKaH))

## The pKaH estimate (the key uncertainty)

The most basic site of these flavonoids is the **4-oxo carbonyl**, a *very weak*
base. Reported carbonyl-protonation pKaH values for flavones/chromones (from
Hammett-acidity studies) cluster around **−1 to −2**. We adopt
`FLAVONOID_CARBONYL_PKAH = −1.5` as a representative **estimate** with ~±1
uncertainty. It is a code constant, overridable per study — **not** a measured,
molecule-specific value, and it is exposed as such in the report.

## Decision & finding

We compute and **report the speciation with its sensitivity band**, and keep the
**neutral form as the headline ranking** (ADR 0003) because at the estimated pKaH
the neutral form dominates:

- At pH ≈ 0 (1 M HCl) with pKaH ≈ −1.5, the inhibitor is **~97% neutral / ~3%
  protonated** — so the neutral descriptors are the right headline basis, and the
  lead is **quercetin**.

But the gap/softness composite lead is **fragile**:

| pKaH | f_protonated @ pH 0 | composite lead |
|---|---|---|
| ≤ −1.5 | ≤ 3 % | **quercetin** |
| ≥ −1.0 | ≥ 9 % | **isorhamnetin** |

The lead **crosses over at only ~5 % protonation** (pKaH ≈ −1.3), and the pKaH ± 1
uncertainty band (≈ 0.3 %–24 % protonated) **straddles that crossover**. So the
quercetin lead holds *only if* the carbonyl is a sufficiently weak base
(pKaH ≲ −1.3); a modestly stronger base would favour isorhamnetin.

The honest conclusion is therefore **quercetin, contingent on the protonation pKa**
— and the protonation pKa is the dominant uncertainty for the acidic case, more
than geometry or level of theory. The report states this explicitly rather than
presenting a falsely confident single lead.

## Consequences

- `report.html` gains a "Speciation in {medium}" section: the population split,
  the pH-weighted descriptor table, and the lead-crossover sensitivity.
- A measured site pKaH (experiment, or a ΔG of protonation from the existing
  neutral/cation DFT energies via a thermodynamic cycle) would sharpen this — a
  natural next step, since it would pin which side of the crossover we are on.
- Do not present the pH-weighted lead as definitive without a sourced pKaH; the
  crossover sensitivity above must travel with any such claim.
