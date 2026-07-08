"""corrosim.fetch — expand the inhibitor library from PubChem (dev-time tool).

``corrosim-add-inhibitor <name|CAS>`` looks a compound up on PubChem's PUG REST
service, validates the returned SMILES with RDKit, and appends it to the
shipped ``corrosim/data/inhibitors.json`` with ``source: pubchem`` provenance.
The committed JSON stays the single source of truth: screening runs and the
test suite never touch the network — this tool is the sanctioned way to grow
the file, run by hand and committed like any other data edit. It uses only the
standard library, so the core install stays offline and dependency-light.

::

    name / CAS --> PubChem PUG REST --> RDKit parse --> inhibitors.json
                   (Title, SMILES)      (validate)      (source: pubchem)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

from rdkit import Chem

# PubChem PUG REST root; every request is HTTPS to this host.
_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# CAS registry number: 2-7 / 2 / 1 digit groups (e.g. 62-56-6).
_CAS_RE = re.compile(r"\d{2,7}-\d{2}-\d")


@dataclass(frozen=True)
class PubChemHit:
    """A PubChem lookup result: SMILES plus provenance for one compound."""

    # Isomeric SMILES as returned by PubChem (RDKit-validated by the caller).
    smiles: str

    # Human-readable compound title (used as the default library name).
    title: str

    # PubChem compound id.
    cid: int

    # CAS registry number, when one could be resolved.
    cas: str | None = None


def _http_get_json(url: str, timeout: float) -> Any:
    """GET ``url`` and parse the JSON body; raise LookupError on a 404."""
    if not url.startswith("https://"):
        raise ValueError(f"refusing to fetch a non-HTTPS url: {url!r}")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "corrosim-add-inhibitor"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            payload = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise LookupError(
                f"PubChem has no record matching this query ({url})."
            ) from exc
        raise
    return json.loads(payload)


def _extract_cas(cid: int, timeout: float) -> str | None:
    """First CAS-shaped synonym for ``cid``, or None if none/unreachable."""
    url = f"{_BASE}/compound/cid/{cid}/synonyms/JSON"
    try:
        data = _http_get_json(url, timeout)
    except (LookupError, OSError):
        return None
    info = data.get("InformationList", {}).get("Information", [])
    synonyms = info[0].get("Synonym", []) if info else []
    for synonym in synonyms:
        if _CAS_RE.fullmatch(synonym):
            return synonym
    return None


def fetch_pubchem(query: str, *, timeout: float = 20.0) -> PubChemHit:
    """Look a compound up on PubChem by name or CAS number.

    Queries the PUG REST ``Title,SMILES`` property endpoint (which accepts both
    a name and a CAS number), then resolves the CAS from the synonyms endpoint
    when the query itself was not one.

    Args:
        query: A compound name or CAS registry number.
        timeout: Per-request socket timeout in seconds.

    Returns:
        The :class:`PubChemHit` for the compound.

    Raises:
        ValueError: If ``query`` is blank.
        LookupError: If PubChem has no matching record or returns no SMILES.
        OSError: On a network failure (``urllib.error.URLError`` and kin).
    """
    q = query.strip()
    if not q:
        raise ValueError("query is empty")
    encoded = urllib.parse.quote(q, safe="")
    url = f"{_BASE}/compound/name/{encoded}/property/Title,SMILES/JSON"
    data = _http_get_json(url, timeout)
    props = data["PropertyTable"]["Properties"][0]
    # PubChem now returns the isomeric structure under "SMILES"; keep the
    # legacy property names as fallbacks so an API rename does not break us.
    smiles = (
        props.get("SMILES") or props.get("IsomericSMILES")
        or props.get("ConnectivitySMILES") or props.get("CanonicalSMILES")
    )
    if not smiles:
        raise LookupError(f"PubChem returned no SMILES for {q!r}")
    title = props.get("Title") or q
    cid = int(props["CID"])
    cas = q if _CAS_RE.fullmatch(q) else _extract_cas(cid, timeout)
    return PubChemHit(smiles=smiles, title=title, cid=cid, cas=cas)


def inhibitors_json_path() -> Path:
    """Filesystem path of the packaged ``inhibitors.json`` for writeback.

    Returns:
        The path to the shipped data file.

    Raises:
        RuntimeError: If it does not resolve to a real file (e.g. the package
            is a zip import) — run the tool from a source checkout.
    """
    resource = files("corrosim") / "data" / "inhibitors.json"
    path = Path(str(resource))
    if not path.is_file():
        raise RuntimeError(
            "inhibitors.json is not on the filesystem; run "
            "corrosim-add-inhibitor from a source checkout."
        )
    return path


def add_inhibitor(
    query: str,
    *,
    name: str | None = None,
    data_path: str | Path | None = None,
    force: bool = False,
    timeout: float = 20.0,
) -> tuple[str, dict[str, Any]]:
    """Fetch a compound from PubChem and append it to the inhibitor library.

    Args:
        query: A compound name or CAS registry number to look up.
        name: Library key to store under; defaults to the PubChem title,
            lower-cased.
        data_path: Target JSON file; defaults to the packaged
            ``inhibitors.json``.
        force: Overwrite an existing entry instead of refusing.
        timeout: Per-request socket timeout in seconds.

    Returns:
        ``(name, record)`` for the entry that was written.

    Raises:
        ValueError: If PubChem returns an unparseable SMILES, no name can be
            derived, or the entry exists and ``force`` is False.
        LookupError: If PubChem has no matching record.
        OSError: On a network failure.
    """
    hit = fetch_pubchem(query, timeout=timeout)
    if Chem.MolFromSmiles(hit.smiles) is None:
        raise ValueError(
            f"PubChem returned an unparseable SMILES: {hit.smiles!r}"
        )
    key = (name or hit.title).strip().lower()
    if not key:
        raise ValueError("could not derive a library name; pass --name")
    path = Path(data_path) if data_path else inhibitors_json_path()
    records = json.loads(path.read_text(encoding="utf-8"))
    if key in records and not force:
        raise ValueError(
            f"'{key}' is already in the library; pass --force to overwrite."
        )
    record: dict[str, Any] = {
        "smiles": hit.smiles,
        "aliases": [],
        "source": "pubchem",
        "cas": hit.cas,
        "notes": f"Fetched from PubChem (CID {hit.cid}: {hit.title}).",
    }
    records[key] = record
    path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return key, record


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for ``corrosim-add-inhibitor``.

    Args:
        argv: Argument vector; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code (0 on success, 1 on a lookup/validation/network
        error).
    """
    parser = argparse.ArgumentParser(
        prog="corrosim-add-inhibitor",
        description="Fetch a compound from PubChem (by name or CAS) and append "
                    "it to the inhibitor library JSON.",
    )
    parser.add_argument(
        "query",
        help="compound name or CAS registry number to look up on PubChem",
    )
    parser.add_argument(
        "--name",
        help="library key to store under (default: the PubChem title)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing library entry",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="per-request timeout in seconds (default: 20)",
    )
    args = parser.parse_args(argv)
    try:
        name, record = add_inhibitor(
            args.query,
            name=args.name,
            force=args.force,
            timeout=args.timeout,
        )
    except (LookupError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        f"added '{name}': {record['smiles']} "
        f"(source: {record['source']}, cas: {record['cas']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
