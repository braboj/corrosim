# ADR 0024 — QM image drift guard: layout-explicit import + packaging-gated CI rebuild

- Status: Accepted
- Date: 2026-07-13
- Relates to: ADR 0011 (src/ layout migration, the trigger); the `corrosim-qm`
  container and `docker-compose.yml`

## Context

The QM engines (pyscf, tblite) have no Windows wheels and run only in the
hand-built `corrosim-qm` image, which installs the package editable
(`pip install -e`) and bind-mounts the repo over `/work` at runtime. An editable
install bakes an absolute finder path into the image at build time. When the
package moved from the repo root to `src/` (ADR 0011), that baked path
(`/work/corrosim`) pointed at a directory that no longer existed, so `import
corrosim` failed even though the live code was present under the bind mount, and
every QM run needed a `-e PYTHONPATH=/work/src` (plus `MSYS_NO_PATHCONV=1` on Git
Bash) override to paper over it.

The immediate breakage was rebuilt away by hand, but the failure mode stayed
open: the image is not exercised by the main test suite (its heavy deps only
exist in the container), so nothing forced a rebuild when the layout changed. It
silently bit every new session until someone rebuilt.

## Decision

Close the drift at its source and guard against recurrence, on two layers.

**Resolve the package by its `src/` location, not the baked finder.** The
Dockerfile sets `ENV PYTHONPATH=/work/src`, so the runtime import resolves by the
live bind-mounted location instead of the frozen editable-finder path. The import
no longer depends on a build-time snapshot, so it cannot go stale when the layout
moves; the per-run workaround is retired.

**Fail the build loudly.** A build-time `RUN python -c "import corrosim, pyscf,
tblite"` step makes any broken image fail the build rather than ship silently.

**Rebuild the image in CI on any packaging change.** A new `qm-image.yml`
workflow rebuilds and import-smokes the image, path-gated to the files that
change the image contract (`Dockerfile`, `pyproject.toml`, `docker-compose.yml`,
`.dockerignore`, the workflow itself). It stays off the hot path of every PR but
catches structural drift before merge.

## Consequences

- The `PYTHONPATH` + `MSYS_NO_PATHCONV` workaround is no longer needed for a
  routine QM run; a plain `docker compose run --rm qm ...` resolves the package.
- Any packaging or layout change re-verifies the image in CI before merge, so the
  image can no longer drift from the layout unnoticed.
- The new job is not yet a required status check; to make it a merge gate it must
  be added to branch protection (a repo setting, not in the diff).
- The build-time import check adds a few seconds to every image build, local or
  CI, which is the point (a broken build is caught immediately).

## Upstream

The transferable kernel (*an editable install baked into a bind-mounted image
should resolve by an explicit source path, not the build-time-frozen finder;
and a hand-built image the test suite never exercises should be rebuilt by a
packaging-change-gated CI job so it cannot drift from the layout*) is generic
container/CI engineering, domain-free. Recorded in
`docs/engineering-know-how.md` and filed upstream against
`base/infra/containers.md` + `base/infra/cicd.md` as `solid-ai-templates#817`.
