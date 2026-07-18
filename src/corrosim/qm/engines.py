"""corrosim.engines.

Uniform wrappers around the two quantum engines used by the tool.

  * 'xtb'   -> GFN2-xTB via tblite. Sub-second, great for screening/ranking.
  * 'pyscf' -> real DFT (default B3LYP). Minutes per molecule; use for the
              final, publication-grade descriptors.

Both return the same EngineResult so the rest of the pipeline is
engine-agnostic. Energies in the result are reported in eV.
"""
from __future__ import annotations

import os
import subprocess  # nosec B404
import tempfile
import uuid
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from ase.data import atomic_numbers

# A molecular geometry: (x, y, z) triples in Angstrom (or an ndarray).
Coords = Sequence[Sequence[float]]

HARTREE_TO_EV = 27.211386245988
ANG_TO_BOHR = 1.8897259886

# One atomic unit of dipole moment (e·a0) in Debye (CODATA), used to report the
# xTB dipole (returned in atomic units) on the same Debye scale as PySCF.
AU_TO_DEBYE = 2.541746473

# ddCOSMO's built-in water dielectric; set explicitly so a solvent change is
# visible at the call site rather than buried in a PySCF default.
WATER_EPS = 78.3553

# An orbital counts as occupied above this occupation number — 0.5 cleanly
# splits filled (~2 e-) from empty for both the xTB and ORCA outputs.
OCCUPIED_MIN = 0.5


def require_virtual_orbital(occ: object) -> None:
    """Fail loud when a molecule has no virtual (LUMO) orbital.

    A fully occupied system — a single atom in a minimal basis, or any case
    where every orbital is filled — has no unoccupied orbital, so referencing
    the LUMO (``homo + 1`` on the sorted energies, ``mo[occ == 0]``, the LUMO
    cube) would otherwise raise an opaque IndexError/ValueError deep in the
    engine. Guard it once with a message that names the cause.

    Args:
        occ: The per-orbital occupation numbers (any array-like).

    Raises:
        ValueError: If no orbital is unoccupied.
    """
    if not np.any(np.asarray(occ) <= OCCUPIED_MIN):
        raise ValueError(
            "no virtual (LUMO) orbital: the molecule is fully occupied at "
            "this basis, so no LUMO-derived quantity can be computed.")


def dipole_magnitude_debye(
    vector: Sequence[float] | None,
    *,
    in_atomic_units: bool,
) -> float | None:
    """Magnitude of a dipole-moment vector, in Debye.

    Args:
        vector: The (x, y, z) dipole components, or None when the engine did
            not report a dipole.
        in_atomic_units: True when ``vector`` is in atomic units (e·a0, as
            tblite returns it) and must be scaled by :data:`AU_TO_DEBYE`; False
            when it is already in Debye (as PySCF's ``dip_moment`` returns it).

    Returns:
        The dipole magnitude in Debye, or None when ``vector`` is missing or has
        fewer than three components.
    """
    if vector is None:
        return None
    arr = np.asarray(vector, dtype=float).ravel()
    if arr.size < 3:
        return None
    magnitude = float(np.linalg.norm(arr[:3]))
    return magnitude * AU_TO_DEBYE if in_atomic_units else magnitude

# PySCF encodes an imaginary vibrational mode as a negative real part or a
# non-zero imaginary part; this tolerance rejects the numerical-noise imaginary
# component of a genuine real mode.
IMAG_FREQ_TOL = 1e-6

# How relax_to_minimum drives a floppy geometry to a verified minimum: a finer
# DFT integration grid (level 4) plus imaginary-mode-displaced restarts. Named
# once so both drivers' geometry-provenance strings stay in step.
MIN_RECIPE = "grid 4, imag-mode refined"

# SCF convergence aids applied only when the default DIIS path fails. A static
# level shift lifts the virtual orbitals to damp the DIIS oscillation that
# diffuse-basis near-linear-dependence provokes; density damping mixes
# successive Fock matrices toward the same end; the extra cycles give the aided
# iteration room to settle.
SCF_LEVEL_SHIFT_HARTREE = 0.2
SCF_DAMP_FACTOR = 0.5
SCF_HARD_MAX_CYCLE = 200

# Memory-budget resolution and the density-fitting guard. The env override lets
# a caller pin the SCF memory budget; the headroom fraction leaves room for the
# Python/PySCF working set on top of the detected limit; the floor keeps a tiny
# cgroup from starving the SCF.
MEMORY_BUDGET_ENV = "CORROSIM_MAX_MEMORY_MB"
MEMORY_HEADROOM = 0.8
MEMORY_FLOOR_MB = 1000
DEFAULT_MEMORY_MB = 3500

# Density-fitting _cderi sizing. The tensor holds naux x (nao pairs) doubles;
# naux runs ~3x nao for a typical auxiliary basis. Keep it in RAM only below the
# in-core fraction of the budget, spill it to disk beyond that, and refuse a
# basis whose tensor tops the hard ceiling even on disk.
CDERI_NAUX_RATIO = 3.0
BYTES_PER_DOUBLE = 8
CDERI_INCORE_FRACTION = 0.5
CDERI_CEILING_GB = 50.0


