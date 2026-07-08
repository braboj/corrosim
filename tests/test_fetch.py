"""corrosim-add-inhibitor: PubChem fetch + JSON writeback (#54, offline).

The fetch tool is the sanctioned dev-time way to grow inhibitors.json. These
tests stay fully offline: the single HTTP seam (``_http_get_json``) is
monkeypatched with canned PubChem payloads, so no test touches the network.
"""
import json

import pytest

from corrosim import fetch

# Canned PubChem PUG REST payloads for thiourea (CID 2723790, CAS 62-56-6).
PROP = {
    "PropertyTable": {
        "Properties": [
            {"CID": 2723790, "SMILES": "C(=S)(N)N", "Title": "Thiourea"},
        ]
    }
}
SYN = {
    "InformationList": {
        "Information": [
            {"CID": 2723790, "Synonym": ["Thiourea", "62-56-6", "Thiocarbamide"]},
        ]
    }
}

# A minimal seed library so writeback tests parse and merge realistically.
SEED = {
    "kaempferol": {
        "smiles": "O=c1c(O)c(-c2ccc(O)cc2)oc2cc(O)cc(O)c12",
        "aliases": [],
        "source": "manual",
        "cas": "520-18-3",
        "notes": "seed",
    }
}


def _fake_get(url, timeout):
    # Dispatch on the endpoint so both the property and synonyms calls resolve.
    if "/synonyms/" in url:
        return SYN
    if "/property/" in url:
        return PROP
    raise AssertionError(f"unexpected url: {url}")


def _seed(tmp_path):
    path = tmp_path / "inhibitors.json"
    path.write_text(json.dumps(SEED), encoding="utf-8")
    return path


def test_fetch_pubchem_parses_smiles_title_cas(monkeypatch):
    monkeypatch.setattr(fetch, "_http_get_json", _fake_get)
    hit = fetch.fetch_pubchem("thiourea")
    assert hit.smiles == "C(=S)(N)N"
    assert hit.title == "Thiourea"
    assert hit.cid == 2723790
    assert hit.cas == "62-56-6"


def test_fetch_pubchem_cas_query_skips_synonyms(monkeypatch):
    # A CAS query records the CAS from the input; no synonyms call needed.
    def only_property(url, timeout):
        assert "/synonyms/" not in url
        return PROP
    monkeypatch.setattr(fetch, "_http_get_json", only_property)
    hit = fetch.fetch_pubchem("62-56-6")
    assert hit.cas == "62-56-6"


def test_fetch_pubchem_blank_query_raises(monkeypatch):
    monkeypatch.setattr(fetch, "_http_get_json", _fake_get)
    with pytest.raises(ValueError, match="empty"):
        fetch.fetch_pubchem("   ")


def test_fetch_pubchem_not_found_raises(monkeypatch):
    def not_found(url, timeout):
        raise LookupError("no record")
    monkeypatch.setattr(fetch, "_http_get_json", not_found)
    with pytest.raises(LookupError):
        fetch.fetch_pubchem("zzznotarealcompound")


def test_add_inhibitor_writes_entry_with_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "_http_get_json", _fake_get)
    path = _seed(tmp_path)
    name, record = fetch.add_inhibitor("thiourea", data_path=str(path))
    assert name == "thiourea"
    assert record["source"] == "pubchem"
    assert record["cas"] == "62-56-6"
    assert "2723790" in record["notes"]
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["thiourea"]["smiles"] == "C(=S)(N)N"
    # The seed entry is preserved, and the file stays newline-terminated.
    assert "kaempferol" in on_disk
    assert path.read_text(encoding="utf-8").endswith("}\n")


def test_add_inhibitor_uses_explicit_name_override(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "_http_get_json", _fake_get)
    path = _seed(tmp_path)
    name, _ = fetch.add_inhibitor("62-56-6", name="TU", data_path=str(path))
    assert name == "tu"
    assert "tu" in json.loads(path.read_text(encoding="utf-8"))


def test_add_inhibitor_refuses_overwrite_without_force(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "_http_get_json", _fake_get)
    path = _seed(tmp_path)
    with pytest.raises(ValueError, match="already in the library"):
        fetch.add_inhibitor("thiourea", name="kaempferol", data_path=str(path))


def test_add_inhibitor_force_overwrites(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "_http_get_json", _fake_get)
    path = _seed(tmp_path)
    _, record = fetch.add_inhibitor(
        "thiourea", name="kaempferol", data_path=str(path), force=True
    )
    assert record["source"] == "pubchem"
    assert json.loads(path.read_text(encoding="utf-8"))["kaempferol"]["source"] == "pubchem"


def test_add_inhibitor_rejects_unparseable_smiles(tmp_path, monkeypatch):
    bad = {"PropertyTable": {"Properties": [
        {"CID": 1, "SMILES": "not a smiles((", "Title": "Bogus"},
    ]}}
    monkeypatch.setattr(fetch, "_http_get_json", lambda url, timeout: bad)
    path = _seed(tmp_path)
    with pytest.raises(ValueError, match="unparseable SMILES"):
        fetch.add_inhibitor("bogus", data_path=str(path))


def test_http_get_json_rejects_non_https():
    with pytest.raises(ValueError, match="HTTPS"):
        fetch._http_get_json("http://example.com/x", timeout=1.0)


def test_main_adds_then_reports_conflict(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fetch, "_http_get_json", _fake_get)
    path = _seed(tmp_path)
    monkeypatch.setattr(fetch, "inhibitors_json_path", lambda: path)
    # First add succeeds and prints the new entry.
    assert fetch.main(["thiourea"]) == 0
    out = capsys.readouterr().out
    assert "added 'thiourea'" in out
    # Re-adding without --force fails cleanly (exit 1, message on stderr).
    assert fetch.main(["thiourea"]) == 1
    assert "already in the library" in capsys.readouterr().err
