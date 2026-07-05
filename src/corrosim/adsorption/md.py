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
from ase import Atoms

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
    # Metal–O closest-contact distribution (per-frame nearest O–metal)
    rdf_metal_O: list[float]
    # Metal–N closest-contact distribution (per-frame nearest N–metal)
    rdf_metal_N: list[float]
    # Adsorption distance via the O donors
    first_peak_metal_O: float | None
    # Adsorption distance via the N donors
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
        mol = Atoms(symbols=self.mol_symbols, positions=self.final_positions)
        c = self.slab + mol
        c.set_cell(self.slab.get_cell())
        c.set_pbc(self.slab.get_pbc())
        return c

    @classmethod
    def from_run(
        cls,
        metal: str,
        substrate: _Substrate,
        rdf: _RdfAccumulator,
        energies: list[float],
        final_positions: np.ndarray,
        mol_symbols: list[str],
        temperature: float,
        equil: int,
    ) -> MDResult:
        """Assemble the result from a finished MD trajectory.

        Args:
            metal: Slab metal symbol.
            substrate: The slab context (kept for the combined-pose plot).
            rdf: The finished contact-histogram accumulator.
            energies: The per-step interaction energies (eV).
            final_positions: The molecule's final pose ``(natom, 3)``, Å.
            mol_symbols: The molecule's element symbols, in order.
            temperature: Thermostat temperature (K).
            equil: Steps discarded before the RDF / mean-energy averaging.

        Returns:
            The RDFs, first-peak distances, mean energy and final pose as an
            :class:`MDResult`.
        """
        r = rdf.bin_centres()
        rdf_o, rdf_n = rdf.normalized()
        e_mean = _mean_energy(energies, equil)
        return cls(
            metal=metal,
            surface=SURFACE_FACET.get(metal, ""),
            temperature=temperature,
            e_mean_ev=round(e_mean, 4),
            e_mean_kjmol=round(e_mean * EV_TO_KJMOL, 2),
            rdf_r=r.tolist(),
            rdf_metal_O=rdf_o.tolist(),
            rdf_metal_N=rdf_n.tolist(),
            first_peak_metal_O=_first_peak(r, rdf_o, RDF_PEAK_WINDOW_A),
            first_peak_metal_N=_first_peak(r, rdf_n, RDF_PEAK_WINDOW_A),
            energies=energies,
            final_positions=final_positions,
            mol_symbols=mol_symbols,
            slab=substrate.slab,
        )


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


def _mean_energy(energies: list[float], equil: int) -> float:
    """Thermal-mean interaction energy past the pre-equilibration transient.

    Args:
        energies: The per-step interaction energies (eV).
        equil: Steps to discard before averaging; ignored when the run did not
            exceed it.

    Returns:
        The mean energy (eV) over the post-equilibration steps, or over all
        steps when the run is no longer than ``equil``.
    """
    if len(energies) > equil:
        return float(np.mean(energies[equil:]))
    return float(np.mean(energies))


