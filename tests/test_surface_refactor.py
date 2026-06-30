"""Regression safety net for the shared-surface refactor (issue #4).

Moving the vdW params, slab builder, flat-orientation, rotation and the
metal->facet map into `corrosim.surface` must not change the physics. These
seeded run_mc / run_md results pin the pre-refactor values: discrete observables
(facet, clamped height, RDF bin-center peaks) are asserted exactly; the
continuous UFF interaction energies use a tight absolute tolerance so the test
stays robust to cross-platform float noise (CI runs on Linux) while still
catching any real change.
"""
from __future__ import annotations

import pytest

from corrosim import build_molecule
from corrosim.mc import run_mc
from corrosim.md import run_md


def test_run_mc_seeded_values_unchanged():
    m = build_molecule("caffeine")            # has both O and N donors
    mc = run_mc(m, metal="Fe", size=(4, 4, 2), n_steps=500, seed=0)
    assert mc.surface == "(110)"              # Fe -> bcc(110)
    assert mc.best_height_A == 2.0            # clamped to min_height
    assert mc.e_ads_ev == pytest.approx(-0.0527, abs=1e-3)
    assert mc.e_ads_kjmol == pytest.approx(-5.08, abs=0.1)


def test_run_md_seeded_values_unchanged():
    m = build_molecule("caffeine")
    md = run_md(m, metal="Fe", size=(4, 4, 2), n_steps=300, equil=100, seed=0)
    assert md.surface == "(110)"
    assert md.first_peak_metal_O == 3.55      # RDF bin centre, discrete
    assert md.first_peak_metal_N == 3.75
    assert md.e_mean_ev == pytest.approx(-0.014, abs=1e-3)
