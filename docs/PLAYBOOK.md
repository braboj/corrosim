# Playbook

Operational reference for common corrosim tasks. New contributors should read
`docs/ONBOARDING.md` first. Project structure lives in `README.md`.

## 1. Git workflow

The commit, branch, and pull-request conventions (conventional commits plus the
`Co-Authored-By` trailer, branch off `main`, the "closes #N" auto-close caveat,
and the `*.local.md` / tracked-artifact rules) have a single home:
[CLAUDE.md](../CLAUDE.md) §2.1. Follow them there; they are not restated here so
the two files cannot drift apart.

## 2. Domain operations

`corrosim` is one command with three subcommands (ADR 0030): `corrosim screen`
for a quick ranking, `corrosim run-study` for the full multiscale study, and
`corrosim add-inhibitor` for the library tool. A leading option is shorthand for
the screen (`corrosim --inhibitors ...`), and the standalone `corrosim-run-study`
/ `corrosim-add-inhibitor` scripts stay as aliases, so the commands below can be
written either way.

The case study (molecule set, substrate, and medium) is defined once in
`src/corrosim/presets.py` as `ARGHEL`. Change it there; the stage drivers import
`ARGHEL.molecule_list()` and `ARGHEL.metal` rather than re-declaring the list.

### Growing the inhibitor library

The inhibitor library ships as data in `src/corrosim/data/inhibitors.json`
(name -> SMILES + `source`/`cas`/`notes`), loaded by `molecules`. Add an
inhibitor as a data edit, or fetch it from PubChem by name or CAS and commit
the result; the JSON stays the offline source of truth:

```bash
corrosim-add-inhibitor thiourea         # by name
corrosim-add-inhibitor 62-56-6          # by CAS number
corrosim-add-inhibitor 68-12-2 --name dmf   # override the stored key
# validates the SMILES with RDKit, appends source: pubchem; then commit the file
```

Because the library is package data, a one-off `docker run --rm
ghcr.io/braboj/corrosim` never sees a new entry: its baked-in copy is read-only
and the write dies with the container. Add from a source clone (a native
`.[qm]` venv, or `docker compose`, which bind-mounts the tree at `/work`), then
commit the JSON and rebuild the image to ship it. For a one-off you need none of
this: pass the SMILES directly wherever a molecule name goes.

### The full study in one command

`corrosim-run-study` (also `python -m corrosim.runs.run_study`) orchestrates the
whole pipeline (`dft -> fukui -> mc -> md -> figures -> report`) for a `--case`,
in dependency order, reusing each driver's per-case output routing so no paths
are passed (ADR 0022). The `corrosim-qm` image carries both the QM and the
classical dependencies, so the whole study runs in one container invocation:

```bash
docker compose run --rm qm corrosim-run-study --case arghel           # the full bundle
docker compose run --rm qm corrosim-run-study --optimize --with-pka   # + opt geometry + speciation
corrosim-run-study --case arghel --plan                               # dry run: list the ordered steps
corrosim-run-study --case arghel --only mc,md,figures,report          # classical stages only (venv)
```

It skips a stage whose output already exists (`--force` recomputes) and stops at
the first failure, so a partial run resumes. Enrichments are opt-in
(`--with-pka`, `--with-cubes`, `--optimize`); `--skip <stage>` drops one. For a
long run, detach and poll:

```bash
docker compose run -d --name corrosim_study qm corrosim-run-study --optimize
docker logs -f corrosim_study     # poll; then: docker rm corrosim_study
```

The individual drivers below remain for partial runs, debugging, and the
QM-vs-venv split when you are not using the container.

Run the classical stages (Monte Carlo, molecular dynamics, figures, report) in
the venv, since they need no QM engines.

```bash
python -m corrosim.runs.run_mc          # Stage 2 adsorption pose
python -m corrosim.runs.run_md          # Stage 3 metal-O RDF
python -m corrosim.runs.make_figures    # -> cases/<case>/report/figures/ set
python -m corrosim.runs.make_report     # -> cases/<case>/report/ bundle (self-contained report.html)
```

Every driver's unset `--out*` flags auto-route to the `--case` study's own
`cases/<case>/results` / `cases/<case>/report` subtree (default case: `arghel`); pass
`--case <name>` to screen another study without overwriting arghel's outputs.
The DFT drivers (`run_dft` / `run_pka`) likewise adopt the case's own level of
theory when `--basis` / `--xc` are unset, so `--case phytic-acid` runs at its
declared `6-31G(d)` (the production diffuse basis diverges on its compact
geometry), not the default `6-311++G(d,p)`.

