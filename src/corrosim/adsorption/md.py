"""corrosim.md.

Stage-3 (light) molecular dynamics: rigid-body Brownian / overdamped-Langevin
dynamics of the inhibitor over the metal slab under the UFF van-der-Waals
field, at 298 K. Yields the template's MD outputs on an open-source
classical-vdW level:

  * the metal-X radial distribution (X = O/N) -> the adsorption distance, and
  * the thermal-averaged interaction energy.

It is genuine time-evolved dynamics (force/torque-driven, thermostatted), but
still a physisorption-level vdW model with a fixed slab; the full
chemisorption-capable MD (metal EAM + organic GAFF/OPLS, explicit solvent)
remains the LAMMPS Stage-3 hand-off (see adsorption.LAMMPS_HANDOFF_NOTE).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from .surface import (
    EV_TO_KJMOL,
    SURFACE_FACET,
    build_slab,
    initial_adsorption_pose,
    rot,
    uff_mixing,
    uff_vdw_forces,
)

if TYPE_CHECKING:
    from ase import Atoms

    from corrosim.molecules import Molecule

# Boltzmann constant, eV/K.
KB_EV = 8.617333262e-5
# Starting gap (Å) between the slab top and the molecule's lowest atom; the
# confinement window [min_height, max_height] takes over from the first step.
MD_START_HEIGHT_A = 2.5
# First-shell search window (Å) for the metal–donor RDF peak = the
# physisorption adsorption distance. The lower bound clears the unphysical
# close-contact spike; the upper bound stays within the first coordination
# shell (peak observed ~3.5 Å).
RDF_PEAK_WINDOW_A = (1.5, 4.0)
# Per-step clamp on the deterministic drift — translation (Å) and rotation
# (rad) alike — so a stiff vdW force can't blow up an overdamped step; the
# Gaussian thermal kick is added on top.
_MAX_DRIFT = 0.15
# Closest-contact histogram grid (Å): 0..6 Å in 0.1-Å bins.
_RDF_MAX_A = 6.0
_RDF_BIN_WIDTH_A = 0.1


@dataclass
class MDResult:
    """Brownian-MD outputs: the metal–O/N RDFs and their first-peak adsorption
    distances (Å), the thermal-mean interaction energy (eV/kJ·mol⁻¹), and the
    final pose.
    """

    metal: str
    surface: str
    temperature: float
    e_mean_ev: float
    e_mean_kjmol: float
    rdf_r: list[float]
    # metal–O closest-contact distribution (per-frame nearest O–metal)
    rdf_metal_O: list[float]
    # metal–N closest-contact distribution (per-frame nearest N–metal)
    rdf_metal_N: list[float]
    # adsorption distance via the O donors
    first_peak_metal_O: float | None
    # adsorption distance via the N donors
    first_peak_metal_N: float | None
    energies: list[float] = field(repr=False, default_factory=list)
    final_positions: np.ndarray = field(repr=False, default=None)
    mol_symbols: list[str] = field(repr=False, default_factory=list)
    slab: Atoms = field(repr=False, default=None)

    @property
    def combined(self) -> Atoms:
        """Slab + molecule (final pose) as one ASE Atoms.

        Returns:
            The combined slab+adsorbate cell for plot_adsorption_pose.
        """
        from ase import Atoms
        mol = Atoms(symbols=self.mol_symbols, positions=self.final_positions)
        c = self.slab + mol
        c.set_cell(self.slab.get_cell())
        c.set_pbc(self.slab.get_pbc())
        return c


def _langevin_step(pos: np.ndarray, forces: np.ndarray, kT: float,
                   D_t: float, D_r: float,
                   rng: np.random.Generator) -> np.ndarray:
    """Advance one overdamped-Langevin step over the vdW field.

    Clipped deterministic drift + Gaussian thermal noise, then a rigid
    Rodrigues rotation about the centre of mass and a translation.

    Args:
        pos: Current atom positions ``(natom, 3)``, Å.
        forces: Per-atom vdW forces ``(natom, 3)``, eV/Å.
        kT: Thermal energy (eV).
        D_t: Translational diffusion (Å² per step).
        D_r: Rotational diffusion (rad² per step).
        rng: The trajectory RNG. Its two ``rng.normal`` draws — translation
            first, then rotation — MUST stay in this order to keep the seeded
            trajectory reproducible.

    Returns:
        The updated positions ``(natom, 3)``, Å.
    """
    com = pos.mean(0)
    F = forces.sum(0)
    tau = np.cross(pos - com, forces).sum(0)
    trans = (np.clip((D_t / kT) * F, -_MAX_DRIFT, _MAX_DRIFT)
             + rng.normal(0, np.sqrt(2 * D_t), 3))
    dphi = (np.clip((D_r / kT) * tau, -_MAX_DRIFT, _MAX_DRIFT)
            + rng.normal(0, np.sqrt(2 * D_r), 3))
    ang = np.linalg.norm(dphi)
    R = rot(dphi / (ang + 1e-12), ang) if ang > 1e-12 else np.eye(3)
    return (pos - com) @ R.T + com + trans


def _confine_z(pos: np.ndarray, top: float, min_height: float,
               max_height: float) -> np.ndarray:
    """Clamp the molecule's lowest atom into the adsorbed-state window.

    Shifts the whole molecule in z so its nearest atom sits within
    ``[top + min_height, top + max_height]`` (Å).

    Args:
        pos: Atom positions ``(natom, 3)``, Å; shifted in place.
        top: Slab-top z coordinate (Å).
        min_height: Lower bound above the slab top (Å).
        max_height: Upper bound above the slab top (Å).

    Returns:
        The (in-place shifted) positions.
    """
    zmin = pos[:, 2].min()
    if zmin < top + min_height:
        pos[:, 2] += top + min_height - zmin
    elif zmin > top + max_height:
        pos[:, 2] += top + max_height - zmin
    return pos


def _closest_contact_hist(pos: np.ndarray, idx: list[int],
                          metal_pos: np.ndarray,
                          edges: np.ndarray) -> np.ndarray:
    """One-frame histogram of the closest donor-to-metal contact distance.

    Bins the single shortest distance between the donor atoms ``idx`` and any
    metal atom. A 3D shell normalisation is wrong above a 2D slab, and the
    molecule's far-side heteroatoms must not swamp the binding ones, so only
    the closest contact is counted. An empty ``idx`` yields an all-zero
    histogram (a no-op accumulation).

    Args:
        pos: Molecule atom positions ``(natom, 3)``, Å.
        idx: Donor-atom indices (the O or N set).
        metal_pos: Metal-atom positions ``(nmetal, 3)``, Å.
        edges: Histogram bin edges (Å).

    Returns:
        The per-bin counts, length ``len(edges) - 1``.
    """
    if not idx:
        return np.zeros(len(edges) - 1)
    dist = np.linalg.norm(
        pos[idx][:, None, :] - metal_pos[None, :, :], axis=2)
    return np.histogram([float(dist.min())], bins=edges)[0]


def _first_peak(r: np.ndarray, g: np.ndarray,
                window: tuple[float, float]) -> float | None:
    """First-shell peak distance of a contact distribution.

    Args:
        r: Bin-centre distances (Å).
        g: Distribution values aligned with ``r``.
        window: ``(lo, hi)`` first-shell search window (Å).

    Returns:
        The distance (Å) of the largest bin inside ``window``, or None when the
        window is empty.
    """
    lo, hi = window
    win = (r >= lo) & (r <= hi)
    return float(r[win][int(np.argmax(g[win]))]) if g[win].any() else None


def run_md(molecule: Molecule, metal: str = "Fe",
           size: tuple[int, int, int] = (5, 5, 3), vacuum: float = 10.0,
           n_steps: int = 4000, equil: int = 1000, temperature: float = 298.0,
           seed: int = 0, D_t: float = 0.004, D_r: float = 0.004,
           min_height: float = 1.6, max_height: float = 4.0,
           start_positions: np.ndarray | None = None) -> MDResult:
    """Brownian rigid-body MD over the slab.

    The molecule's nearest atom is confined to [min_height, max_height] above
    the surface so the run samples the *adsorbed state* (vdW physisorption is
    weak vs kT at 298 K, so an unconfined molecule thermally desorbs). The
    metal-X RDF is recorded after ``equil`` steps.

    Args:
        molecule: The inhibitor to evolve (symbols + coords).
        metal: Slab metal symbol (Fe/Cu/Al).
        size: Slab repetitions ``(nx, ny, layers)``.
        vacuum: Vacuum padding along z (Å).
        n_steps: Total MD steps.
        equil: Steps to discard before recording the RDF / mean energy.
        temperature: Thermostat temperature (K).
        seed: RNG seed (fixes the trajectory).
        D_t: Translational diffusion (Å^2 per step).
        D_r: Rotational diffusion (rad^2 per step).
        min_height: Lower confinement bound on the nearest atom's height (Å).
        max_height: Upper confinement bound on the nearest atom's height (Å).
        start_positions: Optional starting pose; defaults to the flat pose.

    Returns:
        The RDFs, first-peak distances, mean energy and final pose as an
        :class:`MDResult`.

    Raises:
        ValueError: If the molecule carries an element with no UFF params.
    """
    kT = KB_EV * temperature
    rng = np.random.default_rng(seed)
    slab = build_slab(metal, size=size, vacuum=vacuum)
    slab_pos = slab.get_positions()
    slab_sym = np.array(slab.get_chemical_symbols())
    metal_pos = slab_pos[slab_sym == metal]
    cell = slab.get_cell()
    top = slab_pos[:, 2].max()

    # UFF pair parameters + the donor-atom indices whose metal contact the RDF
    # tracks.
    m_sym = list(molecule.symbols)
    x_mix, D_mix = uff_mixing(m_sym, slab_sym)
    o_idx = [i for i, s in enumerate(m_sym) if s == "O"]
    n_idx = [i for i, s in enumerate(m_sym) if s == "N"]

    # start pose: caller-supplied, else the flat lifted pose
    if start_positions is not None:
        pos = np.array(start_positions, float).copy()
    else:
        pos = initial_adsorption_pose(
            molecule.coords, cell, top, MD_START_HEIGHT_A)

    # closest-contact histogram grid (Å) and per-donor accumulators; the +ε
    # stop keeps the closing 6.0 edge (np.arange excludes the stop).
    edges = np.arange(0.0, _RDF_MAX_A + _RDF_BIN_WIDTH_A / 10, _RDF_BIN_WIDTH_A)
    r = 0.5 * (edges[:-1] + edges[1:])
    hist_o = np.zeros(len(r))
    hist_n = np.zeros(len(r))
    nframes = 0
    energies = []

    for step in range(n_steps):
        # vdW force field -> one Langevin move -> confine to the window
        E, forces = uff_vdw_forces(pos, slab_pos, x_mix, D_mix)
        energies.append(E)
        pos = _langevin_step(pos, forces, kT, D_t, D_r, rng)
        pos = _confine_z(pos, top, min_height, max_height)

        # accumulate the closest-contact distances once equilibrated
        if step >= equil:
            hist_o += _closest_contact_hist(pos, o_idx, metal_pos, edges)
            hist_n += _closest_contact_hist(pos, n_idx, metal_pos, edges)
            nframes += 1

    norm = max(nframes, 1)
    rdf_o = hist_o / norm
    rdf_n = hist_n / norm

    # thermal mean discards the pre-equilibration transient when there is one
    if len(energies) > equil:
        e_mean = float(np.mean(energies[equil:]))
    else:
        e_mean = float(np.mean(energies))
    return MDResult(
        metal=metal, surface=SURFACE_FACET.get(metal, ""),
        temperature=temperature,
        e_mean_ev=round(e_mean, 4),
        e_mean_kjmol=round(e_mean * EV_TO_KJMOL, 2),
        rdf_r=r.tolist(), rdf_metal_O=rdf_o.tolist(),
        rdf_metal_N=rdf_n.tolist(),
        first_peak_metal_O=_first_peak(r, rdf_o, RDF_PEAK_WINDOW_A),
        first_peak_metal_N=_first_peak(r, rdf_n, RDF_PEAK_WINDOW_A),
        energies=energies, final_positions=pos, mol_symbols=m_sym, slab=slab)
