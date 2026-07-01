# ADR 0007 — Reconcile the python-lib quality gates with QM-light testing

- Status: Accepted
- Date: 2026-07-01

## Context

The `python-lib` stack template (`templates/stack/python-lib.md`) mandates a
three-layer quality-gate model. Four of its gates were neither implemented nor
explicitly overridden in corrosim, leaving them as *silent* deviations
(issue #31):

1. `pytest-cov ≥ 80%` coverage gate.
2. Google-convention docstrings enforced via ruff `D` rules.
3. `pre-commit` + `gitleaks` secret scanning.
4. Bandit + platform SAST.

The tension is coverage. corrosim's suite is deliberately **QM-light** — no
DFT/xTB/Docker in CI, so it stays fast (CLAUDE.md §3). Global line coverage is
~48%, but that number is dragged down almost entirely by code that *cannot* run
in the venv/CI: the QM engine wrappers (`engines.py`, `fukui.py`) and the
Docker-only stage drivers (`run_dft`, `run_fukui`, `run_pka`, `make_cubes`). The
pure-Python scientific modules are already ~90–100%. A naïve global 80% gate
would therefore force a choice between abandoning QM-light (run QM in CI) and a
permanently red build.

## Decision

Adopt all four gates, scoping coverage to the QM-light-testable surface:

- **Coverage** — gate at 80%, but measured over a scoped denominator.
  `[tool.coverage.run] omit` excludes the QM-engine modules and Docker-only
  drivers (the code that needs PySCF/tblite/Docker); `[tool.coverage.report]
  fail_under = 80` enforces the threshold. New end-to-end fixture tests
  (`tests/test_pipeline_drivers.py`) drive the venv-runnable post-processing
  layer (`make_figures`/`make_report`/`compare_geometry`/`run_mc`/`run_md`)
  against the tracked `results/`, which also covers `figures.py`/`report.py`.
  Scoped coverage is ~85%.
- **Docstrings** — enable ruff `D` with `convention = "google"`. `D205`
  (blank-line-after-summary) is relaxed: corrosim docstrings lead with a long,
  formula-bearing sentence spanning several lines, so the one-line-summary rule
  does not fit; the rest of the convention is enforced. Presence is additionally
  pinned by `tests/test_docstrings.py` (issue #6).
- **Secrets** — keep the `gitleaks` pre-commit hook (Layer 2) and add a Layer-3
  `gitleaks` CI job.
- **Security** — add a Bandit CI job (`[tool.bandit]` config; the two local
  QM-binary `subprocess` launches in `engines.py` are reviewed and `# nosec`-ed
  at the call site) and a GitHub CodeQL workflow for platform SAST.

## Alternatives considered

- **Declare coverage as a deviation (no gate)** — simplest, but leaves the
  regression risk the template's gate exists to prevent.
- **Global 80% via a low ratchet (e.g. `--cov-fail-under=45`)** — keeps CI green
  but bakes the QM/driver dead weight into the number, so the gate never means
  "the tested code is well tested".
- **Run QM in CI to raise real coverage** — rejected: contradicts QM-light,
  and pyscf/tblite have no dependable CI wheels (they are pinned in the Docker
  image for exactly this reason).
- **Full `D205` enforcement** — would require rewriting ~33 dense scientific
  docstring summaries, risking corruption of the science for a formatting nicety.

## Consequences

- The four gates are now explicit and wired; no silent deviations remain.
- Coverage measures what the QM-light suite can actually exercise, so 80% is a
  meaningful, green, non-regressing floor. The omit list is the contract: a new
  pure-Python module is in scope by default and must be tested.
- Two documented, deferrable deviations remain (mirroring the `ruff format` /
  `mypy --strict` deferrals): `D205` relaxed, and coverage scoped rather than
  global. Both can be tightened later.
- The QM layer's correctness continues to rely on the QM test suite
  (`docker compose run --rm qm pytest`) and the tracked pipeline artifacts, not
  the fast CI suite.
