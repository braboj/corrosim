# ADR 0027 — distribution: tool-only, release-on-tag to a GHCR image

- Status: Accepted
- Date: 2026-07-14
- Relates to: ADR 0022 (full-study orchestrator); ADR 0024 (QM image drift
  guard); ADR 0026 (study as data); epic #71, issue #67

## Context

The deployment epic (#71) framed three front doors: Colab (run it, #66), Pages
(see it, #68), and GHCR/PyPI (install it, #67). Issue #67 as written published
*both* a container image to GHCR *and* the package to PyPI.

Two facts narrow this. First, the product decision: ship corrosim as a
downloadable tool, not a PyPI library and not a collaboration notebook. Second,
the hard constraint that has shaped the whole project: the DFT/xTB engines
(pyscf, tblite, geometric) have no Windows wheels, and PySCF has no native
Windows support, so a `pip install` or a standalone binary cannot run the
pipeline cross-platform. The image already bundles every engine and build-smokes
its imports (ADR 0024); it *is* the all-in-one runnable tool. What was missing
was publishing it.

## Decision

**Distribute as one published image, `ghcr.io/braboj/corrosim`, tool-only.** A
`release.yml` on a `v*` tag builds the `Dockerfile`, smoke-runs it, pushes
`:<version>` + `:latest`, and cuts a GitHub Release carrying the `docker run`
instructions. A user runs the whole DFT -> report pipeline with only Docker
installed.

**Drop PyPI (Part B of #67) and Colab (#66).** A tool whose core needs the
container gains little from a separate PyPI library split, and Colab's value (it
is Linux, so `pip` pulls the engines) pulls against the tool-only framing. Both
are recorded as won't-do for this product direction, not deferred.

**Smoke the image in the standalone configuration the user runs.** The dev and
CI smoke (ADR 0024) overlays the repo at `/work` via a bind mount, which never
exercises the *no-mount* path a published-image user takes. `release.yml` runs
`corrosim-run-study --case arghel --plan` with **no volume**, so the console
script must resolve the baked `/work/src` and the orchestrator must run standalone
or the release fails before the push. Outputs reach the host by mounting only
`cases/` (`-v "$PWD/cases:/work/cases"`); never mount over `/work`, which would
shadow the baked `src/` and break the import.

**Image name `corrosim`, not `corrosim-qm`.** It is the one download-and-run
tool, so the public name carries no engine-suffix. The local `docker compose`
build keeps the `corrosim-qm` image name (a dev artifact, unchanged), so nothing
in the container dev workflow moves.

**One-time registry step.** After the first release, set the GHCR package to
Public in its package settings; `GITHUB_TOKEN` can push the image but cannot flip
package visibility.

**Non-goals.** No PyPI, no Colab, and amd64 only for now (the pyscf/tblite Linux
wheels; multi-arch is a later change if demand appears). Pages (#68) stays the
cheap follow-up: the report bundle is already self-contained HTML.

## Consequences

- A clean machine with only Docker runs the full study:
  `docker run --rm -v "$PWD/cases:/work/cases" ghcr.io/braboj/corrosim
  corrosim-run-study --case arghel`.
- The study-as-data feature (ADR 0026) makes the same image screen a user's own
  inhibitors/metal/medium, via a mounted `--case study.json` or the
  `--name/--molecules/...` flags, with no rebuild.
- Cutting a `v*` tag is now a release action: tag from a green `main`.
- The README gains a Docker download-and-run section; issue #67 is re-scoped to
  GHCR-only and #66 is closed as won't-do.

## Upstream

The transferable kernel (*release-on-tag builds, smoke-runs, and pushes a
runnable image, and the smoke must exercise the standalone configuration a user
actually runs — not the dev bind-mount configuration*) is generic CI/CD, a
sibling of the container drift-guard already filed as `solid-ai-templates#817`
(base/infra containers + cicd). Recorded in `docs/engineering-know-how.md` and
added as a comment on that issue.
