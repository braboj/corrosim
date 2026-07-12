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

## 2026-07-02 — Docs DRY sweep; `docs/diagrams/`; §1.1 refiled to identity

- **Tool:** Claude Code (Opus 4.8).
- **Key changes (docs-only, no code touched):**
  - Filed **#34** — optional cleanup of the isorhamnetin-cation imaginary
    frequency (tighter-convergence re-opt); scoped as presentation polish, ~1–3 h
    detached QM job, ranking unaffected.
  - Moved `docs/pipeline.drawio` → **`docs/diagrams/`** (git rename, history kept)
    and updated every reference (README, `pipeline.md`, `CLAUDE.md`, memory).
  - **CLAUDE.md DRY pass:** replaced the duplicate project-structure tree in § 1.2
    with a pointer to README (the SSOT per § 1.4) + the few agent-only facts a
    listing can't give; deduped the tracked-vs-gitignored fact to § 2.1; pointed
    the core-deps list at `pyproject.toml`.
  - **Refiled § 1.1 Identity** to the template's definition (owner/repo/stack/
    hosting): moved the pipeline overview to the top-of-file description and the
    QM-engines Docker-only **execution constraint** to § 1.3 Commands.
  - **Fixed a broken image in `pipeline.md`** (surfaced by the wrap-up audit):
    its `fig0_pipeline.png` link pointed at the pre-ADR-0008 flat path, which no
    longer exists. Committed the rendered diagram co-located as
    `docs/diagrams/pipeline.png` (identical to the report render) and repointed
    the image + re-export command at it.
- **PRs merged:** none — **PR #35** opened (branch
  `docs/diagrams-folder-dedupe-structure`, 2 commits); not merged.
- **Issues closed/created:** created **#34**; PR #35 resolves no issue (no
  auto-close trailer).
- **Decisions:** no new ADR — organizational, not architectural. Principle
  applied and reinforced: CLAUDE.md carries decisions/invariants a directory
  listing can't recover, never a mirror of discoverable facts (README is the SSOT
  for structure, § 1.4).
- **Verification:** docs/config only — no runtime surface, so the `pytest`/`ruff`/
  `mypy` gates were not required to re-run; `report/` bundle unchanged (the
  `.drawio` move is byte-identical, so `fig0_pipeline.png` is unaffected).
- **Pending:** PR #35 awaiting review; **#34** open (isorhamnetin imaginary-freq
  cleanup, optional).

## 2026-07-02 — Tickets #37 + #38: MC/MD geometry doc + descriptor `_ff`/`_opt` rename

- **Tool:** Claude Code (Opus 4.8).
- **Scope:** picked up the two **non-QM** open tickets (the other two, #34 and #36,
  need the `corrosim-qm` image and were left). PR #35 from the prior session had
  merged (tip `2934a35`), so `main` was clean.
- **Key changes:**
  - **#38 (refactor):** disambiguated the two DFT descriptor tables. The
    FF-geometry matrix was `results/dft_descriptors.{csv,json}` (geometry implicit)
    while the optimised one carried `_opt`; renamed the FF one to
    `dft_descriptors_ff.{csv,json}` for a symmetric `_ff` / `_opt` pair. Pure `git
    mv` (byte-identical), incl. the bundled `report/tables/dft/` copy. Updated every
    reader (`report_layout`, `make_report`, `make_figures`, `compare_geometry`,
    `run_dft` docstring, the driver smoke tests) and all docs/config (README,
    CLAUDE.md, PLAYBOOK, pipeline.md, validation.md, docker-compose.yml, Dockerfile).
    `report.html`/`report.docx` are filename-agnostic (verified — zero references),
    so their content is unchanged; only the source/bundled table names moved.
  - **#37 (docs):** made the FF-vs-DFT geometry choice explicit — new **ADR 0009**
    (MC/MD run on the FF geometry by design; Stage-1 descriptors use the
    DFT-optimised geometry; rigid-body-vdW rationale + #36 follow-on), plus an
    **Input** row on the MC and MD stage tables in `pipeline.md` (they had none) and
    a shared "Geometry across stages" note linking the ADR.
  - **Bonus:** fixed a pre-existing broken ADR link in `pipeline.md`
    (`adr/…` → `decisions/…`).
- **PRs merged:** **PR #39** (branch `refactor/dft-descriptors-ff-opt`) — resolves
  #37 and #38.
- **Issues closed/created:** resolves **#37**, **#38**. Still open: **#34**, **#36**
  (both QM-dependent).
- **Decisions:** **ADR 0009** — FF geometry for MC/MD.
- **Verification:** `ruff check .` clean; `mypy` clean (31 files); `pytest` green
  (exit 0, coverage gate satisfied, 1 skip). No QM run needed — rename + docs only.
- **Pending:** **#34** (clear the isorhamnetin cation imaginary frequency,
  tighter-convergence re-opt) and **#36** (persist `results/*_opt.xyz`) remain —
  both need the `corrosim-qm` Docker image; **#36** would unblock the optional MC/MD
  DFT-geometry sharing flagged in ADR 0009.

## 2026-07-03 — #36 persist geometry; report clarity overhaul; docs polish

- **Tool:** Claude Code (Opus 4.8). Session ran 2026-07-02 → 07-03; picked up the
  four open tickets plus a client review of the report.
- **Key changes:**
  - **#36 (persist DFT-optimised geometry) — PR #42 (open):** new
    `molecules.write_xyz`; `run_dft` gains `--opt-xyz-dir`; each optimised species is
    written as `results/<molecule>_opt.xyz` (neutral + `+H+`). Ran the detached
    `corrosim-qm` optimisation — it reproduced the tracked `dft_descriptors_opt`
    matrix to ~12 sig figs (ranking robust; quercetin keeps the smallest aqueous
    gap), so committed the **6 xyz** and reverted the descriptor-file churn (the
    re-run only added float noise + a new `e_total_ev` column the FF matrix lacks).
    Two `write_xyz` tests; pipeline.md Output line updated.
  - **Report clarity overhaul (client review) — PR #43 (open):** added plain-language
    answers, shared across HTML+Word via `report_content.py` — the composite/z-score,
    a data-derived **"Bottom line"**, the DFT level gloss (B3LYP/6-311++G(d,p)/
    ddCOSMO), 2D-structure generation, frontier=HOMO/LUMO, ESP-vs-Fukui, the
    geometry-refinement rationale, protonation, and the **Monte-Carlo methodology +
    software** (ASE standard, UFF Rappé 1992, the MC search corrosim's own).
    **Dropped the "Stage 1/2/3" labels** everywhere (headers, overview, scientific
    basis, equation groups) — the pipeline has more steps than three. **Pretty-
    labelled** the summary table. z-score + bottom-line are now shared functions
    (de-duplicated across the two renderers).
  - **Docs polish (rides in PR #42):** pipeline.md — Output paragraphs, alphabetised
    glossary, numbered Notes section, "Stage-1"→step wording, Materials Studio named
    on its modules, LAMMPS marked free/GPL; README — Limitations/Roadmap split.
  - **Earlier this session (merged):** #37 (document the MC/MD FF-geometry choice,
    ADR 0009) + #38 (descriptor `_ff`/`_opt` rename) → **PR #39 (merged)**.
- **PRs:** #39, **#42** and **#43** all squash-merged to `main` (2026-07-03).
- **Issues:** #37, #38 closed via #39; **#36 closed via #42**. Created **#40**
  (quantitative E_ads hand-off) and **#41** (routine true-minimum/frequency check)
  from the old README roadmap. Still open: #34, #40, #41.
- **Decisions:** ADR 0009 (FF geometry for MC/MD, from #37). **ADR 0010** — the
  report narrative may be AI-authored at dev time (Claude Code) and committed as
  reviewed static content; the shipped pipeline stays LLM-free/deterministic (no
  runtime AI dependency); narrative single-sourced in `report_content.py`.
- **Verification:** `ruff` clean; `mypy` clean (31 files); `pytest` green. Report
  bundle regenerated (HTML + Word).
- **Pending:** all of this session's PRs are merged; this wrap-up (journal + ADR
  0010) is the only open PR. Optional report follow-ups: a tighter "how the final
  score is computed" pipeline thread; refresh both descriptor matrices to add
  `e_total_ev` (schema parity); a PLAYBOOK "report clarity pass" entry. The ADR 0010
  principle is a candidate reusable upstream-template convention (not yet filed).
  Open QM tickets: **#34** (isorhamnetin cation imaginary freq), **#41** (routine
  freq check), **#40** (LAMMPS/periodic-DFT E_ads).

## 2026-07-03 — #34 isorhamnetin imaginary freq cleared + ranking-vs-validation docs

- **Tool:** Claude Code (Opus 4.8).
- **Scope:** two threads. (1) Resolved the last open QM ticket, **#34** — clear the
  lone imaginary frequency on the isorhamnetin cation. (2) A user-requested docs
  clarification: make explicit that **DFT descriptors drive the ranking; MC/MD only
  validate it**.
- **#34 — engine machinery (`corrosim/engines.py`):** `optimize_geometry` and
  `thermo_correction` gained `grid_level` (finer DFT integration grid) + the optimiser
  a `convergence_set`; `thermo_correction` now also returns `freq_cm` + `norm_mode`.
  New helpers: `imaginary_mode` (pick the softest imaginary mode), `displace_along_mode`
  (step off a saddle by a scaled amplitude), and `relax_to_minimum` (opt → freq →
  displace-if-imaginary → re-opt loop). `run_pka` gained `--tight` (routes each `--freq`
  species through `relax_to_minimum`; default path byte-identical). 6 QM-light tests in
  new `tests/test_engines.py` for the two pure helpers.
- **#34 — the QM run (detached, `corrosim-qm`):** the recipe that worked is **finer
  grid (level 4) + GAU convergence + imaginary-mode displacement**, seeded from the
  persisted `results/isorhamnetin_opt.xyz` / `_+H+_opt.xyz` minima. Two false starts
  first, both wall-clock traps and *both my misjudgement*: grid 5 (~8 min/step) and
  GAU_TIGHT (18 micro-steps on flat torsions). Lesson folded back into the code — the
  `relax_to_minimum` defaults are now grid 4 / GAU (not 5 / GAU_TIGHT), and `--tight`
  help/level strings match. A throwaway `_refine_iso.py` (seeded, not committed) drove
  the actual run; `run_pka --freq --tight --molecules isorhamnetin` reproduces it from
  scratch (slower, FF start).
- **#34 — result + narrative correction:** the cation reaches a true minimum
  (`n_imag_cation = 0`); **all six species are now clean minima**. The pKaH refines
  **−5.12 → −3.92** — importantly *less* negative, the **opposite** of ADR 0005's old
  "would only make it more negative" guess: the old value sat on a saddle whose
  inflated cation `g_corr` (6.14 → 6.07 eV at the minimum) understated the cation's
  basicity. Conclusion **unchanged** — still ~0.01 % protonated at pH 0, far below the
  −1.2 crossover, still not the lead, ranking untouched (ranking is neutral-DFT only).
  Spliced the new row into `results/pka.json` (+ bundled `report/tables/pka/pka.json`
  via `make_report`); dropped the caveat and fixed the direction claim in
  `docs/validation.md`, **ADR 0005**, and `corrosim/report_content.py`.
- **Ranking-vs-validation docs:** `docs/pipeline.md` gained a **Ranking** section (the
  composite = z-scored gap/hardness/softness, neutral form; MC E_ads and MD metal–O
  distance are validation, not score inputs) + an overview pointer. The report says it
  too — strengthened `score_explanation` ("the ranking is these electronic descriptors
  alone … E_ads and the Fe–O distance … validate … not inputs") and short clauses in
  the MC/MD stage intros. Report bundle regenerated.
- **PRs merged:** **PR #45** (this branch: #34 fix + ranking-vs-validation docs) squash-
  merged to `main` (2026-07-04), landed **after PR #44** (prior wrap-up: ADR 0010 + the
  #36/#42/#43 journal entries) to preserve dev-journal append order — `main` was merged
  into this branch and the two entries reordered chronologically before merge.
- **Issues closed/created:** PR #45 carries `Closes #34` (auto-closes #34 on merge).
- **Decisions:** no new ADR; **ADR 0005 updated** (2026-07-03 note + Finding row +
  caveat-turned-resolution). The grid-4/GAU recipe lives in `relax_to_minimum`'s
  docstring, not a separate ADR (implementation detail, not a cross-cutting decision).
- **Verification:** `ruff check .` clean; `mypy` clean (31 files); `pytest -q` green
  (1 skip, the xTB smoke test); **all PR #45 CI checks green** (lint, test 3.10–3.12,
  CodeQL, Bandit, gitleaks). Report spot-checked: `−3.9` present, old `−5.1` + caveat
  gone, bundled `pka.json` shows −3.92.
- **Pending:** **Both PRs landed** (#44 then #45); #34 auto-closed on #45 merge. Open
  issues are **#40** (LAMMPS/periodic-DFT E_ads) and **#41** (routine true-minimum/
  frequency check), both QM/compute-heavy and unstarted.

## 2026-07-04 — #41 minimum-check shipped; codebase review → 25 issues, 4 epics, 1 spike

- **Tool:** Claude Code (Opus 4.8).
- **Scope:** three threads. (1) Land the two prior-session PRs. (2) Implement + merge the
  last open QM feature, **#41** (routine true-minimum check for `run_dft --optimize`).
  (3) A full code-quality review of the codebase, filed as a structured backlog.
- **PRs landed (all 2026-07-04):** **#44** (prior wrap: ADR 0010 + #36/#42/#43 journal),
  then **#45** (#34 fix) — reordering the dev-journal on an append-order conflict; then
  **#46**, the #41 feature (`run_dft --check-minimum` / `--to-minimum`, new pure helper
  `engines.min_check_fields`) with the **#49** pre-merge review fixes folded in
  (`Closes #41`, `Closes #49`).
- **#41 + #49 (in #46):** `--check-minimum` records `n_imag` + a **signed**
  `lowest_freq_cm` (negative = imaginary) per descriptor row so a saddle never silently
  feeds Stage-1; `--to-minimum` drives to a verified minimum (grid-4 + imaginary-mode
  restarts, honoring `--opt-maxsteps`); a bare `--check-minimum` no longer clobbers a
  tracked `*_opt.xyz`. New QM-light tests (`test_engines` helper + `test_run_dft` wiring);
  corrected an earlier test that had enshrined the wrong `lowest_freq_cm = 0.0`.
- **QM verification (detached, `corrosim-qm`):** ran `run_dft --check-minimum` on
  kaempferol neutral end-to-end. Geometry opt converged (~71 min); the analytic
  frequency-check Hessian is **still running at wrap** (see Pending) — the log confirms
  the new code reached the frequency stage (result unaffected by the #49 sign fix; a
  neutral is a clean minimum).
- **Code-quality review (planning only — no repo change beyond #46):** reviewed surface,
  md, mc, fukui by hand + a **5-agent parallel sweep** of the remaining ~16 modules.
  Honest triage — **10 of 16 swept modules were SWEEP-ONLY** (mechanical only), **zero
  new correctness bugs** beyond #47/#49. Filed: bug **#47** (`orient_flat` orients
  molecules vertical — confirmed empirically); standards **#51** (full API contract),
  **#52** (readability standard); foundational de-dup **#57** (shared UFF vdW energy +
  `EV_TO_KJMOL` + pose), **#64** (shared driver CLI → `runs/_cli.py`); per-module
  refactors **#48, #50, #55, #56, #58, #59, #60, #61, #62, #63**;
  generalization/validation **#54** (data-driven molecule library + optional fetch),
  **#53** (per-paper validation presets); deployment **#66** (Colab), **#67**
  (release → GHCR + PyPI), **#68** (GitHub Pages); structure **spike #73** (`src/` layout
  and subsystem sub-packages).
