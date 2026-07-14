"""QM-light tests for the run_study orchestrator. The stage drivers' ``main()``
are mocked, so these verify the orchestration itself (selection, order, the
--plan dry run, idempotent skip, stop-on-failure) with no PySCF/Docker."""
from __future__ import annotations

import argparse

import pytest

from corrosim.runs import run_study

_DRIVER_MODULES = ["run_dft", "run_fukui", "run_pka", "run_mc", "run_md",
                   "make_cubes", "make_figures", "make_report"]


def _args(**kw: object) -> argparse.Namespace:
    base = dict(case="arghel", optimize=False, with_pka=False,
                with_cubes=False, only=None, skip=None, force=False,
                plan=False)
    base.update(kw)
    return argparse.Namespace(**base)


def _mock_all_drivers(monkeypatch, calls: list[str]) -> None:
    # every driver main records its module name and succeeds
    for mod in _DRIVER_MODULES:
        monkeypatch.setattr(f"corrosim.runs.{mod}.main",
                            lambda argv, m=mod: calls.append(m) or 0)


def test_default_selection_is_the_six_core_stages():
    keys = [s.key for s in run_study.select_stages(_args())]
    assert keys == ["dft", "fukui", "mc", "md", "figures", "report"]


def test_enrichment_flags_add_pka_and_cubes_in_pipeline_order():
    keys = [s.key for s in
            run_study.select_stages(_args(with_pka=True, with_cubes=True))]
    assert keys == ["dft", "fukui", "pka", "cubes", "mc", "md", "figures",
                    "report"]


def test_only_restricts_to_named_stages_in_pipeline_order():
    # --only is order-insensitive: the pipeline order wins, not the arg order
    keys = [s.key for s in run_study.select_stages(_args(only="report,mc"))]
    assert keys == ["mc", "report"]


def test_skip_removes_a_stage():
    keys = [s.key for s in run_study.select_stages(_args(skip="fukui"))]
    assert "fukui" not in keys and "dft" in keys


def test_unknown_stage_raises_systemexit():
    with pytest.raises(SystemExit, match="bogus"):
        run_study.select_stages(_args(only="bogus"))