Run the quantum stages (DFT descriptors, Fukui, pKa, cubes) in the
`corrosim-qm` container. Long jobs (geometry optimisation, frequencies, MEP
cubes) must run detached so a shell or session exit does not kill them.

```bash
docker compose run --rm qm \
    python -m corrosim.runs.run_dft    # -> cases/arghel/results/dft_descriptors_ff.{json,csv}

# detached (long jobs):
docker compose run -d --name corrosim_job qm \
    python -m corrosim.runs.run_pka --freq --out-json cases/arghel/results/pka_freq.json
docker logs -f corrosim_job             # poll; then: docker rm corrosim_job
```

### Run your own study (bring-your-own inhibitors, metal, medium)

The `--case` names above screen the shipped validation studies. To screen a new
set, declare a study as data (name + molecules + metal + medium, with an optional
DFT level) and point the same runner at it, with no `presets.py` edit. Two
interchangeable front doors, one engine:

```bash
# a study file (durable, shareable, reproducible); copy examples/study.template.json
docker compose run --rm qm corrosim-run-study --case ./my-study.json

# ad-hoc flags: builds the study inline, writing cases/<name>/study.json
corrosim-run-study --name my-study --molecules "quercetin,CCO" \
    --metal Cu(111) --medium "1 M HCl" --basis def2-SVP
```

`--molecules` switches on build mode (it needs `--name`, and is mutually
exclusive with `--case`); the unset study fields fall back to the `CaseStudy`
defaults. Molecules are library names or SMILES, so a novel compound needs no
library edit. The supported envelope is validated before any stage runs: the
metal must be one the slab builder knows (`Fe`/`Cu`/`Al`) and every atom must
have a UFF parameter (`H, C, N, O, S, F, Cl, Br, P`); an out-of-range study exits
with a clear message. A bromine-containing set needs `--basis def2-SVP` (the
Pople sets lack bromine). `--plan` validates and previews without computing.

### Render a validation case end-to-end

Each case study renders the same bundle as arghel (ADR 0019). The one command
does the whole thing in the container; redirect it to a logfile under `logs/` and
poll that, since the background-shell harness does not capture container stdout
on Windows (`logs/` is a gitignored scratch folder, create it if missing):

```bash
mkdir -p logs
docker compose run -d --rm --name qmjob qm sh -c \
    'corrosim-run-study --case <name> --with-cubes > /work/logs/<name>.log 2>&1'
tail -f logs/<name>.log          # poll progress; rm the log once the job is done
```

The figure stage populates `fig0_pipeline.png` (the shared pipeline diagram) into
the bundle automatically: it copies the packaged asset, so no manual copy is
needed.

For a partial run or to debug one stage, drive the drivers directly: the QM
stages (detached, since the ESP cubes are slow) then the classical stages and the
render in the venv:

```bash
docker compose run -d --rm --name qmjob qm sh -c '{
    python -m corrosim.runs.run_dft    --case <name> &&
    python -m corrosim.runs.run_fukui  --case <name> &&
    python -m corrosim.runs.make_cubes --molecules "<mol1>,<mol2>" --what orbital,esp ;
  } > /work/logs/<name>.log 2>&1'
python -m corrosim.runs.run_mc       --case <name>
python -m corrosim.runs.run_md       --case <name>
python -m corrosim.runs.make_figures --case <name>
python -m corrosim.runs.make_report  --case <name>
```

`make_cubes` takes `--molecules` (not `--case`) and writes to the shared
`cubes/`; its basis stays small (`6-31G(d)` default, since cube shapes are
basis-insensitive). On a large, charge-dense molecule where the MEP integral
runs slow or low on memory, drop the grid (`--nx 60`) or skip ESP (`--what
orbital`). A render with no cubes/Fukui still succeeds: those figure sections
degrade gracefully to nothing rather than erroring.

A gotcha when adding a new case: if any molecule contains a heavier element
(Br, I), set the preset `basis` to a def2 set (`def2-SVP`): the engine's Pople
sets (`6-31G(d)`, `6-311++G(d,p)`) carry no bromine. `run_study` threads that
def2 basis into its Fukui and cube stages automatically, but the standalone
`run_fukui` / `make_cubes` keep their light `6-31G(d)` default and need an
explicit `--basis def2-SVP` for such a case, or they fail on the bromine.

