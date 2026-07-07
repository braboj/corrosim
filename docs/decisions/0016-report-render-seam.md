# ADR 0016 — Report render seam (one walker for the data-driven section only)

- Status: Superseded by the lean-report refactor (#110, 2026-07-07)
- Date: 2026-07-06
- Relates to: ADR 0010 (AI-authored report narrative is static prose), ADR 0012
  (API contract), ADR 0014 (factory classmethods; restraint)

> **Superseded.** The lean-report refactor removed the "Scientific basis &
> validation" section entirely (the report is now tables + figures under each
> stage; the methodology lives in `docs/pipeline.md`). That section was the
> render seam's only consumer, so `report/render.py` (`render_blocks` +
> `BasisRenderer`) and the equation-rendering paths were deleted as dead code.
> The `PreparedReport.bottom_line` / `.derive` factory methods this ADR shipped
> alongside the seam remain. Kept here as the decision record for why the seam
> existed and why it is gone.

## Context

The HTML (`report`) and Word (`report_docx`) reports must carry identical prose
— `report_content` is the single home for the narrative so they cannot drift.
But the "Scientific basis & validation" section is data-driven: a list of
`(kind, payload)` blocks (`report_content.SCIENTIFIC_BASIS`) that each renderer
walked with its own `if kind == "h3"/"p"/"table"/"eqgroups"` chain. The two
chains were byte-duplicated **and both lacked an `else`**, so an unhandled kind
was silently dropped — quietly breaking the very "identical prose" invariant the
module promises.

Two more shared computations were duplicated: the bottom-line lead extraction
(read the top-ranked row off the ranking, format the headline) appeared verbatim
in both renderers, and `PreparedReport` was constructed by a free
`prepare_report_data` function rather than on the type (ADR 0014 puts
construction on factory classmethods).

The tempting over-correction is to promote the *whole* report to a generic
block/visitor model. But the hand-authored sections are deliberately
format-specific — the Word report is a more compact rewrite of several sections,
and ADR 0010 fixes the narrative as static prose. A generic model would have to
reproduce those genuine per-format differences, buying nothing.

## Decision

**Only the data-driven Scientific-basis section flows through a shared seam. The
hand-authored sections stay two separate renderers.**

- One `render_blocks(blocks, renderer)` walker (`report/render.py`) dispatches
  each `(kind, payload)` to a four-method `BasisRenderer` Protocol
  (`subheading` / `paragraph` / `table` / `equation_groups`), with an
  `else: raise ValueError` making the kind-set **exhaustive** — an unknown block
  (or a payload of the wrong type) is loud, not dropped. HTML (`_HtmlBasis`) and
  Word (`_DocxBasis`) are the two implementations; a third format or fifth kind
  touches one place.
- The bottom-line extraction becomes `PreparedReport.bottom_line() -> str | None`
  (read once off the ranking); each renderer wraps the returned prose in its own
  note box.
- `PreparedReport` construction moves to the factory classmethod
  `PreparedReport.derive(...)` (ADR 0014). `prepare_report_data` stays as the
  stable public wrapper the drivers import, delegating to `derive`.
- The HTML `build_pipeline_report` is decomposed into `_*_section` helpers
  (`_header_section`, `_overview_section`, …) mirroring `report_docx`'s
  `_*_section` builders, so the two section outlines are diffable side by side.
  The document shell and the `_number_headings` pass stay in
  `build_pipeline_report`.

## Alternatives considered

- **Generic block/visitor model for the entire report** — rejected. The
  hand-authored sections differ by format on purpose (the Word report compacts
  several of them); ADR 0010 fixes the narrative as static prose. A whole-report
  model would encode those differences as per-target branches — ceremony without
  a drift the golden does not already catch.
- **Keep the two `if kind == …` chains, just add an `else`** — rejected: it
  fixes the silent-drop but leaves the dispatch byte-duplicated, so a fifth kind
  still means editing two places in lock-step.
- **Retire `_number_headings` for an `_Html` builder mirroring `_Doc`**
  (issue #127 P2, optional) — deferred. The regex numbers headings correctly
  over the joined HTML and the golden pins it byte-for-byte; a builder rewrite is
  pure refactor risk for no output change. Revisit if the HTML side grows stateful
  rendering needs.
- **Drop `prepare_report_data`, expose only `derive`** — rejected: it is public
  API (`report.__all__`) and imported by the drivers; the wrapper keeps that
  surface stable at negligible cost.

## Consequences

- Adding a Scientific-basis block kind is a one-place change (the walker + both
  Protocol impls, all in view); an unhandled kind raises instead of vanishing.
- The bottom-line and the `PreparedReport` construction each have one home.
- The HTML and Word section outlines read in parallel, so a section added to one
  and forgotten in the other is obvious on inspection (and still caught by the
  full-report golden, `tests/test_report_golden.py`).
- The refactor is behaviour-preserving: the HTML report is byte-identical and the
  Word report section-for-section identical to before (the golden is the gate).
- The seam is intentionally scoped to the one data-driven section; new
  hand-authored sections are still written twice, once per format.
