# ADR 0010 — AI-authored report narrative is a dev-time pass, not a runtime dependency

- Status: Accepted
- Date: 2026-07-03

## Context

A client review found the `report/` bundle unclear: it stated computed numbers
and a ranking but did not explain its own terms (the z-score composite, the DFT
level, ESP vs Fukui, the Monte-Carlo methodology and software, why the geometry
is refined, how protonation is computed) or lead with a takeaway. The fix is
better *prose*, and an LLM (Claude, via the Claude Code CLI on the maintainer's
subscription) is an effective way to draft and polish it.

The question was **how** to wire that in without breaking three corrosim
invariants:

- **Free software only** (CLAUDE.md §1.1) — a runtime dependency on a paid Claude
  API/subscription would break it.
- **Reproducible, deterministic report** — CI builds `report/` and the tests
  assert on it; a build-time LLM call is non-deterministic and needs
  network/credentials CI does not have.
- **Scientific validity** — the report states computed values and ranking claims;
  an LLM must never alter a number or invent a claim.

## Decision

AI enhancement of the report is a **dev-time authoring pass**, not a runtime
step. The maintainer (or Claude Code acting as the dev-time author) rewrites the
report *narrative* for clarity, a human reviews the diff, and the result is
committed as **static content**. The shipped pipeline calls no LLM and stays
deterministic and free.

Concretely:

- The report narrative lives in `corrosim/report_content.py` and is **single-
  sourced** — both renderers (HTML `report`, Word `report_docx`) import it, so the
  two outputs read identically. Shared computed text (the z-score explanation, the
  data-derived "Bottom line") lives in shared functions there, not duplicated per
  renderer.
- An AI pass may only touch **prose**: it must not change any number, unit, or
  ranking claim, and every scientific statement is cross-checked against
  `docs/pipeline.md` / `docs/validation.md` before commit (CLAUDE.md §3).
- `make_report`, the tests, and CI never invoke an LLM.

## Alternatives considered

- **A runtime `make_report --ai-enhance` flag** that calls Claude at build time.
  Rejected: it makes the report non-deterministic, needs a paid subscription/API
  at run time (breaking "free software only"), cannot run in CI, and puts an LLM
  in the path of a scientific artifact where hallucination is unacceptable.
- **The Claude API (Anthropic SDK) as an optional dev extra** instead of the
  Claude Code CLI. Viable for scripting a repeatable pass (Opus 4.8 with prompt
  caching over the shared pipeline.md/validation.md context), but it bills per
  token and adds a paid dependency; the CLI on the maintainer's subscription
  covers the occasional authoring pass at no marginal cost. Left as a future
  option, not adopted.

## Consequences

- The report is clearer without adding any dependency: the base install, the
  tests, and CI are unchanged, and `report/` is still byte-reproducible from the
  committed data + narrative.
- Regenerating `report/` after a narrative edit is the existing venv step
  (`make_report`); the AI is upstream of that, at authoring time.
- Future narrative-clarity work follows the same loop: draft/polish with Claude
  Code → review the diff → verify no numbers changed → commit → regenerate. Do not
  add a runtime LLM call to the pipeline.