@dataclass
class EngineResult:
    """Engine-agnostic single-point result (all energies in eV)."""

    # Engine identity: backend name and its theory level
    # (e.g. "GFN2-xTB" or "B3LYP/6-31G")
    engine: str
    level: str

    # Single-point energies (eV)
    e_total_ev: float
    homo_ev: float
    lumo_ev: float

    # Per-atom Mulliken partial charges, if the engine provides them
    charges: list[float] | None = None

    # Ground-state dipole-moment magnitude (Debye), if the engine reports it —
    # a polarity descriptor independent of the HOMO-LUMO gap.
    dipole_debye: float | None = None

    @property
    def gap_ev(self) -> float:
        """HOMO–LUMO gap.

        Returns:
            The HOMO–LUMO gap (eV).
        """
        return self.lumo_ev - self.homo_ev


# --- Shared PySCF / thermochemistry helpers -------------------------------

class SCFConvergenceError(RuntimeError):
    """An SCF failed to converge after every robustness fallback was tried."""


def _shift_and_damp(mf):
    """Second attempt: level-shift + damping + a longer cycle budget."""
    mf.level_shift = SCF_LEVEL_SHIFT_HARTREE
    mf.damp = SCF_DAMP_FACTOR
    mf.max_cycle = SCF_HARD_MAX_CYCLE
    mf.kernel()
    return mf


def _second_order(mf):
    """Final attempt: a second-order (Newton) restart from the best density."""
    # SOSCF re-solves the same mean field, seeded from the density reached so
    # far; far more robust than DIIS once it has a decent guess
    mf_so = mf.newton()
    mf_so.kernel(dm0=mf.make_rdm1())
    return mf_so


# Ordered escalation: each fallback runs only if the prior attempt did not
# converge, cheapest and least intrusive first.
_SCF_FALLBACKS = (_shift_and_damp, _second_order)


def run_scf(mf: Any, label: str | None = None, strict: bool = True) -> Any:
    """Kernel a mean field, escalating on non-convergence, or fail loud.

    The single home for "converge this SCF or say so". Run the default DIIS
    kernel, then while it has not converged walk the fallback ladder
    (level-shift + damping, then a second-order Newton restart). The ladder
    fires *only* when the cheap path fails, so a normally-converging single
    point is numerically untouched; it exists to rescue the diffuse-basis SCFs
    that oscillate or diverge, and to refuse to hand back an unconverged mean
    field as if it were a real result.

    Args:
        mf: An unkerneled PySCF mean-field object (from :func:`build_rks`).
        label: A level-of-theory / molecule label woven into the error, so a
            failure names what would not converge.
        strict: Raise on final non-convergence (the default); pass False to
            warn and return the best-effort mean field instead.

    Returns:
        The converged (possibly Newton-wrapped) mean field; call sites read
        ``e_tot`` / ``mo_energy`` / ``mo_occ`` off it.

    Raises:
        SCFConvergenceError: If ``strict`` and no fallback converged.
    """
    mf.kernel()
    for apply_fallback in _SCF_FALLBACKS:
        if mf.converged:
            return mf
        mf = apply_fallback(mf)
    if mf.converged:
        return mf
    where = f" for {label}" if label else ""
    if strict:
        raise SCFConvergenceError(
            f"SCF did not converge{where} after level-shift/damping and a "
            "second-order restart; try a less diffuse basis or a finer grid.")
    warnings.warn(
        f"SCF did not converge{where}; returning the best-effort mean field.",
        stacklevel=2)
    return mf


# --- Memory guard: budget resolution + density-fitting _cderi sizing -------

@dataclass(frozen=True)
class MemoryPlan:
    """How an SCF fits its memory budget (see :func:`plan_scf_memory`)."""

    # Run with density fitting (RI) at all
    density_fit: bool

    # Hold the _cderi tensor in RAM (True) vs stream it from disk (False)
    incore: bool

    # Budget to stamp on ``mol.max_memory`` (MB)
    max_memory_mb: int

    # Spill the _cderi tensor to the scratch directory on disk
    cderi_to_disk: bool


def estimate_cderi_gb(nao: int, naux_ratio: float = CDERI_NAUX_RATIO) -> float:
    """Estimate the density-fitting ``_cderi`` tensor size in gigabytes.

    The RI three-index tensor holds ``naux`` x ``nao*(nao+1)/2`` doubles, with
    the auxiliary-basis size ``naux`` running a few times ``nao``. This is the
    tensor that OOM-crashes a small container when held in RAM, so its size
    drives the in-core / disk-spill decision.

    Args:
        nao: Number of atomic orbitals (basis functions).
        naux_ratio: Auxiliary-to-orbital basis size ratio (~3 is typical).

    Returns:
        The estimated tensor size in gigabytes (decimal, 1e9 bytes).
    """
    naux = naux_ratio * nao
    n_pairs = nao * (nao + 1) / 2
    return naux * n_pairs * BYTES_PER_DOUBLE / 1e9


def plan_scf_memory(nao: int, budget_mb: int,
                    density_fit: bool) -> MemoryPlan:
    """Decide how a density-fitted SCF fits inside a memory budget.

    Without density fitting there is no ``_cderi`` tensor, so the plan just
    carries the budget through. With it, keep the tensor in RAM only while it
    stays under the in-core fraction of the budget, spill it to disk past that,
    and refuse a basis whose tensor tops the hard ceiling even on disk (better a
    clear error than an OOM crash mid-run).

    Args:
        nao: Number of atomic orbitals (basis functions).
        budget_mb: The resolved SCF memory budget (MB).
        density_fit: Whether density fitting is requested.

    Returns:
        The :class:`MemoryPlan` for this SCF.

    Raises:
        MemoryError: If the ``_cderi`` tensor exceeds the hard ceiling.
    """
    if not density_fit:
        return MemoryPlan(density_fit=False, incore=True,
                          max_memory_mb=budget_mb, cderi_to_disk=False)
    cderi_gb = estimate_cderi_gb(nao)
    if cderi_gb > CDERI_CEILING_GB:
        raise MemoryError(
            f"density-fitting tensor ~{cderi_gb:.0f} GB for {nao} basis "
            f"functions exceeds the {CDERI_CEILING_GB:.0f} GB ceiling; "
            "use a smaller basis.")
    # Fits in RAM with headroom -> in-core; otherwise stream it from disk
    incore = cderi_gb * 1024 <= budget_mb * CDERI_INCORE_FRACTION
    return MemoryPlan(density_fit=True, incore=incore,
                      max_memory_mb=budget_mb, cderi_to_disk=not incore)


