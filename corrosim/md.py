"""
corrosim.md
-----------
Stage-3 (light) molecular dynamics: rigid-body Brownian / overdamped-Langevin
dynamics of the inhibitor over the metal slab under the UFF van-der-Waals field, at
298 K. Yields the template's MD outputs on an open-source classical-vdW level:

  * the metal-X radial distribution (X = O/N) -> the adsorption distance, and
  * the thermal-averaged interaction energy.

It is genuine time-evolved dynamics (force/torque-driven, thermostatted), but still
a physisorption-level vdW model with a fixed slab; the full chemisorption-capable
MD (metal EAM + organic GAFF/OPLS, explicit solvent) remains the LAMMPS Stage-3
hand-off (see adsorption.LAMMPS_HANDOFF_NOTE).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .surface import KCAL_TO_EV, SURFACE_FACET, UFF, build_slab, orient_flat, rot

KB_EV = 8.617333262e-5   # Boltzmann constant, eV/K


@dataclass
class MDResult:
    """Brownian-MD outputs: the metal–O/N RDFs and their first-peak adsorption
    distances (Å), the thermal-mean interaction energy (eV/kJ·mol⁻¹), and the
    final pose."""
    metal: str
    surface: str
    temperature: float
    e_mean_ev: float
    e_mean_kjmol: float
    rdf_r: list
    rdf_metal_O: list          # metal–O radial distribution (metal = self.metal)
    rdf_metal_N: list          # metal–N radial distribution
    first_peak_metal_O: float  # adsorption distance via the O donors
    first_peak_metal_N: float  # adsorption distance via the N donors
    energies: list = field(repr=False, default_factory=list)
    final_positions: np.ndarray = field(repr=False, default=None)
    mol_symbols: list = field(repr=False, default_factory=list)
    slab: object = field(repr=False, default=None)

    @property
    def combined(self):
        """slab + molecule (final pose) as an ASE Atoms — for plot_adsorption_pose."""
        from ase import Atoms
        mol = Atoms(symbols=self.mol_symbols, positions=self.final_positions)
        c = self.slab + mol
        c.set_cell(self.slab.get_cell()); c.set_pbc(self.slab.get_pbc())
        return c

    # --- back-compat aliases (pre-substrate-agnostic field names) ----------
    @property
    def rdf_FeO(self):
        """Back-compat alias for ``rdf_metal_O``."""
        return self.rdf_metal_O

    @property
    def rdf_FeN(self):
        """Back-compat alias for ``rdf_metal_N``."""
        return self.rdf_metal_N

    @property
    def first_peak_FeO(self):
        """Back-compat alias for ``first_peak_metal_O``."""
        return self.first_peak_metal_O

    @property
    def first_peak_FeN(self):
        """Back-compat alias for ``first_peak_metal_N``."""
        return self.first_peak_metal_N


def _forces_energy(p, s_pos, x_mix, D_mix):
    """UFF vdW energy (eV) and per-molecule-atom forces (eV/A)."""
    diff = p[:, None, :] - s_pos[None, :, :]      # (n, m, 3)
    d = np.maximum(np.linalg.norm(diff, axis=2), 0.3)
    t6 = (x_mix / d) ** 6
    E = float((D_mix * (t6 * t6 - 2.0 * t6)).sum()) * KCAL_TO_EV
    dEdr = 12.0 * D_mix / d * (t6 - t6 * t6)       # kcal/mol/A
    f = -(dEdr[:, :, None] * (diff / d[:, :, None])).sum(axis=1) * KCAL_TO_EV
    return E, f


def run_md(molecule, metal: str = "Fe", size=(5, 5, 3), vacuum: float = 10.0,
           n_steps: int = 4000, equil: int = 1000, temperature: float = 298.0,
           seed: int = 0, D_t: float = 0.004, D_r: float = 0.004,
           min_height: float = 1.6, max_height: float = 4.0,
           start_positions=None) -> MDResult:
    """Brownian rigid-body MD over the slab. D_t/D_r: translational/rotational
    diffusion (A^2 / rad^2 per step). The molecule's nearest atom is confined to
    [min_height, max_height] above the surface so the run samples the *adsorbed
    state* (vdW physisorption is weak vs kT at 298 K, so an unconfined molecule
    thermally desorbs). Records the metal-X RDF after `equil` steps."""
    missing = set(molecule.symbols) - set(UFF)
    if missing:
        raise ValueError(f"No UFF vdW params for elements: {sorted(missing)}")
    kT = KB_EV * temperature
    rng = np.random.default_rng(seed)
    slab = build_slab(metal, size=size, vacuum=vacuum)
    s_pos = slab.get_positions()
    s_sym = np.array(slab.get_chemical_symbols())
    metal_pos = s_pos[s_sym == metal]
    cell = slab.get_cell()
    top = s_pos[:, 2].max()

    m_sym = list(molecule.symbols)
    m_x = np.array([UFF[s][0] for s in m_sym]); m_D = np.array([UFF[s][1] for s in m_sym])
    s_x = np.array([UFF[s][0] for s in s_sym]); s_D = np.array([UFF[s][1] for s in s_sym])
    x_mix = np.sqrt(m_x[:, None] * s_x[None, :]); D_mix = np.sqrt(m_D[:, None] * s_D[None, :])
    o_idx = [i for i, s in enumerate(m_sym) if s == "O"]
    n_idx = [i for i, s in enumerate(m_sym) if s == "N"]

    if start_positions is not None:
        p = np.array(start_positions, float).copy()
    else:
        p = orient_flat(molecule.coords)
        p[:, 0] += cell[0, 0] / 2.0; p[:, 1] += cell[1, 1] / 2.0
        p[:, 2] += top + 2.5 - p[:, 2].min()

    edges = np.arange(0.0, 6.01, 0.1)
    r = 0.5 * (edges[:-1] + edges[1:])
    h_mO = np.zeros(len(r)); h_mN = np.zeros(len(r)); nframes = 0
    energies = []

    for step in range(n_steps):
        E, f = _forces_energy(p, s_pos, x_mix, D_mix)
        energies.append(E)
        com = p.mean(0)
        F = f.sum(0)
        tau = np.cross(p - com, f).sum(0)
        trans = np.clip((D_t / kT) * F, -0.15, 0.15) + rng.normal(0, np.sqrt(2 * D_t), 3)
        dphi = np.clip((D_r / kT) * tau, -0.15, 0.15) + rng.normal(0, np.sqrt(2 * D_r), 3)
        ang = np.linalg.norm(dphi)
        R = rot(dphi / (ang + 1e-12), ang) if ang > 1e-12 else np.eye(3)
        p = (p - com) @ R.T + com + trans
        zmin = p[:, 2].min()
        if zmin < top + min_height:
            p[:, 2] += top + min_height - zmin
        elif zmin > top + max_height:                 # confine to the adsorbed state
            p[:, 2] += top + max_height - zmin
        if step >= equil:
            # closest O/N-to-metal contact per frame = the adsorption-distance
            # distribution (a 3D shell normalisation is wrong above a 2D slab; and
            # the molecule's far-side heteroatoms must not swamp the binding ones).
            if o_idx:
                d = np.linalg.norm(p[o_idx][:, None, :] - metal_pos[None, :, :], axis=2)
                h_mO += np.histogram([float(d.min())], bins=edges)[0]
            if n_idx:
                d = np.linalg.norm(p[n_idx][:, None, :] - metal_pos[None, :, :], axis=2)
                h_mN += np.histogram([float(d.min())], bins=edges)[0]
            nframes += 1

    norm = max(nframes, 1)
    g_mO = h_mO / norm
    g_mN = h_mN / norm

    def _peak(g):
        win = (r >= 1.5) & (r <= 4.0)
        return float(r[win][int(np.argmax(g[win]))]) if g[win].any() else None

    e_mean = float(np.mean(energies[equil:])) if len(energies) > equil else float(np.mean(energies))
    return MDResult(metal=metal, surface=SURFACE_FACET.get(metal, ""), temperature=temperature,
                    e_mean_ev=round(e_mean, 4), e_mean_kjmol=round(e_mean * 96.485, 2),
                    rdf_r=r.tolist(), rdf_metal_O=g_mO.tolist(), rdf_metal_N=g_mN.tolist(),
                    first_peak_metal_O=_peak(g_mO), first_peak_metal_N=_peak(g_mN),
                    energies=energies, final_positions=p, mol_symbols=m_sym, slab=slab)
