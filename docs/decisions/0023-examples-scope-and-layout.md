# ADR 0023 — examples/ scope and layout: a self-describing, offline, try-it-now folder

- Status: Accepted
- Date: 2026-07-13
- Relates to: ADR 0017 (data-driven inhibitor library); ADR 0022 (full-study
  orchestrator); the README "choose your run" split

## Context

`examples/` held one file, `examples/molecules.csv`, described in the README as
"Sample batch CSV". Four of its five rows have an empty `smiles` column. That is
intentional: the CLI resolves a bare name against the bundled inhibitor library
(ADR 0017), so SMILES is optional and only the one off-library molecule needs it.
But nothing said so, so the file read as broken data rather than as a
deliberate "name **or** SMILES" demonstration. The folder under-delivered as an
*examples* directory: no index, no commands, no expected output, no library
usage.

This ADR settles what `examples/` should teach and how it is structured (the
spike's output); the layout is seeded in the same change.

## Decision

**Keep `examples/` as a top-level, user-facing folder**, distinct from
`docs/PLAYBOOK.md` (maintainer operations) and `docs/ONBOARDING.md` (contributor
setup). Its audience is a newcomer evaluating the tool; a top-level `examples/`
with a rendered `examples/README.md` is the discoverable convention for that.

**`examples/README.md` is the index.** Each example pairs the exact command with
its output, so the folder is self-describing. Where the real output needs a QM
engine, show the reproducible `--plan` dry run instead; it conveys the shape
without computing, and runs anywhere. Do not paste fabricated descriptor or
ranking numbers; point to the root README's sample and `docs/validation.md` for
validated leads.

**Keep the empty-SMILES rows; annotate, do not fill.** They are the whole point
of the batch example (name-or-SMILES resolution). Inline `#` comments cannot live
in the CSV (the screen parser would read a comment row as a molecule), so the
intent is made explicit in `examples/README.md`, next to the command.

**One mixed batch CSV, not a file per mode.** `molecules.csv` already mixes
name-only rows and one explicit-SMILES row, so it demonstrates both forms in five
lines. A newcomer sees the name-only form there and in the `--inhibitors ...`
command; the explicit-SMILES form in the `gallic acid` row. Proliferating
near-duplicate `names_only.csv` / `with_smiles.csv` files for a five-row demo
adds maintenance without teaching more.

**Runnable offline against bundled data.** Examples use the shipped inhibitor
library and the venv xTB path, so no network and, on Linux/macOS, no container is
needed. On Windows the engines (`xtb`, `pyscf`) have no wheels and run in the
`corrosim-qm` container; the README says so, consistent with the rest of the
docs. `--plan` needs no engine anywhere.

**Stays in sync by construction.** The examples call the same library and the two
entry points (`corrosim` screen, `corrosim-run-study`, ADR 0022); they duplicate
no case data, so they cannot drift from the shipped presets.

## Consequences

- `examples/README.md` now indexes: a quick xTB screen, a batch-CSV screen (with
  the name-or-SMILES explanation), the full multiscale report via
  `corrosim-run-study`, a custom metal/medium, and a Python-API snippet, each
  with a reproducible `--plan` excerpt or a pointer to a real sample.
- `molecules.csv` is unchanged; its empty-SMILES rows are now explained rather
  than mysterious.
- The root README's `examples/` structure-table entry stops calling it just a
  "sample batch CSV".
- Further examples that need their own runtime (a Colab/Jupyter notebook, #66)
  remain separate follow-ups; this ADR covers the offline CLI/library examples.

## Upstream

The transferable kernel (*ship an `examples/` directory whose README indexes each
example as an exact command paired with its reproducible dry-run output, runnable
offline against bundled data*) is a generic onboarding/docs convention. Recorded
in `docs/engineering-know-how.md` and filed upstream as `solid-ai-templates#816`
to extend the `readme.md` / `docs.md` conventions.
