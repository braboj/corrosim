# ADR 0014 — Pipeline-stage module shape (orchestrator + state objects)

- Status: Accepted
- Date: 2026-07-05
- Relates: ADR 0012 (API contract and readability standard)

## Context

The pipeline-stage modules are numerical routines with the same skeleton: build
a metal slab, seed some evolving state, iterate a stochastic loop that mutates
several interdependent variables together, then assemble a result dataclass.
`adsorption/mc.py` (Metropolis / annealed adsorption search) and
`adsorption/md.py` (Brownian MD, metal–donor RDF) are the two instances, and
their per-step helpers were deliberately kept parallel (`_propose_pose` /
`_confine_pose` mirror `_langevin_step` / `_confine_z`).

Decomposing `run_mc` further (into `_build_substrate`, `_init_search`,
`_metropolis_update`, `_build_result`) surfaced two object-oriented smells the
project's `oop.md` names directly:

- the three `_build_*` / `_init_*` functions are **named constructors in
  function form** — construction that belongs on the type (Factory Method);
- `_metropolis_update(search, …)` mutated the `_Search` state from a
  non-member — the classic **anemic domain model** (`oop.md`: "encapsulate
  state, expose behaviour").

Because the two modules must stay structurally parallel, how much OOP to apply
is a decision about the shape of *every* stage module, not a local tidy — hence
this ADR.

## Decision

Pipeline-stage modules follow one shape:

1. **A free `run_*` function is the public entry point.** It stays a function
   (the drivers in `runs/` call it), not a method on a class — a class whose
   only public method is `.run()` is a function in disguise.
2. **Construction lives on the type as factory classmethods** —
   `_Substrate.build(...)`, `_Search.seed(...)` / `_RdfAccumulator.for_donors(...)`,
   and `MCResult.from_search(...)` / `MDResult.from_run(...)`.
3. **Mutation of a stage's evolving state is a method on the object that owns
   it** — `_Search.accept(...)`, `_RdfAccumulator.record(...)`. No external
   function reaches into that state.
4. **Stateless numerics stay free functions** — `_propose_pose`,
   `_confine_pose`, `_anneal_schedule`, `_langevin_step`, `_confine_z`,
   `_closest_contact_hist`, `_first_peak`, `_mean_energy`. They belong to no
   object's state, so making them methods would couple them to fields they do
   not use.
5. **Every such refactor is behaviour-preserving and gated on a seeded golden
   hash** — a full run of `run_mc` / `run_md` (best pose or RDF + energy trace)
   must be byte-identical before and after.

## Alternatives considered

- **Full method object** — a `_MonteCarloSearch` class holding every local as a
  field with a single `.run()`. Rejected for now: it maximises encapsulation
  but reads as a function in disguise and would force `run_md` to follow into
  the same heavier shape. Revisit only if the per-step state threading grows.
- **Status quo (all free functions)** — rejected: it leaves the anemic-model
  smell (state mutated by non-members) and keeps constructors as functions,
  the two things `oop.md` calls out.
- **Swappable energy model now** — the loop's `uff_vdw_energy` /
  `uff_vdw_forces` call with its fixed parameter bundle is a natural Strategy
  seam (an `EnergyModel.energy(pos)`), and it is the one OOP move that buys
  extensibility rather than tidiness. Deferred to the chemisorption `E_ads`
  work (issue #40) rather than introduced speculatively here.

## Consequences

- `run_mc` / `run_md` read as high-level assembly of named steps; the state
  objects own their own construction and mutation.
- Both stage modules share the shape, and a new stage has a template to follow.
- `run_mc` cognitive complexity drops to 1; the behaviour lives in small,
  independently testable methods (`accept`, `record`, `from_*`).
- The seeded golden hash is the standing safety net for these
  behaviour-preserving reshuffles; a stage refactor that changes any golden is
  a bug, not a style choice.
