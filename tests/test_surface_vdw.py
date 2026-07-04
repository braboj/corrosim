"""Unit tests for the shared UFF vdW machinery extracted in issue #57.

The pair energy is checked against a hand-derived two-atom case (at the pair
equilibrium distance x_ij the LJ 12-6 energy is exactly -D_ij), and the MD
forces against a central finite difference of the energy — so the shared
implementation is pinned to the physics, not to its former per-module copies.
"""
from __future__ import annotations

import numpy as np
import pytest

from corrosim import build_molecule
from corrosim.adsorption import surface


def test_uff_mixing_two_elements_geometric_rule():
    x_mix, D_mix = surface.uff_mixing(["O"], ["Fe", "C"])
    x_o, d_o = surface.UFF["O"]
    x_fe, d_fe = surface.UFF["Fe"]
    assert x_mix.shape == (1, 2) and D_mix.shape == (1, 2)
    assert np.isclose(x_mix[0, 0], np.sqrt(x_o * x_fe))
    assert np.isclose(D_mix[0, 0], np.sqrt(d_o * d_fe))


def test_uff_mixing_unknown_element_raises():
    with pytest.raises(ValueError, match="Se"):
        surface.uff_mixing(["Se"], ["Fe"])


def test_uff_vdw_energy_two_atom_equilibrium_is_minus_well_depth():
    # one O at the pair equilibrium distance above one Fe: t = (x_ij/r)^6 = 1,
    # so E = D_ij (t^2 - 2t) = -D_ij (kcal/mol), converted to eV
    x_mix, D_mix = surface.uff_mixing(["O"], ["Fe"])
    mol = np.array([[0.0, 0.0, float(x_mix[0, 0])]])
    slab = np.array([[0.0, 0.0, 0.0]])
    e = surface.uff_vdw_energy(mol, slab, x_mix, D_mix)
    assert np.isclose(e, -float(D_mix[0, 0]) * surface.KCAL_TO_EV)


def test_uff_vdw_forces_match_energy_and_finite_difference():
    # a small seeded O/C/N cluster ~4 A above a 5-atom Fe patch (all pair
    # distances well beyond the close-contact clamp, where E is smooth)
    rng = np.random.default_rng(1)
    mol = rng.normal(0.0, 1.0, (3, 3)) + np.array([0.0, 0.0, 4.0])
    slab = rng.normal(0.0, 1.0, (5, 3)) * np.array([2.0, 2.0, 0.2])
    x_mix, D_mix = surface.uff_mixing(["O", "C", "N"], ["Fe"] * 5)

    e0, f = surface.uff_vdw_forces(mol, slab, x_mix, D_mix)
    assert e0 == surface.uff_vdw_energy(mol, slab, x_mix, D_mix)
    assert f.shape == mol.shape

    # f = -dE/dr, checked coordinate-by-coordinate by central difference
    h = 1e-6
    for i in range(mol.shape[0]):
        for k in range(3):
            plus, minus = mol.copy(), mol.copy()
            plus[i, k] += h
            minus[i, k] -= h
            de = (surface.uff_vdw_energy(plus, slab, x_mix, D_mix)
                  - surface.uff_vdw_energy(minus, slab, x_mix, D_mix)) / (2 * h)
            assert np.isclose(f[i, k], -de, rtol=1e-5, atol=1e-10)


def test_initial_adsorption_pose_centers_and_lifts():
    slab = surface.build_slab("Fe", size=(4, 4, 2))
    cell = slab.get_cell()
    top = float(slab.get_positions()[:, 2].max())
    m = build_molecule("caffeine")

    pos = surface.initial_adsorption_pose(m.coords, cell, top, 3.0)
    assert np.isclose(pos[:, 2].min(), top + 3.0)
    assert np.isclose(pos[:, 0].mean(), cell[0, 0] / 2.0)
    assert np.isclose(pos[:, 1].mean(), cell[1, 1] / 2.0)
