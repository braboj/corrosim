# ADR 0017 — Data-driven inhibitor library + offline PubChem fetch tool

- Status: Accepted
- Date: 2026-07-08
- Relates to: ADR 0011 (src layout / subsystem packages), ADR 0012 (API
  contract), and the single-source-of-truth rule (CLAUDE.md §2.3)

## Context

`molecules.py` hardcoded a five-entry `LIBRARY` dict in source. `quality.md`
(§Architecture) wants editable content in a data directory, not baked into
modules — adding an inhibitor meant editing Python. The validation-presets work
also needs each paper's inhibitors added quickly and *with provenance* (where a
SMILES came from), which a bare `name -> smiles` dict cannot carry.

## Decision

**The inhibitor library is package data, and a dev-time CLI grows it from
PubChem without adding a runtime dependency or a network path to normal runs.**

- The library ships as `src/corrosim/data/inhibitors.json` (a new directory,
  declared as `package-data` and loaded via `importlib.resources` so it
  resolves the same from a checkout or an installed wheel). Per-entry schema:
  `{smiles, aliases, source, cas, notes}`.
- At import, `molecules` derives the public `LIBRARY` (a `dict[str, str]` view)
  and `ALIASES` from the records, so the public API is unchanged; the full
  records are exposed as `INHIBITORS` for callers that want provenance.
- `corrosim-add-inhibitor <name|CAS>` (`corrosim.fetch`) queries PubChem PUG
  REST (`Title,SMILES`), resolves the CAS from the synonyms endpoint,
  RDKit-validates the SMILES, and appends the entry with `source: pubchem`.
  It uses only the standard library (`urllib`), so there is **no required new
  dependency and no `[fetch]` extra**.
- **Offline invariant:** the committed JSON is the single source of truth;
  screening runs and CI never touch the network. Fetch is a by-hand expand
  tool, run and committed like any other data edit. Its one HTTP seam is
  monkeypatched in tests, so the suite stays offline and deterministic.

## Alternatives considered

- **YAML** for comment-friendly hand-editing — rejected: adds PyYAML, and the
  fetch writeback wants a machine-writable format (stdlib `json`).
- **`pubchempy` / `requests` behind a `[fetch]` extra** — unneeded: stdlib
  `urllib` covers name/CAS → SMILES, so the core install stays dependency-light
  and there is nothing to gate behind an extra.
- **Canonicalise SMILES at import** — rejected: keep it behaviour-preserving.
  RDKit canonicalises at build time as before; PubChem SMILES are stored
  verbatim to preserve provenance.
- **Gated live fallback in `resolve_smiles`** (`CORROSIM_FETCH=1`) — deferred:
  it would add a network path to the library-import hot path. The CLI is the
  sanctioned expand route; the resolver stays offline-pure.

## Consequences

- Adding an inhibitor is a data edit or a one-command fetch; every entry now
  carries `source` / `cas` / `notes` provenance.
- The public API (`LIBRARY` / `ALIASES` / `resolve_smiles` / `build_molecule`)
  is unchanged; a new `src/corrosim/data/` directory ships with the package.
- The JSON is schema-validated and every entry round-trips through
  `build_molecule` offline; the fetch tool is tested against canned payloads.
- Directly unblocks the per-paper validation presets: a paper's inhibitors
  become `corrosim-add-inhibitor` calls that record where each came from.
