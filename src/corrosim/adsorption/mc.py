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
    from ase import Atoms

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

    # substrate: metal symbol + the facet label it maps to (via SURFACE_FACET)
    metal: str
    surface: str

    # best-pose energetics + the nearest-atom gap above the slab top
    e_ads_ev: float
    e_ads_kjmol: float
    best_height_A: float

    # best pose: the molecule's element symbols and atom positions (Å)
    mol_symbols: list[str]
    best_positions: np.ndarray

    # heavy artefacts kept for plotting/analysis but out of the repr, so a
    # printed MCResult does not dump whole coordinate tables
    slab: Atoms = field(repr=False, default=None)
    energies: list[float] = field(repr=False, default_factory=list)

    # search diagnostics
    n_accept: int = 0
    n_steps: int = 0

    @property
    def combined(self) -> Atoms:
        """Slab + molecule (best pose) as one ASE Atoms.

        Returns:
            The combined slab+adsorbate cell for plot_adsorption_pose.
        """
        # Atoms is only imported for typing at module load; import it here for
        # the runtime construction.
        from ase import Atoms
        molecule = Atoms(symbols=self.mol_symbols,
                         positions=self.best_positions)
        combined = self.slab + molecule
        combined.set_cell(self.slab.get_cell())
        combined.set_pbc(self.slab.get_pbc())
        return combined


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
    # build the slab and read its top-layer z
    rng = np.random.default_rng(seed)
    slab = build_slab(metal, size=size, vacuum=vacuum)
    s_pos = slab.get_positions()
    cell = slab.get_cell()
    top = s_pos[:, 2].max()

    # UFF pair parameters + the flat starting pose above the slab centre
    m_sym = list(molecule.symbols)
    x_mix, D_mix = uff_mixing(m_sym, slab.get_chemical_symbols())
    pos = initial_adsorption_pose(molecule.coords, cell, top, MC_START_HEIGHT_A)
    e = uff_vdw_energy(pos, s_pos, x_mix, D_mix)
    best_e, best_pos = e, pos.copy()
    energies = [e]
    n_accept = 0
    com = pos.mean(0)

    # annealed Metropolis search; move sizes shrink as kT cools
    for i in range(n_steps):
        # geometric anneal + shrinking move sizes as the search cools
        frac = i / n_steps
        kT = kT_hi * (kT_lo / kT_hi) ** frac
        scale = 1.0 - _STEP_DECAY * frac

        # propose a rigid rotation + translation, then confine to the box
        step_rot = rot(rng.normal(size=3), rng.normal(0, _ROT_STEP_RAD * scale))
        trial = (pos - com) @ step_rot.T + com
        trial += rng.normal(0, _TRANS_STEP_A * scale, size=3)
        zmin = trial[:, 2].min()
        trial[:, 2] += np.clip(zmin, top + min_height, top + max_height) - zmin
        trial_com = trial.mean(0)
        trial[:, 0] += np.clip(trial_com[0], 0, cell[0, 0]) - trial_com[0]
        trial[:, 1] += np.clip(trial_com[1], 0, cell[1, 1]) - trial_com[1]

        # Metropolis accept/reject; track the best pose seen
        et = uff_vdw_energy(trial, s_pos, x_mix, D_mix)
        if et < e or rng.random() < np.exp(-(et - e) / kT):
            pos, e, com = trial, et, trial.mean(0)
            n_accept += 1
            if e < best_e:
                best_e, best_pos = e, pos.copy()
        energies.append(e)

    return MCResult(
        metal=metal,
        surface=SURFACE_FACET.get(metal, ""),
        e_ads_ev=round(best_e, 4),
        e_ads_kjmol=round(best_e * EV_TO_KJMOL, 2),
        best_height_A=round(float(best_pos[:, 2].min() - top), 2),
        mol_symbols=m_sym,
        best_positions=best_pos,
        slab=slab,
        energies=energies,
        n_accept=n_accept,
        n_steps=n_steps,
    )
