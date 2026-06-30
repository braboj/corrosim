"""Safety net for the shared-surface refactor (issue #4).

Moving the vdW params, slab builder, flat-orientation, rotation and the
metal->facet map into `corrosim.surface` must not change the physics or
re-duplicate state. We deliberately do NOT pin end-to-end seeded run_mc/run_md
values: the Metropolis / Brownian trajectories are chaotic w.r.t. ~1e-15
floating-point differences (an accept/reject or a clip can flip), so although
the PCG64 stream is identical across platforms the *trajectory* is only
same-platform reproducible — a hard-coded golden would be CI-flaky, not a real
regression signal.

Instead we pin what the refactor actually moved, with platform-stable checks:
  * the constants / lattice / facet map (exact),
  * `rot` (pure trig) and `orient_flat`'s isometry invariant,
  * object identity proving mc/md/adsorption share surface's single source
    (this is the DRY/cohesion guarantee: one facet map, no private copies),
  * seeded determinism within a single platform.
"""
from __future__ import annotations

import numpy as np

from corrosim import build_molecule, surface
from corrosim.mc import run_mc
from corrosim.md import run_md


def test_surface_constants_and_facet_map_unchanged():
    assert surface.KCAL_TO_EV == 0.0433641
    assert surface.SURFACE_FACET == {"Fe": "(110)", "Cu": "(111)", "Al": "(111)"}
    assert surface.METAL_LATTICE == {
        "Fe": ("bcc", 2.8665), "Cu": ("fcc", 3.6149), "Al": ("fcc", 4.0495)
    }
    # representative UFF (x_vdw [A], D [kcal/mol]) entries — Rappe et al. 1992
    assert surface.UFF["Fe"] == (2.912, 0.013)
    assert surface.UFF["O"] == (3.500, 0.060)
    assert surface.UFF["N"] == (3.660, 0.069)
    assert surface.UFF["C"] == (3.851, 0.105)


def test_rot_is_known_rotation():
    # 90 deg about +z maps x->y, y->-x
    R = surface.rot(np.array([0.0, 0.0, 1.0]), np.pi / 2)
    assert np.allclose(R, [[0, -1, 0], [1, 0, 0], [0, 0, 1]], atol=1e-9)


def test_orient_flat_is_centered_isometry():
    m = build_molecule("caffeine")
    out = surface.orient_flat(m.coords)
    # centred, and a pure rotation preserves total variance (trace of covariance)
    assert np.allclose(out.mean(axis=0), 0.0, atol=1e-9)
    assert np.isclose(out.var(axis=0).sum(), np.asarray(m.coords).var(axis=0).sum())


def test_single_source_no_duplicate_definitions():
    """mc/md/adsorption must reference surface's objects, not private copies —
    so there is exactly one facet map / UFF table / rotation helper."""
    import corrosim.adsorption as ads
    import corrosim.mc as mc
    import corrosim.md as md

    # the facet map is single-sourced (was duplicated in adsorption + mc._SURFACE)
    assert mc.SURFACE_FACET is surface.SURFACE_FACET
    assert md.SURFACE_FACET is surface.SURFACE_FACET
    # the vdW table and slab builder are shared, not re-defined
    for mod in (ads, mc, md):
        assert mod.UFF is surface.UFF
        assert mod.build_slab is surface.build_slab
    assert mc.rot is surface.rot and md.rot is surface.rot
    assert mc.orient_flat is surface.orient_flat and md.orient_flat is surface.orient_flat


def test_run_mc_md_seeded_reproducible():
    """Same seed -> identical result within a platform (the determinism the
    refactor must preserve)."""
    m = build_molecule("caffeine")
    a = run_mc(m, metal="Fe", size=(4, 4, 2), n_steps=120, seed=0)
    b = run_mc(m, metal="Fe", size=(4, 4, 2), n_steps=120, seed=0)
    assert a.e_ads_ev == b.e_ads_ev and a.best_height_A == b.best_height_A
    assert a.surface == "(110)"

    c = run_md(m, metal="Fe", size=(4, 4, 2), n_steps=120, equil=40, seed=0)
    d = run_md(m, metal="Fe", size=(4, 4, 2), n_steps=120, equil=40, seed=0)
    assert c.first_peak_metal_O == d.first_peak_metal_O
    assert c.e_mean_ev == d.e_mean_ev
