"""corrosim.adsorption.

Stage-2 structure preparation: build the metal slab the inhibitor adsorbs onto
and place the molecule above it. This produces ready-to-run input geometries
for a molecular-dynamics / Monte-Carlo adsorption study (e.g. LAMMPS), which is
the heavy step you run as a separate stage.

The full adsorption-energy MD is intentionally NOT run here (it needs a
metal-compatible force field and real compute). What this gives you,
automatically, is:
  * a correct, periodic metal surface (Fe(110) / Cu(111) / Al(111)),
  * the inhibitor positioned flat above it inside a solvent-sized box,
  * exported files (.xyz / .cif / LAMMPS data) to hand to the MD engine.

The shared substrate/vdW primitives (build_slab, UFF, orient_flat, the facet
map) live in corrosim.surface; this module is the Stage-2 estimate on top.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt
from ase import Atoms
from ase.io import write

from .surface import (
    EV_TO_KJMOL,
    SURFACE_FACET,
    build_slab,
    initial_adsorption_pose,
    uff_mixing,
    uff_vdw_energy,
)

if TYPE_CHECKING:
    from corrosim.molecules import Molecule


@dataclass
class AdsorptionSystem:
    """A prepared metal slab with the inhibitor placed above it, ready for
    MD/MC.
    """

    metal: str
    surface: str
    slab: Atoms
    # slab + molecule
    combined: Atoms
    box: tuple[float, float, float]

    def write_files(self, prefix: str) -> dict[str, str]:
        """Write .xyz and .cif for visualisation/handoff.

        Args:
            prefix: Path prefix; writes ``<prefix>.xyz`` and ``<prefix>.cif``.

        Returns:
            The written paths keyed by extension (``"xyz"`` / ``"cif"``).
        """
        paths = {}
        for ext in ("xyz", "cif"):
            p = f"{prefix}.{ext}"
            write(p, self.combined)
            paths[ext] = p
        return paths


def place_molecule(slab: Atoms, symbols: Sequence[str], coords: npt.ArrayLike,
                   height: float = 2.5) -> Atoms:
    """Lay the molecule flat above the slab centre at the given height.

    Args:
        slab: The metal slab to place the molecule above.
        symbols: The molecule's element symbols.
        coords: The molecule's coordinates, (n, 3) (Å).
        height: Gap between the slab top and the molecule's lowest atom (Å).

    Returns:
        The combined slab+molecule cell.
    """
    coords = np.asarray(coords, dtype=float)
    # centre, then orient the principal plane parallel to the surface
    coords = coords - coords.mean(axis=0)
    mol = Atoms(symbols=symbols, positions=coords)
    cell = slab.get_cell()
    cx, cy = cell[0, 0] / 2.0, cell[1, 1] / 2.0
    top_z = slab.get_positions()[:, 2].max()
    mol.translate((cx, cy, top_z + height - mol.get_positions()[:, 2].min()))
    combined = slab + mol
    combined.set_cell(slab.get_cell())
    combined.set_pbc(slab.get_pbc())
    return combined


def build_adsorption_system(molecule: Molecule, metal: str = "Fe",
                            size: tuple[int, int, int] = (6, 6, 4),
                            vacuum: float = 15.0,
                            height: float = 2.5) -> AdsorptionSystem:
    """Build a metal slab and lay the molecule flat above it.

    Args:
        molecule: The inhibitor to place (symbols + coords).
        metal: Slab metal symbol (Fe/Cu/Al).
        size: Slab repetitions ``(nx, ny, layers)``.
        vacuum: Vacuum padding along z (Å).
        height: Gap between the slab top and the molecule's lowest atom (Å).

    Returns:
        The prepared :class:`AdsorptionSystem`.
    """
    surface = SURFACE_FACET[metal]
    slab = build_slab(metal, size=size, vacuum=vacuum)
    combined = place_molecule(slab, molecule.symbols, molecule.coords, height)
    box = tuple(np.diag(combined.get_cell()))
    return AdsorptionSystem(metal=metal, surface=surface,
                            slab=slab, combined=combined, box=box)


# --- UFF van-der-Waals physisorption estimate -----------------------------
def estimate_adsorption_energy(molecule: Molecule, metal: str = "Fe",
                               size: tuple[int, int, int] = (5, 5, 3),
                               vacuum: float = 10.0,
                               heights: npt.ArrayLike | None = None) -> dict:
    """Fast, bounded physisorption estimate.

    The rigid-body UFF van-der-Waals interaction energy of the (flat-oriented)
    molecule is scanned over heights above the slab and the minimum returned.
    This is a SCREENING proxy (vdW only, no charge transfer / chemisorption);
    for a quantitative, chemisorption-capable E_ads, run the exported structure
    through the LAMMPS MD route (see LAMMPS_HANDOFF_NOTE).

    Args:
        molecule: The inhibitor to estimate (symbols + coords).
        metal: Slab metal symbol (Fe/Cu/Al).
        size: Slab repetitions ``(nx, ny, layers)``.
        vacuum: Vacuum padding along z (Å).
        heights: Heights to scan (Å); defaults to ``arange(2.0, 4.01, 0.25)``.

    Returns:
        A dict with ``metal``, ``method``, ``e_ads_ev``, ``e_ads_kjmol`` and
        the best ``best_height_A``.

    Raises:
        ValueError: If the molecule carries an element with no UFF params.
    """
    if heights is None:
        heights = np.arange(2.0, 4.01, 0.25)

    slab = build_slab(metal, size=size, vacuum=vacuum)
    pos_s = slab.get_positions()
    cell = slab.get_cell()
    top = pos_s[:, 2].max()
    x_mix, D_mix = uff_mixing(molecule.symbols, slab.get_chemical_symbols())

    best_e, best_h = float("inf"), None
    for h in heights:
        p = initial_adsorption_pose(molecule.coords, cell, top, float(h))
        e = uff_vdw_energy(p, pos_s, x_mix, D_mix)
        if e < best_e:
            best_e, best_h = e, float(h)

    return {"metal": metal, "method": "UFF-vdW (rigid physisorption estimate)",
            "e_ads_ev": round(best_e, 4),
            "e_ads_kjmol": round(best_e * EV_TO_KJMOL, 2),
            "best_height_A": best_h}


LAMMPS_HANDOFF_NOTE = """\
Next step (a separate stage), on the exported structure:
  1. Assign a force field: organic = GAFF/OPLS (e.g. via LigParGen/antechamber),
     metal = EAM potential for Fe/Cu/Al (from the NIST Interatomic Potentials
     Repo).
  2. Solvate: add ~500 H2O + a few H3O+ / Cl- to mimic 1 M HCl (packmol).
  3. Run classical MD in LAMMPS: NVT, 298 K, 300-500 ps, 1 fs step.
  4. Adsorption energy:
        E_ads = E_total - (E_slab+solution + E_inhibitor)
     and inspect the radial distribution function for the adsorption distance.
Stay on the CLASSICAL path; first-principles MD will exhaust a $200 budget.
"""
