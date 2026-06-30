"""Medium parsing + the acid -> protonation selection logic (issue #8 / ADR 0003)."""
from corrosim.medium import parse_medium, relevant_forms


def test_parse_strong_acid_molarity_gives_low_ph_and_acidic():
    s = parse_medium("1 M HCl")
    assert s.species == "HCL" and s.concentration_M == 1.0
    assert s.ph == 0.0 and s.acidic


def test_parse_diprotic_acid_counts_both_protons():
    s = parse_medium("0.5 M H2SO4")            # 2 x 0.5 = 1 M H+ -> pH 0
    assert s.ph == 0.0 and s.acidic


def test_parse_explicit_ph_buffer_is_not_acidic():
    s = parse_medium("pH 7 buffer")
    assert s.ph == 7.0 and not s.acidic


def test_parse_explicit_low_ph_is_acidic():
    assert parse_medium("pH 1").acidic


def test_parse_neutral_salt_is_not_acidic():
    s = parse_medium("3.5% NaCl")
    assert not s.acidic and s.ph is None


def test_parse_unknown_medium_never_raises():
    s = parse_medium("some exotic electrolyte")
    assert s.label == "some exotic electrolyte" and not s.acidic


def test_relevant_forms_tracks_acidity():
    assert relevant_forms(parse_medium("1 M HCl")) == {"neutral", "protonated"}
    assert relevant_forms(parse_medium("pH 7 buffer")) == {"neutral"}
