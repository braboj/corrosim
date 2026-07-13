"""corrosim.surface.

Shared substrate + van-der-Waals primitives, single-sourced so that
adsorption / mc / md all agree on the metal surface and the UFF field:

  * METAL_LATTICE / SURFACE_FACET — crystal + conventional inhibitor facet
    per metal,
  * build_slab — the periodic ASE slab,
  * UFF / KCAL_TO_EV / EV_TO_KJMOL — UFF nonbonded parameters and the energy
    unit conversions,
  * uff_mixing / uff_vdw_energy / uff_vdw_forces — the UFF Lennard-Jones 12-6
    molecule–slab interaction (energy, and energy + forces for MD),
  * orient_flat / rot / initial_adsorption_pose — rigid-body geometry helpers
    (flat orientation, rotation, the standard starting pose above the slab).

These were previously underscore-private in adsorption/mc with cross-module
imports; promoted to public here since they are de-facto shared API. The vdW
energy/forces, combining rules and starting pose were de-duplicated out of
adsorption / mc / md into this module.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from ase import Atoms
from ase.build import bcc110, fcc111
from ase.cell import Cell

from corrosim.presets import metal_element

# Lattice constants (Angstrom) and crystal type per metal.
METAL_LATTICE = {
    "Fe": ("bcc", 2.8665),
    "Cu": ("fcc", 3.6149),
    "Al": ("fcc", 4.0495),
}

# The ASE builder and its conventional inhibitor-study facet label, per crystal
# type — a single table so build_slab and SURFACE_FACET can never disagree on
# which surface is produced. Add a crystal here to support a new lattice.
CRYSTAL_BUILDER = {
    "bcc": (bcc110, "(110)"),
    "fcc": (fcc111, "(111)"),
}

# Conventional inhibitor-study facet per metal, derived from the crystal so the
# label cannot drift from what build_slab actually builds.
SURFACE_FACET = {
    metal: CRYSTAL_BUILDER[crystal][1]
    for metal, (crystal, _a) in METAL_LATTICE.items()
}

# UFF nonbonded parameters (Rappe et al. 1992):
# element -> (x_vdw [A], D [kcal/mol]).
UFF = {
    "H": (2.886, 0.044), "C": (3.851, 0.105), "N": (3.660, 0.069),
    "O": (3.500, 0.060), "S": (4.035, 0.274), "F": (3.364, 0.050),
    "Cl": (3.947, 0.227), "Br": (4.189, 0.251), "P": (4.147, 0.305),
    "Fe": (2.912, 0.013), "Cu": (3.495, 0.005), "Al": (4.499, 0.505),
}
KCAL_TO_EV = 0.0433641

# eV -> kJ/mol. Single source for every reported adsorption energy
# (e_ads_kjmol, e_mean_kjmol) and the report's unit-conversion equation.
EV_TO_KJMOL = 96.485

# Close-contact floor (Å) for the UFF pair distance: caps the r -> 0
# Lennard-Jones singularity so a transient overlap can't blow up the energy.
# Defensive only — the adsorbate is confined well above the slab
# (min_height >= 1.6 Å), so the molecule–slab separation never approaches this
# floor in practice. Shared by mc / md / adsorption.
MIN_PAIR_DISTANCE_A = 0.3


def build_slab(metal: str = "Fe",
               size: tuple[int, int, int] = (6, 6, 4),
               vacuum: float = 15.0) -> Atoms:
    """Build a periodic metal slab with the conventional inhibitor facet.

    Args:
        metal: Metal symbol, bare ('Fe') or facet-qualified ('Fe(110)'); the
            element must be one of :data:`METAL_LATTICE` (Fe/Cu/Al).
        size: Slab repetitions ``(nx, ny, layers)``.
        vacuum: Vacuum padding added along z (Å).

    Returns:
        The periodic ASE slab — bcc(110) for Fe, fcc(111) for Cu/Al.

    Raises:
        ValueError: If the metal element has no lattice entry.
    """
    # Accept the facet-qualified pipeline metal ("Fe(110)") or a bare element.
    element = metal_element(metal)
    if element not in METAL_LATTICE:
        raise ValueError(
            f"Unknown metal '{metal}'. Known: {list(METAL_LATTICE)}")
    crystal, a = METAL_LATTICE[element]
    builder, _facet = CRYSTAL_BUILDER[crystal]
    return builder(element, size=size, a=a, vacuum=vacuum)


@dataclass
class Substrate:
    """Cached metal-slab geometry shared by the adsorption search / dynamics.

    Built once via :meth:`build`; the MC/MD loops read the cached ``positions``
    (Å) for scoring, the ``cell`` and top-layer z (Å) for confinement, and the
    metal-only ``metal_positions`` (Å) for the metal–donor RDF.
    """

    slab: Atoms
    positions: np.ndarray
    symbols: np.ndarray
    metal_positions: np.ndarray
    cell: np.ndarray
    top: float

    @classmethod
    def build(
        cls,
        metal: str,
        size: tuple[int, int, int],
        vacuum: float,
    ) -> Substrate:
        """Build the metal slab and cache the geometry the pipeline reads.

        Args:
            metal: Slab metal symbol (Fe/Cu/Al), bare or facet-qualified.
            size: Slab repetitions ``(nx, ny, layers)``.
            vacuum: Vacuum padding along z (Å).

        Returns:
            The slab plus its cached positions/symbols, the metal-atom
            positions, the cell, and the top-layer z (Å).
        """
        slab = build_slab(metal, size=size, vacuum=vacuum)
        pos = slab.get_positions()
        sym = np.array(slab.get_chemical_symbols())
        return cls(
            slab,
            pos,
            sym,
            pos[sym == metal_element(metal)],
            slab.get_cell(),
            pos[:, 2].max(),
        )


def orient_flat(coords: npt.ArrayLike) -> np.ndarray:
    """Rotate a molecule so its largest plane lies parallel to xy (max contact).

    Args:
        coords: Molecule coordinates, (n, 3) (Å; any array-like).

    Returns:
        The centred, rotated (n, 3) coordinates with the molecular plane in xy.
    """
    c = np.asarray(coords, float)
    c = c - c.mean(axis=0)
    # SVD rows come in descending spread, so vt[2] is the least-spread axis;
    # R's columns are the principal axes, mapping it onto z (plane -> xy).
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    R = vt.T
    out = c @ R
    if np.linalg.det(R) < 0:
        # Keep the frame right-handed
        out[:, 0] *= -1
    return out


def rot(axis: npt.ArrayLike, angle: float) -> np.ndarray:
    """Axis-angle (Rodrigues) rotation matrix.

    Args:
        axis: A 3-vector rotation axis (need not be normalised).
        angle: Rotation angle (radians).

    Returns:
        The (3, 3) rotation matrix.
    """
    axis = axis / (np.linalg.norm(axis) + 1e-12)
    x, y, z = axis
    c, s = np.cos(angle), np.sin(angle)
    C = 1.0 - c
    return np.array([[c + x*x*C, x*y*C - z*s, x*z*C + y*s],
                     [y*x*C + z*s, c + y*y*C, y*z*C - x*s],
                     [z*x*C - y*s, z*y*C + x*s, c + z*z*C]])


def uff_mixing(mol_symbols: Iterable[str],
               slab_symbols: Iterable[str]) -> tuple[np.ndarray, np.ndarray]:
    """Geometric UFF combining rules for every molecule/slab atom pair.

    Args:
        mol_symbols: Element symbols of the adsorbate atoms (length n).
        slab_symbols: Element symbols of the slab atoms (length m).

    Returns:
        ``(x_mix, D_mix)``: (n, m) arrays of pair vdW distances
        x_ij = sqrt(x_i x_j) (Å) and well depths D_ij = sqrt(D_i D_j)
        (kcal/mol), per Rappe et al. 1992.

    Raises:
        ValueError: If any element has no UFF nonbonded parameters.
    """
    mol_symbols, slab_symbols = list(mol_symbols), list(slab_symbols)
    missing = (set(mol_symbols) | set(slab_symbols)) - set(UFF)
    if missing:
        raise ValueError(f"No UFF vdW params for elements: {sorted(missing)}")
    m_x = np.array([UFF[s][0] for s in mol_symbols])
    m_D = np.array([UFF[s][1] for s in mol_symbols])
    s_x = np.array([UFF[s][0] for s in slab_symbols])
    s_D = np.array([UFF[s][1] for s in slab_symbols])
    x_mix = np.sqrt(m_x[:, None] * s_x[None, :])
    D_mix = np.sqrt(m_D[:, None] * s_D[None, :])
    return x_mix, D_mix


def uff_vdw_energy(mol_pos: np.ndarray, slab_pos: np.ndarray,
                   x_mix: np.ndarray, D_mix: np.ndarray) -> float:
    """UFF Lennard-Jones 12-6 molecule–slab interaction energy.

    Pair distances are floored at MIN_PAIR_DISTANCE_A to cap the r -> 0
    singularity.

    Args:
        mol_pos: Molecule positions, (n, 3) (Å).
        slab_pos: Slab positions, (m, 3) (Å).
        x_mix: Pair vdW distances from :func:`uff_mixing`, (n, m) (Å).
        D_mix: Pair well depths from :func:`uff_mixing`, (n, m) (kcal/mol).

    Returns:
        The interaction energy in eV (negative = attractive).
    """
    diff = mol_pos[:, None, :] - slab_pos[None, :, :]
    d = np.maximum(np.linalg.norm(diff, axis=2), MIN_PAIR_DISTANCE_A)
    t6 = (x_mix / d) ** 6
    return float((D_mix * (t6 * t6 - 2.0 * t6)).sum()) * KCAL_TO_EV


def uff_vdw_forces(
    mol_pos: np.ndarray,
    slab_pos: np.ndarray,
    x_mix: np.ndarray,
    D_mix: np.ndarray,
) -> tuple[float, np.ndarray]:
    """UFF Lennard-Jones 12-6 energy plus per-molecule-atom forces (for MD).

    Same potential as :func:`uff_vdw_energy`; a separate function rather than
    a boolean flag so energy-only callers stay force-free.

    Args:
        mol_pos: Molecule positions, (n, 3) (Å).
        slab_pos: Slab positions, (m, 3) (Å).
        x_mix: Pair vdW distances from :func:`uff_mixing`, (n, m) (Å).
        D_mix: Pair well depths from :func:`uff_mixing`, (n, m) (kcal/mol).

    Returns:
        ``(energy, forces)``: the energy in eV and the (n, 3) forces on the
        molecule atoms in eV/Å (f = -dE/dr).
    """
    # Pairwise displacement (n, m, 3) and floored distance
    diff = mol_pos[:, None, :] - slab_pos[None, :, :]
    d = np.maximum(np.linalg.norm(diff, axis=2), MIN_PAIR_DISTANCE_A)
    t6 = (x_mix / d) ** 6
    e = float((D_mix * (t6 * t6 - 2.0 * t6)).sum()) * KCAL_TO_EV
    # dE/dr (kcal/mol/Å) projected onto the pair unit vectors -> forces (eV/Å)
    dEdr = 12.0 * D_mix / d * (t6 - t6 * t6)
    f = -(dEdr[:, :, None] * (diff / d[:, :, None])).sum(axis=1) * KCAL_TO_EV
    return e, f


def initial_adsorption_pose(coords: npt.ArrayLike, cell: Cell | np.ndarray,
                            top_z: float, height_A: float) -> np.ndarray:
    """Standard starting pose: flat orientation, centred on the cell, lifted.

    The shared mc / md / adsorption placement: :func:`orient_flat`, then
    translate the molecule to the lateral cell centre with its lowest atom
    ``height_A`` above the slab's top layer.

    Args:
        coords: Molecule coordinates, (n, 3) (Å; any array-like).
        cell: The slab's (orthogonal) cell; only [0, 0] and [1, 1] are used.
        top_z: z of the slab's top atomic layer (Å).
        height_A: Gap between the slab top and the molecule's lowest atom (Å).

    Returns:
        The posed (n, 3) coordinates (Å).
    """
    pos = orient_flat(coords)
    pos[:, 0] += cell[0, 0] / 2.0
    pos[:, 1] += cell[1, 1] / 2.0
    pos[:, 2] += top_z + height_A - pos[:, 2].min()
    return pos
