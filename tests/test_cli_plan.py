"""Tests for the `corrosim` screening CLI's ``--plan`` dry run.

``--plan`` describes the ordered steps a screen would run (given the other
options) and exits without computing — the transparency seam that keeps the
quick screener and the multiscale pipeline from being conflated.
"""
from __future__ import annotations

from corrosim.cli import build_parser, format_plan, main


def _args(argv: list[str]):
    return build_parser().parse_args(argv)


def test_plan_lists_steps_and_names_the_engine():
    plan = format_plan(_args(["--inhibitors", "quercetin,kaempferol"]),
                       ["quercetin", "kaempferol"])
    assert "2 molecule(s) on Fe(110)" in plan
    assert "MMFF force-field" in plan            # geometry step
    assert "GFN2-xTB" in plan                    # xtb engine named
    assert "composite z-score" in plan           # rank step
    # the quick screen is explicit about what it does NOT run
    assert "Not run here" in plan and "Monte Carlo" in plan


def test_plan_adsorption_step_is_conditional():
    base = ["--inhibitors", "quercetin"]
    assert "e_ads_kjmol" not in format_plan(_args(base), ["quercetin"])
    assert "e_ads_kjmol" in format_plan(_args(base + ["--adsorption"]),
                                        ["quercetin"])


def test_plan_reflects_the_pyscf_level():
    plan = format_plan(
        _args(["--inhibitors", "x", "--engine", "pyscf",
               "--basis", "6-31g", "--solvent", "none"]), ["x"])
    assert "single-point DFT (pyscf): b3lyp/6-31g (gas phase)" in plan


def test_plan_short_circuits_main_without_computing(capsys):
    # --plan prints the plan and returns 0 without running the screen (so it
    # works even where the QM engine is not installed)
    rc = main(["--inhibitors", "quercetin", "--plan"])
    assert rc == 0
    assert capsys.readouterr().out.startswith(
        "Plan - quick screen of 1 molecule(s)")
