"""Unit tests for the Monte Carlo step helpers that run_mc assembles.

These pin the *invariants* of each extracted step — a rigid isometry for the
proposal, the box-clamp bounds for the confinement, the anneal endpoints, and
the Metropolis accept/reject logic — rather than any seeded trajectory value:
the annealed walk is chaotic w.r.t. ~1e-15 float differences, so a hard-coded
pose would be CI-flaky, not a regression signal (same rationale as
tests/test_surface_refactor.py).
"""
from __future__ import annotations

import numpy as np

from corrosim.adsorption.mc import (
    MCResult,
    _anneal_schedule,
    _confine_pose,
    _propose_pose,
    _Search,
)
from corrosim.adsorption.surface import Substrate


def _pdist(p: np.ndarray) -> np.ndarray:
    """All pairwise atom-atom distances of a pose (the rigid-shape fingerprint)."""
    return np.linalg.norm(p[:, None, :] - p[None, :, :], axis=2)


# --- _propose_pose -----------------------------------------------------------

def test_propose_pose_seeded_reproducible():
    pos = np.array([[0.0, 0.0, 8.0], [1.0, 0.0, 8.0],
                    [0.0, 1.0, 8.0], [0.0, 0.0, 9.0]])
    com = pos.mean(0)
    a = _propose_pose(pos, com, 0.5, np.random.default_rng(0))
    b = _propose_pose(pos, com, 0.5, np.random.default_rng(0))
    assert np.array_equal(a, b)


def test_propose_pose_preserves_rigid_shape():
    pos = np.array([[0.0, 0.0, 8.0], [1.5, 0.0, 8.0],
                    [0.0, 2.0, 8.0], [0.3, 0.4, 9.2]])
    com = pos.mean(0)
    trial = _propose_pose(pos, com, 0.8, np.random.default_rng(3))
    # rotation + translation is an isometry: pairwise distances are unchanged
    np.testing.assert_allclose(_pdist(trial), _pdist(pos), atol=1e-9)


def test_propose_pose_does_not_mutate_input():
    pos = np.array([[0.0, 0.0, 8.0], [1.0, 0.0, 8.0], [0.0, 1.0, 8.0]])
    original = pos.copy()
    _propose_pose(pos, pos.mean(0), 0.5, np.random.default_rng(1))
    np.testing.assert_array_equal(pos, original)


def test_propose_pose_zero_scale_is_identity_move():
    # scale=0 zeroes both amplitudes: angle 0 -> identity rotation, no shift
    pos = np.array([[0.0, 0.0, 8.0], [1.0, 0.0, 8.0], [0.0, 1.0, 8.0]])
    trial = _propose_pose(pos, pos.mean(0), 0.0, np.random.default_rng(2))
    np.testing.assert_allclose(trial, pos, atol=1e-12)


# --- _confine_pose -----------------------------------------------------------

# top-of-slab z, box window [top+2, top+5] = [7, 10], and a 10x10 footprint
_TOP = 5.0
_CELL = np.diag([10.0, 10.0, 20.0])
_MIN, _MAX = 2.0, 5.0


def test_confine_pose_below_window_lifts_to_min_height():
    pose = np.array([[3.0, 3.0, 6.0], [4.0, 3.0, 6.5], [3.5, 4.0, 6.2]])
    out = _confine_pose(pose.copy(), _TOP, _CELL, _MIN, _MAX)
    # nearest atom starts below top+min_height -> lifted to sit exactly on it
    assert out[:, 2].min() == _TOP + _MIN


def test_confine_pose_above_window_drops_to_max_height():
    pose = np.array([[3.0, 3.0, 12.0], [4.0, 3.0, 12.5], [3.5, 4.0, 13.0]])
    out = _confine_pose(pose.copy(), _TOP, _CELL, _MIN, _MAX)
    assert out[:, 2].min() == _TOP + _MAX


def test_confine_pose_within_window_leaves_z_unchanged():
    pose = np.array([[3.0, 3.0, 8.0], [4.0, 3.0, 8.5], [3.5, 4.0, 9.0]])
    out = _confine_pose(pose.copy(), _TOP, _CELL, _MIN, _MAX)
    np.testing.assert_array_equal(out[:, 2], pose[:, 2])


def test_confine_pose_clamps_centroid_into_footprint():
    # centroid at x=15 (past the 10-Å edge) and y=-1 (below 0) is pulled back
    pose = np.array([[14.0, -2.0, 8.0], [16.0, 0.0, 8.0], [15.0, -1.0, 9.0]])
    out = _confine_pose(pose.copy(), _TOP, _CELL, _MIN, _MAX)
    com = out.mean(0)
    assert com[0] == 10.0 and com[1] == 0.0


