"""The `corrosim` screen turns a bad molecule, a missing engine, or an I/O
failure into a one-line error and a non-zero exit, matching the run_study and
add-inhibitor CLIs instead of dumping a traceback. `corrosim.screen` is mocked,
so these run with no QM engine."""
from __future__ import annotations

from corrosim.cli import main


def test_bad_molecule_exits_cleanly_not_with_a_traceback(capsys, monkeypatch):
    # build_molecule raises ValueError on an unknown name / bad SMILES; the CLI
    # surfaces it as `error: ...` and exits 1, not as a propagated exception
    def _raise(*args: object, **kwargs: object) -> None:
        raise ValueError(
            "'nope' is neither a known inhibitor name nor a valid SMILES")

    monkeypatch.setattr("corrosim.screen", _raise)
    rc = main(["--inhibitors", "nope", "--engine", "xtb"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "error: 'nope' is neither" in err          # one-line error surfaced
    assert "Traceback" not in err                     # not a propagated crash


def test_missing_engine_gives_an_install_hint(capsys, monkeypatch):
    # the QM wheels are absent in a plain venv; a raw ImportError becomes a hint
    def _raise(*args: object, **kwargs: object) -> None:
        raise ImportError("No module named 'tblite'")

    monkeypatch.setattr("corrosim.screen", _raise)
    rc = main(["--inhibitors", "quercetin", "--engine", "xtb"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "error:" in err and "qm" in err            # names the install remedy


def test_a_clean_screen_still_returns_zero(capsys, monkeypatch):
    # the happy path is unchanged: a successful screen prints the ranking and
    # the report path and exits 0
    import pandas as pd

    df = pd.DataFrame([{"name": "quercetin", "score": 1.0}])
    monkeypatch.setattr("corrosim.screen", lambda *a, **k: (df, "report.html"))
    monkeypatch.setattr("corrosim.rank_inhibitors", lambda d: d)
    rc = main(["--inhibitors", "quercetin", "--engine", "xtb"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Ranking (best first):" in out and "HTML report: report.html" in out
