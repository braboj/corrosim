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


def test_case_study_output_dirs_are_per_case():
    # each study self-describes its own output subtree, so runs never collide
    assert ARGHEL.results_dir == "results/arghel"
    assert ARGHEL.report_dir == "report/arghel"
    other = ARGHEL.__class__(name="phytic-acid", molecules=("phytic acid",))
    assert other.results_dir == "results/phytic-acid"
    assert other.report_dir == "report/phytic-acid"


def test_drivers_share_the_preset_list():
    # the run drivers must derive their defaults from the case study via the one
    # shared _cli helper, not re-declare the list (issues #64 single-sourcing)
    import argparse

    from corrosim.runs import (
        _cli,
        compare_geometry,
        make_figures,
        make_report,
        run_dft,
        run_fukui,
        run_mc,
        run_md,
        run_pka,
    )

    # an unset --molecules resolves to exactly the default case-study list
    p = argparse.ArgumentParser()
    _cli.add_case_arg(p)
    _cli.add_molecules_arg(p)
    args = p.parse_args([])
    _cli.resolve_case(args)
    assert _cli.parse_molecules(args.molecules) == list(ARGHEL.molecules)

    # every molecule-taking driver wires the shared helpers (no private default)
    for drv in (run_dft, run_fukui, run_mc, run_md, run_pka):
        assert drv.add_molecules_arg is _cli.add_molecules_arg
    for drv in (run_dft, run_fukui, run_mc, run_md, run_pka,
                make_report, make_figures, compare_geometry):
        assert drv.resolve_case is _cli.resolve_case
