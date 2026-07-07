"""The inhibitor library ships as valid, buildable package data (#54).

Guards the data-driven library: the on-disk JSON matches the per-entry schema,
the module-level LIBRARY / ALIASES views derive from it correctly, and every
shipped SMILES round-trips through build_molecule fully offline.
"""
import json
from importlib.resources import files

import pytest
from rdkit import Chem

from corrosim.molecules import (
    ALIASES,
    INHIBITORS,
    LIBRARY,
    build_molecule,
    resolve_smiles,
)

# Allowed provenance values for the record `source` field.
SOURCES = {"manual", "pubchem", "paper"}

# The five entries migrated from the old hardcoded dict must survive verbatim.
EXPECTED_SMILES = {
    "kaempferol": "O=c1c(O)c(-c2ccc(O)cc2)oc2cc(O)cc(O)c12",
    "quercetin": "O=c1c(O)c(-c2ccc(O)c(O)c2)oc2cc(O)cc(O)c12",
    "isorhamnetin": "O=c1c(O)c(-c2ccc(O)c(OC)c2)oc2cc(O)cc(O)c12",
    "benzotriazole": "c1ccc2[nH]nnc2c1",
    "caffeine": "Cn1cnc2c1c(=O)n(C)c(=O)n2C",
}


def _raw_records() -> dict:
    # Read the shipped file directly so the schema check is independent of the
    # module loader.
    text = (files("corrosim") / "data" / "inhibitors.json").read_text(
        encoding="utf-8",
    )
    return json.loads(text)


def test_json_file_is_a_name_keyed_object():
    records = _raw_records()
    assert isinstance(records, dict)
    assert records, "inhibitors.json must not be empty"
    assert all(isinstance(name, str) and name for name in records)


@pytest.mark.parametrize("name", sorted(_raw_records()))
def test_each_record_matches_the_schema(name):
    rec = _raw_records()[name]
    assert isinstance(rec, dict)
    # SMILES is required, a non-empty string, and RDKit-parseable.
    assert isinstance(rec["smiles"], str) and rec["smiles"]
    assert Chem.MolFromSmiles(rec["smiles"]) is not None
    # Aliases: a list of strings (may be empty).
    assert isinstance(rec["aliases"], list)
    assert all(isinstance(a, str) and a for a in rec["aliases"])
    # Provenance fields.
    assert rec["source"] in SOURCES
    assert rec["cas"] is None or isinstance(rec["cas"], str)
    assert rec["notes"] is None or isinstance(rec["notes"], str)
    # No stray keys beyond the documented schema.
    assert set(rec) <= {"smiles", "aliases", "source", "cas", "notes"}


def test_names_are_lower_case_for_case_insensitive_lookup():
    # resolve_smiles lower-cases its input, so canonical keys must be lower case.
    assert all(name == name.lower() for name in INHIBITORS)


def test_library_view_mirrors_the_records():
    assert LIBRARY == {n: rec["smiles"] for n, rec in INHIBITORS.items()}
    assert all(isinstance(v, str) for v in LIBRARY.values())


def test_aliases_map_lowercased_alias_to_canonical_name():
    expected = {
        alias.lower(): name
        for name, rec in INHIBITORS.items()
        for alias in rec["aliases"]
    }
    assert ALIASES == expected
    # Every alias target is a real library key.
    assert all(target in LIBRARY for target in ALIASES.values())


def test_migrated_entries_survive_verbatim():
    for name, smiles in EXPECTED_SMILES.items():
        assert LIBRARY[name] == smiles


@pytest.mark.parametrize("name", sorted(_raw_records()))
def test_every_entry_round_trips_through_build_molecule(name):
    # Offline build: name -> resolve_smiles -> 3D geometry, no network.
    resolved_name, smiles = resolve_smiles(name)
    assert resolved_name == name
    assert smiles == LIBRARY[name]
    mol = build_molecule(name)
    assert mol.n_atoms > 0
    assert len(mol.coords) == mol.n_atoms
