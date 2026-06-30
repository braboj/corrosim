import pytest

from corrosim.cli import read_input_csv
from corrosim.molecules import build_molecule, resolve_smiles


def test_build_from_library_name():
    mol = build_molecule("kaempferol")
    assert mol.formula == "C15H10O6"
    assert mol.n_atoms == 31           # incl. explicit H
    assert len(mol.coords) == mol.n_atoms


def test_build_from_smiles():
    mol = build_molecule("OC(=O)c1cc(O)c(O)c(O)c1")   # gallic acid
    assert mol.n_atoms > 0
    assert all(len(c) == 3 for c in mol.coords)


def test_arghel_is_a_set_not_a_molecule():
    # "arghel" is a case study (a set of flavonoids), not a single-molecule alias
    from corrosim.presets import ARGHEL
    assert tuple(ARGHEL.molecules) == ("kaempferol", "quercetin", "isorhamnetin")
    with pytest.raises(ValueError):
        resolve_smiles("arghel")


def test_bad_input_raises():
    with pytest.raises(ValueError):
        build_molecule("not_a_molecule_$$$")


def test_csv_with_header(tmp_path):
    p = tmp_path / "m.csv"
    p.write_text("name,smiles\nkaempferol,\nquercetin,\ngallic,OC(=O)c1cc(O)c(O)c(O)c1\n")
    mols = read_input_csv(str(p))
    assert mols[0] == "kaempferol"
    assert any("OC(=O)" in m for m in mols)        # smiles column wins when present


def test_csv_headerless(tmp_path):
    p = tmp_path / "m.csv"
    p.write_text("kaempferol\nquercetin\n")
    mols = read_input_csv(str(p))
    assert mols == ["kaempferol", "quercetin"]
