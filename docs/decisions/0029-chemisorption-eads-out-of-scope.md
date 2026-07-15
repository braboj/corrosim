# ADR 0029 — chemisorption E_ads is out of scope for a $0 setup

- Status: Accepted
- Date: 2026-07-15
- Relates to: ADR 0001 (reject cluster-xTB for the adsorption estimate); issue
  #40 (closed won't-do)

## Context

The adsorption stages model binding with a rigid-body **UFF van-der-Waals**
field: bounded, and validated qualitatively across Fe/Cu/Al for *ranking* and
the *physisorption distance* (the metal–O RDF first peak), but not a
quantitative, bond-capable **chemisorption E_ads**. A long-standing enhancement
(#40) proposed closing that gap through a free/GPL toolchain — either a periodic
DFT slab (Quantum ESPRESSO) or a classical LAMMPS hand-off. The
`LAMMPS_HANDOFF_NOTE` in `adsorption.py` already documents the classical recipe,
and ADR 0001 rejected the cheap cluster-xTB shortcut on physics grounds.

A feasibility pass on the periodic-DFT route sized the actual compute:

- A flat flavonoid (~31–35 atoms) needs a wide lateral supercell to decouple it
  from its periodic image, giving a ~130–200-atom **spin-polarized** Fe(110)
  slab per structure.
- Each E_ads needs relaxed complex + clean-slab + isolated-molecule references,
  each a magnetic geometry relaxation (dozens of ionic steps × a full
  spin-polarized SCF), vdW-corrected. That is **~1–2 weeks on an HPC cluster**
  and **weeks-to-months on a single workstation** — per case.
- There is no cheaper "periodic surface instead of a slab" route: in a
  plane-wave code the laterally-periodic vacuum slab *is* the periodic surface.
  A genuinely semi-infinite surface needs Green's-function / KKR machinery that
  removes only the slab-thickness dimension (not the dominant lateral-cell ×
  magnetic-SCF cost) and lives outside the ASE/QE ecosystem.

This collides head-on with the project's defining constraints: **free software,
$0 budget, no HPC or deploy target, runs in Docker/venv on a workstation.**

## Decision

**Chemisorption E_ads is a deliberate boundary of the tool, not a backlog
item.** The package ships the bounded UFF physisorption surrogate (MC pose + MD
metal–O RDF) as its adsorption answer, and states its limit honestly: where a
source argues chemisorption (e.g. phytic acid on Fe(110)), the report reproduces
the strong, flat adsorption but says plainly it cannot confirm the bond.

**The external hand-off recipe stays documented, not implemented.**
`LAMMPS_HANDOFF_NOTE` and the `docs/pipeline.md` MD-stage note remain as the
"if you have the compute" path — a user with HPC access can seed a periodic-DFT
or LAMMPS run from the exported structure — but corrosim itself does not run it.

**The MC pose is the cost lever if it is ever revisited.** The pipeline already
produces a best adsorption pose; seeding a DFT relaxation from it avoids blind
pose-scanning. That lever, and the decomposition (spike → container → slab
stage → validation), are preserved in the #40 thread should HPC access ever
materialise.

## Alternatives considered

- **Periodic-DFT slab (Quantum ESPRESSO).** The most defensible free route
  (yields charge-transfer / PDOS evidence, and the pyrazolo-pyrimidine source
  already used QE). Rejected on cost/feasibility, not correctness.
- **Classical LAMMPS + EAM/GAFF + explicit water.** Cheaper than DFT but still a
  large solvated MD with fragile organic force-field parameterisation, and it
  does not model charge transfer — so it answers a different, weaker question
  than "is this a chemisorptive bond?". Recipe kept, not built.
- **Semi-infinite surface (KKR Green's function).** Removes slab-thickness /
  dipole artifacts but not the dominant cost, and drags in a specialist code
  outside the ecosystem. Rejected.
- **Finite metal cluster + xTB.** Already rejected in ADR 0001 (unphysical
  ~−33 eV energies from dangling-bond artifacts; xTB unreliable for iron).

## Consequences

- The backlog is empty: #40 is closed won't-do, and corrosim's adsorption scope
  is now a recorded decision rather than an open question.
- The README `Limitations` and `docs/pipeline.md` framing (UFF surrogate;
  quantitative E_ads is an optional external hand-off) are the standing story,
  now anchored to a decision.
- No code changes: this ADR records a boundary the package already respects.

## Upstream

None. The kernel — *a feature whose minimum viable implementation violates a
hard, stated project constraint (budget / hardware / platform) is recorded as an
out-of-scope decision with its feasibility analysis, not carried as perpetual
backlog* — is sound generic scope hygiene but not distinct enough from ordinary
won't-do practice to file as a template convention.

<!-- Generated with solid-ai-templates (github.com/braboj/solid-ai-templates) -->
