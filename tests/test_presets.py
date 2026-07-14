import pytest

from corrosim import ARGHEL, build_molecule, case_study
from corrosim.presets import (
    CaseStudy,
    is_study_file,
    load_study,
    save_study,
    validate_study,
)


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


def test_pkah_is_a_per_case_field():
    # the conjugate-acid pKaH that drives speciation lives on the case study,
    # not as a hardcoded speciation-module default
    assert ARGHEL.pkah == -1.5                        # flavonoid 4-oxo carbonyl
    # an unspecified basic site falls back to the very-weak-base default
    assert CaseStudy(name="x", molecules=("caffeine",)).pkah == -1.5


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


def test_pyrazolo_pyrimidine_validation_preset():
    case = case_study("pyrazolo-pyrimidine")
    # three derivatives sharing one aromatic core, differing only in the tail
    assert case.molecules == (
        "pyrazolopyrimidine propanoic acid",
        "pyrazolopyrimidine propanamide",
        "pyrazolopyrimidine ethyl ester",
    )
    assert case.metal == "Fe(110)" and case.medium == "1 M HCl"
    # the paper's level equals corrosim production, so it keeps the full diffuse
    # basis (a direct numeric check, unlike phytic acid's 6-31G(d) drop)
    assert case.basis == "6-311++G(d,p)" and case.xc == "b3lyp"
    assert "Awad" in case.source and "s41598-025-19022-6" in case.source
    assert case.results_dir == "cases/pyrazolo-pyrimidine/results"
    # aliases resolve to the same preset (case-insensitive)
    assert case_study("ppp") is case is case_study("Pyrazolo")
    # the three novel compounds are in the shipped library and build offline
    assert all(build_molecule(n) is not None for n in case.molecule_list())


def test_tmp_smx_validation_preset_is_the_first_non_fe_case():
    from corrosim.qm.descriptors import METAL_WORK_FUNCTION

    case = case_study("tmp-smx")
    # the co-trimoxazole antibiotic pair
    assert case.molecules == ("trimethoprim", "sulfamethoxazole")
    # the point of this case: a non-Fe substrate, exercising the fcc(111) slab
    # and the aluminium work function rather than the bcc(110) Fe default
    assert case.metal == "Al(111)" and case.metal_element == "Al"
    assert case.metal in METAL_WORK_FUNCTION       # Al descriptor support is wired
    assert case.medium == "1 M HCl"
    # both basic sites are protonated at pH ~0, so a single case pKaH suffices
    assert case.pkah == 7.1
    # the paper's level equals corrosim production, so a direct numeric check
    assert case.basis == "6-311++G(d,p)" and case.xc == "b3lyp"
    assert "Odozi" in case.source and "10.1016/j.exm.2026.100027" in case.source
    assert case.results_dir == "cases/tmp-smx/results"
    # aliases resolve to the same preset (case-insensitive)
    assert case_study("tmpsmx") is case is case_study("TMP_SMX")
    # both antibiotics are in the shipped library and build offline
    assert all(build_molecule(n) is not None for n in case.molecule_list())


def test_tetrazoles_validation_preset_is_a_copper_case():
    from corrosim.qm.descriptors import METAL_WORK_FUNCTION

    case = case_study("tetrazoles")
    # the four tetrazole derivatives, worst-to-best inhibitor
    assert case.molecules == (
        "tetrazole",
        "5-aminotetrazole",
        "5-phenyltetrazole",
        "1-phenyl-5-mercaptotetrazole",
    )
    # the point of this case: copper, exercising the fcc(111) slab and the Cu
    # work function rather than the bcc(110) Fe default (a second non-Fe metal)
    assert case.metal == "Cu(111)" and case.metal_element == "Cu"
    assert case.metal in METAL_WORK_FUNCTION       # Cu descriptor support is wired
    # the source states only "acidic medium"; modelled as nitric acid so the
    # medium parses as acidic with a defined pH for the speciation blend
    assert case.medium == "1 M HNO3"
    # tetrazoles are weak bases, so the default very-weak-base pKaH applies
    assert case.pkah == -1.5
    # same functional as the source (B3LYP); corrosim's larger production basis
    assert case.basis == "6-311++G(d,p)" and case.xc == "b3lyp"
    assert "Surface Science" in case.source
    assert "10.1016/j.susc.2020.121692" in case.source
    assert case.results_dir == "cases/tetrazoles/results"
    # aliases resolve to the same preset (case-insensitive)
    assert case_study("tz") is case is case_study("Tetrazoles-Cu")
    # the abbreviations also resolve as library molecules that build offline
    assert build_molecule("PMTZ").smiles == "Sc1nnnn1-c1ccccc1"
    assert all(build_molecule(n) is not None for n in case.molecule_list())


