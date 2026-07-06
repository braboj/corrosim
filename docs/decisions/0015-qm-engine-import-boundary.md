# ADR 0015 — QM engine-import boundary (the qm package owns pyscf/tblite)

- Status: Accepted
- Date: 2026-07-06
- Relates to: ADR 0011 (src layout + subsystem packages), ADR 0014 (restraint)

## Context

pyscf, tblite and geomeTRIC ship no Windows wheels, are the optional `qm` pip
extra, and run only inside the corrosim-qm Docker image (CLAUDE.md §1.3). Their
imports were correctly deferred — but **scattered across ~8 functions** in
`engines.py`, `fukui.py` and `figures.py` (`from pyscf import dft, gto`,
`pyscf.hessian`, `pyscf.geomopt`, `pyscf.tools.cubegen`, `tblite.interface`), so
the dependency was invisible at a glance and a friendly "install the extra" error
would have to be repeated at each site.

Two pieces of QM *production* had also leaked out of the qm package: the cube
writers (each runs a DFT SCF then `pyscf.tools.cubegen`) lived in
`report/figures.py`, and the protonation-site selector was
`run_dft._best_protonation_site` — a `_`-private symbol reached across modules by
`run_pka` (public in disguise).

## Decision

**All pyscf/tblite-touching code lives in the `qm` package; `report` and `runs`
consume it and never import a QM engine directly.**

- Every deferred pyscf/tblite import is concentrated behind two private backend
  modules, `qm/_backend_pyscf.py` and `qm/_backend_tblite.py`: each imports its
  deps at the module top and is itself imported lazily, so a call path collapses
  to a single `from . import _backend_pyscf` (then `_pyscf.gto` / `.thermo` /
  `.cubegen`). A `try/except ModuleNotFoundError` at each backend top turns a
  missing extra into a "runs only in the corrosim-qm image" hint instead of a
  bare import error. `import corrosim` still pulls in no QM extra.
- Cube writing moves from `report/figures.py` to `qm/cubes.py`; `report/figures`
  is now pure rendering (RDKit/ASE/matplotlib/scikit-image reading `.cube`
  files). Protonation-site selection is promoted to public
  `qm/protonation.py::best_protonation_site`, with its stderr logging separated
  behind an injected `log` callback so the library stays print-free.
- The engine function **bodies** (`build_rks`, `run_pyscf`, `optimize_geometry`,
  `thermo_correction`, `run_xtb`) **stay in `engines.py`**, not the backends.

## Alternatives considered

- **Hoist pyscf/tblite to module top** — rejected: breaks `import corrosim` in
  the venv and Linux CI, where the whole non-QM pipeline (and its tests) runs.
- **Keep the per-function scattered deferrals** — rejected: the dependency is
  not declared in one place and the container-hint guard must be repeated.
- **Move the engine bodies into the backends (Option C)** — rejected on
  restraint (ADR 0014). `run_dft`/`run_pka` import `optimize_geometry` /
  `thermo_correction` at module top and the tests monkeypatch them there, so
  those names must live in a module that does **not** eager-import pyscf. Moving
  the bodies would therefore force thin forwarding wrappers in `engines.py` that
  duplicate the full signature + Google docstring (ADR 0012) — ceremony for a
  marginal gain: `engines.py` is not near the complexity ratchet and the import
  consolidation above already delivers the readability win.
- **Put `best_protonation_site` in `molecules.py`** — rejected: it calls
  `run_engine`, so a leaf value-object module would import the qm layer and
  invert the dependency direction.

## Consequences

- pyscf / tblite / geomeTRIC enter through exactly two greppable, guarded
  modules; `report/figures.py` and the report layer are pyscf-free; the
  `run_pka → run_dft` cross-driver import is gone.
- New QM-touching code belongs in `qm/`; `report` and `runs` stay consumers.
- Each backend module imports every pyscf submodule the pipeline uses
  (dft/gto/solvent, geomopt, hessian, tools), so loading it couples
  geometry-opt + cubegen availability to any pyscf path. Acceptable: the `qm`
  extra bundles all three and they are only ever present together (the
  corrosim-qm image).
- `engines.py` keeps the engine bodies; if they ever must move, the
  forwarding-wrapper cost is re-weighed then.
