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

<!-- Generated with solid-ai-templates (github.com/braboj/solid-ai-templates) -->
