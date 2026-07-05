"""QM-light Fukui dispatch tests. The SCF is mocked (no PySCF/QM container):
they exercise the fmo/fd branch wiring, the charge-difference signs, and the
_result dual/softness math offline."""
import numpy as np
import pytest

from corrosim.qm import fukui


class _FakeMol:
    """A molecule stand-in with just the fields compute_fukui reads."""

    def __init__(self):
        self.symbols = ["O", "H"]
        self.coords = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
        self.charge = 0


def test_result_builds_dual_and_softness():
    res = fukui._result(["O", "H"], [0.2, 0.8], [0.7, 0.3],
                        softness=2.0, basis="6-31G(d)")
    # dual = f+ - f-
    assert res.dual == pytest.approx([0.2 - 0.7, 0.8 - 0.3])
    # local softness = f± * global softness
    assert res.s_plus == pytest.approx([0.4, 1.6])
    assert res.s_minus == pytest.approx([1.4, 0.6])


def test_result_softness_defaults_to_one():
    res = fukui._result(["O"], [0.5], [0.1], softness=None, basis="")
    assert res.s_plus == pytest.approx([0.5])
    assert res.s_minus == pytest.approx([0.1])


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
