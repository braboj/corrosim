"""QM-light wiring tests for run_dft's true-minimum check (issue #41).

``analyse_matrix``'s QM calls (geometry optimisation, the Hessian, the descriptors)
are stubbed, so these verify the *plumbing* without PySCF/Docker: that
``--check-minimum`` / ``--to-minimum`` thread ``n_imag`` + ``lowest_freq_cm`` into
every row and tag the geometry provenance, and that plain ``--optimize`` is unchanged.
"""
from __future__ import annotations

import numpy as np

import corrosim
from corrosim.molecules import Molecule
from corrosim.runs import run_dft


def _fake_mol(name: str = "kaempferol", charge: int = 0) -> Molecule:
    return Molecule(name=name, smiles="O", symbols=["O", "H"],
                    coords=[(0.0, 0.0, 0.0), (0.0, 0.0, 0.97)], charge=charge)


def _patch_common(monkeypatch) -> None:
    monkeypatch.setattr(run_dft, "build_molecule", lambda name: _fake_mol(name))
    monkeypatch.setattr(run_dft, "optimize_geometry",
                        lambda symbols, coords, **kw: (list(symbols), list(coords)))
    # descriptors: a minimal flat row; analyse_matrix adds form/phase/geometry/provenance
    monkeypatch.setattr(corrosim, "analyse_molecule",
                        lambda mol, **kw: {"name": mol.name, "homo_ev": -6.0})


def test_check_minimum_records_saddle_provenance(monkeypatch):
    _patch_common(monkeypatch)
    saddle = {"n_imag": 1, "freq_cm": np.array([-40.0, 200.0, 1600.0])}
    monkeypatch.setattr(run_dft, "thermo_correction",
                        lambda symbols, coords, **kw: saddle)

    rows = run_dft.analyse_matrix(["kaempferol"], engine="xtb", forms="neutral",
                                  optimize=True, check_minimum=True)

    assert rows, "expected descriptor rows"
    for row in rows:                       # gas + aqueous rows both carry the check
        assert row["n_imag"] == 1
        assert row["lowest_freq_cm"] == -40.0
        assert "frequency-checked" in row["geometry"]


def test_to_minimum_drives_to_minimum_and_records_clean(monkeypatch):
    _patch_common(monkeypatch)
    seen = {"relax": 0, "thermo": 0}

    def fake_relax(symbols, coords, **kw):
        seen["relax"] += 1
        return list(symbols), list(coords), {"n_imag": 0,
                                             "freq_cm": np.array([60.0, 210.0])}

    def fail_thermo(*a, **k):              # the drive-to-minimum path must not detect-only
        seen["thermo"] += 1
        return {}

    monkeypatch.setattr(run_dft, "relax_to_minimum", fake_relax)
    monkeypatch.setattr(run_dft, "thermo_correction", fail_thermo)

    rows = run_dft.analyse_matrix(["kaempferol"], engine="xtb", forms="neutral",
                                  optimize=True, to_minimum=True)

    assert seen["relax"] == 1 and seen["thermo"] == 0
    assert rows
    for row in rows:
        assert row["n_imag"] == 0
        assert "true minimum" in row["geometry"]


def test_plain_optimize_adds_no_minimum_provenance(monkeypatch):
    _patch_common(monkeypatch)
    rows = run_dft.analyse_matrix(["kaempferol"], engine="xtb", forms="neutral",
                                  optimize=True)

    assert rows
    for row in rows:
        assert "n_imag" not in row and "lowest_freq_cm" not in row
        assert row["geometry"].startswith("DFT-opt") and "checked" not in row["geometry"]


def test_check_minimum_implies_optimize_when_called_directly(monkeypatch):
    # #50: the "minimum implies optimize" invariant now lives with
    # analyse_matrix, so a direct call with check_minimum but not optimize
    # still relaxes + frequency-checks rather than silently tagging the row FF.
    _patch_common(monkeypatch)
    monkeypatch.setattr(run_dft, "thermo_correction",
                        lambda symbols, coords, **kw: {"n_imag": 0,
                                                       "freq_cm": np.array([55.0])})

    rows = run_dft.analyse_matrix(["kaempferol"], engine="xtb", forms="neutral",
                                  check_minimum=True)

    assert rows
    for row in rows:
        assert row["n_imag"] == 0
        assert "frequency-checked" in row["geometry"]
        assert "FF" not in row["geometry"]
