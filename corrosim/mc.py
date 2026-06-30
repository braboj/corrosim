"""
corrosim.mc
-----------
Stage-2 Monte Carlo adsorption: a Metropolis / simulated-annealing pose search of
a rigid inhibitor over a metal slab, scored with the UFF van-der-Waals interaction
(adsorption.py). An open-source analog of the Adsorption-Locator step the
methodology template uses (ADR 0002), replacing the single-orientation height scan
in `estimate_adsorption_energy` with a real configurational search.

Still a physisorption proxy (vdW, rigid bodies, no charge transfer). The *regime*
matches the Arghel experiment (physical adsorption), but the magnitude stays
conservative; the chemisorption-capable quantitative E_ads is the Stage-3 MD
hand-off. What MC adds over the height scan: full rotational+translational
sampling, the best pose, and an adsorption-energy distribution.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .surface import (
    KCAL_TO_EV,
    MIN_PAIR_DISTANCE_A,
    SURFACE_FACET,
    UFF,
    build_slab,
    orient_flat,
    rot,
)


@dataclass
class MCResult:
    """Best adsorption pose and energetics from the Monte Carlo search
    (e_ads in eV/kJ·mol⁻¹, height in Å)."""
    metal: str
    surface: str
    e_ads_ev: float
    e_ads_kjmol: float
    best_height_A: float
    mol_symbols: list
    best_positions: np.ndarray
    slab: object = field(repr=False, default=None)
    energies: list = field(repr=False, default_factory=list)
    n_accept: int = 0
    n_steps: int = 0

    @property
    def combined(self):
        """slab + molecule (best pose) as an ASE Atoms — for plot_adsorption_pose."""
        from ase import Atoms
        mol = Atoms(symbols=self.mol_symbols, positions=self.best_positions)
        c = self.slab + mol
        c.set_cell(self.slab.get_cell())
        c.set_pbc(self.slab.get_pbc())
        return c


def run_mc(molecule, metal: str = "Fe", size=(5, 5, 3), vacuum: float = 10.0,
           n_steps: int = 4000, seed: int = 0, kT_hi: float = 0.05,
           kT_lo: float = 0.003, min_height: float = 2.0,
           max_height: float = 5.0) -> MCResult:
    """Simulated-annealing Monte Carlo search for the lowest-energy adsorption pose.

    kT in eV; annealed geometrically from kT_hi to kT_lo. Returns the best pose and
    the accepted-energy trace.
    """
    missing = set(molecule.symbols) - set(UFF)
    if missing:
        raise ValueError(f"No UFF vdW params for elements: {sorted(missing)}")
    rng = np.random.default_rng(seed)
    slab = build_slab(metal, size=size, vacuum=vacuum)
    s_pos = slab.get_positions()
    s_sym = slab.get_chemical_symbols()
    s_x = np.array([UFF[s][0] for s in s_sym])
    s_D = np.array([UFF[s][1] for s in s_sym])
    cell = slab.get_cell()
    cx, cy = cell[0, 0] / 2.0, cell[1, 1] / 2.0
    top = s_pos[:, 2].max()

    m_sym = list(molecule.symbols)
    m_x = np.array([UFF[s][0] for s in m_sym])
    m_D = np.array([UFF[s][1] for s in m_sym])
    x_mix = np.sqrt(m_x[:, None] * s_x[None, :])
    D_mix = np.sqrt(m_D[:, None] * s_D[None, :])

    def energy(p):
        d = np.linalg.norm(p[:, None, :] - s_pos[None, :, :], axis=2)
        d = np.maximum(d, MIN_PAIR_DISTANCE_A)
        t = (x_mix / d) ** 6
        return float((D_mix * (t * t - 2.0 * t)).sum()) * KCAL_TO_EV

    pos = orient_flat(molecule.coords)
    pos[:, 0] += cx
    pos[:, 1] += cy
    pos[:, 2] += top + 3.0 - pos[:, 2].min()
    e = energy(pos)
    best_e, best_pos = e, pos.copy()
    energies = [e]
    n_accept = 0
    com = pos.mean(0)

    for i in range(n_steps):
        frac = i / n_steps
        kT = kT_hi * (kT_lo / kT_hi) ** frac
        scale = 1.0 - 0.7 * frac
        trial = (pos - com) @ rot(rng.normal(size=3), rng.normal(0, 0.6 * scale)).T + com
        trial += rng.normal(0, 0.4 * scale, size=3)
        zmin = trial[:, 2].min()
        trial[:, 2] += np.clip(zmin, top + min_height, top + max_height) - zmin
        c2 = trial.mean(0)
        trial[:, 0] += np.clip(c2[0], 0, cell[0, 0]) - c2[0]
        trial[:, 1] += np.clip(c2[1], 0, cell[1, 1]) - c2[1]
        et = energy(trial)
        if et < e or rng.random() < np.exp(-(et - e) / kT):
            pos, e, com = trial, et, trial.mean(0)
            n_accept += 1
            if e < best_e:
                best_e, best_pos = e, pos.copy()
        energies.append(e)

    return MCResult(metal=metal, surface=SURFACE_FACET.get(metal, ""),
                    e_ads_ev=round(best_e, 4), e_ads_kjmol=round(best_e * 96.485, 2),
                    best_height_A=round(float(best_pos[:, 2].min() - top), 2),
                    mol_symbols=m_sym, best_positions=best_pos, slab=slab,
                    energies=energies, n_accept=n_accept, n_steps=n_steps)