def _cgroup_limit_bytes(read_text) -> int | None:
    """Container memory limit (bytes) from cgroup v2 then v1, else None."""
    # cgroup v2 reports 'max' for "no limit"; v1 reports a near-2**63 sentinel
    for path in ("/sys/fs/cgroup/memory.max",
                 "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        raw = read_text(path)
        if raw is None:
            continue
        raw = raw.strip()
        if raw == "max":
            return None
        value = int(raw)
        if value >= 2 ** 62:
            return None
        return value
    return None


def _read_text_or_none(path: str) -> str | None:
    """Read a file's text, or None if it is absent/unreadable."""
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return None


def _physical_ram_bytes() -> int | None:
    """Physical RAM (bytes) via os.sysconf, or None where unsupported."""
    # sysconf is POSIX-only; absent on Windows (where the QM engines never run)
    sysconf = getattr(os, "sysconf", None)
    if sysconf is None:
        return None
    try:
        return sysconf("SC_PAGE_SIZE") * sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError):
        return None


def resolve_memory_budget_mb(env: Mapping[str, str] | None = None) -> int:
    """Resolve the SCF memory budget (MB) for this host.

    An explicit env override wins; otherwise take the smaller of the container
    cgroup limit and physical RAM, scaled by a headroom fraction so PySCF does
    not size its algorithms for memory the process cannot actually use, and
    fall back to a conservative default where neither can be detected.

    Args:
        env: Environment mapping to read the override from (defaults to
            ``os.environ``).

    Returns:
        The memory budget in megabytes, at least ``MEMORY_FLOOR_MB``.
    """
    env = os.environ if env is None else env
    override = env.get(MEMORY_BUDGET_ENV)
    if override:
        return max(int(override), MEMORY_FLOOR_MB)
    limits_bytes = [b for b in (_cgroup_limit_bytes(_read_text_or_none),
                                _physical_ram_bytes()) if b is not None]
    if not limits_bytes:
        return DEFAULT_MEMORY_MB
    usable_mb = int(min(limits_bytes) / (1024 * 1024) * MEMORY_HEADROOM)
    return max(usable_mb, MEMORY_FLOOR_MB)


def _cderi_scratch_path() -> str:
    """A unique on-disk path for a spilled _cderi tensor in the scratch dir.

    Prefer PySCF's scratch dir so the spill lands on the container's disk mount
    rather than a RAM-backed /tmp; fall back to the system temp dir.
    """
    tmpdir = os.environ.get("PYSCF_TMPDIR") or tempfile.gettempdir()
    return os.path.join(tmpdir, f"corrosim_cderi_{uuid.uuid4().hex}.h5")


def build_rks(symbols: Sequence[str], coords: Coords, basis: str, xc: str,
              charge: int, solvent: str | None,
              grid_level: int | None = None, density_fit: bool = False,
              max_memory_mb: int | None = None) -> Any:
    """Configure an unkerneled PySCF RKS mean field (grid + ddCOSMO).

    The shared home for every PySCF single point in corrosim: run_pyscf /
    optimize_geometry / thermo_correction and the report cube writers all build
    their RKS object here so the grid and implicit-solvent setup stay identical.
    The memory budget is sized to the host (or ``max_memory_mb``) so PySCF picks
    the correct in-core / out-of-core path; optional density fitting is guarded
    so its ``_cderi`` tensor spills to disk rather than OOM-crashing the box.

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        basis: The AO basis set.
        xc: The exchange-correlation functional.
        charge: Net molecular charge.
        solvent: None for gas phase, or a solvent name to switch on the ddCOSMO
            implicit-solvation model (water dielectric).
        grid_level: Override for the DFT integration grid (PySCF default 3).
        density_fit: Speed the SCF with density fitting (RI). Off by default:
            the RI approximation shifts the numbers, so it never touches the
            production descriptors unless explicitly requested.
        max_memory_mb: Override the SCF memory budget (MB); auto-detected from
            the host when unset.

    Returns:
        The configured (unkerneled) PySCF RKS mean-field object; call its
        ``.kernel()`` to run the SCF.

    Raises:
        MemoryError: With ``density_fit``, when the density-fitting tensor
            exceeds the hard memory ceiling (propagated from
            :func:`plan_scf_memory`); use a smaller basis.
    """
    from . import _backend_pyscf as _pyscf
    mol = _pyscf.gto.M(atom=[[s, tuple(c)] for s, c in zip(symbols, coords)],
                       basis=basis, charge=charge, verbose=0)
    # Size the SCF memory budget so PySCF sizes its algorithms for memory the
    # process can actually use, rather than its ~4 GB default
    budget = (max_memory_mb if max_memory_mb is not None
              else resolve_memory_budget_mb())
    mol.max_memory = budget
    mf = _pyscf.dft.RKS(mol)
    mf.xc = xc
    if grid_level is not None:
        # Set on the base RKS, before any solvent wrap
        mf.grids.level = grid_level
    if density_fit:
        # Keep the _cderi tensor in RAM only if it fits; else spill it to disk
        plan = plan_scf_memory(mol.nao_nr(), budget, density_fit=True)
        mf = mf.density_fit()
        mf.with_df.max_memory = plan.max_memory_mb
        if plan.cderi_to_disk:
            mf.with_df._cderi_to_save = _cderi_scratch_path()
    if solvent:
        # _backend_pyscf imported pyscf.solvent at load, registering ddCOSMO
        mf = mf.ddCOSMO()
        # ddCOSMO default eps is water already; set it explicitly
        mf.with_solvent.eps = WATER_EPS
    return mf


