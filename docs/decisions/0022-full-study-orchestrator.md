# ADR 0022 — one orchestrator driver for the full multiscale study

- Status: Accepted
- Date: 2026-07-13
- Relates to: ADR 0014 (pipeline-stage module shape); ADR 0015 (QM engine import
  boundary); ADR 0018 (per-case output namespacing); ADR 0011 (subsystem
  packages)

## Context

The quick screen is one command (`corrosim --inhibitors ... --engine xtb`). The
full multiscale study was not: it required hand-running the stage drivers
(`run_dft`, `run_fukui`, `run_mc`, `run_md`, optionally `run_pka` / `make_cubes`,
then `make_figures`, `make_report`) in dependency order, across the QM container
(pyscf/tblite) and the venv, with non-obvious gotchas: some drivers persisted
only with an explicit `--out`, and `make_report` silently dropped the sections
whose inputs were missing, so a wrong order yielded a quietly incomplete report.
The order and the QM-vs-venv split lived only in the PLAYBOOK, enforced nowhere.

This is a barrier to using the tool and error-prone even for maintainers.

## Decision

Add a single orchestrator driver, `runs/run_study` (console script
`corrosim-run-study`, also `python -m corrosim.runs.run_study`), that runs the
stages in dependency order for a `--case`. Three principles:

- **Orchestrate, do not reimplement.** Each stage is a thin runner that calls the
  existing driver `main()` with the case's own output routing (ADR 0018), so no
  paths are threaded and no stage logic is duplicated. The orchestrator owns
  order and selection; the drivers stay the single source of each stage's
  behaviour.
- **One environment.** The `corrosim-qm` image already carries both the QM and
  the classical dependencies, so the whole study runs in one container
  invocation. The orchestrator does not switch environments; it groups stages by
  environment only for the plan display and a reminder.
- **A declared, inspectable pipeline.** Stages are an ordered table of records
  (key, environment, default-on, idempotent, and callables for describe / run /
  outputs). Selection (`--only` / `--skip`), enrichment opt-ins (`--optimize`,
  `--with-pka`, `--with-cubes`), a `--plan` dry run (mirroring `corrosim --plan`),
  and an idempotent skip keyed on each stage's declared outputs (`--force` to
  recompute) all sit on top of that one table.

Default-on core: `dft → fukui → mc → md → figures → report`. Opt-in enrichments:
`pka`, `cubes`, and the DFT-relaxed matrix (`--optimize`). The terminal render
stages (figures, report) declare no skip outputs, so they always re-run and the
bundle tracks the latest data.

Each runner imports its driver lazily, so `--plan` (and a venv install without
the QM engines) pays no QM or matplotlib import cost for a stage it will not run,
the same defer-past-`--plan` shape as `corrosim`'s CLI (ADR 0015).

## Consequences

- The full study collapses to `docker compose run --rm qm corrosim-run-study`;
  the PLAYBOOK's multi-command recipe becomes the fallback / advanced path.
- The stage table is the one place order, environment, and outputs are declared;
  a new stage is one record plus a runner, and the plan/skip/selection logic
  needs no change.
- Idempotent skip makes a study resumable: a failed or partial run re-uses the
  stages already on disk and continues.
- `run_dft` now auto-persists (its own fix), and the orchestrator supplies
  `run_pka`'s output path, so no stage is silently computed-and-discarded.
- The orchestrator is covered by a QM-light test that mocks the stage `main()`s
  and asserts selection, order, the `--plan` output, idempotent skip, and
  stop-on-failure, consistent with the no-Docker suite.

## Upstream

The transferable kernel (*when a multi-stage pipeline is already exposed as N
independent stage commands, add a thin orchestrator that invokes each stage's
existing entry point in dependency order rather than reimplementing the flow, and
layer a dry-run plan, an idempotent skip keyed on each stage's declared outputs,
and stage selection on top*) is a reusable CLI/workflow pattern. Recorded in
`docs/engineering-know-how.md` and contributed upstream to
`solid-ai-templates#755` (the `base/core/cli.md` proposal), alongside the
`--plan` dry-run and persist-by-default (`#815`) CLI conventions it composes
with.
