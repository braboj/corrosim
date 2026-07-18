"""corrosim.md.

Light molecular dynamics: rigid-body Brownian / overdamped-Langevin
dynamics of the inhibitor over the metal slab under the UFF van-der-Waals
field, at 298 K. Yields the template's MD outputs on an open-source
classical-vdW level:

  * the metal-X radial distribution (X = O/N) -> the adsorption distance, and
  * the thermal-averaged interaction energy.

It is genuine time-evolved dynamics (force/torque-driven, thermostatted), but
still a physisorption-level vdW model with a fixed slab; the full
chemisorption-capable MD (metal EAM + organic GAFF/OPLS, explicit solvent)
remains the LAMMPS hand-off (see adsorption.LAMMPS_HANDOFF_NOTE).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from ase import Atoms

from .surface import (
    EV_TO_KJMOL,
    SURFACE_FACET,
    Substrate,
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

# Heteroatom donor elements the metal–donor RDF tracks: the atoms an inhibitor
# physisorbs through. All carry UFF parameters, so the energy/pose already see
# them; the RDF measures the metal contact for each donor the molecule carries.
_DONOR_ELEMENTS = ("O", "N", "S", "P", "F", "Cl", "Br")


@dataclass
class MDResult:
    """Brownian-MD outputs: the per-donor metal RDFs and their first-peak
    adsorption distances (Å), the thermal-mean interaction energy
    (eV/kJ·mol⁻¹), and the final pose.
    """

    # Slab identity: metal symbol and its low-index facet
    metal: str
    surface: str

    # Thermostat temperature (K)
    temperature: float

    # Thermal-mean interaction energy, in eV and kJ/mol
    e_mean_ev: float
    e_mean_kjmol: float

    # Metal–donor RDF: shared bin-centre distances (Å) and the per-frame
    # closest-contact distribution for each heteroatom donor the molecule
    # carries (O/N/S/P/halogen), keyed by element
    rdf_r: list[float]
    rdf_metal: dict[str, list[float]]

    # First-shell adsorption distance (Å) for each donor element
    first_peak_metal: dict[str, float | None]

    # Off-repr trajectory extras, for the combined-pose plot and inspection
    energies: list[float] = field(repr=False, default_factory=list)
    final_positions: np.ndarray | None = field(repr=False, default=None)
    mol_symbols: list[str] = field(repr=False, default_factory=list)
    slab: Atoms | None = field(repr=False, default=None)

    @property
    def combined(self) -> Atoms:
        """Slab + molecule (final pose) as one ASE Atoms.

        Returns:
            The combined slab+adsorbate cell for plot_adsorption_pose.

        Raises:
            ValueError: If this result carries no slab / final positions
                (default-constructed).
        """
        if self.slab is None or self.final_positions is None:
            raise ValueError(
                "MDResult.combined needs a slab and final positions, but this "
                "result was built without them.")
        mol = Atoms(symbols=self.mol_symbols, positions=self.final_positions)
        c = self.slab + mol
        c.set_cell(self.slab.get_cell())
        c.set_pbc(self.slab.get_pbc())
        return c

    @property
    def rdf_metal_O(self) -> list[float]:
        """Metal–O RDF (backward-compatible accessor into ``rdf_metal``).

        Returns:
            The oxygen-donor RDF, or an empty list when the molecule carries no
            oxygen.
        """
        return self.rdf_metal.get("O", [])

    @property
    def rdf_metal_N(self) -> list[float]:
        """Metal–N RDF (backward-compatible accessor into ``rdf_metal``).

        Returns:
            The nitrogen-donor RDF, or an empty list when the molecule carries
            no nitrogen.
        """
        return self.rdf_metal.get("N", [])

    @property
    def first_peak_metal_O(self) -> float | None:
        """First-shell metal–O adsorption distance.

        Returns:
            The oxygen first-peak distance (Å), or None when absent.
        """
        return self.first_peak_metal.get("O")

    @property
    def first_peak_metal_N(self) -> float | None:
        """First-shell metal–N adsorption distance.

        Returns:
            The nitrogen first-peak distance (Å), or None when absent.
        """
        return self.first_peak_metal.get("N")

    @classmethod
    def from_run(
        cls,
        metal: str,
        substrate: Substrate,
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
        rdf_by_donor = rdf.normalized()
        e_mean = _mean_energy(energies, equil)
        return cls(
            metal=metal,
            surface=SURFACE_FACET.get(metal, ""),
            temperature=temperature,
            e_mean_ev=round(e_mean, 4),
            e_mean_kjmol=round(e_mean * EV_TO_KJMOL, 2),
            rdf_r=r.tolist(),
            rdf_metal={e: g.tolist() for e, g in rdf_by_donor.items()},
            first_peak_metal={
                e: _first_peak(r, g, RDF_PEAK_WINDOW_A)
                for e, g in rdf_by_donor.items()
            },
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


def _confine(pos: np.ndarray, top: float, min_height: float,
             max_height: float, cell: np.ndarray) -> np.ndarray:
    """Confine the molecule to the adsorbed state over the finite slab.

    Clamps the lowest atom into the z-window ``[top + min_height,
    top + max_height]`` (Å) and the centroid over the slab footprint
    ``[0, cell[0,0]] x [0, cell[1,1]]``, mirroring the Monte Carlo pose clamp.
    Without the lateral clamp the adsorbate random-walks off the finite patch —
    the vdW field uses raw distances with no periodic wrapping — and the RDF is
    then measured against a slab edge. Applied after the Langevin step, so the
    seeded RNG draw order and a bound run's trajectory are unchanged.

    Args:
        pos: Atom positions ``(natom, 3)``, Å; shifted in place.
        top: Slab-top z coordinate (Å).
        min_height: Lower bound above the slab top (Å).
        max_height: Upper bound above the slab top (Å).
        cell: The slab cell (3x3); ``cell[0,0]`` / ``cell[1,1]`` give the
            lateral footprint.

    Returns:
        The (in-place shifted) positions.
    """
    zmin = pos[:, 2].min()
    if zmin < top + min_height:
        pos[:, 2] += top + min_height - zmin
    elif zmin > top + max_height:
        pos[:, 2] += top + max_height - zmin

    # Keep the centroid over the slab footprint so the adsorbate cannot diffuse
    # off the finite patch (no minimum-image wrapping in the vdW field).
    com = pos.mean(0)
    pos[:, 0] += np.clip(com[0], 0.0, cell[0, 0]) - com[0]
    pos[:, 1] += np.clip(com[1], 0.0, cell[1, 1]) - com[1]
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
        steps when the run is no longer than ``equil``; NaN for an empty run.
    """
    # A zero-step run has nothing to average; return NaN explicitly rather than
    # let np.mean([]) emit a RuntimeWarning and return nan.
    if len(energies) == 0:
        return float("nan")
    if len(energies) > equil:
        return float(np.mean(energies[equil:]))
    return float(np.mean(energies))