def test_pyrazolylnucleosides_validation_preset_is_the_fuller_copper_case():
    from corrosim.qm.descriptors import METAL_WORK_FUNCTION

    case = case_study("pyrazolylnucleosides")
    # five 5a-e derivatives, differing only in the para-phenyl substituent
    assert case.molecules == (
        "pyrazolylnucleoside methyl",
        "pyrazolylnucleoside methoxy",
        "pyrazolylnucleoside fluoro",
        "pyrazolylnucleoside chloro",
        "pyrazolylnucleoside bromo",
    )
    # copper, the second non-Fe substrate; the fuller DFT + MC + MD stack
    assert case.metal == "Cu(111)" and case.metal_element == "Cu"
    assert case.metal in METAL_WORK_FUNCTION       # Cu descriptor support is wired
    # the source's MC/MD box carries hydronium + chloride (HCl)
    assert case.medium == "1 M HCl"
    # the pyrazole ring nitrogen is the basic site (parent pyrazole pKaH ~2.5)
    assert case.pkah == 2.5
    # DMol3/M-11L source, qualitative compare; the set spans F/Cl/Br and the
    # Pople sets lack bromine, so the basis is def2-SVP (B3LYP functional kept)
    assert case.basis == "def2-SVP" and case.xc == "b3lyp"
    assert "Scientific Reports" in case.source
    assert "10.1038/s41598-021-82927-5" in case.source
    assert case.results_dir == "cases/pyrazolylnucleosides/results"
    # aliases resolve; the 5a-e library keys build offline
    assert case_study("pyn") is case is case_study("Pyrazolylnucleoside")
    # 5e is the bromo derivative (the reported strongest adsorber)
    from rdkit import Chem
    from rdkit.Chem import rdMolDescriptors

    formula = rdMolDescriptors.CalcMolFormula(
        Chem.MolFromSmiles(build_molecule("5e").smiles))
    assert formula == "C16H16BrN3O3"
    assert all(build_molecule(n) is not None for n in case.molecule_list())


def test_case_study_carries_the_dft_level():
    # the level of theory is a per-case field of the single source of truth, so
    # a preset that converges only at a smaller basis stays self-reproducing
    assert ARGHEL.basis == "6-311++G(d,p)" and ARGHEL.xc == "b3lyp"
    # an unspecified case inherits the adopted production level
    plain = CaseStudy(name="x", molecules=("caffeine",))
    assert plain.basis == "6-311++G(d,p)" and plain.xc == "b3lyp"
    # phytic acid overrides the basis (its diffuse-set SCF diverges) but keeps
    # the production functional
    assert case_study("phytic-acid").basis == "6-31G(d)"
    assert case_study("phytic-acid").xc == "b3lyp"


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


# --- a study declared as data (bring-your-own inhibitors/metal/medium) -------


def test_case_study_round_trips_through_a_dict():
    # to_dict -> from_dict reproduces the study exactly (molecules as a list)
    case = CaseStudy(name="demo", molecules=("quercetin", "CCO"),
                     metal="Cu(111)", medium="0.5 M H2SO4", pkah=2.5)
    data = case.to_dict()
    assert data["molecules"] == ["quercetin", "CCO"]     # JSON-friendly list
    assert CaseStudy.from_dict(data) == case


def test_from_dict_requires_name_and_a_nonempty_molecule_list():
    with pytest.raises(ValueError, match="name"):
        CaseStudy.from_dict({"molecules": ["CCO"]})
    with pytest.raises(ValueError, match="molecules"):
        CaseStudy.from_dict({"name": "x", "molecules": []})
    with pytest.raises(ValueError, match="molecules"):
        CaseStudy.from_dict({"name": "x", "molecules": "CCO"})   # not a list


def test_from_dict_rejects_an_unknown_field():
    # a typo ('metals') fails loud instead of being silently dropped
    with pytest.raises(ValueError, match="unknown study field"):
        CaseStudy.from_dict(
            {"name": "x", "molecules": ["CCO"], "metals": "Fe"})


def test_is_study_file_distinguishes_a_path_from_a_registry_name():
    assert is_study_file("my-study.json")
    assert is_study_file("./cases/x/study.json")
    assert not is_study_file("arghel")           # a bare word is a preset lookup


def test_save_and_load_study_round_trips_through_a_file(tmp_path):
    case = CaseStudy(name="demo", molecules=("quercetin", "CCO"),
                     metal="Cu(111)")
    path = tmp_path / "sub" / "study.json"        # parent is created
    save_study(case, str(path))
    assert load_study(str(path)) == case


def test_case_study_loads_a_study_file_path(tmp_path):
    # the same resolver serves a registered name and a file path
    case = CaseStudy(name="demo", molecules=("CCO",), metal="Al(111)")
    path = tmp_path / "study.json"
    save_study(case, str(path))
    assert case_study(str(path)) == case
    assert case_study("arghel") is ARGHEL         # registry path is unchanged


def test_validate_study_rejects_an_unsupported_metal():
    # only a metal the slab builder knows runs the full pipeline
    with pytest.raises(ValueError, match="not supported"):
        validate_study(CaseStudy(name="x", molecules=("CCO",), metal="Zn"))


def test_validate_study_rejects_an_unsafe_name():
    # the name becomes the cases/<name>/ directory, so it must be path-safe
    with pytest.raises(ValueError, match="alphanumeric"):
        validate_study(CaseStudy(name="../evil", molecules=("CCO",)))


def test_validate_study_rejects_an_element_with_no_uff_parameters():
    # iodine has no UFF vdW parameter, so the MC/MD field can't score it
    with pytest.raises(ValueError, match="no UFF parameters"):
        validate_study(
            CaseStudy(name="x", molecules=("CI",), metal="Fe(110)"),
            check_elements=True)


def test_validate_study_accepts_a_supported_organic_on_a_known_metal():
    # a CHO organic on Fe/Cu/Al passes both the metal and the element check
    validate_study(
        CaseStudy(name="ok", molecules=("CCO",), metal="Cu(111)"),
        check_elements=True)
