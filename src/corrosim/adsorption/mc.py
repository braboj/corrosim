"""corrosim.mc.

Monte Carlo adsorption: a Metropolis / simulated-annealing pose search of a
rigid inhibitor over a metal slab, scored with the UFF van-der-Waals
interaction (adsorption.py). An open-source analog of the Adsorption-Locator
step the methodology template uses, replacing the single-orientation height
scan in ``estimate_adsorption_energy`` with a real configurational search.

Still a physisorption proxy (vdW, rigid bodies, no charge transfer): the
magnitude stays conservative, and the chemisorption-capable quantitative E_ads
is reserved for the MD hand-off. What MC adds over the height scan is full
rotational + translational sampling, the best pose, and an adsorption-energy
distribution.

One annealed Metropolis step (move sizes shrink as kT cools)::

    current pose --rotate+translate--> trial --confine--> score (UFF vdW)
        ^                                                     |
        +------------ accept?  E_trial < E  or ---------------+
                      random() < exp(-(E_trial - E) / kT)

    confine box:  min_height <= (nearest-atom z - top) <= max_height,
                  the molecule centroid stays over the slab footprint (x, y).
    kT anneals geometrically kT_hi -> kT_lo; the lowest-E pose is kept.
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
    uff_vdw_energy,
)

if TYPE_CHECKING:
    from corrosim.molecules import Molecule

# Starting gap (Å) between the slab top and the molecule's lowest atom; the
# annealing then samples heights in [min_height, max_height].
MC_START_HEIGHT_A = 3.0

# Move-size schedule: the trial rotation (rad) and translation (Å) both shrink
# from these amplitudes as the search cools, by the linear factor
# (1 - _STEP_DECAY * frac), so late steps refine rather than explore.
_STEP_DECAY = 0.7
_ROT_STEP_RAD = 0.6
_TRANS_STEP_A = 0.4


@dataclass
class MCResult:
    """Best adsorption pose and energetics from the Monte Carlo search
    (e_ads in eV/kJ·mol⁻¹, height in Å).
    """

    # Substrate: metal symbol + the facet label it maps to (via SURFACE_FACET)
    metal: str
    surface: str

    # Best-pose energetics + the nearest-atom gap above the slab top
    e_ads_ev: float
    e_ads_kjmol: float
    best_height_A: float

    # Best pose: the molecule's element symbols and atom positions (Å)
    mol_symbols: list[str]
    best_positions: np.ndarray

    # Heavy artefacts kept for plotting/analysis but out of the repr, so a
    # printed MCResult does not dump whole coordinate tables
    slab: Atoms = field(repr=False, default=None)
    energies: list[float] = field(repr=False, default_factory=list)

    # Search diagnostics
    n_accept: int = 0
    n_steps: int = 0

    @property
    def combined(self) -> Atoms:
        """Slab + molecule (best pose) as one ASE Atoms.

        Returns:
            The combined slab+adsorbate cell for plot_adsorption_pose.
        """
        molecule = Atoms(symbols=self.mol_symbols,
                         positions=self.best_positions)
        combined = self.slab + molecule
        combined.set_cell(self.slab.get_cell())
        combined.set_pbc(self.slab.get_pbc())
        return combined

    @classmethod
    def from_search(
        cls,
        metal: str,
        substrate: _Substrate,
        search: _Search,
        mol_symbols: list[str],
        n_steps: int,
    ) -> MCResult:
        """Assemble the result from a finished Monte Carlo search.

        Args:
            metal: Slab metal symbol.
            substrate: The slab context; its top-layer z sets the reported
                height.
            search: The finished search state (best pose + energy trace).
            mol_symbols: The molecule's element symbols, in order.
            n_steps: The number of Metropolis steps run.

        Returns:
            The best pose and energetics as an :class:`MCResult`.
        """
        best_height = float(search.best_pos[:, 2].min() - substrate.top)
        return cls(
            metal=metal,
            surface=SURFACE_FACET.get(metal, ""),
            e_ads_ev=round(search.best_e, 4),
            e_ads_kjmol=round(search.best_e * EV_TO_KJMOL, 2),
            best_height_A=round(best_height, 2),
            mol_symbols=mol_symbols,
            best_positions=search.best_pos,
            slab=substrate.slab,
            energies=search.energies,
            n_accept=search.n_accept,
            n_steps=n_steps,
        )


@dataclass
class _Substrate:
    """Fixed slab context the search reads every step.

    Bundles the ASE slab with the three geometry values the Metropolis loop
    needs on the hot path — the cached atom positions (Å) it scores against,
    the cell, and the top-layer z (Å) — so they travel as one object.
    """

    slab: Atoms
    positions: np.ndarray
    cell: np.ndarray
    top: float

    @classmethod
    def build(
        cls,
        metal: str,
        size: tuple[int, int, int],
        vacuum: float,
    ) -> _Substrate:
        """Build the metal slab and cache the geometry the search reads.

        Args:
            metal: Slab metal symbol (Fe/Cu/Al).
            size: Slab repetitions ``(nx, ny, layers)``.
            vacuum: Vacuum padding along z (Å).

        Returns:
            The slab plus its cached positions, cell, and top-layer z (Å).
        """
        slab = build_slab(metal, size=size, vacuum=vacuum)
        s_pos = slab.get_positions()
        return cls(slab, s_pos, slab.get_cell(), s_pos[:, 2].max())


@dataclass
class _Search:
    """Evolving state of the annealed Metropolis walk.

    :meth:`accept` mutates this in place: the current pose seeds the next
    proposal, and the best pose is snapshotted whenever the energy improves.
    """

    pos: np.ndarray
    e: float
    com: np.ndarray
    best_e: float
    best_pos: np.ndarray
    n_accept: int
    energies: list[float]

    @classmethod
    def seed(
        cls,
        molecule: Molecule,
        substrate: _Substrate,
        x_mix: np.ndarray,
        D_mix: np.ndarray,
    ) -> _Search:
        """Seed the search with the flat starting pose above the slab centre.

        Args:
            molecule: The inhibitor to dock (symbols + coords).
            substrate: The slab context to place the pose over.
            x_mix: UFF vdW distances for the molecule–slab atom pairs (Å).
            D_mix: UFF vdW well depths for the molecule–slab atom pairs (eV).

        Returns:
            The initial state, with the current pose as the best.
        """
        pos = initial_adsorption_pose(
            molecule.coords, substrate.cell, substrate.top, MC_START_HEIGHT_A
        )
        e = uff_vdw_energy(pos, substrate.positions, x_mix, D_mix)
        return cls(
            pos=pos,
            e=e,
            com=pos.mean(0),
            best_e=e,
            best_pos=pos.copy(),
            n_accept=0,
            energies=[e],
        )

    def accept(
        self,
        trial: np.ndarray,
        e_trial: float,
        kT: float,
        rng: np.random.Generator,
    ) -> None:
        """Accept or reject a scored trial pose, tracking the best seen.

        On a Metropolis accept the trial becomes the current pose, and whenever
        the energy improves it is snapshotted as the best. The accepted energy
        is appended to the trace every step.

        Args:
            trial: The proposed pose ``(natom, 3)``, Å.
            e_trial: The trial's UFF vdW energy (eV).
            kT: The current temperature (eV).
            rng: The trajectory RNG. ``rng.random`` is drawn only on an uphill
                move — the short-circuit that keeps the seeded trajectory
                reproducible.
        """
        if e_trial < self.e or rng.random() < np.exp(-(e_trial - self.e) / kT):
            self.pos, self.e, self.com = trial, e_trial, trial.mean(0)
            self.n_accept += 1
            if self.e < self.best_e:
                self.best_e, self.best_pos = self.e, self.pos.copy()
        self.energies.append(self.e)


def _anneal_schedule(
    step: int,
    n_steps: int,
    kT_hi: float,
    kT_lo: float,
) -> tuple[float, float]:
    """Temperature and move-size factor for one annealing step.

    Args:
        step: Current step index (0-based).
        n_steps: Total number of steps.
        kT_hi: Starting temperature (eV).
        kT_lo: Final temperature (eV).

    Returns:
        ``(kT, scale)``: the geometrically annealed temperature (eV) and the
        move-size factor in ``(0, 1]`` that shrinks the trial moves as the
        search cools.
    """
    frac = step / n_steps
    kT = kT_hi * (kT_lo / kT_hi) ** frac
    scale = 1.0 - _STEP_DECAY * frac
    return kT, scale


def _propose_pose(
    pos: np.ndarray,
    com: np.ndarray,
    scale: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Propose a rigid Metropolis trial: rotate about the centroid, translate.

    Args:
        pos: Current pose positions ``(natom, 3)``, Å.
        com: Current pose centroid ``(3,)``, Å — the rotation pivot.
        scale: Move-size factor in ``(0, 1]`` that shrinks both amplitudes as
            the anneal cools.
        rng: The trajectory RNG. Its three draws — rotation axis, rotation
            angle, then translation — MUST stay in this order to keep the
            seeded trajectory reproducible.

    Returns:
        The trial positions ``(natom, 3)``, Å, as a fresh array (``pos`` is not
        mutated).
    """
    step_rot = rot(rng.normal(size=3), rng.normal(0, _ROT_STEP_RAD * scale))
    trial = (pos - com) @ step_rot.T + com
    trial += rng.normal(0, _TRANS_STEP_A * scale, size=3)
    return trial