def test_plan_lists_ordered_stages_without_running(capsys, monkeypatch):
    calls: list[str] = []
    _mock_all_drivers(monkeypatch, calls)
    rc = run_study.main(["--case", "arghel", "--plan"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "full multiscale study" in out
    assert "1. dft" in out and "report" in out
    assert "Nothing computed" in out
    # a dry run computes nothing
    assert calls == []


def test_pipeline_runs_stages_in_dependency_order(monkeypatch):
    calls: list[str] = []
    _mock_all_drivers(monkeypatch, calls)
    rc = run_study.main(["--case", "arghel", "--force"])
    assert rc == 0
    assert calls == ["run_dft", "run_fukui", "run_mc", "run_md",
                     "make_figures", "make_report"]


def test_optimize_adds_a_second_dft_run(monkeypatch):
    argvs: list[list[str]] = []
    monkeypatch.setattr("corrosim.runs.run_dft.main",
                        lambda argv: argvs.append(argv) or 0)
    rc = run_study.main(["--case", "arghel", "--optimize", "--only", "dft",
                         "--force"])
    assert rc == 0
    assert argvs == [["--case", "arghel"],
                     ["--case", "arghel", "--optimize"]]


def test_pipeline_stops_on_first_stage_failure(monkeypatch):
    calls: list[str] = []
    _mock_all_drivers(monkeypatch, calls)
    # dft fails: nothing downstream should run
    monkeypatch.setattr("corrosim.runs.run_dft.main",
                        lambda argv: calls.append("run_dft") or 2)
    rc = run_study.main(["--case", "arghel", "--force"])
    assert rc == 2
    assert calls == ["run_dft"]


def test_idempotent_stages_skip_when_outputs_exist(monkeypatch):
    calls: list[str] = []
    _mock_all_drivers(monkeypatch, calls)
    # pretend every declared output already exists
    monkeypatch.setattr(run_study.os.path, "exists", lambda p: True)
    rc = run_study.main(["--case", "arghel"])   # no --force
    assert rc == 0
    # the compute stages are skipped; only the always-render stages run
    assert calls == ["make_figures", "make_report"]


def test_fukui_stage_passes_the_case_def2_basis_for_a_heavy_element_case(
        monkeypatch):
    # a def2 case (bromine) must reach run_fukui as --basis, not its light
    # Pople default which carries no bromine
    argvs: list[list[str]] = []
    monkeypatch.setattr("corrosim.runs.run_fukui.main",
                        lambda argv: argvs.append(argv) or 0)
    rc = run_study.main(["--case", "pyrazolylnucleosides", "--only", "fukui",
                         "--force"])
    assert rc == 0
    assert argvs == [["--case", "pyrazolylnucleosides",
                      "--basis", "def2-SVP"]]


def test_fukui_stage_omits_basis_for_a_pople_case(monkeypatch):
    # a Pople-basis case keeps run_fukui's own light default (no override)
    argvs: list[list[str]] = []
    monkeypatch.setattr("corrosim.runs.run_fukui.main",
                        lambda argv: argvs.append(argv) or 0)
    rc = run_study.main(["--case", "arghel", "--only", "fukui", "--force"])
    assert rc == 0
    assert argvs == [["--case", "arghel"]]


# --- a user-defined study (the --case file / --molecules build flags) --------


def test_build_flags_write_study_json_and_delegate_via_the_file(
        tmp_path, monkeypatch):
    # --molecules builds a study, writes cases/<name>/study.json, and points the
    # driver subcalls at that file (one engine for both front doors)
    monkeypatch.chdir(tmp_path)
    argvs: list[list[str]] = []
    monkeypatch.setattr("corrosim.runs.run_mc.main",
                        lambda argv: argvs.append(argv) or 0)
    rc = run_study.main(["--name", "byo", "--molecules", "CCO",
                         "--metal", "Cu(111)", "--only", "mc", "--force"])
    assert rc == 0
    study = tmp_path / "cases" / "byo" / "study.json"
    assert study.exists()                          # the reproducible artifact
    assert argvs == [["--case", "cases/byo/study.json"]]


def test_case_file_path_is_resolved_and_delegated(tmp_path, monkeypatch):
    # a --case that names a study file resolves and runs like a preset name
    from corrosim.presets import CaseStudy, save_study

    study = tmp_path / "s.json"
    save_study(CaseStudy(name="filecase", molecules=("CCO",), metal="Al(111)"),
               str(study))
    argvs: list[list[str]] = []
    monkeypatch.setattr("corrosim.runs.run_mc.main",
                        lambda argv: argvs.append(argv) or 0)
    rc = run_study.main(["--case", str(study), "--only", "mc", "--force"])
    assert rc == 0
    assert argvs == [["--case", str(study)]]


def test_build_flags_without_name_is_an_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit, match="needs --name"):
        run_study.main(["--molecules", "CCO", "--only", "mc"])


def test_build_flags_conflicting_with_case_is_an_error():
    with pytest.raises(SystemExit, match="not both"):
        run_study.main(
            ["--case", "phytic", "--molecules", "CCO", "--name", "x"])


def test_unsupported_metal_via_flags_returns_a_clean_error_code(
        tmp_path, monkeypatch, capsys):
    # an out-of-envelope study is a clean exit-2, not a traceback, and nothing
    # runs or is written
    monkeypatch.chdir(tmp_path)
    calls: list[str] = []
    _mock_all_drivers(monkeypatch, calls)
    rc = run_study.main(["--name", "zz", "--molecules", "CCO", "--metal", "Zn"])
    assert rc == 2
    assert calls == []
    assert "not supported" in capsys.readouterr().err
    assert not (tmp_path / "cases" / "zz").exists()


def test_plan_with_build_flags_previews_without_writing(
        tmp_path, monkeypatch, capsys):
    # a dry run validates the metal and prints the plan, but writes no file
    monkeypatch.chdir(tmp_path)
    calls: list[str] = []
    _mock_all_drivers(monkeypatch, calls)
    rc = run_study.main(["--name", "byo", "--molecules", "CCO",
                         "--metal", "Cu(111)", "--plan"])
    assert rc == 0
    assert calls == []
    assert "full multiscale study" in capsys.readouterr().out
    assert not (tmp_path / "cases" / "byo" / "study.json").exists()
