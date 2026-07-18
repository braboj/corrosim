# ADR 0031 — Molecular dipole reported for neutral species only

- Status: Accepted
- Date: 2026-07-18
- Relates to: ADR 0002 (production DFT level, the density the dipole is read
  from); ADR 0032 (the density checkpoint the backfill persisted alongside)

## Context

A molecular dipole-moment descriptor (`dipole_debye`, in Debye) was added to the
descriptor matrix, read for free off the already-converged SCF density in both
the xTB and PySCF engines. It quantifies charge separation — a physisorption-
relevant reactivity signal that the frontier-orbital descriptors do not capture.

The dipole magnitude is only a molecular property for a net-neutral charge
distribution. For a charged species the dipole vector depends on the choice of
coordinate origin: shift the origin by **r** and the dipole changes by
*q*·**r**, so for a non-zero net charge *q* the reported number is an artifact of
where the molecule happens to sit in its coordinate frame, not a physical
observable. The pipeline carries a protonated cation row for every inhibitor
alongside the neutral, so a naive "dipole for every row" would emit these
origin-dependent numbers as if they were descriptors. The tell surfaced in the
data: the isorhamnetin cation reported ~16 D, a value with no physical meaning.

## Decision

**Report the dipole for neutral molecules only; leave the cation rows blank.**
The engines still compute the dipole for whatever density they converge, but the
descriptor is surfaced (CSV column, JSON field, the `Dipole (D)` report-table
row, `DESCRIPTOR_META`) only where the net charge is zero. A protonated-cation
row carries an **empty** dipole cell — not `0`, not the origin-dependent value —
because the honest statement for an ion is "not a well-defined molecular
property here", and any concrete number would be a coordinate artifact read as a
descriptor.

The dipole is a reported descriptor only; it is **not** an input to the
adsorption ranking score. Adding the column left every case's ranking order and
scores byte-identical (verified across all six case studies).

## Consequences

- The descriptor table shows a populated `Dipole (D)` value on each neutral row
  (gas and aqueous, the ddCOSMO value larger as solvent polarization enhances
  the moment) and a blank on each protonated row — a deliberate, documented gap,
  not missing data.
- Because the descriptor is neutral-only, the density checkpoints that the
  backfill persisted (ADR 0032) exist for neutral species only; there is no
  cation wavefunction on disk, matching the neutral-only reporting rule.
- Anyone extending the ranking must not fold `dipole_debye` in without handling
  the blank cation cells; today the score ignores it, so the blanks are inert.

## Upstream

The transferable, domain-free rule is a data-quality one: *a derived quantity
that is only well-defined under a condition (here, origin-independence, which
holds only at zero net charge) should be reported only where the condition holds
and left empty — not zero, not a condition-violating value — everywhere else; an
empty cell states "undefined here" honestly, whereas a fabricated number is a
silent artifact downstream consumers cannot distinguish from a real measurement.*
A candidate for `base/core/quality.md` (the same fail-honest-not-silent family as
ADR 0025's convergence guard); to be judged against the existing quality-doc
issues in the end-of-session upstream audit rather than filed blind.
