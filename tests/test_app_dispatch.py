"""The unified `corrosim` front door (corrosim.app) dispatches to the three
subcommands, forwards the remaining args verbatim, and keeps the original
leading-option screen invocation working. Routing is checked with spies (no
engine needed); two --plan cases exercise the real subcommand parsers end to
end."""
from __future__ import annotations

from importlib.metadata import version

import pytest

import corrosim
from corrosim import app


def _spy(monkeypatch, target: str) -> dict:
    """Replace ``target``'s main with a spy that records its argv, returns 0."""
    seen: dict = {}

    def fake(argv=None) -> int:
        seen["argv"] = list(argv) if argv is not None else None
        return 0

    monkeypatch.setattr(target, fake)
    return seen


def test_leading_option_routes_to_screen(monkeypatch):
    # back-compat: `corrosim --inhibitors ...` is the original bare screen, so
    # the whole argv (leading option included) goes to the screen main
    seen = _spy(monkeypatch, "corrosim.cli.main")
    rc = app.main(["--inhibitors", "quercetin", "--plan"])
    assert rc == 0
    assert seen["argv"] == ["--inhibitors", "quercetin", "--plan"]


def test_screen_subcommand_strips_the_verb(monkeypatch):
    # `corrosim screen ...` forwards only the args after the verb
    seen = _spy(monkeypatch, "corrosim.cli.main")
    rc = app.main(["screen", "--inhibitors", "quercetin"])
    assert rc == 0
    assert seen["argv"] == ["--inhibitors", "quercetin"]


def test_run_study_subcommand_routes(monkeypatch):
    seen = _spy(monkeypatch, "corrosim.runs.run_study.main")
    rc = app.main(["run-study", "--case", "arghel", "--plan"])
    assert rc == 0
    assert seen["argv"] == ["--case", "arghel", "--plan"]


def test_add_inhibitor_subcommand_routes(monkeypatch):
    seen = _spy(monkeypatch, "corrosim.fetch.main")
    rc = app.main(["add-inhibitor", "thiourea", "--force"])
    assert rc == 0
    assert seen["argv"] == ["thiourea", "--force"]


def test_unknown_command_errors_with_usage(capsys):
    rc = app.main(["bogus"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "unknown command 'bogus'" in err
    assert "run-study" in err                        # usage still shown


@pytest.mark.parametrize("argv", [[], ["-h"], ["--help"]])
def test_top_level_help_lists_the_commands(argv, capsys):
    rc = app.main(argv)
    assert rc == 0
    out = capsys.readouterr().out
    assert "screen" in out and "run-study" in out and "add-inhibitor" in out


def test_run_study_plan_end_to_end(capsys):
    # real routing through the run_study parser: --plan computes nothing
    rc = app.main(["run-study", "--case", "arghel", "--plan"])
    assert rc == 0
    assert "multiscale study" in capsys.readouterr().out


def test_screen_plan_end_to_end(capsys):
    # real routing through the screen parser: --plan computes nothing
    rc = app.main(["screen", "--inhibitors", "quercetin", "--plan"])
    assert rc == 0
    assert "quick screen" in capsys.readouterr().out


@pytest.mark.parametrize("flag", ["--version", "-V"])
def test_version_flag_prints_the_version(flag, capsys):
    # resolved at the top level before the leading-option screen shorthand
    rc = app.main([flag])
    assert rc == 0
    assert capsys.readouterr().out.strip() == f"corrosim {corrosim.__version__}"


def test_dunder_version_matches_installed_metadata():
    # __version__ reads the package metadata rather than a duplicated literal
    assert corrosim.__version__ == version("corrosim")
