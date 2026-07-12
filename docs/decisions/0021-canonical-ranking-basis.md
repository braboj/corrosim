# ADR 0021 — one declared canonical basis for the ranking, the rest a robustness-gated sensitivity ensemble

- Status: Accepted
- Date: 2026-07-12
- Relates to: ADR 0009 (force-field geometry for the adsorption stages); ADR 0016
  (report render seam); ADR 0010 (AI-authored report narrative); ADR 0020
  (validation status vocabulary)

## Context

The pipeline reduces a set of global reactivity descriptors (frontier gap,
hardness, softness, charge transfer) to one composite z-score that orders the
candidates and names a lead. But every descriptor can be evaluated on more than
one **basis** — a cross product of three axes:

- **geometry model** — a fast force-field single-point vs a DFT-relaxed geometry;
- **speciation state** — the neutral molecule, the protonated cation, or a
  pH-weighted population of both;
- **solvation phase** — gas vs an implicit-solvent field.

The report today applies the scoring function independently on several of these
bases, in separate sections. Because each section scores its own basis, they can
— and in practice do — name **different leads within one document**. Two further
problems compound it:

- The *canonical* basis is chosen **implicitly**: it is whichever descriptor file
  the driver's default output path resolves to, an artefact of wiring rather than
  a declared decision. Nothing states which basis is authoritative.
- The headline asserts a single #1 even when the candidates are separated by less
  than the method's own resolution. When the lead **flips** as the basis changes
  (e.g. relaxing the geometry reorders the top two), the report still crowns one
  winner, claiming precision the method does not have.

This is a product-shape gap, not a property of any one study: any screening run
that evaluates a scoring function over multiple computational bases faces it.

## Decision

One principle — *rank on a single declared basis; treat every other computation
as a perturbation around it; never assert an ordering finer than the estimator's
resolution* — in three rules.

1. **One declared canonical basis.** The composite ranking is computed on exactly
   one `(geometry, speciation, phase)` basis, and that basis is an **explicit,
   declared property of the run** — surfaced next to the headline — not the
   incidental result of a default file path. Defaults:
   - *Geometry*: the best geometry the run computes — the DFT-relaxed one when it
     exists, the force-field single-point otherwise.
   - *Speciation*: the medium-appropriate state — the pH-weighted population when
     the medium is ionising, degenerating to the neutral form when it dominates.
   - *Phase*: the solvated (implicit-solvent) descriptors when a medium is
     specified; gas is a reference column only.

2. **Every other basis is a sensitivity panel, never a second headline.**
   Force-field-vs-relaxed, neutral-vs-protonated-vs-blend, and gas-vs-solvent are
   rendered as inputs to, and perturbations around, the canonical ranking, and
   are labelled as such. A section that is not the canonical basis does not crown
   its own "best".

3. **The declared lead is robustness-gated.** Let the method resolution `δ` be the
   spread of the score (or of the top-to-runner-up margin) induced by moving the
   ranking across the sensitivity ensemble. The report asserts a single lead only
   when that margin exceeds `δ`. When it does not, the report declares a **tie
   within method resolution** and states only the conclusions that survive the
   ensemble (e.g. the robustly weakest candidate). The lead always carries this
   qualification; a bare "#1 wins" is never emitted.

## Alternatives considered

- **Keep the implicit force-field/neutral headline with the other bases as extra
  scored tables (status quo)** — rejected: the authoritative basis is chosen by
  wiring accident, the secondary tables silently contradict the headline, and
  nothing flags a lead that does not survive a change of basis.
- **Always rank on the fast force-field geometry for cross-run comparability** —
  rejected: candidates from different runs are never pooled into one ranking, so
  cross-run comparability is not a product goal; this permanently headlines the
  less-accurate geometry whenever a better one has been computed.
- **Require the relaxed geometry before any ranking is shown** — rejected: the
  relaxed geometry is an expensive opt-in, and forcing it would block the fast
  screen that is the product's primary mode. Best-available geometry plus the
  robustness gate delivers the accuracy where it exists without blocking the quick
  path.
- **Collapse every basis into one blended number and hide the components** —
  rejected: the components are exactly what a reviewer needs to judge a screening
  claim. The fix is to declare which basis is canonical, not to hide the rest.

## Consequences

- The scoring function stays a pure, basis-agnostic transform; the **selection**
  of the canonical basis moves up into the driver/report seam (ADR 0016) and
  becomes an explicit, testable choice rather than a default path.
- The report gains a compact robustness/sensitivity subsection and drops the
  competing winner marks from the non-canonical tables.
- Implemented in issue #202: a `report/ranking.py` module owns the basis
  selection + robustness gate; the HTML and Word renderers score the headline on
  the canonical basis and render a lead-by-basis panel; the bundled
  `ranking.csv` follows the canonical basis. All three case bundles were
  re-rendered — the pyrazolo lead now reads as a tie (its top two flip with
  geometry), while the arghel lead is robust across all four bases.

## Upstream

None to `solid-ai-templates` — that submodule governs code, testing, and workflow
conventions, not generated-document structure or scientific-computing method
policy (the same boundary recorded for ADR 0020). The transferable kernel — *rank
on one declared basis, treat alternative computations as a sensitivity ensemble,
and never report an ordering finer than the estimator's resolution* — is a
reusable scientific-computing pattern; its home is `docs/engineering-know-how.md`,
not the upstream templates.