def _level_label(xc: str, basis: str, solvent: str | None) -> str:
    """Human-readable 'XC/BASIS (solvent)' level-of-theory descriptor."""
    return (f"{xc.upper()}/{basis}"
            + (f" (ddCOSMO:{solvent})" if solvent else " (gas)"))


def _imaginary_mask(freq_cm: np.ndarray) -> np.ndarray:
    """Boolean mask of imaginary vibrational modes in a frequency array.

    PySCF encodes an imaginary mode as a negative real part or a non-zero
    imaginary part; both are flagged while a real mode's numerical noise is not.
    """
    fw = np.asarray(freq_cm)
    return (fw.real < 0) | (np.abs(fw.imag) > IMAG_FREQ_TOL)


def run_xtb(symbols: Sequence[str], coords: Coords,
            charge: int = 0) -> EngineResult:
    """GFN2-xTB single point.

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        charge: Net molecular charge.

    Returns:
        The single-point :class:`EngineResult`.
    """
    from . import _backend_tblite as _tblite
    Z = np.array([atomic_numbers[s] for s in symbols])
    xyz_bohr = np.asarray(coords, dtype=float) * ANG_TO_BOHR
    calc = _tblite.Calculator("GFN2-xTB", Z, xyz_bohr, charge=float(charge))
    calc.set("verbosity", 0)
    res = calc.singlepoint()
    # Orbital energies (Hartree) + occupations
    orb = np.asarray(res.get("orbital-energies"))
    occ = np.asarray(res.get("orbital-occupations"))
    e_total = float(res.get("energy"))
    require_virtual_orbital(occ)
    homo_i = np.where(occ > OCCUPIED_MIN)[0].max()
    homo = orb[homo_i]
    lumo = orb[homo_i + 1]
    # tblite exposes Mulliken charges for GFN2-xTB; guard only the narrow case
    # where the property is absent (older tblite yields None -> a 0-d array
    # that won't iterate), so a real coding error here surfaces instead of
    # silently dropping the TNC.
    try:
        charges = [float(q) for q in np.asarray(res.get("charges"))]
    except (KeyError, TypeError, ValueError):
        charges = None
    # tblite reports the dipole in atomic units; a missing property (older
    # tblite) degrades to None rather than failing the single point.
    try:
        dipole_debye = dipole_magnitude_debye(res.get("dipole"),
                                              in_atomic_units=True)
    except (KeyError, TypeError, ValueError):
        dipole_debye = None
    return EngineResult("xtb", "GFN2-xTB",
                        e_total * HARTREE_TO_EV,
                        homo * HARTREE_TO_EV,
                        lumo * HARTREE_TO_EV,
                        charges=charges,
                        dipole_debye=dipole_debye)


def run_pyscf(symbols: Sequence[str], coords: Coords,
              basis: str = "6-311++G(d,p)", xc: str = "b3lyp",
              solvent: str | None = "water",
              charge: int = 0, density_fit: bool = False,
              chkfile: str | None = None) -> EngineResult:
    """DFT single point with PySCF.

    The default level B3LYP/6-311++G(d,p) + ddCOSMO(water) is corrosim's
    adopted production DFT standard, matching the methodology template.
    ('6-311++G(d,p)' is PySCF-equivalent to '6-311++g**'; use '6-31g' for
    quick checks.) A non-converging SCF is escalated (level-shift/damping, then
    a second-order restart) and raised loud rather than returned as garbage.

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        basis: The AO basis set.
        xc: The exchange-correlation functional.
        solvent: None for gas phase, or a solvent name to switch on the
            ddCOSMO implicit-solvation model (mirrors the PCM/COSMO used in
            the papers).
        charge: Net molecular charge.
        density_fit: Speed the SCF with density fitting (off by default; the RI
            approximation shifts the numbers).
        chkfile: Optional path to persist the converged wavefunction (a PySCF
            checkpoint of MO coefficients + occupations). When given, a later
            density-derived property reloads it instead of repeating the SCF.

    Returns:
        The single-point :class:`EngineResult`.
    """
    level = _level_label(xc, basis, solvent)
    mf = build_rks(symbols, coords, basis, xc, charge, solvent,
                   density_fit=density_fit)
    # Persist the converged wavefunction when asked, so a later density-derived
    # property reloads it rather than repeating the SCF. Set on the mean field
    # run_scf kernels (the ddCOSMO wrapper under a solvent); run_scf writes the
    # checkpoint on convergence.
    if chkfile:
        os.makedirs(os.path.dirname(chkfile) or ".", exist_ok=True)
        mf.chkfile = chkfile
    mf = run_scf(mf, label=level)
    e_total = mf.e_tot
    occ = mf.mo_occ
    mo = mf.mo_energy
    require_virtual_orbital(occ)
    homo = mo[occ > 0].max()
    lumo = mo[occ == 0].min()
    # mulliken_pop returns (pop, charges); guard only the narrow Mulliken
    # failure (missing/short result) so a real bug, e.g. an API change,
    # surfaces instead of silently dropping the TNC.
    try:
        charges = [float(q) for q in mf.mulliken_pop(verbose=0)[1]]
    except (IndexError, TypeError, ValueError):
        charges = None
    # PySCF's dip_moment returns the (nuclear + electronic) dipole already in
    # Debye; a solvent-wrapped mean field that lacks the method degrades to None
    # rather than losing the whole single point.
    try:
        dipole_debye = dipole_magnitude_debye(
            mf.dip_moment(unit="Debye", verbose=0), in_atomic_units=False)
    except (AttributeError, TypeError, ValueError):
        dipole_debye = None
    return EngineResult("pyscf", level,
                        float(e_total) * HARTREE_TO_EV,
                        float(homo) * HARTREE_TO_EV,
                        float(lumo) * HARTREE_TO_EV,
                        charges=charges,
                        dipole_debye=dipole_debye)


