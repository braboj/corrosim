# ADR 0009 — Monte Carlo and molecular dynamics run on the force-field geometry

- Status: Accepted
- Date: 2026-07-02

## Context

The pipeline turns a name/SMILES into a cheap force-field (FF) geometry (RDKit
ETKDG + MMFF/UFF; `build_molecule`, fixed `seed=42`). Stage 1 then DFT-optimises
that structure and reads every reactivity descriptor off the **DFT-optimised**
geometry (ADR 0002). Stages 2–3 do **not** reuse the DFT structure: `run_mc` and
`run_md` call `build_molecule(name)` again and run on the **FF** geometry.

So the same molecule enters the pipeline with two internal geometries at
different stages. Documenting the pipeline (issue #37) surfaced this as an
apparent inconsistency; this ADR records that it is a deliberate choice, and why.
Two facts frame it: the DFT-optimised geometry is currently not persisted (issue
#36), so MC/MD could not cheaply consume it even if we wanted to; and MC/MD here
are *rigid-body* van-der-Waals models.

## Decision

Monte Carlo (Stage 2) and molecular dynamics (Stage 3) run on the **force-field
geometry**, rebuilt from SMILES with a fixed seed. Stage-1 reactivity descriptors
continue to use the **DFT-optimised geometry**. The geometry each stage consumes
is stated explicitly in `docs/pipeline.md` (an Input row on the MC and MD stages
plus a shared geometry note).

## Rationale

- MC/MD model adsorption as a rigid molecule sampled against a van-der-Waals /
  UFF stickiness field over a metal slab. The observables — the adsorption pose,
  E_ads (kJ/mol), and the metal–O RDF first peak (Å) — are governed by the
  molecule's overall shape and its heteroatom positions, not by sub-ångström
  refinement of the internal conformer, so a DFT-accurate internal geometry
  changes them by less than the model's own noise.
- The FF geometry is deterministic (fixed `seed=42`) and cheap, and needs no QM
  container — keeping Stages 2–3 fast and venv-only, consistent with the
  QM-light testing model (CLAUDE.md §3).
- The expensive DFT geometry is reserved for the descriptors that genuinely
  depend on it (frontier-orbital energies and the derived global/local
  descriptors), where geometry sensitivity is real and is itself checked
  (`compare_geometry`, `docs/validation.md`).

## Alternatives considered

- **Feed the DFT-optimised geometry into MC/MD** for full cross-stage geometric
  coherence. Blocked today because that geometry is discarded (#36); and even
  once persisted, the expected change to the pose/RDF is within the model's own
  noise. Kept as an optional follow-on to #36 rather than a requirement.
- **Leave the choice implicit.** Rejected: it reads as an unintended
  inconsistency and invites "bug" reports — which is how #37 arose.

## Consequences

- `docs/pipeline.md` states the geometry contract on the MC and MD stages, so a
  reader no longer has to infer it from the source.
- If #36 lands, whether MC/MD should consume the persisted DFT geometry becomes a
  documented, optional decision — not a silent behaviour change.
