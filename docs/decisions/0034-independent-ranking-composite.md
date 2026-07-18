# ADR 0034 — Rank on independent axes (gap + ΔN + dipole), not the gap thrice

- Status: Accepted
- Date: 2026-07-18
- Relates to: ADR 0021 (canonical basis + robustness/tie verdict, which the
  score margins feed); the molecular dipole descriptor (ADR 0031)

## Context

`rank_inhibitors` built its composite screening score as the mean of three
z-scored components — the HOMO-LUMO gap, the chemical hardness η, and the
softness σ — and the code, the report, and `docs/pipeline.md` all described them
as three equally-weighted, independent descriptors.

They are not independent. By construction in `compute_descriptors`,
`η = (IP − EA)/2 = gap/2` and `σ = 1/η = 2/gap`. A z-score is invariant under
positive scaling, and the pH blend is linear (`η_blend = gap_blend/2` still
holds exactly), so `zscore(η, invert=True)` is numerically identical to
`zscore(gap, invert=True)` in every basis. The composite was therefore really
`(2·z(−gap) + z(2/gap)) / 3`: the gap carried two-thirds of the weight, hardness
added nothing, and the reciprocal-softness term gave a small-gap molecule extreme
nonlinear leverage. All three components were one degree of freedom — the gap —
while the report claimed three. The mis-weighting distorted exactly the score
margins that ADR 0021's robust-lead/tie verdict and the headline sentence rest
on.

## Decision

**Score on descriptors that measure genuinely different physics: the HOMO-LUMO
gap, the Lukovits ΔN, and the molecular dipole — z-scored and equally averaged.**

- **gap** (smaller = better): electronic softness / frontier polarisability.
  Settled direction.
- **ΔN** (larger = better): the fraction of electrons donated to *this* metal,
  computed from the molecule's electronegativity and the metal work function —
  independent of the gap (the average of the frontier levels, and the substrate,
  not their difference). Settled direction.
- **dipole** (larger = better): electrostatic anchoring to the charged surface.
  Its *correlation direction* with inhibition efficiency is genuinely disputed
  in the QSAR literature (higher-μ anchoring vs lower-μ easier desolvation), and
  the physisorption model carries no explicit electrostatics. It is kept anyway,
  as an equally-weighted axis that only tips genuine near-ties, because
  empirically it reproduces the two experimentally-validated leads (arghel →
  quercetin, tetrazoles → the mercapto compound) that gap + ΔN alone miss;
  experiment outranks computational-paper comparisons as ground truth. The
  dipole is dropped when a frame carries no `dipole_debye` (an older matrix or a
  minimal fixture), leaving a gap + ΔN composite. It is neutral-only (ADR 0031),
  so the pH-weighted blend keeps the neutral value.

Hardness and softness are dropped from the score (still tabulated as
descriptors). The `score_note`, the headline sentence, and `docs/pipeline.md`
are corrected to describe the two settled axes plus the caveated dipole.

## Consequences

- The bug is fixed: the score is now three real degrees of freedom.
- The dependent `cases/*/report/` bundles were regenerated and `docs/validation.md`
  re-checked. The two experimentally-validated leads hold (arghel quercetin,
  tetrazoles mercapto). Three paper-comparison outcomes change, honestly recorded
  in validation.md: pyrazolo's near-degenerate isomers now lead with the amide
  (dipole-tipped) rather than the paper's ester; tmp-smx now crowns SMX rather
  than reporting the tie that had mirrored the paper's synergy; the tetrazole
  composite transposes its near-degenerate middle pair (ATZ/PTZ) while MC/MD
  still give the paper order. The lead ranking is DFT-based, unrelated to the
  MD/adsorption changes of ADR 0032/…; only the electronic score moved.

## Upstream

A composite score's components must be genuinely independent variables, not
algebraic restatements of one another; averaging correlated components silently
re-weights the shared axis while the interface claims independence. Filed as a
review-heuristic candidate for `templates/base/core/review.md`
(composite-metric independence check) — issue: none yet.
