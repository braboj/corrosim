"""Substrate-agnostic Stage-3 MD: the metal threads through to the slab and the
RDF."""
from corrosim import build_molecule
from corrosim.adsorption.md import run_md


def test_md_metal_threads_to_slab_and_rdf():
    m = build_molecule("caffeine")                 # has both O and N donors
    cu = run_md(m, metal="Cu", n_steps=150, equil=50, seed=0)

    assert cu.metal == "Cu"
    assert cu.surface == "(111)"                    # Cu -> fcc(111), not Fe(110)
    assert set(cu.slab.get_chemical_symbols()) == {"Cu"}   # slab really is Cu

    # the metal–O/N contact distributions align with the shared distance grid
    assert len(cu.rdf_metal_O) == len(cu.rdf_r)
    assert len(cu.rdf_metal_N) == len(cu.rdf_r)


def test_md_surface_differs_by_metal():
    m = build_molecule("caffeine")
    fe = run_md(m, metal="Fe", n_steps=80, equil=20, seed=0)
    assert fe.metal == "Fe" and fe.surface == "(110)"   # Fe -> bcc(110)