@dataclass
class _RdfAccumulator:
    """Running metal–donor closest-contact histograms over recorded frames.

    Holds a per-element map of the molecule's donor-atom indices (every
    heteroatom donor it carries — O/N/S/P/halogen), the metal positions and the
    shared bin edges, and adds one closest-contact count per donor per frame via
    :meth:`record`; :meth:`normalized` divides each histogram by the
    recorded-frame count.
    """

    # Donor-atom indices into the molecule, keyed by element
    donor_idx: dict[str, list[int]]

    # Fixed slab metal positions (Å) and the shared histogram bin edges (Å)
    metal_positions: np.ndarray
    edges: np.ndarray

    # Running per-donor closest-contact histograms, one count added per frame
    hist: dict[str, np.ndarray]

    # Frames recorded so far (the normalisation divisor)
    nframes: int = 0

    @classmethod
    def for_donors(
        cls,
        mol_symbols: list[str],
        substrate: Substrate,
    ) -> _RdfAccumulator:
        """Build a zeroed accumulator for a molecule's heteroatom donors.

        The donor set is derived from the molecule's own heteroatoms — every
        element of ``_DONOR_ELEMENTS`` it carries — so a sulfur/phosphorus/
        halogen inhibitor gets its actual binding atom measured, not just O/N.

        Args:
            mol_symbols: The molecule's element symbols, in order.
            substrate: The slab context whose metal atoms are measured against.

        Returns:
            An accumulator keyed to the present donor elements, on the shared
            0..6 Å contact grid.
        """
        donor_idx = {
            e: [i for i, s in enumerate(mol_symbols) if s == e]
            for e in _DONOR_ELEMENTS
            if e in mol_symbols
        }
        # The +ε stop keeps the closing 6.0 edge (np.arange excludes the stop)
        edges = np.arange(
            0.0, _RDF_MAX_A + _RDF_BIN_WIDTH_A / 10, _RDF_BIN_WIDTH_A
        )
        nbins = len(edges) - 1
        hist = {e: np.zeros(nbins) for e in donor_idx}
        return cls(donor_idx, substrate.metal_positions, edges, hist)

    def record(self, pos: np.ndarray) -> None:
        """Add this frame's closest donor–metal contacts to each histogram.

        Args:
            pos: The molecule's atom positions this frame ``(natom, 3)``, Å.
        """
        for e, idx in self.donor_idx.items():
            self.hist[e] += _closest_contact_hist(
                pos, idx, self.metal_positions, self.edges
            )
        self.nframes += 1

    def bin_centres(self) -> np.ndarray:
        """Bin-centre distances (Å), aligned with the RDF values.

        Returns:
            The midpoint of each histogram bin.
        """
        return 0.5 * (self.edges[:-1] + self.edges[1:])

    def normalized(self) -> dict[str, np.ndarray]:
        """Per-frame-averaged contact distribution for each donor element.

        Returns:
            ``{element: rdf}``, each histogram divided by the recorded-frame
            count (or by 1 when no frames were recorded).
        """
        norm = max(self.nframes, 1)
        return {e: h / norm for e, h in self.hist.items()}


def run_md(molecule: Molecule, metal: str,
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
    substrate = Substrate.build(metal, size, vacuum)

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
        pos = _confine(pos, substrate.top, min_height, max_height,
                       substrate.cell)
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
