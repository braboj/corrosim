# ADR 0026 — a study is declarable as data (a code preset or a user file)

- Status: Accepted
- Date: 2026-07-14
- Relates to: ADR 0017 (data-driven inhibitor library); ADR 0018 (per-case
  output namespacing); ADR 0022 (full-study orchestrator)

## Context

A screening study (the molecule set + substrate metal + medium + DFT level) was
a `CaseStudy` object in `presets.py`, registered in `CASE_STUDIES` and looked up
by name. The full-pipeline runner `corrosim-run-study` took only a registered
`--case`, and every driver routed its outputs by `case.name`. So a user who
wanted to screen their *own* inhibitors on their own metal had to edit
`presets.py` and rebuild — impossible for someone running the shipped tool
(the deployment epic's download-and-run goal, #71/#221).

The inhibitor *library* was already promoted to data (ADR 0017); the study
*composition* was the last screening input still locked in code.

## Decision

**A study is declarable as data, resolved through the one existing seam.** Every
driver re-resolves its study from the `--case` string via `resolve_case` ->
`case_study`, so that resolver is the only place to change:

- `CaseStudy` gains `to_dict` / `from_dict` (+ module `load_study` /
  `save_study`); the JSON keys are the field names. `from_dict` does structural
  validation only (required `name`/`molecules`, types, rejects unknown keys), so
  a caller deserialises without pulling the heavy slab/RDKit imports.
- `case_study(name)` grows one branch: a value that names a file (ends `.json`
  or carries a path separator — an explicit marker, *not* `os.path.exists`, so a
  bare preset name never collides with a same-named file) is loaded as a study
  JSON; a bare word is the registry lookup, unchanged.

**Two front doors, one engine.** `corrosim-run-study` also accepts ad-hoc
`--name/--molecules/--metal/--medium` (+ `--pkah/--basis/--xc`). Giving
`--molecules` builds a `CaseStudy`, validates it, writes `cases/<name>/study.json`,
and then proceeds exactly as `--case cases/<name>/study.json` would. The flags
path is sugar that *materialises a file and delegates*, so there is a single
construction/validation path and an ad-hoc run leaves behind a reproducible,
shareable artifact.

**Validate the supported envelope up front, fail loud.** A user study is
checked before any stage runs: the metal must be a known slab substrate
(`Fe`/`Cu`/`Al`, from `METAL_LATTICE`), every atom must have a UFF parameter
(`H,C,N,O,S,F,Cl,Br,P`), and the name must be filesystem-safe (it becomes the
`cases/<name>/` directory). An out-of-envelope study exits with a clear message
naming the supported set, not a traceback three stages deep. The element check
needs RDKit and is skipped for `--plan` (which stays cheap); the metal/name
checks are free and always run. The shipped presets are trusted, so registry
resolution is byte-identical.

**JSON only.** The stdlib `json` covers py3.10-3.12 with no dependency and
matches the already-JSON inhibitor library. No TOML/YAML.

## Consequences

- A downloaded-tool user runs their own study without editing source:
  `corrosim-run-study --case ./my-study.json`, or the flags form. Molecules are
  names (resolved against the bundled library) or SMILES, so a novel compound
  needs no library edit.
- `examples/study.template.json` + an `examples/README.md` section + a
  `docs/PLAYBOOK.md` recipe ship the copy-edit-run path.
- The supported envelope is unchanged and now enforced at the door: this ADR
  does **not** add metals or an electrolyte model. Extending the metal set stays
  a separate change to `METAL_LATTICE` + `UFF` + the work-function table; `medium`
  stays a report label plus the `pkah` speciation knob.
- No new interface for the deployment image to expose: publishing the QM image
  distributes the built-in cases, and this makes the same `corrosim-run-study`
  usable for user studies through the same flags.

## Upstream

The transferable kernel (*promote a code-registered config object to also load
from a user data file through the same resolver, so one entry point serves both
the built-in registry and user-supplied configs, and validate the user input
against the supported envelope at the door*) is generic configuration handling,
not corrosion-specific. Recorded in `docs/engineering-know-how.md` and filed
upstream as `solid-ai-templates#819` to extend `base/core/config.md`.