def test_confine_pose_is_pure_translation():
    # every clamp is a whole-body shift, so the rigid shape must survive intact
    pose = np.array([[14.0, -2.0, 6.0], [16.0, 0.0, 6.0], [15.0, -1.0, 9.5]])
    out = _confine_pose(pose.copy(), _TOP, _CELL, _MIN, _MAX)
    np.testing.assert_allclose(_pdist(out), _pdist(pose), atol=1e-12)


# --- _anneal_schedule --------------------------------------------------------

def test_anneal_schedule_step_zero_is_hot_and_full_scale():
    kT, scale = _anneal_schedule(0, 100, 0.05, 0.003)
    assert kT == 0.05 and scale == 1.0


def test_anneal_schedule_cools_and_shrinks_monotonically():
    kT_early, scale_early = _anneal_schedule(10, 100, 0.05, 0.003)
    kT_late, scale_late = _anneal_schedule(90, 100, 0.05, 0.003)
    assert kT_late < kT_early           # geometric cooling
    assert scale_late < scale_early     # trial moves shrink as it cools
    assert 0.0 < scale_late <= 1.0


# --- _Search.accept ----------------------------------------------------------

def _state(e: float, best_e: float) -> _Search:
    """A two-atom search state pinned to given current / best energies."""
    pos = np.array([[0.0, 0.0, 8.0], [1.0, 0.0, 8.0]])
    return _Search(pos=pos, e=e, com=pos.mean(0), best_e=best_e,
                   best_pos=pos.copy(), n_accept=0, energies=[e])


def test_accept_downhill_move_accepted_and_best_updated():
    # a lower energy is accepted with no rng draw (the first short-circuit)
    s = _state(e=-1.0, best_e=-1.0)
    trial = np.array([[0.0, 0.0, 9.0], [1.0, 0.0, 9.0]])
    s.accept(trial, -2.0, 0.01, np.random.default_rng(0))
    assert s.e == -2.0 and s.best_e == -2.0 and s.n_accept == 1
    np.testing.assert_array_equal(s.pos, trial)
    assert s.energies == [-1.0, -2.0]


def test_accept_downhill_but_not_best_holds_best():
    # accepted (below current e) yet above the running best -> best is held
    s = _state(e=-1.0, best_e=-3.0)
    trial = np.array([[0.0, 0.0, 9.0], [1.0, 0.0, 9.0]])
    s.accept(trial, -2.0, 0.01, np.random.default_rng(0))
    assert s.e == -2.0 and s.best_e == -3.0 and s.n_accept == 1


def test_accept_strong_uphill_rejected_regardless_of_rng():
    # exp(-Δ/kT) underflows to 0 for a large uphill move, so any draw in
    # [0, 1) fails the test -> a deterministic reject, pose unchanged
    s = _state(e=-2.0, best_e=-2.0)
    before = s.pos.copy()
    trial = np.array([[0.0, 0.0, 9.0], [1.0, 0.0, 9.0]])
    s.accept(trial, 50.0, 1e-6, np.random.default_rng(0))
    assert s.e == -2.0 and s.n_accept == 0
    np.testing.assert_array_equal(s.pos, before)
    assert s.energies == [-2.0, -2.0]


# --- factories: Substrate.build / _Search.seed / MCResult.from_search -------

def test_substrate_build_caches_top_and_positions():
    sub = Substrate.build("Fe", (3, 3, 2), 10.0)
    assert sub.top == sub.positions[:, 2].max()
    assert sub.positions.shape == (len(sub.slab), 3)


def test_search_seed_starts_current_pose_as_best():
    from corrosim import build_molecule
    from corrosim.adsorption.surface import uff_mixing
    mol = build_molecule("caffeine")
    sub = Substrate.build("Fe", (3, 3, 2), 10.0)
    x_mix, D_mix = uff_mixing(mol.symbols, sub.slab.get_chemical_symbols())
    s = _Search.seed(mol, sub, x_mix, D_mix)
    assert s.e == s.best_e and s.energies == [s.e] and s.n_accept == 0
    np.testing.assert_array_equal(s.pos, s.best_pos)


def test_from_search_rounds_and_derives_height_and_facet():
    sub = Substrate(slab=None, positions=np.zeros((1, 3)),
                    symbols=np.array(["Fe"]), metal_positions=np.zeros((1, 3)),
                    cell=np.eye(3), top=5.0)
    pos = np.array([[0.0, 0.0, 8.0]])
    s = _Search(pos=pos, e=-1.0, com=pos.mean(0), best_e=-1.23456,
                best_pos=pos, n_accept=3, energies=[-1.0, -1.23456])
    res = MCResult.from_search("Fe", sub, s, ["C"], 100)
    assert res.e_ads_ev == -1.2346          # rounded to 4 dp
    assert res.best_height_A == 3.0         # 8.0 nearest-atom z - 5.0 top
    assert res.surface == "(110)"           # SURFACE_FACET["Fe"]
    assert res.n_accept == 3 and res.n_steps == 100