- **Organization:** grouped into **four workstream epics** — **#69** Standards &
  Foundations, **#70** Per-module refactors (gated by #73), **#71** Deployment, **#72**
  Generalization & Validation (a first mega-epic #65 was created then split/retired). New
  labels `tech-debt`, `epic`, `spike`. Standalone: #40, #47.
- **Decisions:** no ADR filed this session — the durable decisions (adopt the API
  contract + readability standard; the `src/`-layout question; zero-cost deployment via
  Colab/GHCR/PyPI/Pages, **not** a hosted web app) are tracked in #51/#52/#73/#71, each of
  which produces its own ADR (amending ADR 0007's `--strict`/D-rule deferral) when
  implemented.
- **Verification:** `ruff check .` clean; `mypy` clean (31 files); `pytest -q` green
  (93 passed, 1 skip); PR #46 CI all green before merge.
- **Pending:** **the kaempferol frequency-check QM job is still running** (container
  `corrosim_mincheck`, ~3 h; opt done, Hessian in progress) — confirm `n_imag = 0` then
  `docker rm` it. Backlog then executes in order: **spike #73** (structure) → **#69**
  (standards + CI gates + de-dup) → **#70** (per-module refactors) → **#72**
  (generalization) → **#71** (deployment) → **#40** (E_ads). Fix bug **#47**
  (`orient_flat`) early — it regenerates MC/MD artifacts. Cosmetic loose end: deployment
  tickets #66–#68 still cite the retired epic #65.

## 2026-07-04 — #47 orient_flat fix + MC/MD/report regen; n_imag provenance backfill

- **Tool:** Claude Code (Opus 4.8).
- **Scope:** resume from the prior wrap's Pending — (1) close out the kaempferol
  minimum-check QM job, (2) fix bug **#47** (`orient_flat`), (3) fold the existing
  frequency provenance into the opt descriptor matrix. Two focused PRs, both merged.
- **Prior Pending resolved:** the detached `run_dft --check-minimum` job on kaempferol
  neutral finished — **`neutral: true minimum verified (n_imag=0)`**; a background wrapper
  captured the result and `docker rm`'d the container. Its descriptors (gap **3.72** gas /
  **3.69** aqueous) match the committed `dft_descriptors_opt.csv` exactly, so the committed
  opt geometry already sits on the verified minimum. Also removed a stray `C:` phantom
  directory (a Windows-absolute-path-as-relative artifact from the QM job's temp write).
- **#47 (PR #75, merged → `56a6301`, `Closes #47`):** `orient_flat` used `R = vt[::-1].T`;
  since `np.linalg.svd` returns rows in descending spread, the reversal mapped the
  **largest**-spread axis onto `z` (molecule stood vertical). Fix `R = vt.T` → least-spread
  axis on `z`, plane flat on `xy`. Added an orientation-asserting test (the prior isometry
  test can't catch a wrong rotation — any rotation is an isometry; verified it fails on the
  old code). Regenerated dependents in the same change: `md_rdf.json` (Fe–O peaks shift —
  kaempferol 3.35→3.15, quercetin 3.65→3.25, isorhamnetin 3.75; **ranking preserved**,
  kaempferol still closest), 9 MC/MD figures, and the report bundle; corrected a **stale
  hardcoded** RDF-peak value in the cross-check prose (`report_content.py`,
  3.65/3.35/3.75 → 3.25/3.15/3.75).
- **n_imag backfill (PR #76, merged → `3785d2d`):** the opt descriptor matrix predated the
  #41 minimum-check feature, so it carried no `n_imag` column. Folded in the
  already-computed imaginary-mode counts from the pKa opt+freq run (#34/#45, in
  `results/pka.json`) — all 6 species (3 neutral + 3 cations) are true minima (`n_imag=0`),
  covering all 12 rows. **No QM re-run** (a full `--check-minimum` pass ≈ a day for data
  that already exists). CRLF-preserving append via the `csv` module — no existing float
  reformatted (word-diff confirmed additive-only). Report intentionally **not** regenerated:
  its descriptor table uses a fixed column list that excludes `n_imag`, and the prose
  already asserts all six species are clean minima.
- **Verification:** `ruff check .` clean; `mypy` clean (31 files); `pytest` 94 passed / 1
  skip. Both PRs green pre-merge; main CI green post-merge (`#75`, `#76`).
- **Decisions:** no ADR — a bug fix plus a one-off provenance backfill, no structural or
  architectural change, no new directory, no content moved between docs.
- **Pending:** working tree clean, only `main` local. Backlog (all validated open) resumes
  in order: **spike #73** (`src/` layout) → **#69** standards + de-dup → **#70** per-module
  refactors → **#72** generalization → **#71** deployment → **#40** (E_ads). Cosmetic loose
  end still open: deployment tickets **#66–#68** cite the retired epic #65. Submodule
  `docs/solid-ai-templates` not bumped this session (no template work).

## 2026-07-04 — spike #73 resolved: ADR 0011 (src/ layout + subsystem sub-packages)

- **Tool:** Claude Code (Fable 5).
- **Scope:** resume the backlog at its first item — **spike #73** (project
  structure). Analyse-only spike whose deliverable is a decision + ADR, not code.
  Explored the repo with three parallel agents (structure/import graph,
  duplication hotspots for #69/#70, packaging/CI/deployment surface) so the
  decision rests on measured facts, not assumption.
- **Decision (ADR 0011, Accepted):** adopt a **`src/` layout** AND regroup the 22
  flat modules into three subsystem sub-packages — `qm/` (engines, descriptors,
  fukui, pka, speciation), `adsorption/` (surface, adsorption, mc, md), `report/`
  (report, report_content, report_docx, report_layout, figures, equations) — with
  molecules/medium/presets/cli and `runs/` staying at the top. `src/` carries the
  packaging-correctness payoff for #54 package-data + #67 publishing (forces
  test-against-installed); the sub-package grouping is organisational, and its
  only cost (import churn on lines #70 touches) is neutralised by sequencing the
  move **before #70**.
- **Grounding facts:** import DAG is a clean acyclic graph (surface/presets are
  leaves); tests are layout-agnostic (no `sys.path` hacks — reinstall suffices);
  the move edits only path-based refs (`pyproject` find/coverage/mypy/bandit,
  `Dockerfile:26`, `ci.yml:77`, stale doc paths). Public API stays stable via the
  `__init__` `__all__` facade; the one break — `from corrosim import
  figures`/`report` (module→package collision) — is contained by `report/__init__`
  re-exports + three consumer edits.
- **Owner input:** owner leaned `src/` + sub-packages over `src/`-flat; the ADR
  records `src/`-flat as the honest lower-churn alternative and keep-flat as
  rejected (loses import hygiene). Session scope agreed as **ADR only** — no file
  moves this session.
- **Also:** filed migration ticket **#78** (concrete ordered steps, gated strictly
  before #70); pointed CLAUDE.md §1.2 at ADR 0011 (supersedes the "flat is
  deliberate" note). Spike **#73 closes** when this ADR merges.
- **Verification:** doc-only change; `ruff check .`, `mypy`, `pytest -q` re-run as
  a no-op sanity check.
- **Shipped:** **PR #79** squash-merged to `main` (`d6647b1`), all 8 checks green;
  spike **#73 auto-closed**; migration **#78** open (gated before #70). Epic **#69**
  checklist ticks #73; epic **#70** gating note updated to "spike resolved → do #78
  first". Post-merge CI on `main` green (CI + CodeQL).
- **Tagging decision:** owner asked whether to tag before continuing → **no**. No
  tags exist, `version = 0.1.0` static, and release-on-tag automation (#67) does
  not exist yet, so a tag today is a no-op; the whole point of the `src/` move is
  packaging correctness, so the **first tag should be the post-#78 layout**
  (ideally after #67 wires GHCR/PyPI). A pre-migration bookmark tag is redundant
  with the commit SHA + reviewed PRs.
- **Pending:** working tree clean, only `main` local. Backlog resumes: land the
  **#78** migration PR (mechanical `src/` + sub-package move — do it before #70),
  then **#69** standards + de-dup (start #57 shared UFF vdW → surface.py, then
  #64 `runs/_cli.py`, then stage #51/#52 gates) → **#70** per-module refactors →
  **#72** generalization → **#71** deployment → **#40** (E_ads). First release
  tag deferred to post-#78/#67. Cosmetic loose end still open: deployment tickets
  **#66–#68** cite the retired epic #65.

## 2026-07-04 — #78 executed: src/ layout + subsystem sub-packages live

- **Tool:** Claude Code (Fable 5).
- **Scope:** resume at the backlog head — execute migration ticket **#78**
  (ADR 0011): mechanical `git mv` of `corrosim/` → `src/corrosim/` regrouped
  into `qm/` / `adsorption/` / `report/` sub-packages; behaviour-preserving,
  no logic change.
- **Done:** moves with git rename detection intact; sub-package `__init__`
  facades keep the public API stable — including the third module→package
  collision (`corrosim.adsorption`) the ticket hadn't flagged (only
  figures/report); intra-cluster imports stay relative, cross-cluster go
  `..qm.descriptors`; `runs/` + tests re-pointed; packaging re-anchored
  (`packages.find` `where=["src"]`, coverage omit, mypy files, ruff
  per-file-ignores); Dockerfile `COPY src ./src`; CI `bandit -r src/corrosim`;
  docs refreshed (README tree, pipeline.md module table, ONBOARDING, PLAYBOOK,
  CLAUDE.md §1.2).
- **Catch of the session:** bandit's bare `"report"` in `exclude_dirs`
  silently excluded the new `src/corrosim/report/` sub-package from SAST
  (2357 vs 4312 LOC scanned) — anchored to `"./report"`. CI would have stayed
  green while skipping ~2k lines; flagged upstream as a python-lib.md
  candidate (src/-layout excludes must not collide with package dir names).
- **Verification:** editable reinstall resolves `corrosim` from `src/` (the
  ADR's packaging payoff — working-tree/installed ambiguity closed); ruff +
  mypy + pytest green (94 passed, 1 skip; coverage 88.22% ≥ 80% with the
  re-pointed omit); CLI + all drivers smoke-tested; bandit re-scan clean.
  `report/` bundle + `results/` untouched (no input changed — nothing to
  regenerate).
- **Shipped:** **PR #81** squash-merged to `main` (`84df38e`), all 8 checks
  green; **#78 auto-closed**; post-merge CI + CodeQL on `main` green. Epic
  **#70** gate note flipped to "cleared"; epic **#69** #73 line notes the
  landing. Auto-memory (`corrosim-pipeline-state`) updated to the new layout.
- **Decisions:** no new ADR — this session executes ADR 0011; the new
  directories are exactly the ones that ADR decided.
- **Pending:** working tree clean, only `main` local. Backlog resumes at epic
  **#69** standards + de-dup: start **#57** (shared UFF vdW → `surface.py`,
  now `src/corrosim/adsorption/surface.py`), then **#64** (`runs/_cli.py`),
  then stage the #51/#52 gates → **#70** per-module refactors (unblocked) →
  **#72** generalization → **#71** deployment → **#40** (E_ads). All validated
  open in the tracker today (2026-07-04). First release tag still deferred to
  post-#67. Cosmetic loose end: **#66–#68** cite the retired epic #65.

## 2026-07-04 — #69 de-dup: shared UFF vdW (#57) + driver CLI (#64) landed

- **Tool:** Claude Code (Fable 5).
- **Scope:** resume at the epic **#69** backlog head — the two foundational
  de-duplication tickets that unblock the #70 per-module refactors: **#57**
  (shared UFF van-der-Waals machinery → `surface.py`) then **#64** (shared
  driver CLI boilerplate → `runs/_cli.py`). Both behaviour-preserving.
- **#57 done (PR #83):** `surface.py` gained `uff_mixing` (combining rules +
  the UFF-params `ValueError`, was 3 copies), `uff_vdw_energy` /
  `uff_vdw_forces` (one vectorised LJ 12-6; energy for mc/adsorption, energy+
  forces for md — two functions, not a boolean flag), and
  `initial_adsorption_pose` (orient-centre-lift; per-module lifts →
  `MC_START_HEIGHT_A` / `MD_START_HEIGHT_A`). `EV_TO_KJMOL` moved next to
  `KCAL_TO_EV`; `equations.py` imports it and folds it into the conversion
  LaTeX (its "mc uses this" comment was stale — mc hardcoded `96.485`).
  `adsorption.py`'s divergent per-pair Python loop (which *skipped* rather than
  clamped sub-`MIN_PAIR_DISTANCE_A` pairs) is gone.
- **#64 done (PR #84):** `runs/_cli.py` single-sources `parse_molecules`,
  `add_molecules_arg` (kills the per-driver `DEFAULT_MOLECULES`), `stderr_log`
  (cleared 4 ruff E731 lambdas), `write_json`/`read_json` (close handles via
  `with`; fixes the unclosed `open()` I/O in 5 drivers), `print_table`,
  `strip_protonation_suffix`. Folded in: run_md's warm-up `2000` →
  `MC_WARMUP_STEPS`; every driver `main` now types `argv: Sequence[str] | None`.
- **Verification:** #57 proven behaviour-preserving **to the bit** — a golden
  capture (sha256 over full-precision energy/position arrays) of seeded
  `run_mc`/`run_md` + `estimate_adsorption_energy` (3 flavonoids + production
  size) is byte-identical before/after, so `results/` and the `report/` bundle
  needed no regeneration. #64 smoke-ran the venv drivers end-to-end against the
  committed `results/` (tables, JSON I/O, rankings PRESERVED). New unit tests:
  `test_surface_vdw` (two-atom energy = −D_ij, forces vs finite difference,
  pose invariants), `test_runs_cli` (JSON round-trip + missing-file branches,
  print_table rows-vs-DataFrame, suffix strip); the single-source identity test
  and `test_drivers_share_the_preset_list` re-pinned to the new shared APIs.
  ruff + mypy + pytest green (105 passed, 1 skip; `_cli.py` 100% covered, total
  88.4% ≥ 80%). Both PRs squash-merged, all 8 checks green each; **#57/#64
  auto-closed**; epic **#69** boxes ticked; post-merge CI + CodeQL on `main`
  green.
- **Decisions:** no ADR — both are mechanical DRY de-dups governed by the
  existing `quality.md` "third copy is a bug" rule; no new directories, no
  content moved between docs. README structure map notes `runs/_cli.py`.
- **Pending:** working tree clean, only `main` local. Epic **#69** now has only
  the two *standards* tickets left — **#51** (full public API contract; ruff
  `ANN` + `D417`) and **#52** (readability standard; ruff `line-length` +
  `C901`) — which flip CI gates and want an ADR amending ADR 0007's deferrals;
  bigger than this session's mechanical refactors, so confirm scope before
  starting. After #69: **#70** per-module refactors (now fully unblocked —
  #57→#55/#56, #64→#62/#63) → **#72** generalization → **#71** deployment →
  **#40** (E_ads). First release tag still deferred to post-#67. Cosmetic loose
  end: **#66–#68** cite the retired epic #65.

## 2026-07-04 — #51/#52 standards sweep begun: ADR 0012 + 4 module batches

