# How corrosim works — the simulation pipeline

*A plain-English guide to what this tool actually does, and the science behind
it. No computational-chemistry background needed — the technical detail is
layered in for those who want it, but you can follow the story without it.*

---

## The problem, in one paragraph

Metals corrode. Iron rusts, and in an acid — like the hydrochloric acid (HCl)
used industrially to clean steel — it dissolves alarmingly fast. A cheap,
practical defence is a **corrosion inhibitor**: a small amount of a molecule
added to the liquid that sticks to the metal surface and forms a thin protective
film, like a microscopic raincoat that keeps the corrosive acid off the metal.
**Green** inhibitors are ones drawn from plants instead of toxic synthetic
chemicals. The catch: there are thousands of candidate molecules, and testing
each one in the lab is slow and costly. **corrosim screens them on a computer
first**, so only the most promising candidates go to the bench.

## What goes in, what comes out

You give corrosim three things (the three boxes at the top of the diagram):

- **an inhibitor** — the candidate molecule, given by name (e.g. `quercetin`) or
  as a *SMILES* string (a short text code for a chemical structure);
- **a substrate** — the metal you want to protect (mild steel / iron, copper, or
  aluminium);
- **a medium** — the corrosive liquid, e.g. 1 M HCl. This matters because in acid
  the molecule grabs an extra H⁺ and becomes positively charged, which changes
  how it behaves — so corrosim models that charged form too.

Out the other end comes a **ranking** of the candidates and a self-contained
HTML report: every number, chart, and 3D picture bundled into one shareable file.

![corrosim pipeline](../figures/fig0_pipeline.png)

*Source: [`pipeline.drawio`](pipeline.drawio). The bottom of this page maps each
stage to the code.*

## The big idea: three stages, zooming in

Across the scientific literature on green inhibitors, the same three-step recipe
keeps appearing — and corrosim follows it. Each step asks a different question,
zooming from the lone molecule to the molecule sitting on metal:

1. **Stage 1 — what kind of molecule is this?** Study it on its own.
2. **Stage 2 — how does it like to sit on the metal?** Try many poses, keep the best.
3. **Stage 3 — how tightly does it hold on?** Let it jiggle at room temperature and measure.

All three are really chasing one thing: **how strongly the molecule sticks to the
metal** (its *adsorption*). The better it sticks and shields the surface, the
better it fights corrosion.

---

## Stage 1 — Get to know the molecule (quantum chemistry)

**In plain terms.** Before worrying about the metal, we examine the inhibitor by
itself and ask: *how willing is it to share its electrons?* Gripping a metal
surface is largely about donating electrons into the metal, so an
"electron-generous" molecule tends to be a better inhibitor. To find out, we solve
the quantum-mechanical equations for the molecule's electrons — a method called
**DFT** (density functional theory). Think of it as an X-ray of the molecule's
electronic personality.

The two most important numbers come from the molecule's *frontier orbitals*:

- **HOMO** — the highest-energy electrons it holds, i.e. the ones it is most ready
  to *give away*.
- **LUMO** — its lowest empty slot, i.e. where it can *accept* electrons back.

A high HOMO and a small **HOMO–LUMO gap** signal a reactive, electron-donating
molecule that bonds readily to metal.

**What corrosim does.** It offers four interchangeable engines behind one
interface, so you can trade speed for accuracy: `xtb` (very fast, great for a
first pass), `pyscf` (proper open-source DFT — the default for publication-grade
numbers), and optional `orca` / `gaussian` wrappers if you have them. The
literature typically uses commercial Gaussian (B3LYP, 6-311++G(d,p), implicit
water) or DMol³; corrosim matches that level of theory with free tools.

### The descriptors — the molecule's "scorecard"

