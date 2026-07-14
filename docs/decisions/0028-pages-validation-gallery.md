# ADR 0028 — a validation gallery on GitHub Pages, generated from presets

- Status: Accepted
- Date: 2026-07-14
- Relates to: ADR 0006/0008 (report bundle layout); ADR 0023 (examples scope);
  ADR 0027 (tool-only distribution); epic #71, issue #68

## Context

The deployment epic's "see it" front door (#68): a zero-click way to look at a
finished result. The case reports are already tracked, self-contained HTML
(figures, CSS, and equations inlined), so "deploying" one is essentially copying
it. With the validation suite now spanning six published systems across Fe / Cu /
Al, the natural artifact is not one report but a gallery of all six.

## Decision

**Publish a static gallery to GitHub Pages that links each case's own
self-contained report, served as tracked, with no regeneration.** A `pages.yml`
workflow copies each `cases/<name>/report/report.html` into the site and writes a
generated `index.html`; no QM, no engines, no rebuild of the reports.

**Generate the index from `presets.CASE_STUDIES`.** The gallery reads each case's
metal / medium / molecules / source from the single source of truth, so a newly
added case appears automatically with no edit to the gallery. The validation
*verdict* (✅ / 🟡) is not structured data and does not belong on `CaseStudy`
(which holds screening *inputs*, not results), so it lives in a small explicit
status map in the generator, mirroring the scorecard in `docs/validation.md`.

**The design encodes the science.** On a white canvas, each card is accented by
its substrate metal (steel-blue Fe, copper Cu, aluminium Al) with a green
(validated) / amber (partial) status badge, and each names in full the published
study the case is validated against, so the gallery reads as corrosim's own
results checked against the literature. The page is self-contained static HTML
(one web-font link), white-default with a dark variant, and degrades gracefully
without the fonts or `color-mix`.

**Path-gated deploy.** `pages.yml` runs on push to `main` only when a report
bundle, the generator, `presets`, or the workflow changes, so unrelated commits
do not redeploy. One deploy at a time (concurrency group), superseded by a newer
push.

## Consequences

- Live at `https://braboj.github.io/corrosim/`, linked from the README.
- New code: `src/corrosim/report/gallery.py` (the generator) and
  `src/corrosim/runs/make_pages.py` (the driver: `python -m
  corrosim.runs.make_pages --out _site`); `_site/` is gitignored (a CI artifact).
- A case with no rendered report yet is skipped, so the index never links a
  missing file.
- **One-time manual step:** enable Pages with Settings -> Pages -> Source =
  GitHub Actions; the workflow cannot flip that switch (sibling of the "set the
  GHCR package public" step in ADR 0027).
- Non-goals: the reports are served as tracked (no CI regeneration); no per-case
  interactivity. Slimming the 4-6 MB self-contained reports is a separate task.

## Upstream

The transferable kernel (*generate a static index from the config registry and
serve already-self-contained artifacts on Pages, with no regeneration*) is a
generic docs/CI-CD convention, a sibling of the examples README-index
(`solid-ai-templates#816`) and the release-on-tag publish (`#817`). Recorded in
`docs/engineering-know-how.md`.
