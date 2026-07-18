"""Substrate-agnostic Brownian MD: the metal threads through to the slab and the
RDF, plus unit tests for the helpers and state objects run_md assembles."""
from __future__ import annotations

import numpy as np

from corrosim import build_molecule
from corrosim.adsorption.md import (
    MDResult,
    _mean_energy,
    _RdfAccumulator,
    run_md,
)
from corrosim.adsorption.surface import Substrate


def test_md_metal_threads_to_slab_and_rdf():
    m = build_molecule("caffeine")                 # has both O and N donors
    cu = run_md(m, metal="Cu", n_steps=150, equil=50, seed=0)

    assert cu.metal == "Cu"
    assert cu.surface == "(111)"                    # Cu -> fcc(111), not Fe(110)
    assert set(cu.slab.get_chemical_symbols()) == {"Cu"}   # slab really is Cu

    # the metal–O/N contact distributions align with the shared distance grid
    assert len(cu.rdf_metal_O) == len(cu.rdf_r)
    assert len(cu.rdf_metal_N) == len(cu.rdf_r)


def test_md_surface_differs_by_metal():
    m = build_molecule("caffeine")
    fe = run_md(m, metal="Fe", n_steps=80, equil=20, seed=0)
    assert fe.metal == "Fe" and fe.surface == "(110)"   # Fe -> bcc(110)


# --- _mean_energy ------------------------------------------------------------

def test_mean_energy_discards_pre_equilibration_transient():
    energies = [100.0, 100.0, -2.0, -4.0]   # 2 equil steps, then the plateau
    assert _mean_energy(energies, equil=2) == -3.0


def test_mean_energy_averages_all_when_run_not_longer_than_equil():
    # len == equil -> nothing to discard, average everything
    assert _mean_energy([-1.0, -3.0], equil=2) == -2.0


def test_mean_energy_empty_run_is_nan_without_warning():
    # #267: a zero-step run must not emit a np.mean([]) RuntimeWarning
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")            # any RuntimeWarning fails
        assert np.isnan(_mean_energy([], equil=0))


# --- Substrate.build --------------------------------------------------------

def test_substrate_build_caches_metal_positions_and_top():
    sub = Substrate.build("Fe", (3, 3, 2), 10.0)
    assert sub.top == sub.positions[:, 2].max()
    # a single-metal slab: every atom is Fe, so metal_positions is the full set
    assert sub.metal_positions.shape == sub.positions.shape
    assert (sub.symbols == "Fe").all()


# --- _RdfAccumulator ---------------------------------------------------------

def _accumulator(o_idx: list[int], n_idx: list[int]) -> _RdfAccumulator:
    """An accumulator with one metal atom at the origin on a 0..3 Å grid."""
    edges = np.array([0.0, 1.0, 2.0, 3.0])
    return _RdfAccumulator(o_idx=o_idx, n_idx=n_idx,
                           metal_positions=np.zeros((1, 3)), edges=edges,
                           hist_o=np.zeros(3), hist_n=np.zeros(3))


def test_rdf_accumulator_records_closest_contact_per_frame():
    acc = _accumulator(o_idx=[0], n_idx=[])
    # donor O at z=1.5 above the metal -> distance 1.5 -> bin [1, 2)
    acc.record(np.array([[0.0, 0.0, 1.5]]))
    assert acc.nframes == 1
    assert acc.hist_o.tolist() == [0.0, 1.0, 0.0]
    assert acc.hist_n.tolist() == [0.0, 0.0, 0.0]   # empty N set -> no counts


def test_rdf_accumulator_normalized_divides_by_frame_count():
    acc = _accumulator(o_idx=[0], n_idx=[])
    acc.record(np.array([[0.0, 0.0, 1.5]]))
    acc.record(np.array([[0.0, 0.0, 1.5]]))
    rdf_o, _ = acc.normalized()
    assert rdf_o.tolist() == [0.0, 1.0, 0.0]        # 2 counts / 2 frames


def test_rdf_accumulator_normalized_no_frames_is_zero_not_nan():
    acc = _accumulator(o_idx=[0], n_idx=[0])
    rdf_o, rdf_n = acc.normalized()                 # divide by max(0, 1) = 1
    assert not np.isnan(rdf_o).any() and rdf_o.sum() == 0.0
    assert not np.isnan(rdf_n).any()


def test_rdf_accumulator_bin_centres_are_edge_midpoints():
    acc = _accumulator(o_idx=[], n_idx=[])
    assert acc.bin_centres().tolist() == [0.5, 1.5, 2.5]


def test_rdf_accumulator_for_donors_keys_o_and_n_indices():
    sub = Substrate.build("Fe", (3, 3, 2), 10.0)
    acc = _RdfAccumulator.for_donors(["O", "C", "N", "O"], sub)
    assert acc.o_idx == [0, 3] and acc.n_idx == [2]
    assert acc.hist_o.shape == acc.hist_n.shape and acc.nframes == 0


# --- MDResult.from_run -------------------------------------------------------

def test_from_run_rounds_energy_sets_facet_and_empty_rdf_has_no_peak():
    sub = Substrate.build("Fe", (3, 3, 2), 10.0)
    acc = _RdfAccumulator.for_donors([], sub)       # no donors -> zero RDF
    energies = [-1.11111, -2.22222]
    res = MDResult.from_run("Fe", sub, acc, energies, sub.positions[:1],
                            ["C"], temperature=298.0, equil=0)
    assert res.surface == "(110)"
    assert res.e_mean_ev == round(float(np.mean(energies)), 4)
    assert res.temperature == 298.0 and res.mol_symbols == ["C"]
    assert res.first_peak_metal_O is None           # empty RDF -> no peak
