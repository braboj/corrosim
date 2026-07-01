"""
corrosim.adsorption
-------------------
Stage-2 structure preparation: build the metal slab the inhibitor adsorbs onto
and place the molecule above it. This produces ready-to-run input geometries for
a molecular-dynamics / Monte-Carlo adsorption study (e.g. LAMMPS), which is the
heavy step you run as a separate stage.

The full adsorption-energy MD is intentionally NOT run here (it needs a metal-
compatible force field and real compute). What this gives you, automatically, is:
  * a correct, periodic metal surface (Fe(110) / Cu(111) / Al(111)),
  * the inhibitor positioned flat above it inside a solvent-sized box,
  * exported files (.xyz / .cif / LAMMPS data) to hand to the MD engine.

The shared substrate/vdW primitives (build_slab, UFF, orient_flat, the facet map)
live in corrosim.surface; this module is the Stage-2 estimate built on top.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from ase import Atoms
from ase.io import write

from .surface import (
    KCAL_TO_EV,
    MIN_PAIR_DISTANCE_A,
    SURFACE_FACET,
    UFF,
    build_slab,
    orient_flat,
)


@dataclass
class AdsorptionSystem:
    """A prepared metal slab with the inhibitor placed above it, ready for MD/MC."""

    metal: str
    surface: str
    slab: Atoms
    combined: Atoms          # slab + molecule
    box: tuple

    def write_files(self, prefix: str):
        """Write .xyz and .cif for visualisation/handoff. Returns paths."""
        paths = {}
        for ext in ("xyz", "cif"):
            p = f"{prefix}.{ext}"
            write(p, self.combined)
            paths[ext] = p
        return paths


def place_molecule(slab: Atoms, symbols, coords, height: float = 2.5) -> Atoms:
    """Lay the molecule flat above the slab centre at the given height (A)."""
    coords = np.asarray(coords, dtype=float)
    coords = coords - coords.mean(axis=0)          # centre the molecule
    # orient its principal plane parallel to the surface (flatten z-spread)
    mol = Atoms(symbols=symbols, positions=coords)
    cell = slab.get_cell()
    cx, cy = cell[0, 0] / 2.0, cell[1, 1] / 2.0
    top_z = slab.get_positions()[:, 2].max()
    mol.translate((cx, cy, top_z + height - mol.get_positions()[:, 2].min()))
    combined = slab + mol
    combined.set_cell(slab.get_cell())
    combined.set_pbc(slab.get_pbc())
    return combined


def build_adsorption_system(molecule, metal: str = "Fe",
                            size=(6, 6, 4), vacuum: float = 15.0,
                            height: float = 2.5) -> AdsorptionSystem:
    """Build a metal slab and lay the molecule flat at `height` (Å) above it."""
    surface = SURFACE_FACET[metal]
    slab = build_slab(metal, size=size, vacuum=vacuum)
    combined = place_molecule(slab, molecule.symbols, molecule.coords, height)
    box = tuple(np.diag(combined.get_cell()))
    return AdsorptionSystem(metal=metal, surface=surface,
                            slab=slab, combined=combined, box=box)


# --- UFF van-der-Waals physisorption estimate -----------------------------
def estimate_adsorption_energy(molecule, metal: str = "Fe",
                               size=(5, 5, 3), vacuum: float = 10.0,
                               heights=None) -> dict:
    """
    Fast, bounded physisorption estimate: rigid-body UFF van-der-Waals
    interaction energy of the (flat-oriented) molecule scanned over heights
    above the slab. Returns the minimum.

    This is a SCREENING proxy (vdW only, no charge transfer / chemisorption).
    For a quantitative, chemisorption-capable E_ads, run the exported structure
    through the LAMMPS MD route (see LAMMPS_HANDOFF_NOTE).
    """
    if heights is None:
        heights = np.arange(2.0, 4.01, 0.25)
    missing = set(molecule.symbols) - set(UFF)
    if missing:
        raise ValueError(f"No UFF vdW params for elements: {sorted(missing)}")

    slab = build_slab(metal, size=size, vacuum=vacuum)
    sym_s = slab.get_chemical_symbols()
    pos_s = slab.get_positions()
    cell = slab.get_cell()
    cx, cy = cell[0, 0] / 2.0, cell[1, 1] / 2.0
    top = pos_s[:, 2].max()

    base = orient_flat(molecule.coords)
    best_e, best_h = float("inf"), None
    for h in heights:
        p = base.copy()
        p[:, 2] += top + h - p[:, 2].min()
        p[:, 0] += cx
        p[:, 1] += cy
        e = 0.0
        for sa, pa in zip(molecule.symbols, p):
            xa, Da = UFF[sa]
            for sb, pb in zip(sym_s, pos_s):
                xb, Db = UFF[sb]
                r = float(np.linalg.norm(pa - pb))
                if r < MIN_PAIR_DISTANCE_A:        # close-contact guard (never fires in practice)
                    continue
                t = (np.sqrt(xa * xb) / r) ** 6
                e += np.sqrt(Da * Db) * (t * t - 2 * t)
        e *= KCAL_TO_EV
        if e < best_e:
            best_e, best_h = e, float(h)

    return {"metal": metal, "method": "UFF-vdW (rigid physisorption estimate)",
            "e_ads_ev": round(best_e, 4),
            "e_ads_kjmol": round(best_e * 96.485, 2),
            "best_height_A": best_h}


LAMMPS_HANDOFF_NOTE = """\
Next step (a separate stage), on the exported structure:
  1. Assign a force field: organic = GAFF/OPLS (e.g. via LigParGen/antechamber),
     metal = EAM potential for Fe/Cu/Al (from the NIST Interatomic Potentials Repo).
  2. Solvate: add ~500 H2O + a few H3O+ / Cl- to mimic 1 M HCl (packmol).
  3. Run classical MD in LAMMPS: NVT, 298 K, 300-500 ps, 1 fs step.
  4. Adsorption energy:
        E_ads = E_total - (E_slab+solution + E_inhibitor)
     and inspect the radial distribution function for the adsorption distance.
Stay on the CLASSICAL path; first-principles MD will exhaust a $200 budget.
"""