def _confine_pose(
    trial: np.ndarray,
    top: float,
    cell: np.ndarray,
    min_height: float,
    max_height: float,
) -> np.ndarray:
    """Confine a trial pose to the sampling box.

    Clamps the nearest-atom height into ``[top + min_height, top + max_height]``
    (Å) and shifts the centroid back over the slab footprint in x and y.

    Args:
        trial: Trial positions ``(natom, 3)``, Å; shifted in place.
        top: Slab-top z coordinate (Å).
        cell: The slab cell; ``cell[0, 0]`` / ``cell[1, 1]`` bound the
            footprint in x and y.
        min_height: Lower bound on the nearest-atom height above the top (Å).
        max_height: Upper bound on the nearest-atom height above the top (Å).

    Returns:
        The (in-place shifted) trial positions.
    """
    # Clamp the nearest atom into the adsorbed-state height window
    zmin = trial[:, 2].min()
    trial[:, 2] += np.clip(zmin, top + min_height, top + max_height) - zmin

    # Keep the centroid over the slab footprint (x, y)
    trial_com = trial.mean(0)
    trial[:, 0] += np.clip(trial_com[0], 0, cell[0, 0]) - trial_com[0]
    trial[:, 1] += np.clip(trial_com[1], 0, cell[1, 1]) - trial_com[1]
    return trial


