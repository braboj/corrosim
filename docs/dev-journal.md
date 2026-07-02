# Development journal

Session history for agent-assisted work on corrosim. Agents have no memory
across sessions; this journal records what changed and why. Newest entries are
at the bottom. Decisions link to ADRs in `docs/decisions/`; tasks link to issues.

## Architecture overview

corrosim is an open-source multiscale screening pipeline for green corrosion
inhibitors: Stage 1 DFT/xTB reactivity descriptors (with Fukui and ESP maps),
Stage 2 a Monte Carlo adsorption-pose search, and Stage 3 a Brownian
molecular-dynamics run yielding the metal–oxygen radial distribution, ending in
one self-contained HTML report. The reference case study is the Arghel
(*Solenostemma argel*) flavonoids on mild steel in 1 M HCl. The QM engines run
only in the `corrosim-qm` Docker image; everything else runs in a venv. See
`README.md` for structure and `docs/pipeline.md` for the scientific basis.

## 2026-06-29 — Multiscale pipeline build-out

- **Tool:** Claude Code (Opus).
- **Key changes:** Implemented the full DFT → Monte Carlo → MD pipeline
  (descriptors, Fukui, adsorption pose, metal–O RDF) plus the figure set and
  the self-contained HTML report, and added DFT geometry optimisation via the
  geomeTRIC backend.
- **PRs merged:** none — early work landed as direct commits on `main`
  (pre-PR workflow).
- **Issues closed/created:** none.
- **Decisions:** Adopted the pyrazolo-pyrimidine study as the methodology
  template and set production DFT to B3LYP/6-311++G(d,p) + ddCOSMO(water)
  (ADR 0002). Confirmed the lead ranking is geometry-robust (FF vs DFT-opt).

## 2026-06-30 — Tech-debt sweep and protonation science

- **Tool:** Claude Code (Opus).
- **Key changes:** Cleared the review backlog — CI quality gates, exception
  narrowing, a shared `surface.py`, a unified report builder, public-API typing
  with mypy, dependency ranges, and medium parsing. Added quantitative
  pH-speciation and a computed conjugate-acid pKaH from a DFT deprotonation
  cycle, which shows every flavonoid is under 0.1% protonated in 1 M HCl, so the
  quercetin lead is robust.
- **PRs merged:** #9–#17.
- **Issues closed/created:** created and closed the tech-debt set #1–#8.
- **Decisions:** `ruff format` gate deferred; mypy introduced non-strict;
  medium-to-protonation selection (ADR 0003); quantitative pH-speciation
  (ADR 0004); computed pKaH resolves the protonation lead (ADR 0005).

## 2026-07-01 — Optimised matrix, notebook removal, CLAUDE.md hybrid

- **Tool:** Claude Code (Opus 4.8).
- **Key changes:** Surfaced the DFT-optimised descriptor matrix (neutral
  ranking plus protonated cations) in the report and extended
  `compare_geometry` to the cations. Added the frequency-corrected pKaH path
  (`engines.thermo_correction` and `run_pka --freq`); the corrected numbers are
  still computing. Removed the stale notebook subsystem. Folded the Mohammed
  2014 MSc thesis into `docs/validation.md` as the experimental-validation
  anchor and scoped the lab-only gaps out of scope. Rewrote `CLAUDE.md` to the
  solid-ai-templates hybrid model and generated the companion docs.