def optimize_geometry(symbols: Sequence[str], coords: Coords,
                      basis: str = "6-31G(d)", xc: str = "b3lyp",
                      charge: int = 0, solvent: str | None = None,
                      maxsteps: int = 100, grid_level: int | None = None,
                      convergence_set: str | None = None
                      ) -> tuple[list[str], list[tuple[float, ...]]]:
    """DFT geometry optimisation with PySCF (geomeTRIC backend).

    The intended protocol is *optimise at a modest level, then run the
    production single point* on the relaxed geometry: orbital energies are far
    more sensitive to geometry than to the opt basis, so B3LYP/6-31G(d)
    gas-phase relaxation is a good, cheap default. A finer ``grid_level`` (e.g.
    5) suppresses grid noise on a nearly-flat torsion; ``convergence_set``
    selects a geomeTRIC criteria preset (e.g. 'GAU_TIGHT') — both are the knobs
    for clearing a spurious low-frequency imaginary mode.

    Args:
        symbols: Element symbols.
        coords: Starting geometry in Angstrom.
        basis: The AO basis for the optimisation.
        xc: The exchange-correlation functional.
        charge: Net molecular charge.
        solvent: Relax in implicit solvent ('water') or gas phase (None).
        maxsteps: Maximum optimisation steps.
        grid_level: Override for the DFT integration grid (PySCF default 3).
        convergence_set: geomeTRIC convergence-criteria preset name.

    Returns:
        ``(symbols, coords_angstrom)`` for the relaxed structure; atom order
        is preserved.
    """
    from . import _backend_pyscf as _pyscf
    mf = build_rks(symbols, coords, basis, xc, charge, solvent,
                    grid_level=grid_level)
    conv = {"convergence_set": convergence_set} if convergence_set else {}
    mol_eq = _pyscf.optimize(mf, maxsteps=maxsteps, **conv)
    opt_symbols = [mol_eq.atom_symbol(i) for i in range(mol_eq.natm)]
    opt_coords = [tuple(float(x) for x in r)
                  for r in mol_eq.atom_coords(unit="Angstrom")]
    return opt_symbols, opt_coords


def thermo_correction(symbols: Sequence[str], coords: Coords,
                      basis: str = "6-31G(d)", xc: str = "b3lyp",
                      charge: int = 0, solvent: str | None = None,
                      temperature: float = 298.15, pressure: float = 101325.0,
                      grid_level: int | None = None) -> dict:
    """Gibbs free-energy correction ``G_corr = G(T) − E_elec`` (eV).

    Computed at a *stationary* geometry from an analytic Hessian + ideal-gas
    rigid-rotor/harmonic-oscillator thermochemistry (PySCF) — the ZPE +
    thermal-enthalpy − T·S term the electronic-only pKaH omits. ``coords`` MUST
    already be optimised at the same (basis, xc, solvent) level: harmonic
    frequencies (hence G_corr) are only meaningful at a minimum. Add the
    returned ``g_corr_ev`` to the electronic energy to get G. Match
    ``grid_level`` to the optimisation so the Hessian sees the same surface.

    Args:
        symbols: Element symbols.
        coords: Optimised geometry in Angstrom (a stationary point).
        basis: The AO basis set.
        xc: The exchange-correlation functional.
        charge: Net molecular charge.
        solvent: Implicit solvent ('water') or gas phase (None).
        temperature: Temperature (K).
        pressure: Pressure (Pa).
        grid_level: Override for the DFT integration grid (PySCF default 3).

    Returns:
        A dict with ``g_corr_ev``, ``zpe_ev``, ``temperature``, ``n_imag``,
        ``level``, ``freq_cm`` (signed cm⁻¹; imaginary < 0) and ``norm_mode``
        (shape ``(nmode, natom, 3)``). ``n_imag`` > 0 flags a non-minimum, so
        the correction is unreliable and the caller should re-optimise;
        ``freq_cm`` / ``norm_mode`` let a caller step off a saddle.
    """
    from . import _backend_pyscf as _pyscf
    level = _level_label(xc, basis, solvent)
    mf = build_rks(symbols, coords, basis, xc, charge, solvent,
                    grid_level=grid_level)
    # Converge (or fail loud) before the Hessian: a frequency analysis on an
    # unconverged SCF is meaningless. The opt-basis SCF here converges on plain
    # DIIS, so this stays the base mean field the Hessian needs.
    mf = run_scf(mf, label=level)
    e_elec = mf.e_tot
    hess = mf.Hessian().kernel()
    ha = _pyscf.thermo.harmonic_analysis(mf.mol, hess)
    fw = np.asarray(ha["freq_wavenumber"])
    n_imag = int(np.sum(_imaginary_mask(fw)))
    info = _pyscf.thermo.thermo(mf, ha["freq_au"], temperature, pressure)
    # Total Gibbs (Hartree), incl. E_elec
    g_tot = float(info["G_tot"][0])
    zpe = float(info["ZPE"][0])
    return {
        "g_corr_ev": (g_tot - float(e_elec)) * HARTREE_TO_EV,
        "zpe_ev": zpe * HARTREE_TO_EV,
        "temperature": temperature,
        "n_imag": n_imag,
        "level": level,
        # Harmonic frequencies (cm⁻¹); imaginary < 0
        "freq_cm": fw,
        # (nmode, natom, 3) Cartesian modes
        "norm_mode": np.asarray(ha["norm_mode"]),
    }


