import pytest

from corrosim.descriptors import total_negative_charge
from corrosim.molecules import build_molecule, build_protonated, enumerate_protonation_sites


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
