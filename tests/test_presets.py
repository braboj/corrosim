import pytest

from corrosim import ARGHEL, build_molecule, case_study
from corrosim.presets import CaseStudy


def test_arghel_is_the_single_source_of_truth():
    assert ARGHEL.molecules == ("kaempferol", "quercetin", "isorhamnetin")
    assert ARGHEL.metal == "Fe(110)"
    assert ARGHEL.metal_element == "Fe"          # slab/RDF code uses the bare symbol
    assert ARGHEL.medium == "1 M HCl"
    assert ARGHEL.source                          # provenance is recorded
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
    # each study self-describes one co-located subtree, so runs never collide
    assert ARGHEL.case_dir == "cases/arghel"
    assert ARGHEL.results_dir == "cases/arghel/results"
    assert ARGHEL.report_dir == "cases/arghel/report"
    other = CaseStudy(name="phytic-acid", molecules=("phytic acid",))
    assert other.case_dir == "cases/phytic-acid"
    assert other.results_dir == "cases/phytic-acid/results"
    assert other.report_dir == "cases/phytic-acid/report"


def test_source_defaults_empty_for_an_original_screen():
    # an original screen carries no citation; a validation preset does
    assert CaseStudy(name="x", molecules=("caffeine",)).source == ""


def test_phytic_acid_validation_preset():
    case = case_study("phytic-acid")
    assert case.molecules == ("phytic acid",)
    assert case.metal == "Fe(110)" and case.metal_element == "Fe"
    assert case.medium == "0.5 M H2SO4"           # exercises the sulfuric path
    assert "Chidiebere" in case.source and "10.1021/ie404382v" in case.source
    assert case.results_dir == "cases/phytic-acid/results"
    # aliases resolve to the same preset (case-insensitive)
    assert case_study("phytic") is case is case_study("Phytic_Acid")
    # the inhibitor is in the shipped library and builds offline
    assert build_molecule("phytic acid") is not None


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
