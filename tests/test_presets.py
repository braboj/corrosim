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
    # the run drivers must derive their molecule default from ARGHEL via the one
    # shared _cli helper, not re-declare the list (issues #64 single-sourcing)
    import argparse

    from corrosim.runs import (
        _cli,
        make_report,
        run_dft,
        run_fukui,
        run_mc,
        run_md,
        run_pka,
    )

    # the shared --molecules argument defaults to exactly the preset list
    p = argparse.ArgumentParser()
    _cli.add_molecules_arg(p)
    assert _cli.parse_molecules(p.parse_args([]).molecules) == list(ARGHEL.molecules)

    # every molecule-taking driver wires that one helper (no private default)
    for drv in (run_dft, run_fukui, run_mc, run_md, run_pka):
        assert drv.add_molecules_arg is _cli.add_molecules_arg
    assert make_report.ORDER == list(ARGHEL.molecules)