def imaginary_mode(freq_cm: np.ndarray,
                   norm_mode: np.ndarray) -> np.ndarray | None:
    """Cartesian displacement of the softest imaginary vibrational mode.

    ``freq_cm`` and ``norm_mode`` come straight from
    :func:`thermo_correction`; an imaginary mode surfaces as a negative real
    part or a non-zero imaginary part.

    Args:
        freq_cm: Harmonic frequencies (cm⁻¹; imaginary < 0).
        norm_mode: Cartesian normal modes, shape ``(nmode, natom, 3)``.

    Returns:
        The ``(natom, 3)`` direction to step along to leave a first-order
        saddle (feed to :func:`displace_along_mode`), or None at a minimum.
    """
    fw = np.asarray(freq_cm)
    nm = np.asarray(norm_mode)
    imag = np.where(_imaginary_mask(fw))[0]
    if imag.size == 0:
        return None
    # Softest = most-negative frequency
    idx = int(imag[np.argmin(fw.real[imag])])
    return nm[idx]


def displace_along_mode(coords: Coords, mode: np.ndarray,
                        amplitude_ang: float = 0.3
                        ) -> list[tuple[float, ...]]:
    """Step a geometry along a normal mode.

    Scaled so the largest atomic move is ``amplitude_ang`` Angstrom — nudges a
    saddle point off its imaginary mode before a fresh optimisation.

    Args:
        coords: Geometry in Angstrom.
        mode: The normal-mode displacement, shape ``(natom, 3)``.
        amplitude_ang: Largest atomic step (Å).

    Returns:
        The displaced coords in Angstrom (atom order preserved).
    """
    xyz = np.asarray(coords, dtype=float)
    step = np.asarray(mode, dtype=float).reshape(xyz.shape)
    peak = float(np.abs(step).max())
    if peak > 0:
        step = step / peak * amplitude_ang
    return [tuple(float(x) for x in row) for row in xyz + step]


def relax_to_minimum(symbols: Sequence[str], coords: Coords,
                     basis: str = "6-31G(d)", xc: str = "b3lyp",
                     charge: int = 0, solvent: str | None = None,
                     temperature: float = 298.15, grid_level: int = 4,
                     convergence_set: str = "GAU", maxsteps: int = 200,
                     max_restarts: int = 3, amplitude_ang: float = 0.3
                     ) -> tuple[list[str], Coords, dict]:
    """Optimise to a *true* minimum.

    Relax, run frequencies, and while an imaginary mode survives step along it
    (:func:`displace_along_mode`) and re-optimise — up to ``max_restarts``
    times. The recipe for a floppy rotor whose flat torsion tips imaginary: the
    **finer DFT grid** (``grid_level`` 4 vs the default 3) is the actual fix —
    it removes the integration noise that flipped the mode — while the
    displace-loop steps off any genuine saddle. Ordinary ``convergence_set``
    ('GAU') suffices; a tighter set (e.g. 'GAU_TIGHT') chases flat modes for
    many extra steps with a collapsing trust radius, far slower for no gain.

    Args:
        symbols: Element symbols.
        coords: Starting geometry in Angstrom.
        basis: The AO basis for each optimisation.
        xc: The exchange-correlation functional.
        charge: Net molecular charge.
        solvent: Implicit solvent ('water') or gas phase (None).
        temperature: Temperature (K) for the frequency thermochemistry.
        grid_level: DFT integration grid (finer than the default to kill
            grid-noise imaginary modes).
        convergence_set: geomeTRIC convergence-criteria preset name.
        maxsteps: Maximum steps per optimisation.
        max_restarts: Maximum imaginary-mode step-and-reoptimise restarts.
        amplitude_ang: Largest atomic step off a saddle (Å).

    Returns:
        ``(symbols, coords, thermo)`` — ``thermo`` is the final
        :func:`thermo_correction` dict; ``thermo["n_imag"] == 0`` on success,
        else the best geometry reached within the restart budget.
    """
    sym: list[str] = list(symbols)
    xyz: Coords = coords
    info: dict = {}
    for _ in range(max_restarts + 1):
        sym, xyz = optimize_geometry(sym, xyz, basis=basis, xc=xc,
                                     charge=charge, solvent=solvent,
                                     maxsteps=maxsteps, grid_level=grid_level,
                                     convergence_set=convergence_set)
        info = thermo_correction(sym, xyz, basis=basis, xc=xc, charge=charge,
                                 solvent=solvent, temperature=temperature,
                                 grid_level=grid_level)
        if info["n_imag"] == 0:
            break
        mode = imaginary_mode(info["freq_cm"], info["norm_mode"])
        if mode is None:
            break
        xyz = displace_along_mode(xyz, mode, amplitude_ang=amplitude_ang)
    return sym, xyz, info