A large, compact, oxygen-dense molecule can make the diffuse production basis
diverge (near-linear-dependence). The SCF now escalates on non-convergence
(level-shift + damping, then a second-order restart) before giving up, and a
run that still cannot converge **fails loud** (`SCFConvergenceError` naming the
molecule and level) rather than feeding garbage frontier orbitals into the
descriptors; the batch stops at that molecule. Respond by relaxing the geometry
first (`--optimize`) or dropping the preset to a less diffuse `basis`. To speed
(not fix) an intractable exact-integral SCF, opt into density fitting
(`--density-fit`, or the preset `density_fit` field): its `_cderi` tensor is
kept in RAM only while it fits the memory budget and otherwise spills to disk,
so point `PYSCF_TMPDIR` at the container's disk mount (not a RAM-backed `/tmp`)
and pin the budget with `--max-memory-mb` if auto-detection is off. Density
fitting shifts the numbers (RI approximation), so it stays off for the
production descriptors.

Every driver, `run_dft` included, now persists an unset output to
`cases/<name>/results/` by default (`run_dft` writes `dft_descriptors_ff` for
force-field geometries, `dft_descriptors_opt` for `--optimize`/`--to-minimum`
runs). The one exception is `run_dft --engine xtb`: the smoke numbers are not
reportable and share the production path, so that combination writes only when
`--out-csv`/`--out-json` is passed explicitly.

After any change to input data, regenerate the dependent artifacts in the same
change (see 4, Maintenance) and spot-check the diff, not just the file size.

## 3. Quality

Run the automated checks before every pull request; they also run in CI on
Python 3.10-3.12. Manual checks come last.

### 3.1 Tests (pytest)

The suite is deliberately QM-light (no DFT, xTB, or Docker), so it stays fast.
Run `pytest -q` in the venv. Every new feature or module ships a test named
`test_<unit>_<state>_<expected>`.