@dataclass
class _Substrate:
    """Fixed slab context the trajectory reads every step.

    Bundles the ASE slab with the cached positions and symbols, the metal-only
    positions the RDF measures against, the cell, and the top-layer z (Å).
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
    ) -> _Substrate:
        """Build the metal slab and cache the geometry the trajectory reads.

        Args:
            metal: Slab metal symbol (Fe/Cu/Al).
            size: Slab repetitions ``(nx, ny, layers)``.
            vacuum: Vacuum padding along z (Å).

        Returns:
            The slab plus its cached positions/symbols, the metal-atom
            positions, the cell, and the top-layer z (Å).
        """
        slab = build_slab(metal, size=size, vacuum=vacuum)
        s_pos = slab.get_positions()
        s_sym = np.array(slab.get_chemical_symbols())
        return cls(
            slab,
            s_pos,
            s_sym,
            s_pos[s_sym == metal],
            slab.get_cell(),
            s_pos[:, 2].max(),
        )


@dataclass
class _RdfAccumulator:
    """Running metal–donor closest-contact histograms over recorded frames.

    Holds the O and N donor-atom indices, the metal positions and the shared
    bin edges, and adds one closest-contact count per frame via :meth:`record`;
    :meth:`normalized` divides the histograms by the recorded-frame count.
    """

    o_idx: list[int]
    n_idx: list[int]
    metal_positions: np.ndarray
    edges: np.ndarray
    hist_o: np.ndarray
    hist_n: np.ndarray
    nframes: int = 0

    @classmethod
    def for_donors(
        cls,
        mol_symbols: list[str],
        substrate: _Substrate,
    ) -> _RdfAccumulator:
        """Build a zeroed accumulator for a molecule's O/N donors over a slab.

        Args:
            mol_symbols: The molecule's element symbols, in order.
            substrate: The slab context whose metal atoms are measured against.

        Returns:
            An accumulator keyed to the O and N donor indices, on the shared
            0..6 Å contact grid.
        """
        o_idx = [i for i, s in enumerate(mol_symbols) if s == "O"]
        n_idx = [i for i, s in enumerate(mol_symbols) if s == "N"]
        # The +ε stop keeps the closing 6.0 edge (np.arange excludes the stop)
        edges = np.arange(
            0.0, _RDF_MAX_A + _RDF_BIN_WIDTH_A / 10, _RDF_BIN_WIDTH_A
        )
        nbins = len(edges) - 1
        return cls(
            o_idx,
            n_idx,
            substrate.metal_positions,
            edges,
            np.zeros(nbins),
            np.zeros(nbins),
        )

    def record(self, pos: np.ndarray) -> None:
        """Add this frame's closest O– and N–metal contacts to the histograms.

        Args:
            pos: The molecule's atom positions this frame ``(natom, 3)``, Å.
        """
        self.hist_o += _closest_contact_hist(
            pos, self.o_idx, self.metal_positions, self.edges
        )
        self.hist_n += _closest_contact_hist(
            pos, self.n_idx, self.metal_positions, self.edges
        )
        self.nframes += 1

    def bin_centres(self) -> np.ndarray:
        """Bin-centre distances (Å), aligned with the RDF values.

        Returns:
            The midpoint of each histogram bin.
        """
        return 0.5 * (self.edges[:-1] + self.edges[1:])

    def normalized(self) -> tuple[np.ndarray, np.ndarray]:
        """Per-frame-averaged O and N contact distributions.

        Returns:
            ``(rdf_o, rdf_n)``, each histogram divided by the recorded-frame
            count (or by 1 when no frames were recorded).
        """
        norm = max(self.nframes, 1)
        return self.hist_o / norm, self.hist_n / norm


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
    substrate = _Substrate.build(metal, size, vacuum)

    # UFF pair parameters + the O/N donor contact histograms the RDF tracks
    mol_symbols = list(molecule.symbols)
    x_mix, D_mix = uff_mixing(mol_symbols, substrate.symbols)
    rdf = _RdfAccumulator.for_donors(mol_symbols, substrate)

    # Start pose: caller-supplied, else the flat lifted pose
    if start_positions is not None:
        pos = np.array(start_positions, float).copy()
    else:
        pos = initial_adsorption_pose(
            molecule.coords, substrate.cell, substrate.top, MD_START_HEIGHT_A)

    # Langevin trajectory: force -> move -> confine; record contacts post-equil
    energies = []
    for step in range(n_steps):
        E, forces = uff_vdw_forces(pos, substrate.positions, x_mix, D_mix)
        energies.append(E)
        pos = _langevin_step(pos, forces, kT, D_t, D_r, rng)
        pos = _confine_z(pos, substrate.top, min_height, max_height)
        if step >= equil:
            rdf.record(pos)

    return MDResult.from_run(
        metal,
        substrate,
        rdf,
        energies,
        pos,
        mol_symbols,
        temperature,
        equil,
    )
