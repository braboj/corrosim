# ADR 0002 — Adopt the pyrazolo-pyrimidine multiscale study as the methodology template

- Status: Accepted
- Date: 2026-06-29

## Context

corrosim's pipeline (DFT reactivity descriptors → Monte Carlo adsorption →
Molecular Dynamics) was reverse-engineered from a collection of green-inhibitor
papers. To produce a publication-grade study on a defined, citable methodology we
needed to pick **one** paper as the reference template: the workflow whose DFT
level, descriptor set, and MC/MD protocol corrosim targets and reports against.

A full ranking of the candidate literature was carried out (internal note;
DFT mandatory, MD desirable, judged on factual rigor + presentation + domain fit).

## Decision

Adopt **"A multiscale computational investigation for protection of carbon steel
surface by pyrazolo-pyrimidine derivatives," *Scientific Reports* 15:32576
(2025)** (DOI 10.1038/s41598-025-19022-6) as corrosim's methodology template.

It is the only surveyed study running the **complete DFT → Monte Carlo → MD stack
on Fe(110)** with the full reactivity-descriptor suite, and it is the origin of
conventions already in `corrosim/descriptors.py` (Lukovits ΔN < 3.6; Gómez
E_back-donation = −η/4).

### Adopted levels of theory

| Stage | Template | corrosim implementation |
|---|---|---|
| DFT | Gaussian, **B3LYP / 6-311++G(d,p)**, IEFPCM(water), neutral **and** protonated, gas **and** aqueous | PySCF **B3LYP/6-311++G(d,p) + ddCOSMO(water)** (open path); ORCA/Gaussian wrappers for the exact level |
| Global descriptors | E_HOMO, E_LUMO, ΔE, IP, EA, χ, η, σ, ω, ΔN, E_back-donation, TNC | already in `descriptors.py` (TNC = roadmap) |
| Local reactivity | Fukui f±, dual descriptor Δf, MEP/ESP, NBO, LOL/ELF, NCI | **roadmap** (see `article-plan.local.md`, M2) |
| Monte Carlo | Materials Studio Adsorption Locator, COMPASS, simulated annealing, Fe(110) | UFF height-scan proxy now; **real Metropolis/annealing = roadmap (M3)** |
| MD | First-principles MD, Quantum ESPRESSO, PBE + DFT-D2 | classical LAMMPS hand-off now; **run it / optional periodic-DFT E_ads = roadmap (M4)** |

## Consequences

- **Production DFT default is now B3LYP/6-311++G(d,p) + ddCOSMO(water)** in the
  PySCF engine and the CLI `--basis` (longer local runs are acceptable). `xtb`
  remains the fast screening default; `6-31g` stays available for quick checks.
  (`6-311++G(d,p)` is PySCF-equivalent to `6-311++g**`.)
- The article and `docs/validation.md` report against this fixed level so numbers
  are comparable to the template and to the independent Fe(110) cross-checks
  (black-tea quercetin; lady's-mantle kaempferol).
- corrosim's open-source stack **substitutes** for the template's commercial tools
  (PySCF/xTB for Gaussian; ASE+MC for Adsorption Locator; LAMMPS or periodic DFT
  for Forcite/QE) — same methodology, $0 in licenses. The UFF vdW estimate
  (ADR 0001) remains the *fast screening proxy* until M3/M4 land.
- We do **not** adopt the template's molecule class (heterocycles); corrosim keeps
  the Arghel flavonoids, using the template only for *method*.