def min_check_fields(thermo: dict | None) -> dict:
    """Provenance for the true-minimum (frequency) check.

    Condense a :func:`thermo_correction` / :func:`relax_to_minimum` result into
    the two fields a descriptor row carries, so a saddle point never silently
    passes as a minimum: ``n_imag`` (imaginary-mode count; 0 ⇒ a verified
    minimum) and ``lowest_freq_cm`` (the softest harmonic frequency in cm⁻¹;
    negative ⇒ imaginary).

    Args:
        thermo: A :func:`thermo_correction` result, or None if no check ran.

    Returns:
        ``{"n_imag": ..., "lowest_freq_cm": ...}``, or ``{}`` when ``thermo``
        is falsy (leaving a plain ``--optimize`` row untouched).
    """
    if not thermo:
        return {}
    fw = np.asarray(thermo["freq_cm"])
    imag = _imaginary_mask(fw)
    # Report a signed wavenumber (negative = imaginary) so the softest mode
    # ranks correctly and agrees with n_imag and imaginary_mode()
    signed = np.where(imag, -np.abs(fw), fw.real)
    return {
        "n_imag": int(thermo["n_imag"]),
        "lowest_freq_cm": round(float(np.min(signed)), 1),
    }


def run_engine(symbols: Sequence[str], coords: Coords, engine: str = "xtb",
               charge: int = 0, **kwargs: Any) -> EngineResult:
    """Dispatch to the chosen engine.

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        engine: 'xtb', 'pyscf', 'orca' or 'gaussian'.
        charge: Net molecular charge (e.g. +1 for a protonated inhibitor).
        **kwargs: Extra keyword arguments forwarded to the chosen engine.

    Returns:
        The single-point :class:`EngineResult`.

    Raises:
        ValueError: If ``engine`` is not a known engine name.
    """
    engine = engine.lower()
    if engine == "xtb":
        return run_xtb(symbols, coords, charge=charge)
    if engine == "pyscf":
        return run_pyscf(symbols, coords, charge=charge, **kwargs)
    if engine == "orca":
        return run_orca(symbols, coords, charge=charge, **kwargs)
    if engine == "gaussian":
        return run_gaussian(symbols, coords, charge=charge, **kwargs)
    raise ValueError(f"Unknown engine '{engine}'. "
                     "Use 'xtb', 'pyscf', 'orca', or 'gaussian'.")


# --- Production engines: ORCA / Gaussian ----------------------------------
# These shell out to a locally installed binary (not bundled). The input
# writers and output parsers below are the automated part; point them at your
# executable via orca_cmd / gaussian_cmd or the ORCA_CMD / GAUSSIAN_CMD env
# vars.

def _xyz_block(symbols: Sequence[str], coords: Coords) -> list[str]:
    """Aligned 'element x y z' geometry lines (Angstrom) for an input deck."""
    return [f" {s:2s} {x:16.8f} {y:16.8f} {z:16.8f}"
            for s, (x, y, z) in zip(symbols, coords)]


def _run_external_engine(cmd: str, prefix: str, in_ext: str, out_ext: str,
                         deck: str, workdir: str | None = None) -> str:
    """Write a deck, run a local QM binary, and return its output text.

    Shared by run_orca / run_gaussian: resolve a scratch dir, write the input
    deck, run the fixed-argv (no-shell) binary, and read the log back.
    """
    workdir = workdir or tempfile.mkdtemp(prefix=prefix)
    inp = os.path.join(workdir, f"job.{in_ext}")
    out = os.path.join(workdir, f"job.{out_ext}")
    with open(inp, "w") as f:
        f.write(deck)
    with open(out, "w") as f:
        # Fixed argv (QM binary + generated input); no shell, no untrusted input
        subprocess.run([cmd, inp], stdout=f,  # nosec B603
                       stderr=subprocess.STDOUT, check=True)
    with open(out) as f:
        return f.read()


def write_orca_input(symbols: Sequence[str], coords: Coords, keywords: str,
                     charge: int = 0, mult: int = 1,
                     solvent: str | None = "water", nprocs: int = 4) -> str:
    """Build an ORCA input deck (keywords + optional CPCM solvent + xyz block).

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        keywords: The ORCA keyword line (without the leading '!').
        charge: Net molecular charge.
        mult: Spin multiplicity.
        solvent: CPCM solvent name, or None for gas phase.
        nprocs: Number of parallel processes.

    Returns:
        The ORCA input deck as text.
    """
    lines = [f"! {keywords}"]
    if solvent:
        lines.append(f"! CPCM({solvent})")
    if nprocs > 1:
        lines += ["%pal", f"  nprocs {nprocs}", "end"]
    lines.append(f"* xyz {charge} {mult}")
    lines += _xyz_block(symbols, coords)
    lines.append("*")
    return "\n".join(lines) + "\n"