- **Tool:** Claude Code (Fable 5).
- **Scope:** the last two epic **#69** tickets — **#51** (full public API
  contract) + **#52** (readability standard). Being run **together, module by
  module** (both rewrite the same functions), each a green PR, with enforcement
  staged so CI never half-breaks.
- **Enforcement mechanism (key design):** a **`CONTRACTED` allowlist** in
  `tests/test_docstrings.py` — for the listed modules it asserts full public
  annotations, Google `Args:`/`Returns:` completeness, ≤80 cols, no trailing
  comments (tokenize; `# noqa`/`# nosec` exempt) and no ticket-number comments.
  The list grows one batch per PR; a final PR flips the global ruff gate and
  retires it. **Decision: NOT ruff `ANN`** — #51 is the *public* contract, so
  the allowlist test enforces public-def annotation (private pyscf-object
  helpers stay un-annotated, avoiding `Any`/`attr-defined` friction); the flip
  adds only `line-length=80` + `D417` + `C901`. Also fixed a real bug:
  `test_docstrings.py`'s package path still pointed at the pre-#78 `corrosim/`,
  so the docstring-presence gate had silently been a **no-op** since the `src/`
  move — re-pointed at `src/corrosim`.
- **Landed (all squash-merged, 8/8 checks each, main green):** **PR #86**
  foundation (ADR 0012 amending ADR 0007; CLAUDE.md §2.2 — line length 100→80,
  scientific-comment clause now names the *source* not an ADR number, block/no-
  trailing conventions; the contract tests; `presets.py` + `runs/_cli.py`
  cleaned). **PR #87** `adsorption/` (surface/adsorption/mc/md/__init__) — mc/md
  are numeric, so verified **bit-identical** via a full-precision golden
  (`scratchpad/golden_57.py`: sha256 of seeded run_mc/run_md + estimate over 3
  flavonoids). **PR #88** `qm/` (engines/fukui/pka/speciation/descriptors/
  __init__). **PR #89** `report/` part 1 (report_layout/equations/report_docx).
- **Rules that bit / conventions:** string *content* is never changed — long
  strings reflow only as value-preserving adjacent literals (a caption edit was
  reverted); rule 5 (no ticket numbers) is **comments only**, not docstrings or
  rendered strings; tool directives stay inline; the mc rotation-step and md
  trans/dphi splits preserve RNG draw order exactly.
- **Pending — resume the #51/#52 sweep at `report/` remainder:**
  - **`figures.py`** (~14 public fns): full param annotations (duck-typed
    render inputs `system`/`result`/`fukui`/`molecule` → `Any`; heterogeneous
    returns → `object` with a Returns note) + Args/Returns; 37 ruff line-length.
  - **`report.py`**: 8 public fns need Args/Returns + return types. **Caveat:**
    it has an `E501` per-file-ignore for embedded CSS — when it joins
    `CONTRACTED`, the contract test's width check must skip report.py (or its
    CSS lines) to match, else the CSS lines fail. Mostly private helpers (out of
    the public contract).
  - **`report_content.py`** (~116): almost all E501 in narrative strings —
    reflow as adjacent literals, value-preserving; regenerate + diff the report
    bundle to confirm no drift.
  - Then **`runs/`** drivers + top-level (`cli` 11, `molecules` 11, `medium` 9,
    `__init__` 11). C901 offenders at threshold 15: `run_dft.main` (17) and
    `report_docx.build_docx_report` (16) — split them, or set max-complexity ≥17
    at the flip (decide then; they are linear section-emitters).
  - **Final PR F:** flip global ruff (`line-length=80`, `select+=C90` with the
    chosen `max-complexity`, `extend-select=D417`), drop the staging, update ADR
    0012 to record the enforcement mechanism actually used (test-based public
    annotation; no `ANN`). Keep the `report.py` CSS `E501` ignore.
  - `CONTRACTED` so far: presets, runs/_cli, adsorption/* (5), qm/* (6),
    report/{report_layout,equations,report_docx}. Working tree clean, only
    `main` local.

## 2026-07-04 — #51/#52 sweep COMPLETE: epic #69 closed

- **Tool:** Claude Code (Fable 5). Continues the same-day checkpoint above.
- **Scope:** finish the #51 (full public API contract) + #52 (readability)
  sweep begun earlier, then flip the global gate.
- **Landed (all squash-merged, 8/8 checks each, `main` green after each):**
  **PR #91** report/ part 2 (figures + report — figures' 14 public fns typed,
  duck-typed render inputs → `Any`, heterogeneous returns → `object`; report.py
  E501-exempt for CSS so the contract test skips its width check via
  `WIDTH_EXEMPT`). **PR #92** report_content.py — the ~116-line narrative reflow,
  proven **byte-identical** by a string-value golden (sha256 over every exported
  string + function output; a space-only splitter guaranteed value-preservation).
  **PR #93** the nine runs/ drivers + top-level (`__init__`/`cli`/`molecules`/
  `medium`) — `analyse_matrix` fully typed across 15 params, `compute_pka_rows`
  typed; two latent mypy gaps that typing surfaced fixed narrowly (optimiser
  `Coords`→`Molecule.coords` cast; pyscf `**kw` → `dict[str, Any]`). **PR #94**
  the global gate flip.
- **The gate (PR #94):** `pyproject` ruff `line-length` 100→**80**,
  `extend-select D417`, `select += C90` with `max-complexity 15`; `tests/**`
  exempt from E501/C901; `report.py` keeps its CSS E501 ignore; one linear docx
  builder (`build_docx_report`, cyclomatic 16) carries a documented
  `# noqa: C901`. **No ruff `ANN`** — the public annotation contract is enforced
  by `tests/test_docstrings.py` (now scanning the whole package, allowlist
  retired), which also owns the no-trailing / no-ticket-number comment rules
  ruff has no rule for. **#51 + #52 auto-closed; epic #69 COMPLETE** (all five
  tickets #73/#57/#64/#51/#52).
- **Decisions:** **ADR 0012** finalised to the actual enforcement (test-based
  public annotation, ruff for width/D417/C901, no ANN); CLAUDE.md §2.2 updated.
  Key call recorded: #51 is the *public* contract, so ruff `ANN` (which flags
  every arg) was rejected in favour of the public-only test — keeps private QM
  helpers taking un-stubbed pyscf objects annotation-free.
- **Verification:** every sweep PR behaviour-preserving — mc/md **bit-identical**
  (full-precision golden), report narrative **byte-identical** (string golden),
  so `results/` and the `report/` bundle are untouched; the venv drivers still
  pass `test_pipeline_drivers` end-to-end. ruff + mypy + pytest green throughout
  (108 passed, 1 skip); C901 gate confirmed live.
- **Pending:** working tree clean, only `main` local. Epic **#69 done**;
  backlog resumes at **#70** per-module refactors (now fully unblocked — but #48
  surface / #56 mc / #55 md / #61 engines etc. are largely *already applied* by
  this sweep + #57, so re-scope #70 against the swept tree before starting) →
  **#72** generalization → **#71** deployment → **#40** (E_ads). First release
  tag still deferred to post-#67. Cosmetic loose end: **#66–#68** cite the
  retired epic #65.

## 2026-07-05 — SonarQube gap analysis → cognitive-complexity ratchet (#97/#98)

- **Tool:** Claude Code (Fable 5).
- **Scope:** user question "do we have a Python SonarQube?" → gap analysis of
  the existing gate stack, adopt what is genuinely missing, decide the rest.
- **Landed:** **PR #97** — complexipy (SonarQube's cognitive-complexity
  metric) as a CI gate in **snapshot-ratchet** mode: `[tool.complexipy]`
  (src/corrosim, threshold 15 = the C901 value), committed
  `complexipy-snapshot.json` freezes the nine over-threshold functions; CI
  fails only when an over-threshold function is new or has increased; the
  lint job pins `complexipy==6.0.*` (snapshot format is version-sensitive).
  **ADR 0013**; PLAYBOOK §3.4; CLAUDE.md §1.3/§3/§5.2; README + ONBOARDING
  check lists. **PR #98** — PLAYBOOK §3.8: duplication + dead code stay
  review-time rules plus a periodic whole-tree audit at epic boundaries
  (pylint duplicate-code / vulture commands + the 2026-07-04 clean baseline);
  deliberately NOT CI gates (clean tree; false-positive suppression cost).
  Both squash-merged, 8/8 checks; post-merge CI + CodeQL green; the Linux
  runner confirmed "Snapshot watermark passed" (Windows-made snapshot is
  portable).
- **Measurements (feed the #70 re-scope; posted as a comment on #70):**
  cognitive vs cyclomatic genuinely disagree — `analyse_matrix` cognitive 47
  yet C901-clean; `build_docx_report` cognitive 26, correcting ADR 0012's
  "low cognitive" noqa rationale. Four over-threshold functions have no #70
  ticket: `cli.read_input_csv` 31, `build_docx_report` 26,
  `make_figures.main` 18, `report_docx._scientific_basis` 16. Duplication:
  only two blocks package-wide — the pyscf SCF setup incl. the hardcoded
  water eps 78.3553 duplicated engines↔figures (already covered by #61+#60),
  and run_mc/run_md argparse boilerplate (absorbable into `_cli`). vulture:
  zero dead code at ≥80% confidence; radon MI all grade A; wily skipped (the
  ratchet already guards the trend).
- **Upstream:** filed solid-ai-templates **#722** (cognitive-complexity
  ratchet for quality-gates) and **#723** (diff-invisible rules need a
  periodic whole-tree sweep, not a CI gate). Correction to the 2026-07-02
  entry: the ADR 0010 template candidate marked "not yet filed" WAS filed as
  upstream **#718** on 2026-07-04 (alongside #719 bandit-exclude collision
  and #720 always-run-job).
- **Verification:** ruff + mypy + complexipy + pytest green on merged `main`
  (108 passed, 1 skip); templates submodule in sync with upstream.
- **Pending:** the **#70 re-scope** against the swept tree remains the next
  thread — now with measured priorities (see the #70 comment; decide whether
  the four unticketed offenders get tickets). Then #72 → #71 → #40; first
  release tag post-#67. Cosmetic: #66–#68 still cite retired epic #65.

## 2026-07-05 (session 2) — --case flag, #70 re-scope, run_dft + make_report decompositions

- **Tool:** Claude Code (Opus 4.8).
- **Scope:** resume the #70 per-module refactor sequence from the previous
  session's Pending (the #70 re-scope), then execute the top refactors.
- **Landed (merged to `main`):**
  - **#99** — the prior session's cognitive-complexity journal wrap (merged
    first, as the session's opening action).
  - **#100 / PR #101** — `--case <name>` threaded through all eight run drivers
    via a shared `_cli.resolve_case`; drivers derive `--molecules/--metal/`
    `--medium` from the resolved `presets.CaseStudy` instead of referencing
    `ARGHEL` directly (ARGHEL now lives only in presets.py / molecules.py).
    Behaviour-preserving: run_mc pre/post byte-identical, report.html
    byte-identical, `--case argel` == default; the complexity-frozen driver
    `main()`s gained only non-branching statements (snapshot unchanged).
  - **#63 / PR #105** — decomposed `run_dft.analyse_matrix` (cognitive **47**,
    the worst function in the tree) + `main` (16) into
    `_geometry_tag`/`_species_forms`/`_optimize_species`/`_single_points` +
    `_build_parser`/`_warn_medium_mismatch`/`_opt_geom_dir`/`_write_outputs`;
    run_dft.py now has zero over-threshold functions. Folded in **#50**:
    self-safety `optimize = optimize or check_minimum or to_minimum`
    (+ regression test), deliberate separation from `run_pka._relax_and_thermo`
    (noted in the docstring), and single-sourced the true-minimum recipe via
    `engines.MIN_RECIPE` (chosen "grid 4, imag-mode refined" to keep
    results/pka.json byte-identical). Rule-5: dropped #41/#34 from the module
    docstring (a docstring ticket-ref the comment-only gate can't see).
  - **#62 / PR #106** — decomposed `make_report.main` (cognitive **38**,
    second-worst) into seven stage loaders (`_neutral_rows`/`_acid_cation_rows`/
    `_speciation_summary`/`_computed_pkah`/`_opt_geometry_rows`/`_render_reports`/
    `_bundle_tables`) + `_build_parser`; nested `_rank`/`_bundle` lifted to
    module-level `_rank_blend`/`_bundle_one`. Byte-identical report.html.
- **#70 re-scope (grooming):** audited every per-module ticket against the swept
  tree. Key finding — **#57 already landed** (adsorption/surface.py is the
  shared home of `EV_TO_KJMOL` + `uff_mixing`/`uff_vdw_energy`/`uff_vdw_forces`),
  so the cross-module UFF/units duplication that dominated #55/#56 is resolved.
  Posted the measured verdict table as a #70 comment; rewrote the epic body
  (priority order; #56 near-closeable; #59 downgraded to style-only since
  `build_pipeline_report` is cognitively under 15; #50 subsumed into #63). Filed
  **#102** (cli.read_input_csv cc 31) and **#103** (report_docx.build_docx_report
  cc 26) for the two worth-improving unticketed offenders; left
  `make_figures.main` (18) + `report_docx._scientific_basis` (16) frozen.
- **#72 update:** added a case-study-agnostic acceptance criterion (report
  narrative + `speciation.FLAVONOID_CARBONYL_PKAH` fold into the `CaseStudy`
  schema under #53/#54); #100 checked off.
- **Ratchet progress:** over-threshold functions down **9 → 6**; the two worst
  (analyse_matrix 47, make_report.main 38) eliminated. Remaining:
  read_input_csv 31 (#102), build_docx_report 26 (#103), run_md 24 (#55),
  make_figures.main 18 (frozen), render_orbital 17 (#60),
  _scientific_basis 16 (frozen).
- **Issues:** closed #100 / #63 / #62 / #50; created #100 / #102 / #103.
- **Verification:** every refactor behaviour-preserving and independently
  checked — stubbed-QM goldens (test_run_dft) green with identical
  geometry-tag strings + provenance; report.html byte-identical (modulo the
  generation timestamp) for both #100 and #62; ruff + mypy + complexipy
  (snapshots refreshed: run_dft + make_report entries removed) + pytest
  (**111 passed, 1 skipped**) on merged `main`. `results/` and `report/`
  untouched throughout.
- **Process note:** a stacked PR (#104, #63 on the #100 branch) auto-closed
  when its base branch was deleted on merge; rebuilt cleanly on `main` via
  cherry-pick as #105. Prefer branching refactors directly off `main`, or merge
  the base before the stack.
- **Pending:** #70 sequence continues at **#61** (engines.py dedup: 78.3553×3,
  `_build_rks`, ORCA/Gaussian — Docker-gated, so verify via the stubbed tests)
  → **#60** figures.py (consumes #61's shared SCF home) → **#55** md.py
  (run_md cc 24 + dead `rdf_FeO`/`first_peak_FeO` aliases) → light **#58**/**#48**
  → the two new offender tickets **#102**/**#103**. Then #72 → #71 → #40; first
  release tag post-#67. Cosmetic loose end unchanged: #66–#68 still cite retired
  epic #65.

## 2026-07-05 (session 3) — #70 per-module sweep completed; epics #69/#70 closed

- **Tool:** Claude Code (Opus 4.8).
- **Scope:** finish the #70 per-module refactor sequence from session 2's
  Pending, then close the standards/refactor epics.
