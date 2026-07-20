# ADR 0036 — Register corrosim.org as the project's canonical URL

- Status: Accepted
- Date: 2026-07-20
- Relates to: #321 (domain spike); #320 (Zenodo DOI + CITATION.cff); ADR 0028
  (Pages validation gallery)

## Context

corrosim is about to be cited in a paper. Its public entry point today is
`braboj.me/corrosim`, a project page under the maintainer's personal domain. A
personal-name subpath is fragile as a cited URL: if that domain lapses or is
rebranded the citation rots, and the URL is not obviously project-owned.

Two identifiers are in play and they are not interchangeable:

- The permanent, archival citation identifier is a Zenodo DOI (#320). It resolves
  through doi.org independently of any website and is what a journal should cite.
- A project domain is only a human-facing convenience URL. It is not required for
  citation and can be changed or dropped without affecting the DOI.

Availability checked 2026-07-20 (RDAP): `corrosim.org`, `.com`, `.net`, and
`.dev` are all unregistered.

## Decision

**Register `corrosim.org` as the project's canonical human-facing URL and point
the Pages gallery at it; keep the Zenodo DOI as the citation anchor.**

- TLD: `.org`, the convention for scientific and open-source projects and clean
  in a methods section. Optionally register `.com` defensively and redirect it.
- Registrar: Cloudflare Registrar (at-cost pricing, free DNS, CNAME flattening
  for the apex).
- Pages setup: set the custom domain on the corrosim repo (writes the CNAME
  file); point the apex at the four GitHub Pages A records
  (185.199.108-111.153) or CNAME-flatten to `braboj.github.io`; add a `www`
  CNAME to `braboj.github.io`; enable Enforce HTTPS. `braboj.me/corrosim` then
  redirects to the new domain, so existing links keep working.
- The paper cites the Zenodo concept DOI, not the domain. The domain stays a
  convenience and remains swappable.

Cost: about 10 to 15 USD/yr, renewable, held by the maintainer.

## Consequences

- The cited artifact's permanence rests on the DOI (#320), not on the domain, so
  the domain can lapse without breaking any citation.
- One recurring cost and a small DNS and renewal responsibility.
- `braboj.me/corrosim` keeps resolving through a redirect, so no existing link
  breaks.
- Accepted 2026-07-20: corrosim.org was registered (Namecheap), its DNS points at
  the GitHub Pages IPs (four A records on the apex, `www` CNAME to
  `braboj.github.io`), and it is set as the repo's Pages custom domain with a
  CNAME file pinned in the build. `braboj.me/corrosim` redirects to it. HTTPS is
  enforced once GitHub finishes provisioning the certificate.

## Upstream

Generic pattern: for a citable software artifact, mint a persistent identifier (a
DOI) as the canonical citation anchor and treat any vanity domain as a disposable
convenience, never the citation of record. This is reusable engineering guidance
independent of the specific domain. Upstream: `base/core/docs.md`
(software-citation guidance); issue: `braboj/solid-ai-templates#845`.
