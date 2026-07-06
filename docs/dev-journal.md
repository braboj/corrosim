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

<!-- Generated with solid-ai-templates (github.com/braboj/solid-ai-templates) -->
