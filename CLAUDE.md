# corrosim

Automated screening of green corrosion inhibitors: a molecule (name or SMILES)
and a metal in — DFT/QM reactivity descriptors + an adsorption estimate + a
ranking + a self-contained HTML report out. Free software only.

Quality conventions are defined in `docs/solid-ai-templates/` (submodule). Key
references — the resolved `python-lib` chain and the extras used here:

- `templates/base/core/quality.md`, `git.md`, `docs.md`, `readme.md`,
  `testing.md`, `config.md`, `oop.md`, `review.md`
- `templates/base/workflow/quality-gates.md`, `scope.md`
- `templates/stack/python-lib.md`

Project-specific overrides and additions follow below.

## 1. Project

### 1.1 Identity

- Model: hybrid
- Owner: Branimir Georgiev
- Repo: github.com/braboj/corrosim
- Stack: Python >= 3.10 scientific library + CLI (`corrosim`), MIT.
- Multiscale pipeline: Stage 1 DFT/xTB descriptors + Fukui + ESP -> Stage 2
  Monte Carlo adsorption pose -> Stage 3 Brownian MD (metal-O RDF) -> a
  self-contained HTML report. Scientific basis: `docs/pipeline.md`.
- Core deps: numpy, rdkit, ase, pandas, matplotlib.
- The QM engines (pyscf, tblite, geometric) have no Windows wheels and run
  ONLY in the `corrosim-qm` Docker image. Everything else runs in a venv.

### 1.2 Project structure

Layout is flat (`corrosim/`, not `src/`). `README.md` is the single source of
truth for structure; the tree below is the agent-oriented view.

```text
corrosim/        package: molecules, engines, descriptors, fukui, mc, md,
                 adsorption, surface, medium, speciation, pka, figures,
                 report, cli, presets
corrosim/runs/   stage drivers (run_dft/fukui/mc/md/pka, make_cubes/figures/
                 report, compare_geometry)
tests/           pytest suite (no DFT/Docker — fast)
results/         tracked pipeline data (descriptors, Fukui, MC/MD, pKa, comparison)
cubes/           volumetric .cube files (regenerable, gitignored)
report/          tracked report bundle: report.html (self-contained) + figures/
                 (PNG; fig0 = pipeline diagram) + tables/ (csv/json)
docs/
  ONBOARDING.md        onboarding guide for new contributors
  PLAYBOOK.md          operational reference for common tasks
  dev-journal.md       development history and session log
  decisions/           architecture decision records (NNN-slug.md)
  pipeline.md          scientific basis for the multiscale pipeline
  validation.md        computational + experimental validation
  pipeline.drawio      editable source for the pipeline diagram
  local/               private notes + source literature (gitignored)
  solid-ai-templates/  quality-convention template submodule
Dockerfile, docker-compose.yml   the corrosim-qm QM environment
```

### 1.3 Commands

```bash
pytest -q                              # test suite (venv; no QM)
ruff check .                           # lint
mypy                                   # type-check (non-strict) — also a CI gate
docker compose build qm                # build the QM image once
docker compose run --rm qm pytest -q   # run anything needing pyscf/tblite
python -m corrosim.runs.run_dft   --out-csv results/dft_descriptors.csv
python -m corrosim.runs.make_report    # -> report/ (report.html + figures + tables)
```

Long QM jobs (geometry-opt, frequency, MEP cubes) MUST run detached so a shell
or session exit does not kill them mid-run:

```bash
docker compose run -d --name corrosim_job qm \
    python -m corrosim.runs.run_dft --optimize ...
docker logs -f corrosim_job            # poll; then: docker rm corrosim_job
```

### 1.4 Documentation

Standard documents follow `docs.md`; `README.md` is the single source of truth
for structure. Keep each rule/fact in one home and cross-reference, do not
duplicate.

| Document | Purpose |
| --- | --- |
| `README.md` | Project overview, structure, setup, commands |
| `CLAUDE.md` | AI agent context and project rules (this file) |
| `docs/ONBOARDING.md` | Onboarding guide for new contributors |
| `docs/PLAYBOOK.md` | Operational reference for common tasks |
| `docs/dev-journal.md` | Development history and session log |
| `docs/decisions/` | Architecture decision records (`NNN-slug.md`, one concern each) |
| `docs/pipeline.md` | Scientific basis for the pipeline (project-specific) |
| `docs/validation.md` | Computational and experimental validation (project-specific) |

- Record significant decisions as ADRs in `docs/decisions/` using the ADR format
  in `docs.md`; each addresses exactly one concern.
- A rule the agent applies every turn belongs in this file as one line; if it
  needs a paragraph, write an ADR and leave a one-line pointer. Session history
  goes in `docs/dev-journal.md`; structure and setup in `README.md` /
  `ONBOARDING.md`. Do not record changelogs or session logs here.

## 2. Code conventions

### 2.1 Git

- Conventional commits: `<type>(<scope>): <summary>`, types
  feat/fix/chore/docs/refactor/style/test; subject imperative, < 80 chars.
- End every commit message with this trailer:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Branch off `main` for nontrivial work; never commit directly to `main`.
  Commit and push ONLY when asked.
