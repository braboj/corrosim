from types import SimpleNamespace

import pytest

from corrosim.molecules import (
    Molecule,
    build_molecule,
    build_protonated,
    enumerate_protonation_sites,
)
from corrosim.qm import protonation
from corrosim.qm.descriptors import total_negative_charge


def _stub_site_screen(monkeypatch, energies_ev):
    """Stub the protonation screen to yield one site per energy in ``energies_ev``.

    Replaces the RDKit enumeration/build and the QM engine so the selection
    logic is exercised QM-light: site ``i`` returns ``energies_ev[i]`` as its
    conjugate-acid total energy (consumed in enumeration order).
    """
    monkeypatch.setattr(protonation, "enumerate_protonation_sites",
                        lambda name: list(range(len(energies_ev))))
    monkeypatch.setattr(protonation, "build_protonated",
                        lambda name, idx: Molecule(
                            name=f"{name}+H+", smiles="O", symbols=["O", "H"],
                            coords=[(0.0, 0.0, 0.0), (0.0, 0.0, 0.97)],
                            charge=1))
    seq = iter(energies_ev)
    monkeypatch.setattr(protonation, "run_engine",
                        lambda *a, **k: SimpleNamespace(e_total_ev=next(seq)))


def test_best_protonation_site_skips_nonfinite_and_picks_lowest(monkeypatch):
    # A non-finite energy (an engine that reports no total energy) must be
    # skipped for ranking, not silently kept — the lowest finite energy wins.
    _stub_site_screen(monkeypatch, [float("nan"), -12.0, -11.0])
    idx, cation = protonation.best_protonation_site("x", select_engine="xtb")
    assert idx == 1                            # the -12.0 eV site, not site 0
    assert cation.charge == 1


def test_best_protonation_site_fails_loud_when_no_finite_energy(monkeypatch):
    # orca/gaussian return nan e_total by design; ranking on nan used to keep
    # the first-enumerated site silently. Now it raises rather than lying.
    _stub_site_screen(monkeypatch, [float("nan"), float("nan")])
    with pytest.raises(RuntimeError, match="no finite total energy"):
        protonation.best_protonation_site("x", select_engine="orca")


def test_enumerate_sites_has_oxygens():
    # kaempferol (C15H10O6) has several protonatable O sites
    sites = enumerate_protonation_sites("kaempferol")
    assert len(sites) >= 1


def test_build_protonated_adds_exactly_one_proton():
    neutral = build_molecule("kaempferol")
    site = enumerate_protonation_sites("kaempferol")[0]
    prot = build_protonated("kaempferol", site)
    assert prot.charge == 1
    assert prot.n_atoms == neutral.n_atoms + 1        # one extra H
    assert all(len(c) == 3 for c in prot.coords)


def test_build_molecule_is_neutral_by_default():
    assert build_molecule("quercetin").charge == 0


def test_total_negative_charge():
    assert total_negative_charge([-0.3, 0.2, -0.1, 0.4]) == pytest.approx(-0.4)
    assert total_negative_charge([0.1, 0.2]) == pytest.approx(0.0)
    assert total_negative_charge(None) is None
