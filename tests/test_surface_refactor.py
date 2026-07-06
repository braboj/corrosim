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

from corrosim import build_molecule
from corrosim.adsorption import surface
from corrosim.adsorption.mc import run_mc
from corrosim.adsorption.md import run_md


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


def test_orient_flat_puts_least_spread_axis_on_z():
    """The molecular plane must lie in xy so the slab sees maximum contact:
    the thinnest (least-variance) axis maps to z (issue #47). The isometry test
    above cannot catch a wrong orientation, since any rotation is an isometry."""
    rng = np.random.default_rng(0)
    n = 40
    # a markedly anisotropic slab (wide-x, medium-y, thin-z) ...
    cloud = np.column_stack([rng.normal(0, 5, n), rng.normal(0, 2, n),
                             rng.normal(0, 0.05, n)])
    # ... tumbled to an arbitrary orientation, then re-flattened
    cloud = cloud @ surface.rot(np.array([0.3, -0.7, 0.5]), 1.1).T
    std = surface.orient_flat(cloud).std(axis=0)
    assert np.argmin(std) == 2            # thin axis recovered on z, not x
    assert std[2] < std[0] and std[2] < std[1]


def test_single_source_no_duplicate_definitions():
    """mc/md/adsorption must reference surface's objects, not private copies —
    one facet map, one vdW field, one pose helper, one unit constant (#4, #57)."""
    import corrosim.adsorption.adsorption as ads
    import corrosim.adsorption.mc as mc
    import corrosim.adsorption.md as md
    from corrosim.report import equations

    # the facet map / vdW machinery are shared, not re-defined
    for mod in (ads, mc, md):
        assert mod.SURFACE_FACET is surface.SURFACE_FACET
        assert mod.uff_mixing is surface.uff_mixing
        assert mod.initial_adsorption_pose is surface.initial_adsorption_pose
        assert mod.EV_TO_KJMOL is surface.EV_TO_KJMOL
    # the slab is built once — adsorption calls build_slab directly, mc/md go
    # through the shared Substrate; no per-module copy of either
    assert ads.build_slab is surface.build_slab
    for mod in (ads, mc, md):
        assert mod.Substrate is surface.Substrate
    # one LJ implementation: energy (mc, adsorption) + energy-with-forces (md)
    assert mc.uff_vdw_energy is surface.uff_vdw_energy
    assert ads.uff_vdw_energy is surface.uff_vdw_energy
    assert md.uff_vdw_forces is surface.uff_vdw_forces
    assert mc.rot is surface.rot and md.rot is surface.rot
    # the report's conversion constant is surface's, no longer a private copy
    assert equations.EV_TO_KJMOL is surface.EV_TO_KJMOL


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
