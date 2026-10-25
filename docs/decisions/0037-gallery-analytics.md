# ADR 0037 — Count gallery page views with self-hosted Umami

- Status: Accepted
- Date: 2026-10-25
- Relates to: ADR 0028 (Pages validation gallery); ADR 0036 (corrosim.org)

## Context

corrosim.org serves the validation gallery: `index.html` plus a copy of each
case's self-contained `report.html`. There is no signal on whether anyone
reads it, which matters now that the domain is cited alongside the DOI.

The same reports are also tracked in `cases/<case>/report/` and generated
locally by users. A tracker in the report template would ship into every
offline report and phone home from a file a user opened on their own machine.

## Decision

**Add the self-hosted Umami tracker (`stats.imbra.io`, cookieless) to the
published site only, at Pages-build time.**

- `report.gallery.with_analytics` inserts one `<script>` before `</head>`;
  `assemble_site` applies it to the index and to each copied report.
- The tracked and locally generated reports are never modified.
- `data-domains="corrosim.org"` drops events from local previews of `_site`.
- Website ID `4d3a7c37-c6b1-409c-92f9-973099f8bc83`; Umami runs on the
  maintainer's lab server, exposed through a Cloudflare tunnel that serves only
  `/script.js` and `/api/send`.

## Consequences

- Page views per case report become visible without cookies or a consent
  banner; IP addresses are not stored by Umami.
- The gallery now loads one third-party-origin script; if `stats.imbra.io` is
  down the pages still render (`defer`, no dependency).
- Changing the tracker means editing one constant in `gallery.py`; the
  path-gated Pages workflow redeploys on that change.

## Upstream

Generic pattern: inject analytics into the published copy at deploy time, not
into the artifact generator, so artifacts users open locally never phone home.
Reusable but narrow; Upstream: none.