The full pipeline report (HTML + docx) is pinned by a golden in
`tests/test_report_golden.py` / `tests/goldens/` (the render-seam safety net,
ADR 0015 / #127). After an *intentional* report change, regenerate the goldens
and eyeball the diff before committing:
`UPDATE_GOLDENS=1 pytest -q tests/test_report_golden.py`.

### 3.2 Linting (ruff)

Run `ruff check .`. The line length is 80, and `C901` gates cyclomatic
complexity at 15 (ADR 0012). Keep new and edited code clean; do not
bulk-reformat untouched files. Ruff also enforces Google-convention docstrings
(`D` rules incl. `D417`; `D205` relaxed per ADR 0007). The full public API
contract (every public symbol documented, all public params/returns typed,
plus the no-trailing / no-ticket-number comment rules) is pinned by
`tests/test_docstrings.py` (not ruff `ANN`; ADR 0012).

### 3.3 Type checking (mypy)

Run `mypy`. It is non-strict but is a CI gate; run it before pushing, since
`ruff` alone does not catch type errors.

### 3.4 Cognitive complexity (complexipy)

Run `complexipy` from the repo root (config in `[tool.complexipy]`; threshold
15, same as `C901`, but counting nesting and control-flow interruptions rather
than branches, per ADR 0013). It ratchets against the committed
`complexipy-snapshot.json` watermark: an over-threshold function fails only
when it is new or has increased relative to the snapshot, so pre-existing
offenders are frozen, not exempted. A successful run rewrites the snapshot, so
when a refactor shrinks an offender, commit the tightened snapshot in the same
change. `complexipy --snapshot-ignore` lists the current offenders;
`--ignore-complexity --top 20` shows the package-wide picture.

### 3.5 QM tests (Docker)

Anything exercising the real engines runs in the container:
`docker compose run --rm qm pytest -q`. This is manual; CI does not run QM.

### 3.6 Coverage (pytest-cov)

Run `pytest --cov=corrosim --cov-report=term-missing`. Gated at 80% over a
*scoped* surface: the QM-engine modules and Docker-only drivers are `omit`-ted in
`[tool.coverage.run]` (they can't run in the venv), so the threshold measures the
QM-light-testable code (ADR 0007). A new pure-Python module is in scope by
default, so add a test. The scoped surface currently sits at ~85%.

### 3.7 Security & secrets (Bandit, gitleaks, CodeQL)

Three CI gates guard the supply/security surface:

- **Bandit** (SAST): `bandit -c pyproject.toml -r corrosim`. The only findings
  are the local QM-binary `subprocess` launches in `engines.py`, reviewed and
  marked `# nosec` at the call site (fixed argv, no shell).
- **gitleaks** (secrets): runs both as a `pre-commit` hook and a CI job. Install
  hooks once with `pre-commit install`; scan the tree with `pre-commit run
  --all-files`.
- **CodeQL** (platform SAST): `.github/workflows/codeql.yml`; findings surface in
  the repo Security tab.

### 3.8 Periodic audits: duplication & dead code

Duplication and dead code are review-time rules (`quality.md`: DRY, no dead
code), deliberately NOT CI gates: the tree measures clean, and both tools
false-positive on legitimate patterns (look-alike scientific/argparse
boilerplate; intentionally unused parameters in API signatures). What review
alone cannot catch is a pasted block whose twin lives outside the diff, so
sweep the whole tree at epic boundaries and release points:

```bash
pip install pylint vulture    # ad hoc, deliberately not dev deps
pylint --disable=all --enable=duplicate-code src/corrosim
vulture src/corrosim --min-confidence 80
```

File findings as tickets instead of fixing on the spot (scope guard).
Baseline 2026-07-04: two duplicate blocks (both covered by the per-module
refactor epic), zero dead-code findings at ≥80% confidence.

### 3.9 360-degree audit (whole-project health)

A strategic, multi-perspective review run periodically (before a release, after a
milestone, or when gauging readiness), distinct from the diff-level code review
and the duplication sweep above. Follow `360.md` and ADR 0035:

- Run role-isolated reviewers, one per perspective, each with a clean context.
  For this headless library and CLI, keep Value, Viability, and Discovery as light
  lenses and re-project Quality into engineering dimensions (Architecture, Code
  Quality, Testing, CI/CD, Security and Dependencies, Documentation).
- Run the quality gates green first (`pytest -q`, `ruff check .`, `mypy`,
  `PYTHONIOENCODING=utf-8 complexipy`) so the audit builds on a clean mechanical
  layer.
- Grade each dimension A-F; the overall grade is the lowest dimension.
- Persist the report at `docs/audits/YYYY-MM-DD-360.md` (the only audit location),
  with a scores table, an issues-created record, and a current-bottleneck section.
- File one tracked issue per finding under a tracking epic, then fold the issue
  numbers back into the report so it doubles as a durable backlog record.

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
  which produce the `cases/<case>/report/` bundle.
- After editing `docs/diagrams/pipeline.drawio`, re-export the pipeline diagram
  to **both** destinations (they must stay identical: the doc copy shown by
  `docs/pipeline.md` and the packaged `fig0` asset the figure stage copies into
  each bundle); commit the `.drawio` source and both PNGs together, then
  re-render the reports so each bundle picks up the new `fig0`:

  ```bash
  drawio -x -f png -s 2 -o docs/diagrams/pipeline.png                        docs/diagrams/pipeline.drawio
  drawio -x -f png -s 2 -o src/corrosim/report/assets/fig0_pipeline.png      docs/diagrams/pipeline.drawio
  ```

  If `drawio` is not on PATH, invoke the installed draw.io desktop app's CLI
  (`draw.io.exe --export --format png ...`) instead.
- Cross-check ranking and descriptor claims against `docs/validation.md` before
  reporting them. After a geometry or level-of-theory change, confirm the lead
  ranking is robust with `python -m corrosim.runs.compare_geometry`.

## 5. Release and deploy

corrosim ships as a downloadable **tool**, not a PyPI library or a notebook
(ADR 0027); PyPI and Colab were dropped deliberately. Two automated channels:

### Publish the image (release-on-tag)

`.github/workflows/release.yml` fires on a `v*` tag: it builds the `Dockerfile`,
smoke-runs it standalone (no bind mount), pushes
`ghcr.io/braboj/corrosim:<version>` + `:latest`, and cuts a GitHub Release with
the `docker run` instructions. The image tag is derived from the git tag
(`vX.Y.Z` -> `X.Y.Z`). To cut a release, bump the package version to match, land
it on a green `main`, then tag that commit:

```bash
# 1. bump `version` in pyproject.toml to X.Y.Z, land it on main (PR)
# 2. tag the merge commit (annotated) and push the tag
git tag -a vX.Y.Z -m "corrosim vX.Y.Z" && git push origin vX.Y.Z
```

Use an **annotated** tag (`-a`), not a lightweight one: it carries a tagger,
date, and message, and it is what every shipped release has used.

The GHCR package inherits the public repo's visibility, so it publishes
**Public** automatically; no manual visibility toggle is needed.

### The validation gallery (GitHub Pages)

`.github/workflows/pages.yml` deploys the case-report gallery on push to `main`
(path-gated to the report bundles + `report/gallery.py` + `runs/make_pages.py` +
`presets.py`). The reports are tracked, self-contained HTML, so it only copies
them and generates the index (ADR 0028). Build it locally to preview:

```bash
python -m corrosim.runs.make_pages --out _site   # then open _site/index.html
```

Live at `https://braboj.me/corrosim/` (the `braboj.github.io/corrosim/` URL
redirects there). One-time: enable Pages with Settings -> Pages -> Source =
GitHub Actions.

<!-- Generated with solid-ai-templates (github.com/braboj/solid-ai-templates) -->
