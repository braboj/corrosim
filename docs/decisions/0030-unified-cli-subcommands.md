# ADR 0030 — one `corrosim` CLI with subcommands

- Status: Accepted
- Date: 2026-07-15
- Relates to: ADR 0022 (full-study orchestrator); ADR 0026 (study as data);
  ADR 0023 (examples)

## Context

The tool shipped three separate console scripts: `corrosim` (the quick screen),
`corrosim-run-study` (the multiscale orchestrator), and `corrosim-add-inhibitor`
(the PubChem library tool). They are genuinely different programs — a one-shot
ranking function, a multi-stage pipeline with idempotency and plan mode, and a
data-maintenance utility — with almost disjoint argument surfaces (of ~24 flags
across the first two, only five are shared). But three top-level commands hurt
discoverability: a user has to know all three names, and there is no single
`--help` that lists what the tool can do.

A proposed alternative was one command with a mode flag (`corrosim --quick` /
`--full`). Rejected: it forces every flag onto one parser where most are
valid in only one mode (argparse cannot cleanly express "requires `--full`"),
and the output contracts clash — the screen writes one file, the study writes a
`cases/<name>/` directory tree.

## Decision

**One front door, `corrosim`, dispatching to three subcommands**, the git /
docker idiom:

```
corrosim screen ...         # quick reactivity screen + ranking
corrosim run-study ...      # full multiscale study for a case
corrosim add-inhibitor ...  # fetch a compound into the library
```

The dispatcher (`corrosim.app`) is a thin forwarder: it takes the first token as
the command and passes the remaining args verbatim to the existing module
`main()` — `cli.main`, `runs.run_study.main`, `fetch.main`. Each subcommand
module is **imported lazily**, only when its command is chosen, so a `screen`
run never pays the study's import cost and `add-inhibitor` stays
dependency-light. The subcommand `main()`s and their parsers are unchanged, so
each keeps its own focused `--help` and its own tests.

**Back-compat is preserved two ways.** A leading option routes to the screen, so
`corrosim --inhibitors ...` (the original bare-command form) keeps working. And
the `corrosim-run-study` / `corrosim-add-inhibitor` console scripts are kept as
aliases of the subcommands, so existing invocations — and the already-published
image's documented commands — do not break. `python -m corrosim` runs the
dispatcher too.

## Alternatives considered

- **Mode flag (`--quick` / `--full`) on one parser.** Rejected: flag-valid-by-mode
  confusion and the file-vs-directory output-contract clash (see Context).
- **argparse subparsers building all three parsers up front.** A cleaner unified
  `--help`, but it imports all three subcommand modules (and their transitive
  deps) to route any single command, losing the lazy-import property. The thin
  forwarder keeps each command's imports isolated; the small cost is a
  hand-written top-level usage instead of an argparse-generated one.
- **Rename the standalone scripts away.** Rejected: it breaks the published
  image's documented `corrosim-run-study` command. Aliases cost nothing.

## Consequences

- `corrosim <command> --help` and a bare `corrosim` now list the whole tool.
- The `corrosim` console script repoints to `corrosim.app:main`; the subcommand
  forms (`corrosim screen` / `run-study` / `add-inhibitor`) require this build
  (a native `pip install -e .`, or the next image). The alias scripts and the
  leading-option screen form work everywhere, including the current image.
- New surface is one small module plus its tests; no stage or engine code moves.

## Upstream

The kernel — *a single front-door command forwards to subcommands, each backed by
an existing entry-point main, imported lazily, with a leading-option back-compat
default and standalone aliases* — is generic CLI architecture, a sibling of the
thin-orchestrator-over-stage-commands pattern already raised on
`solid-ai-templates#755` (base/core/cli.md). Recorded there as a follow-up
comment.

<!-- Generated with solid-ai-templates (github.com/braboj/solid-ai-templates) -->