- **Landed (9 PRs, all squash-merged to `main`, each behaviour-preserving and
  verified byte-identical against a captured golden):**
  - **#61 / PR #108** — engines.py: extracted `build_rks` (promoted from a
    private helper to the public shared-SCF home, per the #57 precedent) +
    `_level_label`/`_imaginary_mask`/`_xyz_block`/`_run_external_engine`;
    named `WATER_EPS`/`IMAG_FREQ_TOL`/`OCCUPIED_MIN`; fixed both
    `open(out).read()` handle leaks; +4 QM-light tests (writers/parsers).
  - **#60 / PR #111** — figures.py: `_cube_scf` (delegates to `build_rks`,
    killed the 4th `78.3553`), `_read_cube_grid`/`_draw_bonds`/`_style_3d_axes`
    (`BOND_CUTOFF_ANG`)/`_atom_index_structure`; `render_orbital` **17 → gate**;
    +1 synthetic-cube test.
  - **#55 / PR #112** — md.py: decomposed `run_md` (cc **24**) into
    `_langevin_step`/`_confine_z`/`_closest_contact_hist`/`_first_peak` (rng
    order preserved); named `_MAX_DRIFT`/`_RDF_MAX_A`/`_RDF_BIN_WIDTH_A`;
    removed the 4 dead `*_Fe*` back-compat aliases + their assertions.
  - **#58 / PR #113** — fukui.py: extracted `_mulliken_charges` (unwound the
    `_scf(...)[1].mulliken_pop()[1]` chain); `c`→`mo_coeff`/`coords`;
    charge-sign comment; new `tests/test_fukui.py` (first offline dispatch
    coverage, SCF mocked).
  - **#48 / PR #114** — surface.py: `CRYSTAL_BUILDER` single-sources the facet
    (SURFACE_FACET derived); `_metal_element` lets `build_slab` accept the
    canonical `"Fe(110)"`; +3 tests.
  - **#102 / PR #115** — cli.py: decomposed `read_input_csv` (cc **31**, the
    worst in the tree) into `_nonempty_rows`/`_cell`/`_molecules_from_header`/
    `_molecules_headerless`; +5 tests over 7 input shapes.
  - **#103 / PR #116** — report_docx.py: decomposed `build_docx_report`
    (cc **26**) into 11 `_*_section` builders + `_equation_groups`; dropped the
    inaccurate `# noqa: C901`; **also dropped `_scientific_basis` (16)** under
    the gate. Golden = full+minimal docx structure byte-identical.
  - **#56 / PR #117** — mc.py (polish): named `_STEP_DECAY`/`_ROT_STEP_RAD`/
    `_TRANS_STEP_A`; `c2`→`trial_com`.
  - **#59 / PR #118** — report.py (style-only): `rank_inhibitors` cryptic
    locals + `score/3` → `sum/len(components)`; split `plot_homo_lumo`
    semicolons; `_number_headings` `c`→`counts`, `m`→`match`.
- **Complexity ratchet:** over-threshold functions **6 → 1**. The only entry
  left in `complexipy-snapshot.json` is `make_figures.main` (18), deliberately
  frozen. Eliminated this session: `read_input_csv` (31), `build_docx_report`
  (26), `run_md` (24), `render_orbital` (17), `_scientific_basis` (16).
- **Epics:** closed **#69** (Standards & Foundations — its 5 tickets were done
  earlier) and **#70** (Per-module refactors — all 11 tickets now landed);
  updated #70's body with the ticket→PR map. Verified auto-close of every
  per-module issue.
- **Verification discipline:** each behavioural refactor gated on a
  pre-refactor golden (seeded MC/MD run hashes, docx paragraph/table/equation
  structure, full pipeline HTML, CSV shapes, engine geometry) — all matched
  post-refactor. Test count **111 → 129** (+18, all QM-light). ruff + mypy +
  complexipy + pytest green on every merge; `results/` and the `report/` bundle
  untouched throughout.
- **Process:** every branch cut from `main`, PR opened, CI watched to green,
  squash-merged, `main` fast-forwarded — no stacked-PR issues this session.
- **Readability-rule addendum (PR #120):** a client-driven mc.py readability
  pass surfaced two new conventions, added to CLAUDE.md §2.2 and applied to
  `adsorption/mc.py` as the exemplar — **(1) no "Stage 1/2/3" in any docstring
  or comment** (name the actual work; stage labels rot, already dropped from
  the reports per ADR 0010), **(2) a module docstring SHOULD carry a small
  ASCII diagram** when the flow isn't obvious. mc.py gained a stage-free
  docstring + an ASCII diagram of the annealed Metropolis step; fixed a latent
  bug folded in from the client edit (`combined` used `Atoms(...)` with only
  the TYPE_CHECKING import → NameError; runtime import restored); run_mc
  byte-identical. **Filed #119** for the codebase-wide Stage-N purge (~44
  mentions across ~16 files, docstrings/comments only — report narrative in
  `report_content.py` excluded, as rephrasing it changes report output).
- **Pending:** the entire standards + per-module refactor program is done and
  the ratchet is effectively cleared. Next up: **#119** (deferred this session)
  — purge the remaining ~44 "Stage 1/2/3" docstring/comment mentions
  codebase-wide (behaviour-preserving; verify report goldens). Then feature
  scope: **#72** Generalization & Validation (P-next candidate — #53 per-paper
  validation presets ties into the approved Arghel/Mohammed 2014 source; #54
  data-driven library), **#71** Deployment (#66 Colab / #67 GHCR+PyPI / #68
  Pages), **#40** chemisorption E_ads, **#109/#110** report/pipeline docs
  restructure. First release tag is gated on #67. Cosmetic loose end unchanged:
  #66–#68 still cite retired epic #65.

## 2026-07-05 (session 4) — mc/md OOP: orchestrator + state objects (ADR 0014)

- **Tool:** Claude Code (Opus 4.8).
- **Scope:** a client-driven readability/OOP deep-dive on `adsorption/mc.py`,
  extended to keep `adsorption/md.py` structurally parallel. Behaviour-
  preserving throughout, gated on seeded golden hashes.
- **Landed (2 PRs, squash-merged to `main`, CI green):**
  - **#122** — reshaped both pipeline-stage modules to one OOP shape and
    recorded it as **ADR 0014**:
    - `run_mc` decomposed into a high-level assembly — move helpers
      `_propose_pose` / `_confine_pose`, pure `_anneal_schedule`, factory
      classmethods `_Substrate.build` / `_Search.seed`, behaviour on the state
      (`_Search.accept`, was the free `_metropolis_update`, curing an anemic
      model), and `MCResult.from_search`. Cognitive complexity **7 → 1**.
    - `md.py` mirrored: `_Substrate.build` (caches metal positions + symbols),
      `_RdfAccumulator` (`for_donors` / `record` / `bin_centres` / `normalized`,
      replacing the external `hist_o += …; nframes += 1` mutation),
      `MDResult.from_run`, and `_mean_energy` extracted as a pure helper.
      `run_md` cognitive complexity **24 → 5**.
    - promoted the `ase.Atoms` import out of the `TYPE_CHECKING` guard in both
      modules (it is constructed at runtime in `combined`; the guarded form
      deferred nothing since `surface.py` already imports ase eagerly).
    - verification: seeded `run_mc` **and** `run_md` byte-identical before/after
      (2 seeds × 2 slab sizes each). New `tests/test_mc.py` + extended
      `tests/test_md.py`; suite **129 → 155**.
  - **#123** — added the **sentence-case comment** rule to CLAUDE.md §2.2
    (capitalize the first word; acronyms/proper nouns keep their case; a terse
    fragment needs no terminal period; docstrings already comply) and applied it
    to `mc.py` / `md.py`. Filed **#124** for the codebase-wide sweep.
- **Decisions:** **ADR 0014** — pipeline-stage module shape (free `run_*`
  orchestrator + factory classmethods + behaviour on the state object;
  stateless numerics stay free functions). It **defers the swappable
  energy-model Strategy to #40** rather than building it speculatively.
- **Considered and declined (with reasons):** further OOP in `mc.py` — assessed
  as at equilibrium. The only remaining seam is a `_Scorer` / energy-model,
  deliberately parked for #40. Rejected a `_MonteCarloSearch.run()` method
  object ("function in disguise") and turning the stateless numerics into
  methods (would couple them to state they don't use).
- **Ratchet:** `run_mc` 7 → 1, `run_md` 24 → 5; `complexipy-snapshot.json`
  untouched (`make_figures.main` 18 remains the only frozen entry).
- **Aside (not a repo change):** fixed the VS Code parameter *underline* — it
  came from the Real IntelliJ Light theme's TextMate `variable.parameter` rule,
  not semantic tokens — via `editor.tokenColorCustomizations` in the user's
  settings.
- **Pending:** two comment-hygiene sweeps now pair up — **#124** (sentence-case
  codebase-wide, new) and **#119** (Stage-N purge; `md.py`'s *module* docstring
  still says "Stage-3"); do them together. **#40** chemisorption E_ads is now
  also the home for the energy-model Strategy seam (per ADR 0014). Unchanged
  feature scope: **#72** Generalization & Validation (#53 per-paper presets /
  #54 data-driven library), **#71** Deployment (#66 Colab / #67 GHCR+PyPI / #68
  Pages), **#109/#110** report/pipeline docs restructure; first release tag
  gated on #67. Upstream candidate not yet filed: the sentence-case comment rule
  could extend the solid-ai-templates readability guidance.

## 2026-07-06 (session 5) — codebase OOP/SOLID audit + 6/8 execution (epic #126)

- **Tool:** Claude Code (Opus 4.8).
- **Scope:** a whole-codebase design audit through the OOP / design-pattern /
  SOLID lens (following the ADR 0014 exemplar and the restraint principle),
  then execution of the resulting per-module tickets. Continues directly from
  session 4's mc/md OOP work.
- **Audit + filing:** reviewed all ~30 modules with **5 parallel design-review
  agents** (one per subsystem), each applying ADR 0014 + explicit restraint.
  Most modules came back **already well-structured**; the agents *rejected*
  more than they proposed (no Strategy hierarchy for the engine/Fukui string
  dispatch, no Command/base-`Driver` class for the CLI mains, no behaviour on
  frozen value objects). Filed **epic #126** + **8 curated tickets #127–#134**;
  two upstream issues on `braboj/solid-ai-templates` (**#739** oop.md
  "when-not-to-reach-for-a-class" restraint, **#740** testing.md
  characterization-fingerprint technique); comments on **#119** (Stage-N scope
  is broader — spans qm/, adsorption/, core) and **#40** (the
  `UffVdwField`/`EnergyModel` Strategy seam confirmed, correctly deferred).
- **Executed 6 / 8 (PRs #135–#140, all squash-merged, CI-green):**
  - **#128 / PR #135** — `FukuiResult.from_populations` (replaces private
    `_result`) + `.from_rows` (round-trip inverse of `as_rows`, de-anemizing
    make_figures' by-index loader).
  - **#132 / PR #136** — decomposed `make_figures.main` (cc 18 → 0) into six
    `_fig_*` helpers; consumes `FukuiResult.from_rows`. **The complexity
    ratchet backlog is now fully cleared — `complexipy-snapshot.json` is `[]`.**
  - **#134 / PR #137** — centralized the `metal_element` facet-strip (4 inline
    copies → one `presets.metal_element`); `medium.relevant_forms` →
    `MediumSpec.relevant_forms`; `analyse_*` return hints → `dict[str, Any]`.
  - **#130 / PR #138** — promoted a shared `Substrate` (with `.build`) into
    surface.py (was defined twice in mc/md + inlined in the estimate); routes
    the metal filter through `metal_element`, **fixing the latent `Fe(110)`
    empty-`metal_positions` → silent all-zero RDF hazard**.
  - **#131 / PR #139** — **bug fix**: `place_molecule` only centred coords and
    never oriented flat, so the exported LAMMPS `.xyz`/`.cif` kept the
    arbitrary embedded orientation; now delegates to `initial_adsorption_pose`.
    Added a flatness lock-in test.
  - **#129 / PR #140** — `Molecule.from_smiles` / `.protonated` factories
    (`_embed_and_relax` → private classmethod); `Molecule.write_xyz` method;
    `formula` guards a missing `rdkit_mol`. `build_*`/free `write_xyz` stay thin
    wrappers.
- **Restraint held:** declined `Descriptors.from_frontier`, `Speciation.at_ph`,
  `MediumSpec.parse` — stateless value constructors that ADR 0014 §4 keeps as
  free functions — each with a recorded reason in the PR/commit.
- **Verification:** every behaviour-preserving refactor gated on a **seeded
  golden hash** (mc/md byte-identical across 2 seeds × 2 slab sizes); test
  count 155 → 161; ruff + mypy + complexipy + pytest green on every merge.
- **Pending:** two tickets remain under epic #126. **#133** (runs shared free
  helpers: `_form_rows_in_order` ×5 sites, `iter_molecules`, and promoting
  `run_dft._best_protonation_site` out of a private cross-module reach — the
  one wrinkle is its stderr logging, plan is an injected `log` callback so the
  library stays print-free). **#127** (the large P1: a shared HTML/docx
  `render_blocks` walker + renderer Protocol with an exhaustive `else`,
  `PreparedReport.bottom_line()`, and mirroring the docx section decomposition
  on the HTML side — needs an HTML+docx golden). Unchanged longer threads:
  **#119/#124** paired comment sweeps, **#40** energy-model Strategy,
  **#72** Generalization/Validation (#53/#54), **#71** Deployment (#66–#68;
  first release tag gated on #67), **#109/#110** docs restructure.

## 2026-07-06 (session 6) — QM import boundary, runs helpers, report golden (epic #126 → 7/8)

