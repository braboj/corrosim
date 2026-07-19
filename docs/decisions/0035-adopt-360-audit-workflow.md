# ADR 0035 — Adopt the 360-degree audit workflow and docs/audits/ storage

- Status: Accepted
- Date: 2026-07-19
- Relates to: the `base-360` template in the `solid-ai-templates` submodule; the
  end-of-session scope guard (`scope.md`)

## Context

corrosim's convention chain (the CLAUDE.md header) referenced the base core and
workflow templates but not `workflow/360.md`, and the project had no defined home
for a periodic whole-project health check. A code review checks a diff and the
structure audit checks completeness, but neither steps back to grade the project
from the user, engineer, analyst, and marketer perspectives at once. The
`base-360` template prescribes exactly that: role-isolated reviewers, letter
grades A-F, an overall grade equal to the lowest dimension, and a report persisted
at `docs/audits/YYYY-MM-DD-360.md` (the sole location for audit history).

The trigger was the first such audit, run against v0.4.0. It surfaced 69 findings,
none higher than Minor, and needed a durable home rather than living only in the
session transcript.

## Decision

**Adopt `base-360` as a corrosim convention.** A 360-degree audit persists its
report at `docs/audits/YYYY-MM-DD-360.md`, one dated file per run, and
`workflow/360.md` is added to the referenced template chain.

- **Headless adaptation.** corrosim is a library and CLI with no user-facing web
  surface, so the template's headless variant applies: Value, Viability, and
  Discovery are kept as light lenses, and Quality is re-projected into engineering
  dimensions (Architecture, Code Quality, Testing, CI/CD, Security and
  Dependencies, Documentation), one context-isolated reviewer each. The overall
  grade is the lowest dimension grade.
- **One issue per finding.** Each actionable follow-up is filed as its own tracked
  issue, grouped under a tracking epic, and the issue numbers are folded back into
  the persisted report so the document is self-contained and every finding traces
  to open work.
- **Prose conventions win.** The report is written to the project's own prose
  rules (no em-dashes, no horizontal-rule dividers), not the template's house
  typography.

## Consequences

- A new top-level `docs/audits/` directory holds the audit history; the first
  report is `docs/audits/2026-07-18-360.md` (overall grade B, Discovery-limited;
  engineering and product body A-/B+).
- That audit's follow-ups were filed as #296-#307 under epic #308.
- corrosim's pytest suite does not wire the submodule's `SYS-07` smoke check that
  enforces the `docs/audits/` location; the convention is upheld by this ADR and
  review, not an automated gate. Wiring an equivalent check is a candidate
  follow-up only if the location drifts.
- The audit is periodic (before a release, after a milestone, or when evaluating
  readiness), not an every-session step; the end-of-session checklist only appends
  the dated report when an audit was run.

## Upstream

Generic pattern: a project should submit to a periodic multi-perspective health
audit whose report is a durable, dated, version-controlled artifact, and each
finding should become a tracked issue rather than living in a transcript. This is
already upstream in full: it is the `base-360` template itself, plus the
submodule's own audit-storage decision. This ADR records downstream adoption, so
there is no new generic pattern to file. Upstream: `workflow/360.md` (already
upstream); issue: none.
