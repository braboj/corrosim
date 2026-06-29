import pytest
from corrosim.molecules import build_molecule
from corrosim.adsorption import build_slab, estimate_adsorption_energy


def test_build_slab_fe():
    slab = build_slab("Fe", size=(4, 4, 2))
    assert len(slab) == 32
    assert "Fe" in slab.get_chemical_symbols()


def test_adsorption_estimate_is_bounded_and_negative():
    mol = build_molecule("kaempferol")
    res = estimate_adsorption_energy(mol, metal="Fe", size=(4, 4, 2))
    # physisorption window: negative, but not the unphysical tens-of-eV artifact
    assert res["e_ads_ev"] < 0
    assert -1.0 < res["e_ads_ev"] < 0.0
    assert res["best_height_A"] is not None


def test_adsorption_estimate_rejects_unknown_element():
    mol = build_molecule("[Se]")          # no UFF params for Se? -> ValueError path
    with pytest.raises(ValueError):
        estimate_adsorption_energy(mol, metal="Fe", size=(3, 3, 2))


# --- engine smoke test (requires tblite) ----------------------------------
def test_xtb_screen_smoke():
    pytest.importorskip("tblite")
    import corrosim
    df, _ = corrosim.screen(["kaempferol", "quercetin"], engine="xtb",
                            adsorption=False, progress=None)
    assert list(df["name"]) == ["kaempferol", "quercetin"]
    assert (df["gap_ev"] > 0).all()
