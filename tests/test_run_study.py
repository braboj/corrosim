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
