# ADR 0001 — Reject cluster-xTB for the adsorption-energy estimate

- Status: Accepted
- Date: 2026-06-28

## Context

Stage 2 of the pipeline needs an adsorption energy for the inhibitor on the metal
surface. The validated route is periodic DFT or classical MD (LAMMPS) — both too
heavy to run inline for fast screening. We evaluated a lightweight shortcut:
a **finite metal-cluster model with GFN2-xTB** (cut a small Fe slab fragment,
combine with the inhibitor, take `E_complex - E_cluster - E_molecule`).

## Decision

**Rejected** as the adsorption-energy method. We use a bounded **UFF van-der-Waals
physisorption estimate** instead (rigid bodies, height scan), and treat the full
quantitative E_ads as a LAMMPS hand-off on the exported structure.

## Evidence

On a 32-atom Fe(110) cluster + kaempferol, GFN2-xTB returned an "adsorption energy"
of about **-33 eV (~-3200 kJ/mol)** — two orders of magnitude beyond physical
adsorption (which is roughly -0.5 to -3 eV). Causes:

1. **Dangling-bond artifact** — small bare metal clusters are wildly
   over-reactive; the SCF finds large charge transfer into under-coordinated
   surface atoms that does not exist on a real periodic surface.
2. **xTB is unreliable for iron** — open d-shell / magnetic; absolute energies and
   even relative ordering are not trustworthy here.

Relative-to-reference values did not rescue it: the spread across the three
flavonoids was several eV and partly contradicted the DFT descriptor ranking, so
the systematic cluster error does **not** cancel cleanly.

## Consequences

- The shipped Stage-2a number is a *screening proxy* (vdW only), clearly labelled
  as such in the report and README.
- Quantitative, chemisorption-capable adsorption energies require Stage 3 (MD).
- Do **not** reintroduce cluster-xTB as an E_ads method without (a) a much larger,
  relaxed and/or H-saturated cluster and (b) validation against periodic DFT.