def parse_orca_output(text: str) -> tuple[float, float]:
    """Parse HOMO/LUMO from an ORCA output's ORBITAL ENERGIES block.

    Args:
        text: The ORCA output text.

    Returns:
        ``(homo_ev, lumo_ev)`` in eV.

    Raises:
        ValueError: If the orbital-energies block is missing or unparsable.
    """
    lines = text.splitlines()
    try:
        i = next(k for k, line in enumerate(lines)
                 if "ORBITAL ENERGIES" in line)
    except StopIteration:
        raise ValueError("No 'ORBITAL ENERGIES' section found in ORCA output.")
    occ, energies_ev = [], []
    for line in lines[i:]:
        cols = line.split()
        if len(cols) >= 4 and cols[0].isdigit():
            try:
                # Occupation in col 2, E(eV) in col 4
                occ.append(float(cols[1]))
                energies_ev.append(float(cols[3]))
            except ValueError:
                continue
        elif energies_ev and not cols:
            break
    if not energies_ev:
        raise ValueError("Could not parse orbital energies from ORCA output.")
    require_virtual_orbital(occ)
    homo_i = max(k for k, occ_val in enumerate(occ) if occ_val > OCCUPIED_MIN)
    return energies_ev[homo_i], energies_ev[homo_i + 1]


def run_orca(symbols: Sequence[str], coords: Coords,
             keywords: str = "B3LYP def2-TZVP",
             solvent: str | None = "water", charge: int = 0, mult: int = 1,
             nprocs: int = 4, orca_cmd: str | None = None,
             workdir: str | None = None) -> EngineResult:
    """Run an ORCA single point via the local ``orca`` binary.

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        keywords: The ORCA keyword line.
        solvent: CPCM solvent name, or None for gas phase.
        charge: Net molecular charge.
        mult: Spin multiplicity.
        nprocs: Number of parallel processes.
        orca_cmd: Path to the orca binary (else $ORCA_CMD, else 'orca').
        workdir: Scratch directory (a temp dir by default).

    Returns:
        The :class:`EngineResult` (e_total is NaN — HOMO/LUMO only).
    """
    orca_cmd = orca_cmd or os.environ.get("ORCA_CMD", "orca")
    deck = write_orca_input(symbols, coords, keywords, charge, mult,
                            solvent, nprocs)
    text = _run_external_engine(orca_cmd, "orca_", "inp", "out", deck, workdir)
    homo, lumo = parse_orca_output(text)
    level = f"{keywords}" + (f" CPCM({solvent})" if solvent else "")
    return EngineResult("orca", level, float("nan"), homo, lumo)


def write_gaussian_input(symbols: Sequence[str], coords: Coords, route: str,
                         charge: int = 0, mult: int = 1,
                         solvent: str | None = "water", nprocs: int = 4,
                         mem: str = "2GB") -> str:
    """Build a Gaussian input deck (route + optional PCM solvent + xyz block).

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        route: The Gaussian route line (without the leading '#').
        charge: Net molecular charge.
        mult: Spin multiplicity.
        solvent: PCM solvent name, or None for gas phase.
        nprocs: Number of shared processors.
        mem: Memory request (e.g. '2GB').

    Returns:
        The Gaussian input deck as text.
    """
    r = route
    if solvent and "scrf" not in route.lower():
        r += f" SCRF=(PCM,solvent={solvent})"
    head = [f"%nprocshared={nprocs}", f"%mem={mem}", f"# {r}", "",
            "corrosim job", "", f"{charge} {mult}"]
    body = _xyz_block(symbols, coords)
    return "\n".join(head + body) + "\n\n"


def parse_gaussian_output(text: str) -> tuple[float, float]:
    """Parse HOMO/LUMO from a Gaussian log's eigenvalue lines.

    Args:
        text: The Gaussian log text.

    Returns:
        ``(homo_ev, lumo_ev)`` in eV (converted from Hartree).

    Raises:
        ValueError: If the Alpha occ./virt. eigenvalue lines are missing.
    """
    occ, virt = [], []
    for line in text.splitlines():
        if "Alpha  occ. eigenvalues" in line:
            occ += [float(v) for v in line.split("--")[1].split()]
        elif "Alpha virt. eigenvalues" in line:
            virt += [float(v) for v in line.split("--")[1].split()]
    if not occ or not virt:
        raise ValueError(
            "Could not find Alpha occ./virt. eigenvalues in Gaussian log.")
    return occ[-1] * HARTREE_TO_EV, virt[0] * HARTREE_TO_EV


def run_gaussian(symbols: Sequence[str], coords: Coords,
                 route: str = "B3LYP/6-311++G(d,p)",
                 solvent: str | None = "water", charge: int = 0, mult: int = 1,
                 nprocs: int = 4, mem: str = "2GB",
                 gaussian_cmd: str | None = None,
                 workdir: str | None = None) -> EngineResult:
    """Run a Gaussian single point via the local ``g16`` binary.

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        route: The Gaussian route line.
        solvent: PCM solvent name, or None for gas phase.
        charge: Net molecular charge.
        mult: Spin multiplicity.
        nprocs: Number of shared processors.
        mem: Memory request (e.g. '2GB').
        gaussian_cmd: Path to g16 (else $GAUSSIAN_CMD, else 'g16').
        workdir: Scratch directory (a temp dir by default).

    Returns:
        The :class:`EngineResult` (e_total is NaN — HOMO/LUMO only).
    """
    gaussian_cmd = gaussian_cmd or os.environ.get("GAUSSIAN_CMD", "g16")
    deck = write_gaussian_input(symbols, coords, route, charge, mult,
                                solvent, nprocs, mem)
    text = _run_external_engine(gaussian_cmd, "g16_", "gjf", "log", deck,
                                workdir)
    homo, lumo = parse_gaussian_output(text)
    level = route + (f" PCM({solvent})" if solvent else "")
    return EngineResult("gaussian", level, float("nan"), homo, lumo)
