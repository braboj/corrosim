# The simulation pipeline

The scientific basis for `corrosim`. Across the green corrosion-inhibitor
literature, the same **three-stage computational pipeline** recurs: study the
inhibitor in isolation (quantum chemistry), dock it onto a metal surface inside a
simulated acid solution (Monte Carlo), then relax it dynamically to measure how
strongly it binds (molecular dynamics). All three aim to explain and rank
*adsorption strength*, since inhibition efficiency is governed by how well a
molecule adsorbs onto and shields the metal.

```
   Inhibitor molecule
         │
   ┌─────▼─────┐   Stage 1: DFT / quantum chemistry (isolated molecule, implicit solvent)
   │   DFT     │   → HOMO/LUMO, gap, hardness, electrophilicity, ΔN, Fukui (where it reacts)
   └─────┬─────┘
         │
   ┌─────▼─────┐   Stage 2: Monte Carlo (adsorption pose search)
   │    MC     │   → best adsorption geometry + adsorption energy on the metal slab
   └─────┬─────┘
         │
   ┌─────▼─────┐   Stage 3: Molecular Dynamics
   │    MD     │   → interaction/binding energy, RDF (adsorption distance), film stability
   └───────────┘
         │
   Compare to experiment (EIS, polarization, weight loss)
```

How each stage maps to the code is summarised at the bottom.

---

## Stage 1 — DFT / quantum-chemical descriptors (single molecule)

Computes the *electronic reactivity* of the inhibitor: where it donates/accepts
electrons and how strongly it should bind. In the literature this is done with
**Gaussian** (B3LYP, 6-311++G(d,p), PCM/IEFPCM water) or **DMol³** (GGA-PBE/M-11L,
DNP, COSMO). Procedure: geometry optimization → frequency check (true minimum) →
extract descriptors, in gas and aqueous phase.

**`corrosim` implements this** with four interchangeable engines behind one
interface: `xtb` (GFN2, fast screening), `pyscf` (open DFT, e.g. B3LYP +
ddCOSMO), and `orca` / `gaussian` wrappers (write input → run the local binary →
parse HOMO/LUMO).

### Global reactivity descriptors

From the frontier-orbital energies E_HOMO and E_LUMO (Koopmans' theorem):

```
Energy gap            ΔE   = E_LUMO − E_HOMO          (smaller → more reactive)
Ionization potential  IP   = − E_HOMO
Electron affinity     EA   = − E_LUMO
Electronegativity     χ    = (IP + EA) / 2
Chemical hardness     η    = (IP − EA) / 2            (= ΔE / 2; softer adsorbs better)
Chemical softness     σ    = 1 / η
Chemical potential    µ    = − χ
Electrophilicity      ω    = µ² / (2η)
Electrons transferred ΔN   = (Φ_metal − χ) / [2 (η_metal + η)]
Back-donation energy  ΔE_back = − η / 4
```

The metal is described by its work function Φ (Fe ≈ 4.82, Cu ≈ 4.94, Al ≈ 4.26 eV)
with η_metal ≈ 0. A high E_HOMO and a small gap indicate a strong electron-donor
that bonds readily to the metal. Implemented in `corrosim/descriptors.py`.

### Local reactivity (roadmap)

The literature also uses **Fukui functions** f⁺/f⁻, the **dual descriptor** Δf,
**ESP** maps and **NBO** charges to pinpoint *which atoms* adsorb. `corrosim`
does not compute these yet — it is the planned Stage-1 completion (finite
differences over the N, N±1 electron systems, which the existing engines support).

---

## Stage 2 — Monte Carlo adsorption (best pose + energy)

Searches for the lowest-energy way the inhibitor sits on the metal inside the
acid. In the literature: **Materials Studio Adsorption Locator**, **COMPASS**
force field, simulated annealing over a metal slab (**Fe(110)** steel, **Cu(111)**
copper, **Al(111)** aluminium) with periodic boundaries and an explicit
water + H₃O⁺ + Cl⁻ box mimicking HCl. Key output: the **adsorption energy E_ads**
(more negative = stronger).

**`corrosim` implements** the slab construction and molecule placement
(`corrosim/adsorption.py`, via ASE) and exports geometries for the full MD run.
For a fast, bounded screening number it computes a **rigid-body UFF van-der-Waals
physisorption estimate** (orient flat, height scan) rather than a full
configurational search. A real Monte Carlo pose search (random rotate/translate +
Metropolis/annealing) is on the roadmap.

> A finite metal-cluster + GFN2-xTB shortcut for E_ads was evaluated and
> **rejected** — bare clusters give unphysical (tens-of-eV) energies. See
> [ADR 0001](adr/0001-reject-cluster-xtb-adsorption-energy.md).

---

## Stage 3 — Molecular dynamics (equilibrium binding, film stability)

Lets the system evolve in time for a realistic interaction energy and the
adsorption geometry. Literature route: **Forcite** (COMPASS, NVT, 298 K,
300–500 ps, 1 fs) or first-principles MD (**Quantum ESPRESSO**, PBE + DFT-D2).
Outputs:

```
Interaction energy   E_interaction = E_total − (E_surface+solution + E_inhibitor)
Binding energy       E_binding     = − E_interaction
Radial distribution function (RDF) → adsorption distance; <3.5 Å ⇒ chemisorption
```

**`corrosim` does not run MD.** It exports the slab + molecule and provides a
LAMMPS hand-off (`LAMMPS_HANDOFF_NOTE`): assign force fields (GAFF/OPLS for the
organic, EAM for the metal), solvate, run NVT, compute E_ads and the RDF. This is
the heavy, compute-bound step and stays outside the package. Stay on the
**classical** path; first-principles MD is far more expensive.

---

## Open-source toolchain

The reference papers use Gaussian and BIOVIA Materials Studio (both commercial).
`corrosim` is built entirely on free software so the pipeline costs **$0 in
licenses**:

| Reference (commercial) | Free equivalent used here |
|---|---|
| Gaussian / DMol³ (DFT) | PySCF, xTB (ORCA optional, free for academia) |
| Adsorption Locator (MC) | ASE slab + UFF estimate (MC search: roadmap) |
| Forcite / QE (MD) | LAMMPS / Quantum ESPRESSO (hand-off) |
| Multiwfn (Fukui/ESP) | Multiwfn / finite differences (roadmap) |

Spend any compute budget on the Stage-3 classical MD, not on software.

---

## Stage → module map

| Stage | Module | Entry points |
|---|---|---|
| Build molecule | `corrosim/molecules.py` | `build_molecule` |
| Stage 1 (engines) | `corrosim/engines.py` | `run_xtb`, `run_pyscf`, `run_orca`, `run_gaussian` |
| Stage 1 (descriptors) | `corrosim/descriptors.py` | `compute_descriptors` |
| Stage 2 | `corrosim/adsorption.py` | `estimate_adsorption_energy`, `build_adsorption_system` |
| Reporting | `corrosim/report.py` | `results_dataframe`, `rank_inhibitors`, `build_html_report` |
| Orchestration | `corrosim/__init__.py`, `cli.py` | `screen`, `analyse_one` |

## Important caveats

- Simulations **screen and explain**; they do not prove inhibition efficiency.
  Validate against electrochemistry (EIS, potentiodynamic polarization, weight loss).
- For plant extracts (e.g. Arghel / *Solenostemma argel*), the whole mixture is not
  simulated — the **major identified constituents** are (here, the flavonoids
  kaempferol, quercetin, isorhamnetin). Confirm a specific extract with LC-MS/GC-MS.