- **PRs merged:** #21 (issues #18/#19), #22 (notebook removal).
- **Issues closed/created:** closed #19 and #20; reopened #18 pending the
  frequency-corrected results; filed four upstream issues in
  braboj/solid-ai-templates (#708–711).
- **Lesson:** The CI lint job runs `ruff` and `mypy`; run `mypy` before pushing,
  since `ruff` alone missed the type errors that turned PR #21 red. Do not write
  "closes #N" in a PR body unless the PR resolves the issue — the phrase
  auto-closed #18 prematurely and it had to be reopened. Chose the hybrid model
  deliberately for this repo (it vendors the templates, and reference-reads
  proved unreliable in practice).

## 2026-07-01 — Template conformance, docs de-clutter, report/ bundle

- **Tool:** Claude Code (Opus 4.8).
- **Key changes:** Rewrote `CLAUDE.md` strictly to the solid-ai-templates hybrid
  model and migrated `docs/adr/` → `docs/decisions/`; added the mandated
  companion docs (ONBOARDING, PLAYBOOK, dev-journal). Restructured `README.md`
  to the readme.md eight-section layout (capability/Features list, Quick start,
  Usage-with-output, Configuration reference, Links) and consolidated the
  redundant README Pipeline section into `docs/pipeline.md`. De-cluttered
  `docs/`: the seven `*.local.md` notes and the `whitepapers/` PDFs moved under
  a gitignored `docs/local/`. Consolidated pipeline outputs into a tracked
  `report/` bundle (`report.html` + `figures/` + `tables/`); stage drivers no
  longer write preview PNGs, so `results/` is now data-only.
- **PRs merged:** none yet — all on branch `docs/claude-md-hybrid` (PR #29, open).
- **Issues closed/created:** filed #23–#31; PR #29 closes #23–#28 and #30 on
  merge. #18 (freq-corrected pKaH) and #31 (python-lib stack deviations) remain
  open.
- **Decisions:** report/ output bundle + results/ data-only (ADR 0006).
- **Pending:** #18 QM job (`corrosim_pka_freq`) still running (~4 h) — no
  `results/pka_freq.json` yet; finalisation blocked on it. PR #29 awaiting merge.

## 2026-07-01 — Reconcile the four silent python-lib gate deviations (#31)

- **Tool:** Claude Code (Opus 4.8).
- **Key changes:** Adopted all four previously-silent quality gates. (1) ruff
  `D` with `convention = "google"` — cleaned the 26 reST-heading module
  docstrings to Google style and relaxed `D205` for the long scientific summary
  lines. (2) Scoped coverage gate: `[tool.coverage.run] omit` drops the
  QM-engine/Docker-only modules and `fail_under = 80` enforces the threshold on
  the QM-light-testable surface; added `tests/test_pipeline_drivers.py` (five
  venv-only driver smoke tests) which lifts scoped coverage 48% → ~85%.
  (3) gitleaks CI job alongside the existing pre-commit hook. (4) Bandit CI job
  (`[tool.bandit]`; the two `engines.py` QM-binary `subprocess` launches
  reviewed and `# nosec`-ed) plus a CodeQL SAST workflow.
- **PRs merged:** #32 (squash-merged to `main` as `a151ea8`; all 8 CI checks
  green — lint, test ×3.10/3.11/3.12, Bandit, gitleaks, CodeQL).
- **Issues closed/created:** closed #31 (auto-closed on merge).
- **Decisions:** reconcile the python-lib gates with QM-light by scoping
  coverage and relaxing `D205` (ADR 0007).
- **Verification:** `ruff check .`, `mypy`, `bandit -r corrosim` clean;
  `pytest` 66 passed / 1 skipped; scoped coverage ~85% (gate 80%).
- **Pending:** #18 (frequency-corrected pKaH) is the only open issue. The
  detached QM job `corrosim_pka_freq` (gas opt+freq cycle) has 1 of 3 molecules
  done — first corrected pKaH ≈ −12.90 (vs −7.29 electronic-only), so still ~0%
  protonated in 1 M HCl and the quercetin lead is unaffected; `results/pka_freq.json`
  is written only once all 3 finish. On completion: verify `n_imag = 0`, fold
  into `results/pka.json`, regenerate the `report/` bundle, update ADR 0005 +
  `docs/validation.md`, PR, and close #18.

## 2026-07-01 — Report insight: per-stage subfolders, Word output, equations

- **Tool:** Claude Code (Opus 4.8).
- **Key changes (customer request):** Reorganised the `report/` bundle into
  per-stage subfolders (`figures/{pipeline,dft,fukui,esp,mc,md}/`,
  `tables/{dft,pka}/`), single-sourced by a new `report_layout.py` that both the
  figure generator and the report builders resolve paths through. Added a Word
  (`.docx`) report (`report_docx.py`, python-docx) written alongside the HTML by
  `make_report`; both renderers share the derived data (`prepare_report_data`),
  the governing equations (`equations.py`) and the narrative (`report_content.py`).
  Equations appear in scientific form in both: matplotlib-mathtext images in the
  HTML, and **native, editable Word equations (OMML)** in the `.docx` via the
  pure-Python `latex2mathml` + `mathml2omml` chain (image fallback if absent) —
  no LaTeX/pandoc/Office toolchain. Every figure now carries
  a standalone explanation, and a new "Scientific basis & validation" section
  folds in `pipeline.md` (three-stage rationale, descriptor definitions) and
  `validation.md` (descriptor results, computed-pKaH resolution, published Fe(110)
  cross-checks, the Mohammed 2014 experimental anchor). Section/subsection headings
  (h2/h3) are numbered hierarchically (1, 1.1 …) identically in both formats, and
  Fukui + ESP were folded into Stage 1 as subsections (3.7 / 3.8) — the pipeline is
  three stages, so the old "Stage 1b/1c" badges were misleading. Regenerated the
  bundle (HTML 4.2 MB / DOCX 3.0 MB; 27 figures + 19 equations embedded in each).
- **Housekeeping:** de-duplicated obsolete memory/handoff files earlier in the
  session (retired `tech-debt-backlog`, `arghel-experimental-tbd`,
  `tech-debt.local.md`; collapsed `SESSION-HANDOFF.local.md` into this journal's
  Pending line).
- **PRs merged:** none yet — branch `feat/report-word-subfolders`.
- **Issues closed/created:** —.
- **Decisions:** report-bundle subfolders + Word output + equations in scientific
  form — HTML mathtext images, Word native editable OMML (ADR 0008); `report`
  extra (python-docx + latex2mathml + mathml2omml, also in `dev`), all pure-Python
  — reconciled with the venv/CI free-software model (no pandoc/Office/system binary).
- **Verification:** `ruff check .` and `mypy` clean; `pytest` 78 passed / 1
  skipped; scoped coverage 87.64% (gate 80%); regenerated `.docx` carries 19
  native (editable) equations + 27 figures.

## 2026-07-02 — Frequency-corrected pKaH folded in (#18 resolved)

- **Tool:** Claude Code (Opus 4.8).
- **Key changes:** The detached `corrosim_pka_freq` QM job finished for all three
  molecules; folded its frequency-corrected pKaH into `results/pka.json` (now the
  canonical file; the transient `pka_freq.json` was removed). Values became **more
  negative** (quercetin −13.3, kaempferol −12.9, isorhamnetin −5.1) than the
  electronic-only estimate, deepening the "all < 0.1 % protonated, quercetin lead
  robust" conclusion. Regenerated the `report/` bundle (HTML + Word) — the
  speciation section now shows the frequency-corrected caption and values.
- **Verification finding (surfaced, not hidden):** quercetin and kaempferol are
  clean minima (n_imag = 0 for neutral and cation); the **isorhamnetin cation
  retained one imaginary frequency** (a low methoxy/hydroxyl torsion). Documented
  as a caveat in `docs/validation.md`, ADR 0005 and the report itself — it does not
  change the conclusion (isorhamnetin stays neutral and is not the lead; the lead
  rests on a clean calc).
- **PRs merged:** none yet — added onto branch `feat/report-word-subfolders`
  (PR #33), since finalising #18 requires the new report code to regenerate the
  bundle. Resolves #18 on merge.
- **Issues closed/created:** resolves #18.
- **Decisions:** ADR 0005 updated (frequency-corrected pKaH is now the canonical
  result; isorhamnetin imaginary-mode caveat recorded).
- **Verification:** `ruff check .` and `mypy` clean; `pytest` 78 passed / 1 skipped.
- **Pending:** none — no open issues; PR #33 (report overhaul + #18) awaiting review.

<!-- Generated with solid-ai-templates (github.com/braboj/solid-ai-templates) -->
