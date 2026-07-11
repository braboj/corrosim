# ADR 0020 — validation.md documents the approach, with a per-case status vocabulary

- Status: Accepted
- Date: 2026-07-11
- Relates to: ADR 0019 (report bundle per validation case); ADR 0010 (AI-authored
  report narrative); issue #53 (per-paper validation presets, closed); the
  reframe PR #196

## Context

`docs/validation.md` grew up as an Arghel document: the substrate, the
descriptors, the pKaH speciation, the experiment, and the "defensible claim" were
all Arghel's, and the other reproduced studies were appended under a "Multi-study
validation suite" heading that called Arghel "validation study #1". Once every
study ships its own report bundle (ADR 0019) and the suite has three peers,
Arghel is just the default preset, not a privileged reference. The document also
read as dense prose, and every case ended in a "Validated"-flavoured narrative
with no fixed, comparable outcome label.

## Decision

1. `validation.md` leads with the **validation approach**, not a case. The
   general principles (the level-of-theory ceiling, the FF-vs-opt geometry
   offset, the rule that `E_ads` / `ΔG°ads` / `E_bind` are non-interchangeable
   observables, and screening-as-a-hypothesis) are stated once at the top, and
   the three studies follow as peer cases (Arghel, phytic acid,
   pyrazolo-pyrimidine).
2. Each case carries a **status from a fixed vocabulary**: Validated, Partial,
   Rejected, Pending, with a `(qualitative)` or `(quantitative)` rigor qualifier,
   rendered as a plain emoji-and-text badge (no external service). Alongside it, a
   claim-by-claim **scorecard table** (claim / corrosim / reported / match) makes
   the verdict scannable. A validation document that can show Partial or Rejected
   is more credible than one that only ever says Validated.
3. An at-a-glance summary table and an ASCII diagram of what each pipeline stage
   is checked against front-load the whole comparison logic.

## Alternatives considered

- **Keep the Arghel-centric structure** rejected: it privileges the default
  study, buries the general principles inside one case, and treats the peers as an
  appendix.
- **Prose-only verdicts** rejected: dense to scan, no fixed vocabulary to compare
  two cases at a glance, and no honest slot for a refuted result.
- **Shields.io image badges** rejected: an external dependency that blanks out
  offline or in a plain Markdown viewer, whereas the emoji-and-text badge renders
  everywhere.

## Upstream

None. This is a results-presentation convention for a generated scientific
document (a fixed outcome vocabulary plus a scorecard per validated entity);
`solid-ai-templates` covers code, testing, and workflow conventions, not
generated-document or results-presentation structure. Same boundary recorded for
the report transpose and per-metric winner mark (session 21) and for ADR 0019.
