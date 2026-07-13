# ADR 0025 — SCF robustness ladder + density-fitting memory guard

- Status: Accepted
- Date: 2026-07-13
- Relates to: ADR 0002 (production DFT level B3LYP/6-311++G(d,p) + ddCOSMO);
  the per-case `basis`/`xc` fields (the reproducibility half of the same work)

## Context

The production DFT level is intractable for large, compact, diffuse-sensitive
inhibitors, and the pipeline handled that badly on two fronts. First, the shared
single-point path kerneled the SCF and never checked convergence, so a diverged
SCF — exactly what the diffuse (`++`) basis provokes on a folded, oxygen-dense
molecule through near-linear-dependence — returned garbage frontier orbitals
straight into the descriptor matrix, silently. Second, the usual speed fix for a
large SCF, density fitting, builds a three-index `_cderi` tensor (~13 GB at the
production basis for a ~1000-orbital molecule) that, held in RAM, OOM-crashes the
small QM container.

Dropping to a non-diffuse basis per case (the `basis`/`xc` fields) made the cases
*reproducible*, but left the production level itself un-runnable for these
molecules. This ADR makes the production SCF converge when it can, fail loud when
it cannot, and lets density fitting be used without crashing the box.

## Decision

**One home for "converge this SCF or say so" (`engines.run_scf`).** Run the
default DIIS kernel; only if it does not converge, walk an escalation ladder —
level-shift + damping + a longer cycle budget, then a second-order (Newton)
restart seeded from the best density reached. If the whole ladder fails, raise
`SCFConvergenceError` naming the molecule and level of theory (fail loud). The
ladder fires *only* on non-convergence, so every single point that converges on
the first kernel is numerically untouched; it exists solely to rescue the SCFs
that today oscillate, diverge, or — worse — return unconverged numbers. Every
explicit-kernel call site (the descriptor single point, the frequency job, the
cube writers, and the Fukui SCF, which previously carried its own one-off Newton
fallback) routes through it, so the behaviour is uniform and the duplication is
gone.

**Density fitting is opt-in and off by default.** The RI approximation shifts the
descriptors, so it never touches the production numbers unless explicitly
requested (a `CaseStudy.density_fit` field, a `--density-fit` flag). It is a
deliberate per-case choice for a molecule whose exact-integral SCF is otherwise
intractable, not a global speed default.

**Size the SCF memory to the box and guard the `_cderi` spill.** Every mean field
gets a memory budget resolved from the host — an env override, else the smaller
of the cgroup limit and physical RAM scaled by a headroom fraction, else a
conservative default — so PySCF picks the correct in-core / out-of-core path
instead of assuming its ~4 GB default. When density fitting is on, the `_cderi`
tensor is sized (`naux x nao-pairs` doubles): kept in RAM only while it fits a
fraction of the budget, spilled to a disk scratch path beyond that, and refused
with a clear error past a hard ceiling — a diagnosable failure instead of an OOM
crash mid-run.

## Consequences

- A diverged production SCF now fails loud with a descriptive error rather than
  feeding silent garbage into the ranking; a multi-molecule batch stops at the
  offender (the chosen trade for never trusting an unconverged descriptor).
- The escalation only alters results for SCFs that did not converge on the
  default path, so the shipped descriptors are unchanged; verified by a
  no-regression single point at the production basis.
- Density fitting can be enabled on an intractable case without crashing the
  container; the `_cderi` spill needs the scratch directory to point at real
  disk, not a RAM-backed `/tmp` (set `PYSCF_TMPDIR` to the container's disk
  mount).
- The Fukui finite-difference anion SCF, historically "often ill-converged", now
  fails loud if it truly cannot converge rather than proceeding on an
  unconverged density; the default frozen-orbital Fukui uses only the neutral
  SCF and is unaffected.

## Upstream

The transferable kernel is domain-free numerics/quality engineering: *an
iterative numerical solver that can silently return a non-converged result
should verify convergence and, on failure, escalate through stabilisation aids
and then fail loud rather than hand back an unconverged answer as if it were
real*; and *an opt-in approximation that changes results stays off by default*;
and *a memory-heavy step should size its budget to the container (cgroup/RAM,
not a fixed default) and spill to disk or refuse with a clear error rather than
OOM-crash*. Candidate against `base/core/quality.md`; recorded in
`docs/engineering-know-how.md` and to be filed in the end-of-session upstream
audit.