From E_HOMO and E_LUMO a standard set of reactivity numbers (the *global
descriptors*) is derived. **You don't need the algebra** — the two to watch are
the **gap** (smaller = more reactive) and **ΔN** (roughly, how many electrons the
molecule tends to hand to the metal). The full set, for completeness (via
Koopmans' theorem):

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

The metal enters through its **work function** Φ — essentially how tightly it
holds its own electrons (Fe ≈ 4.82, Cu ≈ 4.94, Al ≈ 4.26 eV; we treat the metal's
hardness η_metal ≈ 0). Implemented in `corrosim/descriptors.py`.

### Which atoms actually do the gripping?

The descriptors above describe the *whole* molecule; we also want to know *which
individual atoms* latch onto the metal. Two tools answer that:

- **Fukui functions / dual descriptor** — flag the most reactive atoms (the
  electron donors and acceptors).
- **ESP map** — a 3D "heat map" of charge across the molecule; the red, electron-
  rich patches are the spots that love metal.

For the Arghel flavonoids both agree: the oxygen atoms on the catechol ring and
the 3-OH group are the metal-binding sites. Implemented in `corrosim/fukui.py`
(condensed Fukui, by frozen-orbital or finite-difference) and
`figures.render_esp` (PySCF `cubegen` density + electrostatic potential, painted
onto the molecule's surface).

---

## Stage 2 — Find the comfiest fit on the metal (Monte Carlo)

**In plain terms.** Now we place the molecule on the metal surface and look for
the *best way it can lie down* — the position and orientation where it sits most
comfortably (lowest energy). There are countless possible poses, so we can't
check them all. Instead we use a **Monte Carlo** search: randomly nudge and rotate
the molecule thousands of times, generally keeping changes that lower the energy
but occasionally accepting a worse one so we don't get stuck in a so-so spot. This
trick is called *simulated annealing* — like gently shaking a jar so the contents
settle into their tightest packing. We keep the best pose found and its
**adsorption energy** E_ads (the more negative, the stronger the grip).

**What corrosim does.** It builds a realistic metal surface (a periodic "slab")
with ASE and runs the Monte Carlo pose search (`corrosim/adsorption.py` +
`corrosim/mc.py`) over a van-der-Waals stickiness model (UFF). For the flavonoids
on steel it finds them lying **flat** against the surface at **E_ads ≈ −16
kJ/mol** — modest, weak "physical" sticking (*physisorption*), consistent with
published results for similar plant inhibitors. The literature does this step with
Materials Studio's Adsorption Locator; corrosim's open-source pose search plays the
same role.

> A tempting shortcut — a tiny metal *cluster* scored with the fast `xtb` engine —
> was tried and **rejected**: bare clusters give wildly unphysical energies. See
> [ADR 0001](adr/0001-reject-cluster-xtb-adsorption-energy.md).

---

## Stage 3 — Let it settle and measure the grip (molecular dynamics)

**In plain terms.** A single best pose is just a snapshot; real molecules wiggle.
In **molecular dynamics (MD)** we let the molecule move around over the surface at
room temperature (298 K) and watch how it actually settles over time. The headline
result is the **adsorption distance**: how far the molecule's oxygen atoms
typically sit from the metal. We read it off a **radial distribution function
(RDF)** — basically a histogram of "how common is each distance," whose first peak
marks the typical binding distance. Closer than ~3.5 Å hints at a strong chemical
bond (*chemisorption*); farther means weaker physical sticking (*physisorption*).

**What corrosim does.** It runs a light **Brownian molecular dynamics**
(`corrosim/md.py`) under the same van-der-Waals field and reads the **metal–O
RDF** (Fe–O for our steel case study). For the flavonoids the first peak sits at
≈ 3.5 Å — the physisorption range, agreeing with Stage 2.

For a *quantitative, bond-capable* adsorption energy, corrosim hands off to
**LAMMPS** (the step-by-step recipe is in `LAMMPS_HANDOFF_NOTE`): assign force
fields (GAFF/OPLS for the organic molecule, EAM for the metal), add explicit
water, run the simulation, and compute E_ads and the RDF. That's the heavy,
compute-hungry job deliberately left *outside* the package — stay on this
classical path; full first-principles MD is far more expensive.

---

## Everything here is free software

The reference papers lean on Gaussian and BIOVIA Materials Studio — both
expensive commercial packages. corrosim reproduces the whole pipeline with free,
open-source tools, so it costs **$0 in licences**:

| Reference (commercial) | Free equivalent used here |
|---|---|
| Gaussian / DMol³ (DFT) | PySCF, xTB (ORCA optional, free for academia) |
| DMol³ geometry-opt | PySCF + geomeTRIC (`run_dft --optimize`) |
| Adsorption Locator (MC) | ASE slab + UFF Monte Carlo pose search (`corrosim/mc.py`) |
| Forcite (MD) | Brownian rigid-body MD → metal–O RDF (`corrosim/md.py`); LAMMPS hand-off for quantitative E_ads |
| Multiwfn (Fukui / ESP) | `corrosim/fukui.py` (condensed Fukui) + PySCF cubegen ESP/MEP map |

The takeaway: spend any compute budget on the Stage-3 simulation, not on software
licences.

---

## Where each stage lives in the code

| Stage | Module | Entry points |
|---|---|---|
| Build molecule | `corrosim/molecules.py` | `build_molecule`, `build_protonated` |
| Stage 1 (engines) | `corrosim/engines.py` | `run_xtb`, `run_pyscf`, `run_orca`, `run_gaussian`, `optimize_geometry` |
| Stage 1 (descriptors) | `corrosim/descriptors.py` | `compute_descriptors` |
| Stage 1b (Fukui) | `corrosim/fukui.py` | `compute_fukui` |
| Stage 1c (ESP/orbitals) | `corrosim/figures.py` | `write_density_esp_cubes`, `render_esp`, `render_orbital` |
| Stage 2 (MC) | `corrosim/adsorption.py`, `corrosim/mc.py` | `build_adsorption_system`, `run_mc` |
| Stage 3 (MD) | `corrosim/md.py` | `run_md` |
| Reporting | `corrosim/report.py` | `rank_inhibitors`, `build_html_report`, `build_pipeline_report` |
| Drivers | `corrosim/runs/*` | `run_dft`, `run_fukui`, `run_mc`, `run_md`, `make_cubes`, `make_figures`, `make_report`, `compare_geometry` |
| Orchestration | `corrosim/__init__.py`, `cli.py` | `screen`, `analyse_one` |

---

## What this does — and doesn't — tell you

- Simulations **screen and explain**; they do not *prove* that a molecule works.
  Always confirm the promising candidates with real electrochemistry — EIS,
  potentiodynamic polarization, and weight-loss tests.
- For a plant extract like Arghel (*Solenostemma argel*), we don't simulate the
  whole mixture — only its **major known ingredients** (here the flavonoids
  kaempferol, quercetin, isorhamnetin). What is actually in a given batch should
  be confirmed by LC-MS/GC-MS.
