"""Canonical-basis selection + robustness gate (ADR 0021).

The composite ranking is reported on one canonical basis (best geometry x
pH-weighted speciation); the lead is asserted only when every available basis
agrees on it, else the report calls a tie. These pin both paths.
"""
from __future__ import annotations

import pandas as pd

from corrosim.report import ranking


def _row(name: str, gap: float) -> dict:
    """A minimal descriptor row whose ranking is monotonic in the gap.

    hardness = gap / 2 and softness = 2 / gap, so a smaller gap wins on every
    component and the composite order is exactly the gap order — which keeps the
    fixtures readable.
    """
    return {"name": name, "gap_ev": gap, "hardness_ev": gap / 2,
            "softness_inv_ev": 2 / gap, "delta_n": 0.2}


def test_rank_inhibitors_orders_smallest_gap_first():
    ranked = ranking.rank_inhibitors(pd.DataFrame(
        [_row("A", 4.0), _row("B", 4.4), _row("C", 4.6)]))
    assert list(ranked["name"]) == ["A", "B", "C"]


def test_rank_inhibitors_breaks_score_ties_by_name():
    # Two molecules with identical descriptors score identically (a 3-dp tie);
    # the deterministic name tie-break must order them A before B regardless of
    # input row order, so the highlighted lead never flips across runs.
    ranked = ranking.rank_inhibitors(pd.DataFrame(
        [_row("B", 4.0), _row("A", 4.0), _row("C", 4.6)]))
    assert list(ranked["name"]) == ["A", "B", "C"]
    assert ranked.iloc[0]["score"] == ranked.iloc[1]["score"]


def test_canonical_prefers_relaxed_and_blended():
    neutral = [_row("A", 4.0), _row("B", 4.4)]
    prot = [_row("A+H+", 3.3), _row("B+H+", 3.6)]
    opt = [_row("A", 3.7), _row("B", 4.1)]
    opt_prot = [_row("A+H+", 3.1), _row("B+H+", 3.4)]
    ens = ranking.build_ensemble(neutral, prot, opt, opt_prot, 0.03)
    assert ens.canonical.key == "opt_blend"
    assert {b.key for b in ens.bases} == {
        "ff_neutral", "ff_blend", "opt_neutral", "opt_blend"}


def test_robust_lead_when_every_basis_agrees():
    neutral = [_row("A", 4.0), _row("B", 4.4), _row("C", 4.6)]
    opt = [_row("A", 3.6), _row("B", 4.0), _row("C", 4.3)]
    v = ranking.build_ensemble(neutral, None, opt, None, None).verdict
    assert v.robust and v.lead == "A"
    assert v.coleaders == ()
    assert v.n_bases == 2


def test_tie_when_lead_flips_across_geometry():
    # A wins on the force-field geometry, B once relaxed -> not robust
    neutral = [_row("A", 4.0), _row("B", 4.1), _row("C", 4.6)]
    opt = [_row("A", 4.2), _row("B", 4.0), _row("C", 4.6)]
    v = ranking.build_ensemble(neutral, None, opt, None, None).verdict
    assert not v.robust
    assert v.lead is None
    assert v.coleaders == ("A", "B")
    assert v.laggard == "C"                 # last on both bases


def test_single_basis_is_trivially_robust():
    ens = ranking.build_ensemble(
        [_row("A", 4.0), _row("B", 4.4)], None, None, None, None)
    assert ens.verdict.robust and ens.verdict.lead == "A"
    assert ens.verdict.n_bases == 1
    assert ens.canonical.key == "ff_neutral"


def test_no_blend_basis_without_a_population_weight():
    # protonated rows present but f_protonated None (unknown pH) -> no blend
    neutral = [_row("A", 4.0), _row("B", 4.4)]
    prot = [_row("A+H+", 3.3), _row("B+H+", 3.6)]
    ens = ranking.build_ensemble(neutral, prot, None, None, None)
    assert {b.key for b in ens.bases} == {"ff_neutral"}