def run_mc(
    molecule: Molecule,
    metal: str = "Fe",
    size: tuple[int, int, int] = (5, 5, 3),
    vacuum: float = 10.0,
    n_steps: int = 4000,
    seed: int = 0,
    kT_hi: float = 0.05,
    kT_lo: float = 0.003,
    min_height: float = 2.0,
    max_height: float = 5.0,
) -> MCResult:
    """Simulated-annealing Monte Carlo search for the lowest-energy pose.

    kT is in eV, annealed geometrically from ``kT_hi`` to ``kT_lo``.

    Args:
        molecule: The inhibitor to dock (symbols + coords).
        metal: Slab metal symbol (Fe/Cu/Al).
        size: Slab repetitions ``(nx, ny, layers)``.
        vacuum: Vacuum padding along z (Å).
        n_steps: Number of Metropolis steps.
        seed: RNG seed (fixes the trajectory).
        kT_hi: Starting temperature (eV).
        kT_lo: Final temperature (eV).
        min_height: Lower bound on the adsorbate's nearest-atom height (Å).
        max_height: Upper bound on the adsorbate's nearest-atom height (Å).

    Returns:
        The best pose and the accepted-energy trace as an :class:`MCResult`.

    Raises:
        ValueError: If the molecule carries an element with no UFF params.
    """
    # Build the slab and seed the search from the flat starting pose
    rng = np.random.default_rng(seed)
    substrate = _Substrate.build(metal, size, vacuum)

    # UFF pair parameters for the molecule against the slab
    mol_symbols = list(molecule.symbols)
    x_mix, D_mix = uff_mixing(
        mol_symbols, substrate.slab.get_chemical_symbols()
    )
    search = _Search.seed(molecule, substrate, x_mix, D_mix)

    # Annealed walk: anneal -> propose -> confine -> score -> accept
    for step in range(n_steps):
        kT, scale = _anneal_schedule(step, n_steps, kT_hi, kT_lo)
        trial = _propose_pose(search.pos, search.com, scale, rng)
        trial = _confine_pose(
            trial, substrate.top, substrate.cell, min_height, max_height
        )
        e_trial = uff_vdw_energy(trial, substrate.positions, x_mix, D_mix)
        search.accept(trial, e_trial, kT, rng)

    return MCResult.from_search(metal, substrate, search, mol_symbols, n_steps)
