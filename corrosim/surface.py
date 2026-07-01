"""corrosim.surface.

Shared Stage-2/3 substrate + van-der-Waals primitives, single-sourced so that
adsorption / mc / md all agree on the metal surface and the UFF field:

  * METAL_LATTICE / SURFACE_FACET — crystal + conventional inhibitor facet per metal,
  * build_slab — the periodic ASE slab,
  * UFF / KCAL_TO_EV — UFF nonbonded parameters and the energy unit conversion,
  * orient_flat / rot — rigid-body geometry helpers (flat orientation, rotation).

These were previously underscore-private in adsorption/mc with cross-module
imports; promoted to public here (issue #4) since they are de-facto shared API.
"""
from __future__ import annotations

import numpy as np
from ase import Atoms
from ase.build import bcc110, fcc111

# Lattice constants (Angstrom) and crystal type per metal.
METAL_LATTICE = {
    "Fe": ("bcc", 2.8665),
    "Cu": ("fcc", 3.6149),
    "Al": ("fcc", 4.0495),
}

# Conventional inhibitor-study facet per metal (the surface build_slab produces).
SURFACE_FACET = {"Fe": "(110)", "Cu": "(111)", "Al": "(111)"}

# UFF nonbonded parameters (Rappe et al. 1992): element -> (x_vdw [A], D [kcal/mol]).
UFF = {
    "H": (2.886, 0.044), "C": (3.851, 0.105), "N": (3.660, 0.069),
    "O": (3.500, 0.060), "S": (4.035, 0.274), "F": (3.364, 0.050),
    "Cl": (3.947, 0.227), "P": (4.147, 0.305),
    "Fe": (2.912, 0.013), "Cu": (3.495, 0.005), "Al": (4.499, 0.505),
}
KCAL_TO_EV = 0.0433641

# Close-contact floor (Å) for the UFF pair distance: caps the r -> 0 Lennard-Jones
# singularity so a transient overlap can't blow up the energy. Defensive only — the
# adsorbate is confined well above the slab (min_height >= 1.6 Å), so in practice the
# molecule–slab separation never approaches this floor. Shared by mc / md / adsorption.
MIN_PAIR_DISTANCE_A = 0.3


def build_slab(metal: str = "Fe", size=(6, 6, 4), vacuum: float = 15.0) -> Atoms:
    """Build a periodic metal slab with the conventional inhibitor facet."""
    if metal not in METAL_LATTICE:
        raise ValueError(f"Unknown metal '{metal}'. Known: {list(METAL_LATTICE)}")
    crystal, a = METAL_LATTICE[metal]
    if crystal == "bcc":      # Fe -> (110)
        slab = bcc110(metal, size=size, a=a, vacuum=vacuum)
    else:                     # Cu, Al -> (111)
        slab = fcc111(metal, size=size, a=a, vacuum=vacuum)
    return slab


def orient_flat(coords):
    """Rotate the molecule so its largest plane lies parallel to xy (max contact)."""
    c = np.asarray(coords, float)
    c = c - c.mean(axis=0)
    # principal axes; smallest-variance axis -> z
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    R = vt[::-1].T               # least-spread direction becomes z
    out = c @ R
    if np.linalg.det(R) < 0:     # keep right-handed
        out[:, 0] *= -1
    return out


def rot(axis, angle):
    """Axis-angle (Rodrigues) rotation matrix for a 3-vector axis and angle (rad)."""
    axis = axis / (np.linalg.norm(axis) + 1e-12)
    x, y, z = axis
    c, s = np.cos(angle), np.sin(angle)
    C = 1.0 - c
    return np.array([[c + x*x*C, x*y*C - z*s, x*z*C + y*s],
                     [y*x*C + z*s, c + y*y*C, y*z*C - x*s],
                     [z*x*C - y*s, z*y*C + x*s, c + z*z*C]])
