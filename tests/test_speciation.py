"""pH-speciation: Henderson–Hasselbalch fraction, blending, and lead crossover
(issue #8 follow-up / ADR 0004)."""
import math

from corrosim.speciation import (
    analyse_speciation,
    blend_descriptors,
    pkah_for_fraction,
    protonation_fraction,
    speciate,
)


def test_fraction_is_half_at_ph_equals_pkah():
    assert protonation_fraction(ph=-1.5, pkah=-1.5) == 0.5


def test_fraction_limits():
    assert protonation_fraction(ph=-5, pkah=0) > 0.99       # pH << pKaH -> protonated
    assert protonation_fraction(ph=5, pkah=0) < 0.01        # pH >> pKaH -> neutral


def test_pkah_for_fraction_is_the_inverse():
    ph = 0.0
    for f in (0.03, 0.2, 0.5, 0.8):
        pkah = pkah_for_fraction(ph, f)
        assert math.isclose(protonation_fraction(ph, pkah), f, abs_tol=1e-9)


def test_speciate_dominant_form():
    assert speciate(ph=0.0, pkah=-1.5).dominant == "neutral"     # ~3% protonated
    assert speciate(ph=0.0, pkah=1.0).dominant == "protonated"   # ~91% protonated


def test_blend_endpoints_and_weighting():
    n = {"name": "x", "gap_ev": 4.0, "form": "neutral"}
    p = {"name": "x+H+", "gap_ev": 3.0, "form": "protonated"}
    assert blend_descriptors(n, p, 0.0)["gap_ev"] == 4.0        # all neutral
    assert blend_descriptors(n, p, 1.0)["gap_ev"] == 3.0        # all protonated
    mid = blend_descriptors(n, p, 0.25)
    assert mid["gap_ev"] == 3.75 and mid["form"] == "pH-weighted"


def test_analyse_speciation_finds_lead_crossover():
    # neutral lead = A (smaller gap); protonated lead = B (its cation drops further)
    neutral = [{"name": "A", "gap_ev": 4.0}, {"name": "B", "gap_ev": 4.1}]
    protonated = [{"name": "A+H+", "gap_ev": 3.5}, {"name": "B+H+", "gap_ev": 3.0}]
    rank_by_gap = lambda rows: sorted(rows, key=lambda r: r["gap_ev"])

    s = analyse_speciation(neutral, protonated, ph=0.0, rank_fn=rank_by_gap, pkah=-1.5)
    assert s["neutral_lead"] == "A"
    assert s["blended_lead"] == "A"                 # ~3% protonated -> still A
    assert s["crossover_lead"] == "B"
    assert 0.15 <= s["crossover_fraction"] <= 0.18  # B overtakes near 1/6
