# Playbook

Operational reference for common corrosim tasks. New contributors should read
`docs/ONBOARDING.md` first. Project structure lives in `README.md`.

## 1. Git workflow

- Branch off `main` for any nontrivial work; never commit directly to `main`.
  Commit and push only when asked.
- Use conventional commits: `<type>(<scope>): <summary>`, with types
  feat/fix/chore/docs/refactor/style/test and an imperative subject under 80
  characters.
- End every commit message with the trailer
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Open a pull request titled like the commit with the number appended, for
  example `feat(pka): ... (#NN)`. Do not write "closes #N" in a PR body unless
  the PR actually resolves the issue — GitHub auto-closes it on merge.
- Private working notes match `*.local.md` and are gitignored — never commit
  them. `report.html` and `results/*.{csv,json}` are tracked; `cubes/` and
  `*.log` are not.

## 2. Domain operations

The case study — molecule set, substrate, and medium — is defined once in
`corrosim/presets.py` as `ARGHEL`. Change it there; the stage drivers import
`ARGHEL.molecule_list()` and `ARGHEL.metal` rather than re-declaring the list.

Run the classical stages (Monte Carlo, molecular dynamics, figures, report) in
the venv — they need no QM engines.

```bash
python -m corrosim.runs.run_mc          # Stage 2 adsorption pose
python -m corrosim.runs.run_md          # Stage 3 metal-O RDF
python -m corrosim.runs.make_figures    # figures/ set
python -m corrosim.runs.make_report     # -> report.html (self-contained)
```

Run the quantum stages (DFT descriptors, Fukui, pKa, cubes) in the
`corrosim-qm` container. Long jobs — geometry optimisation, frequencies, MEP
cubes — must run detached so a shell or session exit does not kill them.

```bash
docker compose run --rm qm \
    python -m corrosim.runs.run_dft --out-csv results/dft_descriptors.csv

# detached (long jobs):
docker compose run -d --name corrosim_job qm \
    python -m corrosim.runs.run_pka --freq --out-json results/pka_freq.json
docker logs -f corrosim_job             # poll; then: docker rm corrosim_job
```

After any change to input data, regenerate the dependent artifacts in the same
change (see 4, Maintenance) and spot-check the diff, not just the file size.

## 3. Quality

Run the automated checks before every pull request; they also run in CI on
Python 3.10–3.12. Manual checks come last.

### 3.1 Tests (pytest)

The suite is deliberately QM-light — no DFT, xTB, or Docker — so it stays fast.
Run `pytest -q` in the venv. Every new feature or module ships a test named
`test_<unit>_<state>_<expected>`.

### 3.2 Linting (ruff)

Run `ruff check .`. The line length is 100. Keep new and edited code clean; do
not bulk-reformat untouched files.

### 3.3 Type checking (mypy)

Run `mypy`. It is non-strict but is a CI gate — run it before pushing, since
`ruff` alone does not catch type errors.

### 3.4 QM tests (Docker)

Anything exercising the real engines runs in the container:
`docker compose run --rm qm pytest -q`. This is manual — CI does not run QM.

## 4. Maintenance

- Update dependencies by editing the ranges in `pyproject.toml` (ranges, not
  pins); keep the `dev`, `qm`, and `viz` extras coherent.
- Update the quality templates with
  `git submodule update --remote docs/solid-ai-templates`; the next session
  re-resolves the chain referenced from `CLAUDE.md`.
- Record significant decisions as ADRs in `docs/decisions/` using the
  `NNN-slug.md` numbering; each ADR addresses one concern.
- When a change alters an input, regenerate the dependent artifact in the same
  change: descriptors or `md_rdf.json` feed `make_figures` and `make_report`,
  which produce `report.html`.
- Cross-check ranking and descriptor claims against `docs/validation.md` before
  reporting them. After a geometry or level-of-theory change, confirm the lead
  ranking is robust with `python -m corrosim.runs.compare_geometry`.

## 5. Release and deploy

corrosim is an MIT-licensed library and CLI. There is currently no automated
release or PyPI publish; the version lives in `pyproject.toml` and the tracked
`report.html` plus `results/` are the shipped artifacts. When a release process
is added, it should publish to PyPI from CI on a version tag, built with the
standard `build` backend.

<!-- Generated with solid-ai-templates (github.com/braboj/solid-ai-templates) -->
