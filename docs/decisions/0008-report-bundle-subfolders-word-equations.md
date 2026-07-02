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

3. **Equations in scientific form — images in HTML, native editable objects in
   Word.** `corrosim/equations.py` holds the governing equations (Koopmans
   descriptors, condensed Fukui, Henderson-Hasselbalch, the DFT pKaH cycle, the
   Stage-2/3 adsorption observables) as LaTeX. The **HTML** renders each to a PNG
   with matplotlib's built-in mathtext (no LaTeX/MathJax) and inlines it base64,
   so the file stays self-contained. The **Word** report inserts each as a native,
   editable equation (OMML): the LaTeX is converted LaTeX -> MathML -> OMML with
   the pure-Python `latex2mathml` + `mathml2omml` packages (added to the `report`
   extra) and appended to the paragraph via python-docx's XML API — so a reader
   can click and edit formulas in Word's equation editor. If that toolchain is
   absent or a conversion fails, the Word equation degrades to the mathtext image,
   so a formula is never missing. No LaTeX, pandoc or Office toolchain is required.

4. **Standalone explanations + woven scientific basis.** `report_content.py` is
   the single home for each figure's standalone explanation, the per-stage
   intros, and a "Scientific basis & validation" section distilled from
   `pipeline.md` + `validation.md` (the descriptor results, the computed-pKaH
   resolution, the published Fe(110) cross-checks, and the Mohammed 2014
   experimental anchor). Both renderers import it.

## Alternatives considered

- **pandoc from a Markdown source** for the Word output — also yields editable
  OMML, but pandoc is a system binary outside the venv and absent in CI, and it
  would mean rebuilding the whole document from Markdown (discarding the
  python-docx structure). Rejected once the pure-Python `latex2mathml` +
  `mathml2omml` chain was shown to produce the same editable OMML with no system
  binary.
- **Equations as images in Word too** (the initial choice) — simplest, but the
  client wanted editable equation objects; superseded by the OMML path above, with
  the image kept only as a fallback.
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
- New pure-Python dependencies in the `report`/`dev` extras (`python-docx`, plus
  `latex2mathml` + `mathml2omml` for the editable equations); the base install
  and the HTML path are unaffected. If python-docx is absent, `make_report` logs
  and skips the `.docx`, still writing the HTML; if only the equation toolchain is
  absent, the `.docx` is written with the equation images instead.
- `report_layout` is the contract for figure/table placement: a new figure is
  slotted by its `figN_` prefix (or added to the map), and both renderers pick it
  up automatically.
- The new modules are venv-testable and in the coverage denominator (all at
  100%); scoped coverage stays well above the 80% gate.