- PR titles use the commit format with the number: `... (#NN)`. Do NOT write
  "closes #N" in a PR body unless the PR actually resolves it — GitHub
  auto-closes the issue on merge.
- `*.local.md` (kept in `docs/local/`) are private working notes: gitignored,
  never committed.
- The `report/` bundle (report.html + figures/ + tables/) and
  `results/*.{csv,json}` ARE tracked; `cubes/` and `*.log` are not.

### 2.2 Python

- `from __future__ import annotations`; type-hint public functions.
- Keep `mypy` clean — it is a CI gate. Run `ruff check`, `mypy`, and `pytest`
  before pushing (ruff alone is not enough).
- Units are part of the contract: energies in eV, distances in Å, adsorption
  energies in kJ/mol. Put the unit in the name or docstring (`e_ads_kjmol`,
  `first_peak_metal_O`); never leave a bare number.
- Scientific-comment exception to "a name that needs a comment is wrong":
  non-obvious physics or derivations MUST carry a short comment naming the
  descriptor or source (Koopmans, Lukovits ΔN, the relevant ADR).
- Substrate-agnostic: thread the `metal` parameter through; derive labels and
  output keys from the actual metal, never hardcode "Fe".
- Linter/formatter: ruff + `ruff format` (line length 100). Keep new and
  edited code ruff-clean; do not bulk-reformat untouched files.

### 2.3 Data, artifacts, and the single source of truth

- Single source of truth: the case study (molecule set + substrate + medium)
  lives in `corrosim/presets.py` (`ARGHEL`). Drivers import
  `ARGHEL.molecule_list()` / `ARGHEL.metal`; never re-declare the list.
- Generated data -> `results/`; figures -> `report/figures/`; report bundle ->
  `report/`; cubes -> `cubes/`.
- When a change alters an input, regenerate the dependent artifact in the SAME
  change: descriptors / `md_rdf.json` -> `make_figures` + `make_report` ->
  `report/`. Verify the diff (spot-check values, not just file size).

## 3. Quality

Testing, quality gates, and packaging follow the referenced templates
(`testing.md`, `quality-gates.md`, `python-lib.md`). corrosim deviations:

- Testing is deliberately QM-light: NO DFT/xTB/Docker in the pytest suite so CI
  stays fast. Run `pytest -q`. CI matrix is py3.10-3.12 with
  `pip install -e .[dev]`. Every new feature/module ships a test; name
  `test_<unit>_<state>_<expected>`.
- Quality gates in CI: `ruff check` + `mypy` (non-strict) + `pytest`. The
  `ruff format` gate is deferred (see `docs/dev-journal.md`).
- Scientific validity: cross-check ranking / descriptor claims against
  `docs/validation.md` before stating them as results. After a geometry or
  level-of-theory change, confirm the lead ranking is robust:
  `python -m corrosim.runs.compare_geometry`.

## 4. Identity

Not applicable — a scientific library / CLI with no design system or brand voice.

## 5. Review process

Follow `templates/base/core/review.md` priority order
(security > correctness > clarity > conventions); apply `quality.md`, `oop.md`,
and `python-lib.md` as the standard.

### 5.1 Code review — corrosim-specific checks

- Units stated (eV / Å / kJ/mol); no bare numbers.
- Outputs metal-agnostic — no stray hardcoded "Fe".
- Case study read from `presets.ARGHEL`, not re-declared.
- Dependent artifacts (the `report/` bundle) regenerated in the same change.

### 5.2 Structure audit

- Run `pytest -q`, `ruff check .`, and `mypy` before every PR/merge.
- Confirm docs are in their home (see 1.4): decisions in `docs/decisions/`, a
  session entry added to `docs/dev-journal.md`, structure changes in `README.md`.

## 6. Session protocol

Follow `templates/base/workflow/scope.md` for the scope guard and the
end-of-session audit.

### 6.1 Start of session

- Read `MEMORY.md` (the auto-memory index) and `docs/local/SESSION-HANDOFF.local.md`.
- Run `git status`.

### 6.2 During the session

- Run long QM jobs DETACHED (see 1.3); they survive a session teardown. Docker
  Desktop may be down after a host restart — start it and wait for
  `docker info` to answer before launching containers.
- Keep `results/` and the `report/` bundle regenerated as you go.
- When a path-based shell query (`test -f`, `ls`, `git -C`) returns an
  unexpected empty/negative, verify `pwd` first — the shell cwd persists
  across commands and an earlier `cd` can make it false-negative.

### 6.3 End of session

When the user signals end of session, first run the generic audit — **read
`docs/solid-ai-templates/templates/base/workflow/scope.md` (End of session
audit) and execute each item sequentially; do not summarize or skip.** Then
complete these corrosim-specific steps:

1. Run `pytest -q` (plus `ruff check .` and `mypy`); report the results.
2. Add a session entry to `docs/dev-journal.md`; record any decision as an ADR
   in `docs/decisions/`.
3. Update `docs/local/SESSION-HANDOFF.local.md` and `MEMORY.md`.
4. Commit (conventional, with the trailer) and push only when asked.

<!-- Generated with solid-ai-templates (github.com/braboj/solid-ai-templates) -->
