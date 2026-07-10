# ADR 0018 — Per-case output namespacing (`cases/<case>/results/`, `cases/<case>/report/`)

- Status: Accepted (the rejected "no per-study report bundle" alternative is
  revised by ADR 0019 — each case now renders its own bundle)
- Date: 2026-07-08
- Relates to: ADR 0006 (report-bundle output layout), ADR 0008 (bundle
  subfolders), ADR 0011 (src layout / subsystem packages), and the
  single-source-of-truth rule (CLAUDE.md §2.3); enables the per-paper validation
  presets (issue #53)

## Context

Every driver wrote to a single flat root: computed data to `results/`, the
report bundle to `report/`. That was fine with one shipped study, but the
validation-presets work (issue #53) adds a `CaseStudy` per simulation
whitepaper. A second study run would emit the *same* filenames
(`dft_descriptors_ff.csv`, `mc_adsorption.json`, `report.html`, …) and silently
overwrite the first. The flat root also left the shipped study **unlabelled** —
nothing in `results/` said the data belonged to arghel.

## Decision

**Each case study owns one co-located output subtree; no study is special-cased
at the root.**

- Everything a study produces lives under a single `cases/<name>/` root, split
  into `results/` (data) and `report/` (bundle) — so a whole study can be
  browsed, shared, or removed as a unit, while the data-vs-deliverable
  distinction is preserved as subfolders rather than merged. `CaseStudy` gains
  `case_dir` (`cases/<name>`), `results_dir` (`cases/<name>/results`) and
  `report_dir` (`cases/<name>/report`), so a study self-describes where it
  writes. The shipped arghel artifacts were relocated to `cases/arghel/`.
- Every driver's output flags (`--outdir` / `--datadir` / `--out` / `--figdir`
  / `--tablesdir` / …) default to `None` and backfill from the resolved
  `--case` via the shared `_cli.default_output` helper. An explicit flag always
  wins; a bare run routes to the case's subtree, so a study can never clobber
  another's outputs by omission.
- `cubes/` stays a single shared, gitignored, regenerable tree — it is not part
  of the numbers-only validation surface, so it is not case-scoped. Sharing is
  deliberate: a cube is a slow QM-container product keyed by molecule name, so
  identical molecules reuse one file across studies. **Revisit when** a study
  beyond arghel renders a full report bundle (orbital/ESP figures, not just
  numbers): cube names carry no level/medium qualifier, so two studies using
  the same molecule at different levels would then collide — at that point make
  cubes case-scoped (or level/medium-qualify the name).
- The report bundle is a study's *purpose*, not its *location*: the layout is
  symmetric (`cases/<case>/report/` exists for any study), but only studies we render
  a report for populate it. Validation cross-checks are numbers-only and leave
  `cases/<case>/report/` empty, recording their computed-vs-reported comparison in
  `docs/validation.md` instead.

## Alternatives considered

- **Keep arghel at the flat root; nest only validation studies** under a
  `validation/` subtree — rejected: it special-cases arghel and leaves the root
  data unlabelled, the two problems this ADR set out to fix.
- **Two parallel roots — `results/<case>/` and `report/<case>/`** — the first
  cut; refined to the co-located `cases/<case>/{results,report}` so a study's
  data and report sit together (one place to zip / delete / browse) instead of
  the case name appearing in two sibling trees.
- **One undifferentiated `cases/<case>/` folder** (data + report intermingled)
  — rejected: it blurs tracked *source data* against the regenerable
  *deliverable* and muddies the `.gitignore` split; the `results/` vs `report/`
  subfolders keep that distinction.
- **Central name-based backfill inside `resolve_case`** — rejected: driver flag
  names collide (`--outdir` is the results dir for run_mc but the figures root
  for make_figures; `--out-csv` means "skip" for run_dft but the geometry CSV
  for compare_geometry). Each driver backfills its own paths from the shared
  `CaseStudy` dirs instead.
- **A full report bundle per validation study** — rejected: validation's
  deliverable is the comparison table in `docs/validation.md`; rendering an
  HTML/DOCX bundle per study multiplies tracked artifacts for little gain.

## Consequences

- Running any `--case` lands its whole run under `cases/<case>/results/` and
  `cases/<case>/report/`; studies coexist without collision, and the owner is visible
  from the path.
- Supersedes the flat-root assumption in ADR 0006/0011: the bundle root is now
  `cases/<case>/report/` (the stage-subfolder scheme under it is unchanged); the
  `.gitignore` report allowlist becomes `!cases/*/report/report.html`.
- The report is self-contained again: the pKaH caption no longer cites an
  internal `results/pka.json` path (which the move would have made stale).
- Directly unblocks the validation presets — a new study is a `CaseStudy` plus
  its own `cases/<case>/results/` outputs, with nothing to rewire.
