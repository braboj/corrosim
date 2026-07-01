# ADR 0008 — Report: per-stage subfolders, a Word output, and rendered equations

- Status: Accepted
- Date: 2026-07-01

## Context

The `report/` bundle (ADR 0006) put every figure in one flat `report/figures/`
directory and every table in one flat `report/tables/`, and the report itself
was HTML only. A customer asked for more insight into the report: the figures
(and tables and other results) grouped into per-stage folders; a Word (`.docx`)
deliverable alongside the HTML; each graphic explained so it stands on its own;
the scientific basis (`docs/pipeline.md`) and the validation record
(`docs/validation.md`) folded in; and the governing equations shown in
scientific form.

Two constraints shaped the design. First, corrosim is "free software only" and
everything except the QM engines runs in a plain venv (CLAUDE.md 1.1) — so the
Word path must not add a system binary. Second, the HTML report is
self-contained (all figures inlined base64), so equations must render without a
web/MathJax dependency.

## Decision

1. **Per-stage subfolders for the `report/` bundle.** `report/figures/` and
   `report/tables/` gain one nesting level keyed by pipeline stage
   (`figures/{pipeline,dft,fukui,esp,mc,md}/`, `tables/{dft,pka}/`). A single
   module, `corrosim/report_layout.py`, owns the filename→stage mapping so the
   write side (`runs.make_figures`, `runs.make_report`) and the read side
   (`report`, `report_docx`) never drift. The `figN_` manuscript numbering is
   kept as the file name. The reorg is scoped to the `report/` bundle; the source
   `results/` data tree stays flat (its drivers are unchanged).

2. **Word output via python-docx.** `runs.make_report` now writes
   `report/report.docx` next to `report.html`, built by `corrosim/report_docx.py`.
   python-docx is pure-Python (a new `report` extra, and in `dev`), so the venv/CI
   model holds; the HTML report needs none of it. Both renderers consume the same
   derived data (`report.prepare_report_data`) and the same narrative
   (`report_content.py`), so the two outputs stay in lock-step.

3. **Equations rendered as images via matplotlib mathtext.** `corrosim/equations.py`
   holds the governing equations (Koopmans descriptors, condensed Fukui,
   Henderson-Hasselbalch, the DFT pKaH cycle, the Stage-2/3 adsorption
   observables) and renders each to a PNG with matplotlib's built-in mathtext —
   no LaTeX, no MathJax. The HTML inlines them base64 (still self-contained); the
   Word doc adds them as pictures. Both therefore show real typeset formulas.

4. **Standalone explanations + woven scientific basis.** `report_content.py` is
   the single home for each figure's standalone explanation, the per-stage
   intros, and a "Scientific basis & validation" section distilled from
   `pipeline.md` + `validation.md` (the descriptor results, the computed-pKaH
   resolution, the published Fe(110) cross-checks, and the Mohammed 2014
   experimental anchor). Both renderers import it.

## Alternatives considered

- **pandoc from a Markdown source** for the Word output — gives editable OMML
  equations, but pandoc is a system binary outside the venv and absent in CI;
  rejected to keep the free-software/venv model (the customer needs equations in
  scientific form, not necessarily editable Word objects).
- **MathJax / KaTeX in the HTML** — would break the self-contained guarantee (CDN)
  or bloat the file (inlined JS); matplotlib mathtext reuses a core dependency.
- **Also nesting `results/`** by stage — deferred: it would rewire every stage
  driver's default paths and the coverage-omit list for little gain; the source
  data stays flat.
- **A single generic document model** feeding both renderers — heavier and a risk
  to the HTML test contract; instead the *content* is shared (`report_content`,
  `equations`, `prepare_report_data`) while each renderer keeps its own formatting.

## Consequences

- `report/` is navigable by stage, and ships both a shareable HTML file and a
  Word document with identical data, equations and prose.
- A new pure-Python dependency (`python-docx`) in the `report`/`dev` extras; the
  base install and the HTML path are unaffected. If python-docx is absent,
  `make_report` logs and skips the `.docx`, still writing the HTML.
- `report_layout` is the contract for figure/table placement: a new figure is
  slotted by its `figN_` prefix (or added to the map), and both renderers pick it
  up automatically.
- The new modules are venv-testable and in the coverage denominator (all at
  100%); scoped coverage stays well above the 80% gate.
