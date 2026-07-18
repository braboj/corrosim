# ADR 0032 — Persist the converged SCF density (checkpoint capability)

- Status: Accepted
- Date: 2026-07-18
- Relates to: ADR 0002 (the production SCF whose density is persisted); ADR 0031
  (the neutral-only dipole whose backfill motivated this)

## Context

The DFT single point converges a wavefunction and then reads scalars off it
(energy, frontier orbitals, and now the dipole). Historically `run_pyscf`
discarded that converged density the moment it returned its `EngineResult`. So
every density-derived property is paid for with its own full SCF: the dipole
backfill re-ran the SCF for each molecule purely to read one number, and a later
question about the same molecule and level (an ESP surface, a Fukui map, a `.cube`)
would re-run the identical, expensive SCF again from scratch.

The diffuse production basis makes these SCFs the dominant cost in the pipeline
(minutes to hours per molecule), so repeating one to extract a second cheap
density-derived quantity is pure waste.

## Decision

**Give `run_pyscf` an optional `chkfile` parameter that persists the converged
wavefunction.** When a path is passed, the mean field's native PySCF checkpoint
(MO coefficients + occupations) is written on convergence; a later
density-derived property reloads it and evaluates in seconds instead of
re-running the SCF. The parameter defaults to `None`, so every existing caller is
untouched and cheap callers pay nothing — it is opt-in.

The checkpoint is a **regenerable** artifact, so it lives with the other
regenerable volumetric data under gitignored `cubes/chk/`, named
`<case>/<molecule>_<matrix>_<phase>.chk`. It is a local reuse cache, never a
tracked deliverable.

One engine-specific subtlety is captured in the code comment: under a solvent the
mean field is a ddCOSMO wrapper, and the checkpoint attribute must be set on the
object that `run_scf` actually kernels, before the kernel runs, or the wrapper
silently swallows it and no file appears.

## Consequences

- The neutral-only dipole backfill persisted 36 densities (every neutral, gas +
  ddCOSMO, across all five non-arghel cases and both the FF and DFT-optimized
  geometry matrices), each now reusable for ESP / Fukui / cube regeneration at
  the same level without re-converging the SCF.
- Correctness was validated by a round-trip on a small case before trusting a
  long batch: gas and ddCOSMO checkpoints both reload and reproduce the dipole
  exactly, confirming the wrapper layer does not corrupt the persisted state.
- `cubes/chk/` grows with each checkpointed run; because it is gitignored and
  regenerable, it can be deleted freely to reclaim disk with no loss of a
  tracked result.

## Upstream

The transferable pattern is domain-free: *a costly computation produces a rich
internal state from which callers usually keep one scalar; discarding the state
forces a full re-run for the next derived quantity, so persist the reusable state
to a checkpoint (opt-in, default off; stored with regenerable artifacts) once you
are already paying for the computation.* Recorded in
`docs/engineering-know-how.md` ("Persist the expensive intermediate, not just its
derived scalar"), together with the sibling text-append pattern the backfill used
to inject the column without churning the serialized matrices. Filed upstream
against `base/data` as `solid-ai-templates#828`.
