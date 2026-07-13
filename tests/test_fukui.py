"""QM-light Fukui dispatch tests. The SCF is mocked (no PySCF/QM container):
they exercise the fmo/fd branch wiring, the charge-difference signs, and the
FukuiResult.from_populations dual/softness math offline."""
import numpy as np
import pytest

from corrosim.qm import fukui
from corrosim.qm.fukui import FukuiResult


class _FakeMol:
    """A molecule stand-in with just the fields compute_fukui reads."""

    def __init__(self):
        self.symbols = ["O", "H"]
        self.coords = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
        self.charge = 0


def test_from_populations_builds_dual_and_softness():
    res = FukuiResult.from_populations(["O", "H"], [0.2, 0.8], [0.7, 0.3],
                                       softness=2.0, basis="6-31G(d)")
    # dual = f+ - f-
    assert res.dual == pytest.approx([0.2 - 0.7, 0.8 - 0.3])
    # local softness = f± * global softness
    assert res.s_plus == pytest.approx([0.4, 1.6])
    assert res.s_minus == pytest.approx([1.4, 0.6])


def test_from_populations_softness_defaults_to_one():
    res = FukuiResult.from_populations(["O"], [0.5], [0.1],
                                       softness=None, basis="")
    assert res.s_plus == pytest.approx([0.5])
    assert res.s_minus == pytest.approx([0.1])


def test_from_rows_round_trips_as_rows():
    # from_rows is the exact inverse of as_rows (to the 4-dp it rounds at)
    original = FukuiResult.from_populations(
        ["O", "H", "N"], [0.21, 0.83, 0.11], [0.72, 0.34, 0.05],
        softness=2.0, basis="6-31G(d)")
    back = FukuiResult.from_rows(original.as_rows())
    assert back.symbols == original.symbols
    assert back.f_plus == pytest.approx(original.f_plus, abs=1e-4)
    assert back.f_minus == pytest.approx(original.f_minus, abs=1e-4)
    assert back.dual == pytest.approx(original.dual, abs=1e-4)
    assert back.s_plus == pytest.approx(original.s_plus, abs=1e-4)
    assert back.s_minus == pytest.approx(original.s_minus, abs=1e-4)


def test_as_json_carries_basis_and_round_trips():
    # as_json/from_json keep the basis label the bare-row form drops
    original = FukuiResult.from_populations(
        ["Br", "C"], [0.4, 0.6], [0.5, 0.5], softness=1.0,
        basis="def2-SVP (FMO)")
    payload = original.as_json()
    assert payload["basis"] == "def2-SVP (FMO)"
    back = FukuiResult.from_json(payload)
    assert back.basis == "def2-SVP (FMO)"
    assert back.f_minus == pytest.approx(original.f_minus, abs=1e-4)


def test_from_json_reads_legacy_bare_list_with_empty_basis():
    # legacy files are a bare row list (no recorded basis) -> basis == ""
    original = FukuiResult.from_populations(
        ["O", "H"], [0.2, 0.8], [0.7, 0.3], softness=1.0, basis="6-31G(d)")
    back = FukuiResult.from_json(original.as_rows())
    assert back.basis == ""
    assert back.symbols == ["O", "H"]


def test_from_rows_tolerates_unordered_and_missing_softness():
    # rows out of order, and without s_plus/s_minus (older JSON) -> zeros
    rows = [{"idx": 1, "symbol": "H", "f_plus": 0.8, "f_minus": 0.3,
             "dual": 0.5},
            {"idx": 0, "symbol": "O", "f_plus": 0.2, "f_minus": 0.7,
             "dual": -0.5}]
    fr = FukuiResult.from_rows(rows)
    assert fr.symbols == ["O", "H"]
    assert fr.f_minus == pytest.approx([0.7, 0.3])
    assert fr.s_plus == [0.0, 0.0] and fr.s_minus == [0.0, 0.0]


def test_fmo_maps_homo_to_donor_and_lumo_to_acceptor(monkeypatch):
    mol = _FakeMol()

    class _FakeMF:
        mo_occ = np.array([2.0, 2.0, 0.0, 0.0])   # HOMO index 1
        mo_coeff = np.zeros((2, 4))

        def get_ovlp(self):
            return np.eye(2)

    monkeypatch.setattr(fukui, "_scf",
                        lambda *a, **k: (object(), _FakeMF()))
    # first _atom_pop call is the HOMO (-> f_minus), second the LUMO (-> f_plus)
    pops = iter([np.array([0.7, 0.3]), np.array([0.2, 0.8])])
    monkeypatch.setattr(fukui, "_atom_pop", lambda *a, **k: next(pops))

    res = fukui.compute_fukui(mol, method="fmo")
    assert res.f_minus == pytest.approx([0.7, 0.3])
    assert res.f_plus == pytest.approx([0.2, 0.8])
    assert res.basis.endswith("(FMO)")


def test_fd_takes_finite_differences_on_charges(monkeypatch):
    mol = _FakeMol()
    # the three SCFs in order: N (neutral), N-1 (cation), N+1 (anion)
    charges = iter([np.array([0.1, -0.1]),     # qN
                    np.array([0.4, 0.2]),       # qcat
                    np.array([-0.3, -0.5])])    # qan
    monkeypatch.setattr(fukui, "_mulliken_charges",
                        lambda *a, **k: next(charges))

    res = fukui.compute_fukui(mol, method="fd")
    # f_plus = qN - qan ; f_minus = qcat - qN
    assert res.f_plus == pytest.approx([0.4, 0.4])
    assert res.f_minus == pytest.approx([0.3, 0.3])
    assert res.basis.endswith("(FD)")


def test_unknown_method_raises():
    with pytest.raises(ValueError, match="fmo"):
        fukui.compute_fukui(_FakeMol(), method="bogus")