- **Tool:** Claude Code (Opus 4.8).
- **Scope:** finish the epic-#126 `runs` refactor (#133) and, en route, tidy the
  QM/report layering (two new tech-debt tickets #142/#143 filed and executed),
  then stand up the report golden that the last epic item (#127) needs. Continues
  session 5's Pending line.
- **#142 / PR #144 — QM backend-import boundary (Option B).** The deferred
  pyscf/tblite imports were correct but scattered across ~8 functions; concentrate
  them behind `qm/_backend_pyscf.py` + `qm/_backend_tblite.py` (deps at the module
  top, imported lazily), each call site now one `from . import _backend_pyscf`. A
  `try/except` at each backend top yields a friendly "runs only in the corrosim-qm
  image" hint; `import corrosim` still pulls in no QM extra. Hoisted the trivial
  always-available imports (os/subprocess/tempfile/ase.data/io/matplotlib/ase.io).
  The pre-existing dataclass field-grouping edits rode along as a `style` commit.
- **#143 / PR #145 — cube writers → `qm/cubes.py`.** Relocated the HOMO/LUMO,
  MEP and density+ESP cube writers (+ `_cube_scf`) out of `report/figures.py`
  (they run a DFT SCF + `cubegen`, i.e. QM production), so `report/figures` is now
  pure rendering. **Declined** the originally-planned engine-body move (Option C)
  on restraint — it would force forwarding wrappers duplicating signature +
  docstring for a marginal gain (recorded on the issue + **ADR 0015**).
- **#133 / PR #146 — shared `runs` free helpers.** `form_rows_in_order` and
  `iter_molecules` in `_cli.py` (no Command/Driver hierarchy, ADR 0014); collapsed
  the 4× make_report + compare_geometry row-selection and the mc/md/fukui molecule
  loops. Promoted `run_dft._best_protonation_site` → public
  `qm/protonation.py::best_protonation_site` (stderr logging behind an injected
  `log` callback), removing the `run_pka → run_dft` reach. Row-selection outputs
  captured before/after and verified **byte-identical**, so the report is unchanged.
- **#127 prep / PR #147 — report render golden.** New `tests/test_report_golden.py`
  with `tests/goldens/`: full pipeline report with every optional section on, pinned
  HTML **byte-for-byte** (base64 equation-PNG payloads masked — freetype-dependent)
  and docx as **document-order text**. Mutation-tested (a heading tweak fails the
  golden). Un-ignored `tests/goldens/*.html`. This is the safety net for #127.
- **ADR 0015** — QM engine-import boundary (the qm package owns pyscf/tblite;
  report/runs consume it; engine bodies deliberately stay in `engines.py`).
- **Verification:** ruff + mypy (39 files) + complexipy + pytest green on every
  merge; PRs #144–#147 all squash-merged, CI-green; #142/#143/#133 auto-closed.
- **Pending:** epic **#126** is now **7/8** — only **#127** (the P1 HTML/docx
  render seam: a shared `render_blocks` walker + renderer Protocol,
  `PreparedReport.bottom_line`, mirroring the docx section decomposition on the
  HTML side) remains, and its **golden safety net (PR #147) is now in place**.
  Start it with a design pass (map both renderers → the shared block model → walk
  it), keeping the golden byte/text-identical. Deferred: the #133 **P3** note
  (`add_metal_arg`/`add_medium_arg` to single-source the drifting `--metal` /
  `--medium` help text). Unchanged longer threads: **#119/#124** comment sweeps,
  **#72** Generalization/Validation (#54→#53), **#71** Deployment (#66–#68),
  **#40** chemisorption E_ads.

## 2026-07-06 (session 7) — report render seam: shared walker + PreparedReport factory (epic #126 → 8/8)

- **Tool:** Claude Code (Opus 4.8).
- **Scope:** execute the last epic-#126 item, **#127** — the HTML/docx render
  seam. Continues session 6's Pending line. Behaviour-preserving throughout: the
  report golden (PR #147) is the gate.
- **#127 — one walker for the data-driven section.** New `report/render.py`:
  a four-method `BasisRenderer` Protocol (`subheading`/`paragraph`/`table`/
  `equation_groups`) + `render_blocks(blocks, renderer)` with an `else: raise`.
  Replaces the two byte-duplicated `if kind == …` chains in
  `report._scientific_basis_section` and `report_docx._scientific_basis` that
  **both lacked an `else`** and silently dropped an unknown block kind. HTML
  (`_HtmlBasis`) and Word (`_DocxBasis`) are the two impls; the scope stays the
  one data-driven section (the hand-authored sections remain two renderers).
- **`PreparedReport.bottom_line()`.** The byte-duplicated lead extraction (top
  ranked row → headline) moves onto the DTO; each renderer wraps the returned
  prose in its own note box.
- **HTML section decomposition.** `build_pipeline_report`'s ~100-line list
  literal becomes `_header/_overview/_summary/_dft/_fukui/_esp/_mc/_md/_method`
  section helpers mirroring `report_docx`'s `_*_section` builders, so the two
  outlines diff side by side. The document shell + `_number_headings` stay in the
  entry point.
- **`PreparedReport.derive(...)`.** Construction moves to a factory classmethod
  (ADR 0014); `prepare_report_data` stays the stable public wrapper delegating to
  it.
- **ADR 0016** — report render seam: the shared walker covers only the
  data-driven Scientific-basis section; the hand-authored, format-specific
  sections stay two renderers (ADR 0010). Whole-report block model rejected;
  `_number_headings` → `_Html`-builder retirement deferred.
- **Tests** — new `tests/test_render_blocks.py` (per-kind dispatch, the
  `else: raise` exhaustiveness, `bottom_line` None-branch); +6 tests.
- **Verification:** report golden byte-identical (HTML) + section-for-section
  (docx); pytest **169 passed / 1 skipped**; ruff + mypy (40 files) + complexipy
  (all < 15, `derive` = 11, snapshot `[]`) green.
- **Pending:** epic **#126** is **complete (8/8)**. Deferred inside #127: retire
  `_number_headings` for an `_Html` builder mirroring `_Doc` (issue #127 P2,
  optional). Longer threads unchanged: **#133 P3** (`add_metal_arg` /
  `add_medium_arg` help-text single-source), **#119/#124** comment sweeps,
  **#72** Generalization/Validation (#54→#53), **#71** Deployment (#66–#68),
  **#40** chemisorption E_ads.

## 2026-07-07 (session 8) — comment/docstring hygiene sweep (#119 + #124)

- **Tool:** Claude Code (Opus 4.8).
- **Scope:** the paired mechanical comment-hygiene passes over `src/corrosim/`,
  behaviour-preserving throughout (the report golden is the gate). Both close.
- **#124 — sentence-case comments.** Capitalised 56 opening inline/block
  comments across 22 files (scripted by re-deriving the opening lines, then
  reviewed). Left lowercase exactly where the rule requires: unit / identifier /
  proper-noun first tokens (`eV`, `pH`, `dE/dr`, `eta_metal`, `ddCOSMO`,
  `tblite`, `mulliken_pop`, `set_box_aspect`, `bbox_inches`, `fig8`/`fig3b`) and
  every wrapped-comment continuation.
- **#119 — purge "Stage 1/2/3" / "Stage-N".** Rephrased every in-scope
  docstring/comment to name the actual work (DFT descriptors, MC adsorption, MD
  RDF): module docstrings (`adsorption/*`, `qm/*`, `runs/*`, both `__init__`s),
  the docx `_dft/_mc/_md_section` docstrings + a comment, `equations.py` section
  headers, `cli.py --adsorption` help, and the `qm/engines.py` min-check
  docstring (reflowed stage-free). Renamed the lone `_STAGE1` → `_DESCRIPTORS`
  (private, 2 refs). **Left the rendered narrative out of scope** — the
  `report_content.py` mentions and the rendered `method` string in
  `report.py::build_html_report` (line 179) would change the shipped bundle.
- **Verification:** report golden byte-identical (HTML) + section-for-section
  (docx) — none of this renders; pytest **169 passed / 1 skipped**; ruff + mypy
  (40 files) + complexipy (snapshot `[]`) + docstring-contract test green. Diff
  is 90/90 balanced across 26 files; the only non-comment/docstring lines are the
  `_STAGE1` rename and the CLI help string.
- **Pending:** epic **#126** complete; **#119/#124 now closed**. Deferred inside
  #127: retire `_number_headings` for an `_Html` builder (P2, optional). Open
  threads: **#133 P3** (`add_metal_arg` / `add_medium_arg` help-text
  single-source), **#72** Generalization/Validation (#54→#53), **#71**
  Deployment (#66–#68), **#40** chemisorption E_ads.

## 2026-07-07 (session 9) — purge ADR/ticket numbers from docstrings (#151)

- **Tool:** Claude Code (Opus 4.8). Ticket **#151** filed + executed this session.
- **Scope:** extend §2.2's "no ticket/PR/ADR *number*" rule from comments to
  **docstrings**, sweep the existing refs, and enforce it so it can't regress.
  Behaviour-preserving (docstrings don't render; the golden is the gate).
- **Sweep.** Removed **25** rotting number-pointers — `ADR 00NN` plus a few stray
  `issue #NN` / `#NN` — from module/class/function docstrings across 11 files
  (`adsorption`/`qm`/`report` `__init__`s, `medium`, `report/render`,
  `report/report.py` block docstrings + `PreparedReport.derive` +
  `build_pipeline_report`, `qm/pka`, `qm/speciation`, `runs/_cli`,
  `runs/run_dft`, `runs/run_pka`), keeping each docstring self-sufficient (the
  substance stays in the prose). **Comments were already clean** — the comment
  rule + `test_comments_are_clean` had banned them.
- **Convention.** CLAUDE.md §2.2 amended: the rule now covers comments **and**
  docstrings; noted the Markdown docs (README/ONBOARDING/ADRs/journal) still
  cross-reference ADRs by number on purpose.
- **Enforcement.** New `tests/test_docstrings.py::test_docstrings_have_no_ticket_refs`
  applies the existing `TICKET_RE` to every module/class/function docstring;
  mutation-tested (an injected `ADR 0099` fails it, clean after revert).
- **Out of scope (as ticketed).** The rendered report narrative
  (`report_content.py` + the rendered strings in `report.py` / `report_docx.py`)
  — removing those changes the shipped bundle; the CLI `--basis` help text; and
  the Markdown docs.
- **Verification:** report golden byte/section-identical; pytest **170 passed /
  1 skipped** (+1 new); ruff + mypy (40 files) + complexipy (`[]`) green. Diff is
  docstring/doc/test-only — no logic.
- **Pending:** unchanged threads — **#133 P3** (`add_metal_arg`/`add_medium_arg`
  help-text single-source), **#127 P2** (`_Html` builder, optional), **#72**
  Generalization/Validation (#54→#53), **#71** Deployment (#66–#68), **#40**
  chemisorption E_ads. Possible follow-up: purge ADR numbers from the *rendered*
  report narrative (would change the golden).

## 2026-07-07 (session 10) — lean stage-keyed report (#110)

- **Tool:** Claude Code (Opus 4.8). Interactive editorial pass — reviewed the
  rendered report and iterated on wording/placement with the user.
- **Scope:** make the generated report a lean, stage-keyed artifact — tables +
  figures under each stage with minimal captions, no methodology essay. The
  narrative already lived in `docs/pipeline.md` (verified), so this is a
  de-duplication, not a relocation; #109 (per-stage prose) stays a separate
  enhancement.
- **Stripped `report_content.py`** to the shared essentials: `HEADLINE_CAVEAT`,
  `METHOD_CAVEAT` (now pointing to pipeline.md / validation.md), `bottom_line`,
  `inline_runs`, and a one-line `score_note`. Removed `STAGE_INTROS`,
  `FIGURE_EXPLANATIONS`, `SCIENTIFIC_BASIS`, and `score_explanation`.
- **Both renderers** (`report.py` + `report_docx.py`) rebuilt lean: dropped the
  per-stage intros, the `_explain()` figure essays, and the interpretive prose
  inside the opt-geometry / acid-cation / speciation / computed-pKaH blocks
  (tables kept, one-line captions). The **"Scientific basis & validation"
  section was removed entirely** (user's call — leanest).
- **Dead code removed:** the section was the only consumer of the #127 render
  seam, so `report/render.py` (`render_blocks` + `BasisRenderer`) +
  `tests/test_render_blocks.py` and the equation-rendering paths in both
  renderers were deleted. `equations.py` stays (standalone, tested). **ADR 0016
  marked Superseded.**
- **Editorial (per user review):** the data-derived headline sentence moved out
  of the top note box into the *Summary & ranking* section as plain content, and
  its wording was formalised (dropped "Bottom line" / "electron-generous"). The
  report's **static text was de-Arghel'd** — generic `HEADLINE_CAVEAT`, and the
  "flavonoids" / "Fe(110)" / "1 M HCl" figure captions genericised. The fuller
  CaseStudy-driven report stays epic **#72**.
- **Verification:** report goldens refreshed (docx content ~155 → 53 lines) and
  re-pinned; `report/` bundle regenerated (html + docx; reverted an unrelated
  stale-CSV `n_imag` drift the regen surfaced). pytest **162 passed / 1 skipped**
  (−8: the deleted render-seam + docx-equation tests); ruff + mypy (39 files) +
  complexipy (`[]`) green. `src/corrosim/molecules.py` carries an unrelated
  user WIP edit — deliberately excluded from this change.
- **Pending:** **#153** (purge ADR refs from rendered narrative — now smaller,
  most narrative is gone), **#109** (pipeline.md per-stage prose), **#72**
  Generalization/Validation, **#71** Deployment, **#40** chemisorption E_ads.

## 2026-07-07 (session 11) — #110 loose ends + session wrap

- **Tool:** Claude Code (Opus 4.8). End-of-session audit follow-ups from #110.
- **Committed the user's `Molecule` field doc-comments** (fixed 2 lint nits; PR
  #155, merged).
- **Dead-dep + doc cleanup after the lean report:** `latex2mathml` +
  `mathml2omml` were only used by the removed OMML equation rendering, so
  dropped them from the `report` / `dev` extras in `pyproject.toml` (the `report`
  extra is now just `python-docx`). Updated `README.md` to describe the lean,
  stage-keyed report (was "figures, standalone explanations, governing equations
  and the validation record").
- **Audit:** pytest 162 passed / 1 skipped; ruff + mypy (39 files) + complexipy
  (`[]`) green; tree clean on `main`. Epic #126 closed; issues
  #110/#151/#124/#119 closed; #153 re-scoped smaller by #110.
- **Pending:** feature backlog only — **#153**, **#109** (pipeline.md per-stage
  prose), **#72** Generalization/Validation (#54→#53), **#71** Deployment
  (#66–#68), **#40** chemisorption E_ads. Note: `equations.py` is retained but
  production-unused (only its own test) — a candidate for removal if equations
  stay out of the report.

## 2026-07-07 (session 12) — #109 pipeline prose + #153 ADR-token purge

- **Tool:** Claude Code (Opus 4.8). Cleared the two remaining doc-hygiene
  tickets from the lean-report follow-up thread; shipped as **PR #157**
  (squash-merged), closing **#109** and **#153**.
- **#109 — per-stage methodology prose in `docs/pipeline.md`.** Each stage
  (3D geometry → MD) now opens with a question-style intro paragraph *before*
  its Why/What/How table, covering (1) the actual method named and **cited by
  source** (ETKDG / Riniker & Landrum 2015, B3LYP / Becke 1993 + Lee-Yang-Parr
  1988, geomeTRIC / Wang & Song 2016, Koopmans, hardness-softness / Parr &
  Pearson 1983, electrophilicity / Parr Szentpály Liu 1999, Lukovits ΔN, Fukui /
  Parr & Yang 1984 + Yang & Mortier 1986, dual descriptor / Morell 2005,
  Metropolis + simulated annealing / Kirkpatrick 1983, UFF / Rappé 1992,
  Brownian dynamics / Ermak & McCammon 1978) — never an issue/ADR number; (2)
  the free software implementing it; (3) an **inline free-vs-commercial
  head-to-head per stage** (vs Gaussian/DMol³, Adsorption Locator, Forcite,
  Multiwfn), decomposed from the single bottom table, which stays as a roll-up.
  Ranking kept its existing z-score intro. Prose only — no code change.
- **#153 — last ADR token out of user-facing strings.** The lean-report
  refactor (#110) had already removed 9 of the 10 tokens the ticket surveyed
  (the report narrative is gone); the only survivor was the `--basis` `--help`
  text (`ADR 0002`), rewritten to state the substance ("the production DFT
  level"). No report-bundle/golden change — the token was not in a rendered
  string. `grep -rniE "ADR[ -]?[0-9]" src/corrosim --include=*.py` now returns
  **0**.
- **Audit:** pytest 162 passed / 1 skipped; ruff + mypy (39 files) + complexipy
  (`[]`) green; tree clean on `main`, nothing unpushed.
- **Pending:** feature backlog only — **#72** Generalization/Validation
  (#54→#53), **#71** Deployment (#66–#68), **#40** chemisorption E_ads. Two
  standing housekeeping notes: `equations.py` is retained but production-unused
  (removal candidate), and the `docs/solid-ai-templates` submodule is ~80
  commits behind (local v2.17.0-80 → upstream v2.30) — a dedicated template-sync
  session should reconcile it (and file the #151 "no ticket refs in
  docstrings" convention upstream) rather than bump it blind at a wrap.

## 2026-07-08 (session 13) — #54 data-driven inhibitor library (both parts)

- **Tool:** Claude Code (Opus 4.8). Cleared **#54** end to end — the data-driven
  library refactor and its on-demand fetch tool — across two merged PRs, closing
  the issue and advancing epic **#72** (`#100 ✅ → #54 ✅ → #53` remaining).
- **Part 1 (PR #159, squash-merged) — externalise the library.** Moved the
  hardcoded five-entry `LIBRARY` dict out of `molecules.py` into shipped package
  data `src/corrosim/data/inhibitors.json` (new dir; `[tool.setuptools.package-data]`),
  loaded at import via `importlib.resources`. Richer per-entry schema
  (`smiles / aliases / source / cas / notes`); the public `LIBRARY`
  (`dict[str, str]` view) and `ALIASES` derive from the records, full records
  exposed as `INHIBITORS`. Behaviour-preserving — same five SMILES, names, and
  order; `resolve_smiles` / `build_molecule` unchanged. New
  `tests/test_inhibitors_json.py` schema-validates the JSON and round-trips
  every entry offline; verified the JSON ships in a built wheel.
- **Part 2 (PR #160, squash-merged) — `corrosim-add-inhibitor`.** New
  `src/corrosim/fetch.py` + console script: `<name|CAS>` → PubChem PUG REST
  (`Title,SMILES`), CAS from the synonyms endpoint, RDKit-validate, append with
  `source: pubchem`; refuses overwrite without `--force`. **Stdlib `urllib`
  only** — no new dependency, no `[fetch]` extra; the committed JSON stays the
  offline single source of truth and runs/CI never hit the network. 11 offline
  tests (single HTTP seam monkeypatched). Locked the PubChem contract by probing
  live first (the `SMILES` property is the current isomeric one; old names still
  resolve). Live smoke test: `thiourea` and CAS `68-12-2` (DMF) both round-trip.
- **Decision:** recorded as **ADR 0017** (data-driven library + offline fetch
  tool; the new `data/` dir is its trigger). The optional gated
  `resolve_smiles` live fallback (`CORROSIM_FETCH`) was **deliberately deferred**
  to keep the import hot path offline-pure.
- **Docs:** README structure block (`fetch` + `data/`), PLAYBOOK grow-the-library
  command block, CLAUDE.md §2.3 one-line library rule.
- **Audit:** pytest **188 passed / 1 skipped**; ruff + mypy (40 files) +
  complexipy (`[]`, snapshot unchanged) green; tree clean on `main`, nothing
  unpushed.
- **Pending:** feature backlog — **#53** per-paper validation presets (now
  unblocked: add a `source` field to `CaseStudy`, reproduce a Tier-1 paper's
  system, compare vs reported values in `docs/validation.md`), **#71**
  Deployment (#66–#68), **#40** chemisorption E_ads. Standing housekeeping:
  `equations.py` production-unused (removal candidate); `docs/solid-ai-templates`
  submodule ~80 commits behind (dedicated sync session, and file the
  no-ticket-refs-in-docstrings convention upstream — still not landed). Optional
  deferred: the gated `CORROSIM_FETCH` resolver fallback.

## 2026-07-08 (session 14) — #53 validation presets + `cases/<case>` layout + CLI transparency

- **Tool:** Claude Code (Opus 4.8). Eight squash-merged PRs advancing epic
  **#72**/**#53**: a per-case output layout, the first validation preset, and
  making the two-tools split discoverable. **#53 stays open** (compute deferred;
  more presets to come).
- **#162 — per-case output namespacing.** Driver outputs move from a flat
  `results/`/`report/` root to per-case subtrees; `CaseStudy` gains
  `results_dir`/`report_dir`, drivers default `--out*` to `None` and backfill
  from `--case` via new `_cli.default_output`. Relocated arghel (51 renames);
  `.gitignore` → `!report/*/report.html`; regenerated the arghel report (dropped
  a stale `results/pka.json` caption; re-synced a bundled table). **ADR 0018.**
- **#164 — `source` field + phytic-acid preset.** Optional `CaseStudy.source`
  (citation/DOI); `phytic-acid` preset (Fe(110)/0.5 M H₂SO₄, Chidiebere 2014);
  phytic acid added to `inhibitors.json` (RDKit-verified C₆H₁₈O₂₄P₆, CAS
  83-86-3); a "Multi-study validation suite" section in `docs/validation.md`
  with the paper's reported values (AM1 HOMO/LUMO/gap 4.776 eV, COMPASS E_bind
  −199 kcal/mol, exp IE 88.7 % / ΔG_ads −29.6 kJ/mol) and level-of-theory
  caveats; computed column marked pending a QM run. Chose phytic-acid over the
  issue's pyrazolo-pyrimidine because the latter's three compounds are novel (no
  CAS/PubChem) — hand-drawn SMILES with no cross-check while compute is deferred;
  its reported values are saved to a gitignored note for a later preset landed
  *with* the first DFT run.
- **#165 — co-locate under `cases/<case>/`.** Folded the two parallel roots into
  one subtree per study: `cases/<case>/{results,report}`. `CaseStudy.case_dir`
  added; pure `git mv` (report is path-agnostic → no regen). ADR 0018 amended.
- **#166 — ADR 0018 cubes trigger.** Recorded when to make the shared `cubes/`
  case-scoped (a second study rendering full cube figures collides on the
  level-unqualified filename).
- **#167 — README structure table; drop arghel limitation.** Structure section →
  `Path | Contents` table; removed the *S. argel* flavonoid-constituents bullet
  (the tool is molecule-agnostic).
- **#168 — drop "Stage-2/3" labels.** Three stragglers (2 README + a rendered
  facade-report string) violating the no-stage-labels convention; the
  `--adsorption` label was also inaccurate (it runs the crude height-scan, not
  the MC pose search).
- **#169 — `corrosim --plan` + README "How it fits together".** A dry-run flag
  that prints a screen's ordered steps (adapting to engine/flags) and what it
  does *not* run, short-circuiting before the engine import (works with no QM
  installed). New README section on the two tools.
- **#170 — tighten that section** to a comparison table (prose was too AI).
- **Audit:** pytest **199 passed / 1 skipped**; ruff + mypy (40 files) +
  complexipy (`[]`, snapshot unchanged) green; tree clean on `main`, nothing
  unpushed. Two `sed -i` gotchas noted for next time: over-matching source paths,
  and CRLF churn on Windows `autocrlf` — scope such rewrites to matching files.
- **Pending:** **#53** still open — the **phytic-acid QM run** (fill
  `cases/phytic-acid/results/` + the computed-vs-reported column) and the
  **pyrazolo-pyrimidine preset** (values in
  `docs/local/pyrazolo-pyrimidine-reported.local.md`, land with the first DFT run
  so QM validates the structures). Also **#71** Deployment (#66–#68), **#40**
  chemisorption E_ads. Post-wrap housekeeping (done): **`equations.py` removed**
  (production-unused after the lean report, PR #175); **submodule synced to
  v2.30.0** (PR #174 — the "~80 behind" note was stale, it was v2.28.0-16/12
  behind; all referenced template files intact); `.gitattributes` added to end
  the Windows CRLF churn (PR #173); repo **auto-merge enabled**. The
  no-ticket-refs-in-docstrings convention was **filed upstream**
  (solid-ai-templates#745) during the wrap audit. Optional deferred:
  `CORROSIM_FETCH` resolver fallback.

## 2026-07-08 (session 15) — pKaH folded into the `CaseStudy` schema (#177)

- **Tool:** Claude Code (Opus 4.8). One squash-merged PR closing the last
  *structural* leftover on epic **#72**'s case-study-agnostic criterion.
- **Status review first.** Corrected a stale claim in the **#72** issue body: it
  demanded the report narrative "become a function of the active `CaseStudy`",
  but the lean-report refactor (#110) already did that — `report_content.py`
  carries only generic caveats + a data-derived `bottom_line` + a
  metal-parameterised `score_note`, with no B-ring/Mohammed-2014 prose. Edited
  #72 to mark that bullet **done** and relabel the pKaH field as the sole
  remaining structural leftover.
- **#177 — `CaseStudy.pkah`.** Folded `speciation.FLAVONOID_CARBONYL_PKAH` (the
  flavonoid-named module default for `protonation_fraction` / `speciate` /
  `analyse_speciation`) into a per-case `CaseStudy.pkah` field (default −1.5, a
  generic very-weak-base fallback). Renamed the module constant to the neutral
  `DEFAULT_PKAH`, now documented as a standalone/library fallback while
  production threads `case.pkah` through `make_report._speciation_summary` →
  `analyse_speciation`. `ARGHEL` sets `pkah=−1.5` explicitly (flavonoid 4-oxo
  carbonyl). Two tests: the per-case field + default, and a regression guard
  that a non-default `pkah=2.0` reaches the `Speciation` unchanged. Updated
  **ADR 0004** to name the current mechanism (no new ADR — this realises the
  "overridable per study" the ADR already anticipated). No new ADR/README/
  PLAYBOOK/ONBOARDING changes; CLAUDE.md §2.3 already frames the case study as
  the single source of truth. Pattern is project-specific (corrosim's schema);
  nothing to file upstream.
- **Regeneration check:** since arghel's pKaH is unchanged (−1.5), the report
  is byte-identical — regenerating produced only a `Generated` timestamp diff,
  which was reverted. No artifact needed regenerating.
- **Audit:** pytest **198 passed / 1 skipped**; ruff + mypy (39 files) +
  complexipy (`complexipy --color no`, snapshot passed) green; tree clean on
  `main`, nothing unpushed. Submodule at upstream tip (`a6d7747`), no bump.
- **Pending:** epic **#72** now needs only **#53** (validation-preset compute):
  the **phytic-acid QM run** (fill `cases/phytic-acid/results/` + the
  computed-vs-reported column in `docs/validation.md`) and the
  **pyrazolo-pyrimidine preset** (land with the first DFT run so QM validates
  the hand-drawn SMILES; reported values in
  `docs/local/pyrazolo-pyrimidine-reported.local.md`) — both need Docker. Then
  **#71** Deployment (#66 Colab / #67 GHCR+PyPI / #68 Pages) and **#40**
  chemisorption E_ads. Optional deferred: `CORROSIM_FETCH` resolver fallback.

## 2026-07-09 (session 16) — phytic-acid validation compute (#53, PR #179)

- **Tool:** Claude Code (Opus 4.8). One squash-merged PR (#179) filling the
  **phytic-acid** validation preset's computed-vs-reported column — the first
  compute deliverable on the multi-study validation suite (#53).
- **#179 — phytic-acid DFT+MC+MD.** Ran `--case phytic-acid` (Fe(110) / 0.5 M
  H₂SO₄): DFT descriptors (B3LYP/6-31G(d), neutral, gas + aqueous ddCOSMO) + MC
  adsorption + MD Fe–O RDF; committed `cases/phytic-acid/results/` and filled
  `docs/validation.md`. **Finding:** corrosim reads phytic acid as a
  **charge-dense multidentate oxygen chelator** — large gap, small ΔN (+0.09),
  but TNC −14.6 from its 24 phosphate oxygens — binding flat (MC −11.5 kJ/mol at
  ~2.3 Å; MD Fe–O 3.25 Å). A *mechanistic* corroboration of Chidiebere 2014's
  flat-lying adsorption, not a quantitative match (AM1 ≠ B3LYP; UFF E_ads ≠
  COMPASS periodic E_bind; classical MC/MD can't confirm the chemisorption claim).
- **Level-of-theory wall (the session's main discovery).** The production
  6-311++G(d,p) is **intractable** for phytic acid (54 atoms, compact 24-O
  geometry, Rg ≈ 4 Å): its diffuse `++` functions drive SCF-diverging
  near-linear-dependence, and the density-fitting workaround (~13 GB `_cderi`)
  OOMs the ~8 GB Docker VM — which **crashed Docker Desktop/WSL** once (recovered
  via kill + `wsl --shutdown` + relaunch). Converged instead at **B3LYP/6-31G(d)**
  (no diffuse, ~450 BF, low-memory), documented as a qualitative-comparison
  choice. The QM image is also **stale** (editable pointer → `/work/corrosim`,
  not `/work/src`; every run needs `-e PYTHONPATH=/work/src` + `MSYS_NO_PATHCONV=1`).
- **Tickets:** filed **#180** (rebuild the stale `corrosim-qm` image) and **#181**
  (tractable + reproducible DFT level-of-theory for large inhibitors — a per-case
  `CaseStudy.basis`/`xc` override closes a real reproducibility gap:
  `run_dft --case phytic-acid` at defaults would re-diverge). Commented **#40**
  (phytic acid as a motivating chemisorption case + Quantum ESPRESSO as the free
  periodic-DFT route) and **#53** (status).
- **Gotcha caught in the wrap audit:** PR #179's body said "does **not** close
  #53", but GitHub matched the substring `close #53` and **auto-closed #53** on
  merge — **reopened it**, and hardened CLAUDE.md §2.1 (never write a close/fix
  keyword next to `#N`, even negated).
- **Also:** rendered `docs/pipeline.md` as a mobile reading-page Artifact
  (ephemeral, not a repo change).
- **Audit:** pytest **exit 0** (198 passed / 1 skipped), ruff + mypy (39 files) +
  complexipy (snapshot `[]` unchanged) green; **no production code changed** (the
  result used the existing `--basis` flag). Tree clean on `main`.
- **Pending:** **#53** stays open — the **pyrazolo-pyrimidine** preset (SMILES
  authored + RDKit-verified in `docs/local/pyrazolo-pyrimidine-reported.local.md`;
  land with its own DFT run, which should use the **production** 6-311++G(d,p) for
  a direct numeric comparison → wants #181's per-case basis first). Also **#181**
  (DFT tractability), **#180** (QM image rebuild), **#71** Deployment (#66–#68),
  **#40** chemisorption E_ads.

## 2026-07-09 (session 17) — per-case level of theory (#181) + pyrazolo preset (#53)

- **Tool:** Claude Code (Opus 4.8, 1M context).
- **Scope:** three threads off the phytic-acid wrap. (1) A design Q&A — why
  B3LYP/6-31G(d) beats AM1, why the production diffuse basis is intractable for
  phytic acid, and how much RAM the 16 GB laptop can give Docker — which motivated
  (2) landing **#181**'s first sub-task (per-case level of theory on `CaseStudy`)
  and (3) teeing up the next validation preset, **pyrazolo-pyrimidine** (#53). Two
  PRs merged, one issue filed, a Docker compute prepared for the owner to launch in
  the evening.
- **#184 — per-case DFT level of theory (#181, 1st sub-task).** `CaseStudy` gains
  `basis`/`xc` fields (default the adopted production B3LYP/6-311++G(d,p));
  `phytic-acid` declares `basis="6-31G(d)"` — the level it converges at, since the
  diffuse (++) functions drive near-linear-dependence on its compact 24-O geometry
  and the SCF diverges. `resolve_case` backfills `args.basis`/`args.xc` from the
  case when a driver leaves them unset (hasattr + None guard); `run_dft`/`run_pka`
  opt in via `None` defaults, while `make_cubes`/`run_fukui` keep their own small
  6-31G(d). Closes the reproducibility gap: `run_dft --case phytic-acid` now
  resolves to 6-31G(d) instead of re-diverging. Every case self-documents its full
  level (ARGHEL restated at production, matching how it already restates
  metal/medium/pKaH). The remaining two #181 sub-tasks (SCF robustness, memory
  guard) stay open.
- **#185 — pyrazolo-pyrimidine validation preset (#53).** Second study on the
  multi-study suite: three novel derivatives (Awad et al., Sci. Rep. 15:32576,
  2025) — 3-methyl-1-phenyl-pyrazolo[3,4-d]pyrimidin-4-yloxy propanoate
  acid/amide/ethyl-ester lead — on Fe(110)/1 M HCl at B3LYP/6-311++G(d,p). Novel
  (no CAS): SMILES authored + RDKit-verified (formula + MW exact), added to
  `inhibitors.json` (`source:"paper"`), build offline (36/37/42 atoms).
  `docs/validation.md` reported column filled (gaps 4.651/4.647/4.640, cmpd-1
  ΔN +0.244 / E_back −0.582, E_ads −130 kcal/mol, ranking 3 > 2 > 1); **computed
  column pending the DFT run**. Because the paper's level equals corrosim
  production, the descriptors compare digit-for-digit (the payoff of #181; unlike
  the AM1 phytic anchor). Two flagged in-code defaults: medium molarity assumed
  1 M HCl (the note recorded only "acidic HCl") and pKaH left at the default (no
  value for novel compounds; does not affect the DFT run).
- **Framing correction (owner):** ARGHEL is not "special" — it is a validation
  study like the rest (source = Mohammed 2014, cross-checked in validation.md),
  distinguished only as the default the drivers use and the one whose report is
  rendered. Reframed the presets docstring + section headers; rendering is no
  longer asserted as a preset property.
- **#183 filed (deferred):** every case study should be rendered (own report
  bundle), not just ARGHEL — revises **ADR 0018**. Deferred by owner: a complete
  phytic-acid render needs Docker (missing cubes + `*_fukui.json`; the venv renders
  only dft/mc/md/pipeline figures). The ADR revision is written when it lands.
- **Owner preference:** a blank line between dataclass field groups for readability
  (kept whitespace-free for ruff W293). Recorded to memory.
- **Docker allocation (16 GB laptop):** the WSL2 VM defaults to ~8 GB (no
  `.wslconfig`); a 13–14 GB density-fit `_cderi` won't fit — max safe real
  allocation ~12 GB (`[wsl2] memory=12GB` + swap), or spill `_cderi` to disk (cap
  pyscf `max_memory`). Memory alone doesn't fix the SCF linear-dependence
  divergence — `remove_linear_dep_` does. Recorded to memory; it is why the phytic
  production basis stays out of reach on this box.
- **Evening compute prep:** the owner will launch the pyrazolo DFT+MC+MD run at
  20:00 themselves. Prepared `docs/local/run_qm_compute.sh` (gitignored) — one
  command launches a detached `corrosim-qm` container chaining run_dft
  (→ `cases/pyrazolo-pyrimidine/results/dft_descriptors_ff.{json,csv}`) + run_mc +
  run_md; uses `PYTHONPATH=/work/src` + `MSYS_NO_PATHCONV=1` (no rebuild needed). A
  cloud routine can't reach local Docker, so this is a local one-command script,
  not a schedule.
- **Docs:** PLAYBOOK's `--case` note extended (unset `--basis`/`--xc` now adopt the
  case's level). README stays generic (the case list is data in presets.py, not
  re-declared). No new ADR — no new directory / content move; per-case level is a
  schema extension following the CaseStudy-as-single-source-of-truth pattern,
  documented in-code.
- **Verification:** `pytest` 208 passed / 1 skip; `ruff check .` clean; `mypy`
  clean (39 files); `complexipy --color no` snapshot passed (unchanged — the
  mid-session `complexipy .` failures were a wrong-scope artifact: the gate reads
  `[tool.complexipy] paths = ["src/corrosim"]`, not the whole tree). Both PRs green
  pre-merge; tree clean on `main`. Submodule at upstream tip (a6d7747), no bump.
- **Pending:** **#53 remaining = Docker compute only.** Owner runs
  `bash docs/local/run_qm_compute.sh` ~20:00 (pyrazolo DFT+MC+MD), then spot-checks
  the gap ordering (expect ester 3 < 2 < 1) vs validation.md and fills the computed
  column. Then **#183** (render every study; phytic-acid first — needs cubes +
  fukui), the two remaining **#181** sub-tasks (SCF robustness, memory guard),
  **#180** (rebuild the stale corrosim-qm image), **#71** Deployment (#66–#68),
  **#40** chemisorption E_ads.

## 2026-07-09 (session 18) — README de-slop + em-dash purge; ai-writing-detector skill; imbra-agent-skills repo

Docs-only on corrosim; the rest is cross-project agent tooling.

- **README de-slop:** reviewed the README for AI-writing tells and cut them.
  Removed scaffolding/signpost sentences ("corrosim has two modes:", "corrosim
  is two tools:", the "multiscale pipeline ... is documented in" pointer, the
  "Open report.html ... in Word" paragraph, the "Quercetin is the robust lead"
  result-claim). Reframed the one-liner so the mechanism is generic ("screens
  corrosion inhibitors") with "green" as design intent, not a filter. Features
  simplified to one capability per line. `emit`/`Emit` to `writes`/`Write` for a
  plainer, consistent verb. Net 28 insertions / 53 deletions, all prose.
- **Em-dash purge (owner rule):** owner declared the em-dash a definitive
  AI-writing tell. Removed all 24 from the README, each replaced by the
  punctuation its role needs (colon for a gloss, parentheses for an aside,
  comma/period for a break); en-dashes in ranges (`HOMO-LUMO`) kept. Recorded as
  a feedback memory (`em-dashes-are-ai-tell`).
- **ai-writing-detector skill (global, `~/.claude/skills`):** built from
  *Wikipedia:Signs of AI writing*, generalized to any prose; a mechanical grep
  pass + a judgement pass + a 0-100 score over five bands, with a calibration
  section to avoid false positives; em-dash reclassified as a strong tell. Scored
  the README (floor-level clean after the purge) and PLAYBOOK (clean).
- **imbra-agent-skills repo (new, PRIVATE, Imbra-Ltd):** the authored-capability
  skills layer, installable onto devices and usable as a submodule. Holds
  ai-writing-detector, install.ps1/.sh (symlink or copy into `~/.claude/skills`),
  and discussions. Committed and pushed (github.com/Imbra-Ltd/imbra-agent-skills).
- **#186 filed:** one command to run the full multiscale study end-to-end. Today
  the pipeline is 8 driver modules across two environments with real gotchas
  (run_dft/run_pka do not auto-route outputs; make_report silently drops missing
  MC/MD/pKa/cubes sections). Proposed a `corrosim-run-study` orchestrator with a
  `--plan` dry run; UX sketch attached.
- **Skills survey + architecture:** swept all braboj + imbra-ltd repos; the only
  skills are three in imbra-ltd/nango-blogs (article-scorer, blog-article,
  deploy-blog). Two already ban em-dashes, so the AI-tell knowledge is
  triplicated; dedupe target is ai-writing-detector. Reconciled the skills
  direction against solid-ai-templates' reference-model work (P1 epic #712 +
  spikes #179/#414/#415): skills are the only real progressive-disclosure
  mechanism (corrosim's missed mypy gate is the cited evidence), a compilation
  target from an agnostic source; two skill kinds (emitted convention vs authored
  capability) map onto solid-ai-templates (public base) and imbra-agent-skills
  (private company). Captured in the new repo's
  discussions/reference-model-and-layering.md.
- **Verification:** `pytest -q` exit 0 (green, 1 skip). No code/config/test
  changed this session, only README prose, so ruff/mypy are unaffected. Nothing
  committed this session (owner commits on request). The working tree also still
  carries the previous session's unshipped wrap (the session-17 dev-journal entry
  plus a 4-line PLAYBOOK edit) alongside these README changes.
- **Pending:** corrosim changes uncommitted (README de-slop + em-dash purge, and
  the still-unshipped session-17 wrap: dev-journal + PLAYBOOK). Owner to say
  whether to ship, and how to split (README vs the inherited wrap). Cross-repo
  follow-ups: dedupe the Nango AI-tell list into ai-writing-detector (lands in
  nango-blogs); adopt a skill namespace prefix once solid-ai-templates#415
  settles; optionally comment on #414/#712 with the authored-vs-emitted finding.
  Prior threads carried from session 17 (unvalidated this session): **#53** Docker
  compute (owner runs the pyrazolo DFT+MC+MD), then **#183**, the two **#181**
  sub-tasks, **#180**, **#71**, **#40**.

## 2026-07-10 (session 19) — QM image rebuild (#180), pyrazolo compute in-flight (#53), template-gap tickets

Compute session plus a run of upstream-template gap tickets surfaced while
explaining the config files.

- **#180 QM image rebuilt.** No local `corrosim-qm` image existed, so a fresh
  `docker compose build` regenerated the editable install: `import corrosim` now
  resolves to `/work/src/corrosim` (the ADR-0011 path) with no `PYTHONPATH`
  workaround, verified via a bind-mounted probe (`pyscf 2.13.1`, `tblite` import
  OK). Windows gotcha found and worked around: `docker` stdout is not captured by
  the background-shell harness, so QM jobs are monitored via bind-mounted
  logfiles / their output files on the host, and `docker compose run` needs `-T`.
- **#53 pyrazolo compute.** MC + MD ran in the venv (no QM needed): MC E_ads
  ranking is acid −20.4 > amide −15.6 > ester −8.8 kJ/mol; MD Fe-O peaks
  3.85-3.95 A with Fe-N peaks present. The DFT matrix
  (B3LYP/6-311++G(d,p), forms=both) was launched detached and is STILL running at
  session close (~2 h in, on molecule 2 of 3); each protonated diffuse-basis SCF
  is 12-15 min at 8 threads. Descriptors, the `validation.md` computed column, and
  the report render all wait on it finishing.
- **#188 merged.** `.gitignore` now ignores `.claude/settings.local.json`
  (scoped to the local file so a shared `.claude/settings.json` stays trackable).
  Squash-merged from a branch.
- **Stray `report/` removed.** An empty pre-ADR-0018 `report/tables/` at the repo
  root (untracked, from before per-case output routing) was deleted after the
  owner released a native process that held it as its working directory (found via
  Resource Monitor).
- **Upstream template-gap tickets (solid-ai-templates), from a quality-gates +
  config-file coverage audit:** #749 (bug) Go stacks inherit the Python/TS
  complexity-tool line with no Go tool; #750 (spike, reframed) move the concrete
  complexity-tool mapping to the language layer (DIP); #751 (bug) prescribe
  `.gitattributes` so the LF-only MUST is enforceable (EditorConfig is editor-side
  only; this is corrosim's own EOL-churn fix generalized); #752 (task) cover Docker
  Compose in the infra layer; #753 (task, P2) add `base/language/python.md` and a
  tooling section to `typescript.md` as the home for per-language tool selection
  (umbrella that subsumes #750). All cross-linked.
- **corrosim #189 (spike) filed:** define what `examples/` should contain; a bare
  `examples/molecules.csv` with empty SMILES columns reads as broken rather than a
  name-or-SMILES demo.
- **Memory:** added `wuseria-husky-hooks` (Imbra-Ltd/wuseria uses Husky +
  lint-staged, not pre-commit; the Python-vs-JS hook-tooling split; a
  config-hygiene reference for #751/#753).
- **Quality gates:** `pytest -q` green (1 skip), `ruff check .` clean, `mypy`
  clean (39 files). Nothing committed this session beyond the merged #188 (owner
  commits on request); working tree carries only the in-flight
  `cases/pyrazolo-pyrimidine/` results and this journal entry.
- **Pending:** the pyrazolo **DFT is still running detached** (molecule 2 of 3) and
  survives session teardown; on completion: parse `dft_descriptors_ff`, fill the
  `validation.md` pyrazolo computed column and check the reported gap ordering
  3 < 2 < 1 vs Awad 2025, then commit the whole pyrazolo case (DFT + MC + MD +
  figures + report) as one change. Then **#183** phytic-acid render (make_cubes +
  run_fukui at B3LYP/6-31G(d), then venv figures/report), serialized after the DFT
  frees the CPU. **#180** optional CI/Makefile pin (drift prevention) remains.
  Cross-repo, filed but not landed (owner's to work): solid-ai-templates
  #749/#750/#751/#752/#753 and corrosim #189. Prior threads carried: the two
  **#181** sub-tasks, **#71**, **#40**.

## 2026-07-10 (session 20) — engineering know-how doc + skill; upstream feedback loop

A meta/tooling session (no new pipeline code); the detached pyrazolo DFT finished
in the background near the end.

- **`docs/engineering-know-how.md` (new).** A generic, project-agnostic
  distillation of the codebase's transferable software-engineering patterns:
  package structure, dependency isolation, config, CLI, typing contracts,
  testability, CI/CD, DevSecOps, cross-platform, decision hygiene. Built by three
  read-only fan-out passes (ADRs, config/CI toolchain, source patterns) then
  synthesis. Iterated per owner steer: stripped ALL repo/domain references
  (no ADR numbers, file paths, or chemistry), placeholder names (`mypkg`,
  `Profile`, `nativelib`); added verbatim-then-genericized code examples and ASCII
  diagrams; finally reorganized by the solid-ai-templates taxonomy (core /
  language / infra / security / workflow) plus a **free-form** section that
  doubles as the upstream-candidate queue. Style: no em-dashes, no `---` dividers.
- **`engineering-know-how` skill (Imbra-Ltd/imbra-agent-skills).** Authored the
  reusable capability behind the doc (`SKILL.md` + `reference.md`: scope, fan-out
  method, genericize + style rules, taxonomy outline, extractor prompts, gap
  analysis). Installed onto the device and pushed (commits `aac0945` add,
  `36a7491` taxonomy structure).
- **Upstream feedback loop.** A gap analysis of the doc against the templates
  surfaced 7 genuine gaps, filed on braboj/solid-ai-templates: **#754** in-process
  config model, **#755** `base/core/cli.md`, **#756** scoped coverage, **#757**
  single-backdoor optional-dep module, **#758** AST public-API-contract test,
  **#759** full-history secret scan, **#760** reconcile the `mypy --strict`
  mandate. Then root-caused why these were not auto-filed at prior session ends
  (the template-feedback audit item fired shallowly: gated on an explicit
  end-signal, delta-only scope, domain-skin bias, one-line depth) and filed the
  process meta-fix **#761**; commented the taxonomy mechanism on #761 and a
  cross-note on #349.
- **CLAUDE.md process fix.** New 1.4 rule: judge upstream reusability at
  ADR-decision time (strip the domain nouns, add an `Upstream:` line), and 6.3
  harvests it in the end-of-session audit. Indexed the new doc in the 1.4 table.
- **`.markdownlint.json`** added in the memory folder so MD041 accepts `name:`
  frontmatter as the title.
- **pyrazolo DFT (#53) FINISHED** in the background (container exited 0;
  `dft_descriptors_ff.{csv,json}` written). MC + MD were already done. The case is
  now compute-complete but UNPROCESSED and uncommitted (see Pending).
- **Verification:** `pytest -q`, `ruff check .`, `mypy` run at wrap-up (results in
  the PR). Shipped `docs/engineering-know-how.md` + the CLAUDE.md rule + this
  journal via PR on a branch (squash-merged).
- **Pending:** the pyrazolo **DFT is now COMPLETE but UNPROCESSED**: parse
  `dft_descriptors_ff`, fill the `validation.md` pyrazolo computed column, verify
  the reported HOMO-LUMO gap ordering ester 3 < 2 < 1 vs Awad 2025, regenerate
  figures + report, then commit the whole `cases/pyrazolo-pyrimidine/` case as one
  change (currently untracked). Then **#183** phytic-acid render (make_cubes +
  run_fukui at B3LYP/6-31G(d), then venv figures/report). Cross-repo, filed but
  owner's to work: solid-ai-templates #754-761 (+ #349 comment) and corrosim #189.
  Prior threads carried: the two **#181** sub-tasks, **#71**, **#40**.

## 2026-07-10 (session 21) — pyrazolo case shipped (#193) + report table/figure UX (#191, #192)

Processed the pyrazolo compute left unprocessed at the end of session 20, shipped
it as a full validation case, and refined the report table/figure presentation
along the way. Three PRs merged.

- **Pyrazolo-pyrimidine validation case (#193).** Parsed the finished DFT matrix
  and filled the `validation.md` computed column with an honest read: corrosim
  reproduces the absolute frontier levels, the physisorption regime, and the
  reported **lead compound** (the ethyl ester tops the composite descriptor
  ranking), but **not** the full **3 > 2 > 1** order. The margins separating the
  three sit below what a single-point MMFF-geometry run can resolve (the reported
  gap spread is ~0.01 eV), the computed gaps run ~0.24 eV narrower than reported
  (force-field vs the paper's optimised geometry), and the single-molecule MC
  adsorption order inverts. Ran `run_fukui` + `make_cubes` in Docker (the ESP MEP
  integral is slow, ~10-12 min per molecule on these ~40-atom aromatics),
  rendered a placeholder-free bundle (26 figures), committed the whole case.
- **Report tables transposed (#191).** Every descriptor / ranking / pKaH / cation
  table now reads molecules-as-columns, quantities-as-rows (the wide 12-to-15
  column tables were the only thing overflowing the report body). Units live in
  the row labels; HTML and Word share `descriptor_matrix` / `ranking_matrix`; all
  tables gain an `overflow-x` safety net. Goldens + arghel bundle regenerated.
- **Figure + winner-mark UX (#192).** Report figures stack in a single
  fixed-width (600px) column instead of flowing two or three per row. Ranking
  tables mark the best value in each metric row with a green checkmark (smallest
  gap, highest softness, most-negative E_ads, highest score); metrics with no
  defensible best (ΔN, metal-O distance, TNC) stay unmarked, and the overall-lead
  column stays highlighted. Chosen interactively by the owner.
- **ADR 0019 (per-case report bundles).** Rendering the pyrazolo bundle
  contradicted ADR 0018's rejected "no per-study bundle" alternative, so 0019
  records the flip: each validation case renders its own bundle
  (`cases/<case>/report/`), with `validation.md` still the cross-study comparison
  home. This resolves the policy half of **#183**; the remaining half is the
  phytic-acid compute-and-render.
- **PLAYBOOK.** Added a "Render a validation case end-to-end" recipe (the QM
  container + venv sequence, the shared-`fig0` copy step, and the small-basis /
  drop-ESP escape hatch for large charge-dense molecules).
- **Quality gates:** `pytest` (all pass), `ruff`, `mypy`, and the `complexipy`
  watermark all green at each merge; working tree clean, all feature branches
  auto-deleted.
- **Template feedback.** The transpose (orient a comparison table so the fewer
  entities are columns) and the per-metric winner-mark are generic dataviz ideas,
  but `solid-ai-templates` covers code/testing/workflow conventions, not
  generated-report or dataviz structure, so there is no upstream home; recorded
  as project-specific. ADR 0019 likewise carries `Upstream: none`.
- **Pending:** **#183** phytic-acid render is the one open case (ADR 0019 settled
  the policy; the compute-and-render remains): `run_fukui` + `make_cubes` at
  `6-31G(d)` then venv figures/report. Its ESP cube is the risk step (the folded
  54-atom, 24-oxygen geometry that forced its DFT off the diffuse basis), so
  generate cubes at a modest grid / drop `--what esp` if the MEP integral chokes.
  Cross-repo, filed but owner's to work: solid-ai-templates #754-761 (+ #349),
  corrosim #189 / #186 / #181 / #180. Prior threads carried: **#71**, **#40**.

## 2026-07-11 (session 22): validation suite completed and epic #53 closed

Six PRs plus the epic. Completed the #53 multi-study validation suite, resolved
the pyrazolo geometry open-test, reframed `docs/validation.md`, and closed the
epic honestly.

- **Phytic-acid render (#195, closes #183).** Ran `run_fukui` + `make_cubes`
  (orbital, then ESP at `--nx 60` to stay under container memory on the folded
  24-oxygen geometry), then rendered the venv bundle. Phytic acid now ships the
  same per-case bundle as arghel and pyrazolo; Fukui reads a single dominant
  oxygen donor (O9, f-=+0.71). Descriptors stayed at 6-31G(d).
- **validation.md reframe (#196, ADR 0020).** Restructured around the validation
  *approach* rather than Arghel: general principles up top (level-of-theory
  ceiling, geometry offset, the `E_ads`/`ΔG°ads`/`E_bind` observable rule,
  screening-as-hypothesis), then arghel/phytic/pyrazolo as three peer cases.
  Added a status vocabulary (Validated/Partial/Rejected/Pending +
  qualitative/quantitative qualifier), a per-case status badge and claim-by-claim
  scorecard, a summary table, and an ASCII comparison diagram. Renamed the stale
  Stage-1/2/3 labels to the named work. Ran the ai-writing-detector: the doc
  scored ~58/100 driven almost entirely by em-dash density, so swept all 51 prose
  em-dashes (down to ~15, all table no-data cells).
- **logs/ scratch folder (#197).** Detached QM jobs write monitoring logs to a
  gitignored `logs/` (the container bind-mount only reaches `/work`); the PLAYBOOK
  render recipe now redirects to `logs/<name>.log` with a `mkdir -p`.
- **Submodule bump to v2.35 (#198).** `docs/solid-ai-templates` a6d7747 to
  6969ccd, pulling in the resolved upstream issues distilled from corrosim's own
  patterns (#754, #756, #758, #759, #760, #761, #751, #752, #745, #746).
- **Pyrazolo geometry open-test resolved (#199).** Ran the flagged `--optimize`
  DFT-geometry rerun (6 species, ~19 h detached; the ester tail converged slowly,
  host slept overnight). Optimised geometry closes the absolute offset: every
  neutral gap rises ~0.20 eV, landing within ~0.05 eV of reported (was ~0.24 eV
  low), confirming geometry as the cause. The 3>2>1 order still does not sharpen:
  the opt gaps span 0.007 eV (below the reported 0.011 eV spread) and the gap-lead
  flips ester-to-acid between FF and DFT geometry, so it is noise-limited, not
  geometry-limited (`compare_geometry`: gap ranking CHANGED, ΔN PRESERVED).
  Case 3 stays Partial, now with a tested explanation.
- **Epic #53 closed + #200 filed.** All three cases done (arghel Validated, phytic
  Validated-qualitative, pyrazolo Partial). Closed #53 honestly: all three cases
  are Fe(110), so the "non-Fe substrate" goal and the Tier-2 preset tail were
  carried forward to **#200**, not claimed complete. Also set the GitHub About +
  20 topics.
- **Verification.** `pytest -q`, `ruff check .`, `mypy` green at each merge; main
  clean, feature branches auto-deleted.
- **Template feedback.** The validation status vocabulary, scorecard, and ASCII
  diagram are results-presentation conventions for a generated document, outside
  the solid-ai-templates code/testing/workflow scope (ADR 0020 `Upstream: none`).
  The `logs/` + poll-a-bind-mounted-logfile trick is a niche Windows/Docker/
  background-shell quirk, kept project-specific.
- **Pending:** epic-level validation work is done. Open corrosim threads: **#200**
  (non-Fe Cu/Al cases + Tier-2 tail), the **#71** deployment epic (#66 Colab /
  #67 GHCR+PyPI / #68 Pages), standalone **#40** (quantitative chemisorption), and
  #189 / #186 / #181 / #180. Cross-repo: solid-ai-templates now current at v2.35.

## 2026-07-12 (session 23): canonical ranking basis + robustness gate (ADR 0021)

Started from a reader's question — why the pyrazolo headline crowned the ethyl
ester when the ester's gap edge over the propanoic acid is sub-milli-eV and the
DFT-optimised geometry flips the lead. Tracing it showed the report scored the
composite z-score independently on three descriptor bases (force-field vs
DFT-relaxed geometry x neutral vs pH-blend speciation) and named up to three
different leads, with the "headline" basis chosen by which CSV the driver's
default path resolved to. Framed the fix generically and shipped it.

- **ADR 0021 (Accepted).** One declared canonical basis (best geometry x
  pH-weighted speciation x solvated phase); every other basis is a labelled
  sensitivity panel, never a competing ranking; the lead is asserted only when it
  survives a change of basis, else the report calls a tie within method
  resolution. Confirmed the two open defaults with the owner (best-available
  geometry; pH-weighted speciation). `Upstream: none` — a scientific-computing /
  results-presentation pattern (home is `docs/engineering-know-how.md`), outside
  the solid-ai-templates code/testing/workflow scope.
- **Implementation (#202).** New `report/ranking.py` owns `rank_inhibitors` +
  `build_ensemble` (assembles every available basis, picks the canonical one,
  judges robustness by leader agreement). The HTML and Word summary sections now
  score the canonical basis, render a lead-by-basis sensitivity table + a
  robust/tie verdict sentence, and suppress the winner marks on a tie; the
  optimised-geometry / protonated-cation / speciation tables were demoted to
  plain descriptor panels (no score row, no competing "best"). The bundled
  `ranking.csv` follows the canonical basis. Removed the now-dead FF-neutral
  `PreparedReport.bottom_line` / `ranked` / `summary`.
- **Re-rendered all three bundles.** Pyrazolo now reads honestly as a tie (ethyl
  ester tops force-field-neutral, the propanoic acid tops the other three bases;
  propanamide robustly weakest) — the direct answer to the opening question.
  Arghel stays a robust quercetin lead across all four bases; phytic acid is a
  single-molecule / single-basis lead.
- **Tests + gates.** New `tests/test_ranking.py` pins canonical selection and both
  the robust and tie verdicts; a report-level test asserts the tie renders with no
  crowned winner; goldens regenerated and eyeballed. `pytest` 215 passed /1
  skipped, `ruff` + `mypy` clean, complexipy adds no over-threshold function.
- **Docs.** README structure map gains `report/ranking`; CLAUDE.md §5.1 gains a
  review check for the canonical-basis + robustness convention.
- **Know-how distillation now per-session.** On the user's steer, ADR 0021's
  transferable kernel ("rank on one declared basis; treat alternatives as a
  sensitivity ensemble; never order finer than the estimator resolves") was
  written straight into `docs/engineering-know-how.md` (Quality and design)
  instead of being deferred, and CLAUDE.md §6.3 gained a standing step 3 making
  the distillation an every-wrap-up task, not a periodic reconciliation. Upstream
  candidate: tighten solid-ai-templates `scope.md` item 11 the same way.
- **Pending:** none from this session's work. Prior open threads unchanged:
  **#200**, **#71** (#66/#67/#68), **#40**, #189 / #186 / #181 / #180.

## 2026-07-12 (session 24): first non-Fe validation case (TMP-SMX on Al(111))

Picked up **#200** (the non-Fe + Tier-2 tail left when #53 closed) and took its
headline goal end-to-end: the pipeline claims to be substrate-agnostic, but every
shipped case was Fe(110), so the claim was architecturally true yet never
exercised. Shipped the first non-iron validation case, trimethoprim +
sulfamethoxazole on aluminium, chosen because its paper computes at corrosim's own
production level (a direct numeric cross-check) and carries experimental data.

- **New case `tmp-smx` (Al(111) / 1 M HCl).** Added TMP + SMX to the library via
  `corrosim-add-inhibitor` (PubChem, CAS 738-70-5 / 723-46-6), a `TMP_SMX` preset
  at B3LYP/6-311++G(d,p), and a preset test asserting the non-Fe substrate wiring
  (Al work function present, `metal_element == "Al"`). No engine changes were
  needed: the fcc(111) slab, the Al work function, and the ΔN reference all read
  from the case's `metal`, so the metal-agnostic path just worked.
- **Ran the full stack on aluminium.** DFT descriptors (Docker, both forms x two
  phases, ~2 h at the diffuse basis), then MC + MD in the venv, then the bundle
  (`cases/tmp-smx/`, report.html + docx + figures + ranking.csv). Source:
  Odozi et al., Extreme Materials 2 (2026) 100027.
- **Result: 🟡 Partial (quantitative).** Absolute frontier levels reproduce (HOMO
  -6.22/-6.53 vs reported -5.94/-6.29 eV, the usual ~0.25 eV MMFF-geometry
  offset); the better-donor identity (TMP: shallower HOMO, lower chi) reproduces;
  and the ADR 0021 robustness gate independently returns a **tie** (the composite
  lead flips TMP on the neutral basis to SMX on the protonated / pH-weighted
  basis), which matches the paper's own refusal to crown a winner (it splits TMP
  the donor vs SMX the stronger adsorber, a synergistic pair). The adsorption
  ordering is observable-dependent (single-molecule UFF MC favours TMP, MD
  mean-energy favours SMX, the paper's solvent-box MC favours SMX), and the
  classical field cannot confirm the reported sub-3.5 A chemisorption (corrosim
  sits at 3.55 A). A clean demonstration of the robustness gate on a live case.
- **Docs.** `validation.md` gains Case 4 (scorecard, reported + computed tables,
  verdict), a four-case intro, and a dual substrate-model section (Fe(110) +
  Al(111)). Separately, on request, `pipeline.md` gained a per-stage **Libraries**
  row naming the package doing each calculation (RDKit / PySCF + geomeTRIC / PySCF
  + tblite / ASE + NumPy / NumPy + ASE / pandas), plus a pointer to
  `pyproject.toml` as the version-pinned source of truth.
- **No new ADR.** The case uses existing machinery (ADR 0018/0019 per-case
  bundle, ADR 0021 gate); no new directory or cross-document move. Know-how: the
  session validated two existing patterns ("inject the one axis you are tempted to
  hardcode" via the first non-Fe run; "rank on one declared basis, gate on
  robustness" via the tie) and added one new inverse guard ("check the regime
  before adding a per-item knob", from the single-case-pKaH-for-two-bases call).
- **Gates.** `pytest` 220 passed / 1 skipped, `ruff` + `mypy` clean.
- **Pending:** **#200 stays open** — done: Al(111)/tmp-smx; remaining: a Cu(111)
  case (tetrazoles or pyrazolylnucleosides) and the Fe(110) Tier-2 tail
  (carbonitriles, guar-gum, pyrazolone-sulfonamide, tangerine). Also a tmp-smx
  follow-up: its bundle omits Fukui maps and ESP/orbital isosurfaces (the paper
  has both) since the QM Fukui/cube stages were not run. Other threads unchanged:
  **#71** (#66/#67/#68), **#40**, #189 / #186 / #181 / #180.

<!-- Generated with solid-ai-templates (github.com/braboj/solid-ai-templates) -->
