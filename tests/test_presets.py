import pytest

from corrosim import ARGHEL, case_study


def test_arghel_is_the_single_source_of_truth():
    assert ARGHEL.molecules == ("kaempferol", "quercetin", "isorhamnetin")
    assert ARGHEL.metal == "Fe(110)"
    assert ARGHEL.metal_element == "Fe"          # slab/RDF code uses the bare symbol
    assert ARGHEL.medium == "1 M HCl"
    # a fresh mutable copy each call, so a driver can't clobber the preset
    lst = ARGHEL.molecule_list()
    lst.append("caffeine")
    assert "caffeine" not in ARGHEL.molecules


def test_case_study_lookup():
    assert case_study("arghel") is ARGHEL
    assert case_study("Argel") is ARGHEL          # case-insensitive alias
    with pytest.raises(KeyError):
        case_study("nope")


def test_drivers_share_the_preset_list():
    # the run drivers must derive their defaults from ARGHEL, not re-declare them
    from corrosim.runs import make_report, run_dft, run_mc
    assert run_dft.DEFAULT_MOLECULES == list(ARGHEL.molecules)
    assert run_mc.DEFAULT_MOLECULES == list(ARGHEL.molecules)
    assert make_report.ORDER == list(ARGHEL.molecules)
