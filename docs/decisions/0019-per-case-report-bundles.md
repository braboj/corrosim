# ADR 0019 — Render a report bundle per validation case (revises ADR 0018)

- Status: Accepted
- Date: 2026-07-10
- Relates to: ADR 0018 (per-case output namespacing) — this revises 0018's
  rejected alternative; ADR 0016 (report render seam); issue #183 (render every
  validation case study); issue #53 (per-paper validation presets)

## Context

ADR 0018 namespaced outputs under `cases/<case>/results/` and
`cases/<case>/report/`, but explicitly **rejected** rendering a full HTML/DOCX
report bundle per validation study: "validation's deliverable is the comparison
table in `docs/validation.md`; rendering an HTML/DOCX bundle per study
multiplies tracked artifacts for little gain."

Experience with the first reproduced studies argued the other way. A validation
case's evidence is not only the descriptor numbers — it is the frontier-orbital
isosurfaces, the electrostatic-potential maps, the Fukui donor sites, the
adsorption poses, and the radial distribution functions. `docs/validation.md`
records the numeric comparison; it cannot show a reviewer *why* a molecule
adsorbs the way it does. The shipped `arghel` study already ships a full bundle,
so withholding one from every other case is also inconsistent.

## Decision

**Each validation case renders and tracks its own report bundle**, identical in
shape to `arghel`: `cases/<case>/report/report.html` + `report.docx` +
`figures/<stage>/` + `tables/<stage>/`, produced by `make_figures` +
`make_report --case <name>`. `docs/validation.md` stays the cross-study
comparison home (computed-vs-reported, one section per paper); the per-case
bundle is the detailed evidence behind that row.

ADR 0018's output namespacing already routes every driver's output to the right
`cases/<case>/` subtree, so no new plumbing is needed — only the policy flips
from "table only" to "table plus bundle."

## Alternatives considered

- **Keep ADR 0018's table-only rule** — rejected: it hides the qualitative
  evidence (isosurfaces, ESP, RDF) that a validation reviewer most wants to see,
  and it leaves `arghel` inconsistently privileged as the only case with a
  bundle.
- **One shared multi-study report** — rejected: studies use different substrates,
  media and levels of theory; a single merged report blurs them, whereas a
  per-case bundle can be browsed, shared, or removed as a unit (the same reason
  ADR 0018 co-locates outputs).

## Consequences

- Tracked artifacts grow by one bundle per case (accepted: the evidence is worth
  the bytes; bundles are self-contained and regenerable).
- Implemented for `arghel` and `pyrazolo-pyrimidine`; `phytic-acid` remains
  unrendered and is the open work under issue #183, which this ADR resolves the
  *policy* half of (the remaining half is the compute-and-render pass).
- The `.gitignore` report allowlist (`!cases/*/report/report.html`, from ADR
  0018) already tracks each bundle; cubes and logs stay ignored.

## Upstream

None. This is a generated-report artifact policy for a scientific reporting
tool (evidence bundle per entity alongside a central comparison document);
`solid-ai-templates` covers code, testing, and workflow conventions, not
generated-report structure, so there is no template home for it.
