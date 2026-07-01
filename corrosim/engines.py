"""corrosim.engines.

Uniform wrappers around the two quantum engines used by the tool.

  * 'xtb'   -> GFN2-xTB via tblite. Sub-second, great for screening/ranking.
  * 'pyscf' -> real DFT (default B3LYP). Minutes per molecule; use for the
              final, publication-grade descriptors.

Both return the same EngineResult so the rest of the pipeline is engine-agnostic.
Energies in the result are reported in eV.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

# A molecular geometry: a sequence of (x, y, z) triples in Angstrom (or an ndarray).
Coords = Sequence[Sequence[float]]

HARTREE_TO_EV = 27.211386245988
ANG_TO_BOHR = 1.8897259886


@dataclass
class EngineResult:
    """Engine-agnostic single-point result (all energies in eV)."""
    engine: str
    level: str               # e.g. "GFN2-xTB" or "B3LYP/6-31G"
    e_total_ev: float
    homo_ev: float
    lumo_ev: float
    charges: list | None = None   # per-atom partial charges (Mulliken), if available

    @property
    def gap_ev(self) -> float:
        """HOMO–LUMO gap (eV)."""
        return self.lumo_ev - self.homo_ev


def run_xtb(symbols: Sequence[str], coords: Coords, charge: int = 0) -> EngineResult:
    """GFN2-xTB single point. coords in Angstrom. charge: net molecular charge."""
    from ase.data import atomic_numbers
    from tblite.interface import Calculator
    Z = np.array([atomic_numbers[s] for s in symbols])
    xyz_bohr = np.asarray(coords, dtype=float) * ANG_TO_BOHR
    calc = Calculator("GFN2-xTB", Z, xyz_bohr, charge=float(charge))
    calc.set("verbosity", 0)
    res = calc.singlepoint()
    orb = np.asarray(res.get("orbital-energies"))      # Hartree
    occ = np.asarray(res.get("orbital-occupations"))
    e_total = float(res.get("energy"))
    homo_i = np.where(occ > 0.5)[0].max()
    homo = orb[homo_i]
    lumo = orb[homo_i + 1]
    # tblite exposes Mulliken charges for GFN2-xTB; guard only the narrow case
    # where the property is absent (older tblite yields None -> a 0-d array that
    # won't iterate), so a real coding error here surfaces instead of silently
    # dropping the TNC.
    try:
        charges = [float(q) for q in np.asarray(res.get("charges"))]
    except (KeyError, TypeError, ValueError):
        charges = None
    return EngineResult("xtb", "GFN2-xTB",
                        e_total * HARTREE_TO_EV,
                        homo * HARTREE_TO_EV,
                        lumo * HARTREE_TO_EV,
                        charges=charges)


def run_pyscf(symbols: Sequence[str], coords: Coords, basis: str = "6-311++G(d,p)",
              xc: str = "b3lyp", solvent: str | None = "water",
              charge: int = 0) -> EngineResult:
    """DFT single point with PySCF. coords in Angstrom.

    Default level B3LYP/6-311++G(d,p) + ddCOSMO(water): corrosim's adopted
    production DFT standard, matching the methodology template (see ADR 0002).
    ('6-311++G(d,p)' is PySCF-equivalent to '6-311++g**'; use '6-31g' for quick
    checks.)

    solvent: None for gas phase, or a solvent name to switch on the ddCOSMO
             implicit-solvation model (mirrors the PCM/COSMO used in the papers).
    """
    from pyscf import dft, gto
    mol = gto.M(atom=[[s, tuple(c)] for s, c in zip(symbols, coords)],
                basis=basis, charge=charge, verbose=0)
    mf = dft.RKS(mol)
    mf.xc = xc
    if solvent:
        from pyscf import solvent as pyscf_solvent  # noqa: F401
        mf = mf.ddCOSMO()
        # dielectric for water; ddCOSMO default eps is water already, set explicitly
        mf.with_solvent.eps = 78.3553
    e_total = mf.kernel()
    occ = mf.mo_occ
    mo = mf.mo_energy
    homo = mo[occ > 0].max()
    lumo = mo[occ == 0].min()
    # mulliken_pop returns (pop, charges); guard only the narrow Mulliken failure
    # (missing/short result) so a real bug, e.g. an API change, surfaces instead
    # of silently dropping the TNC.
    try:
        charges = [float(q) for q in mf.mulliken_pop(verbose=0)[1]]
    except (IndexError, TypeError, ValueError):
        charges = None
    level = f"{xc.upper()}/{basis}" + (f" (ddCOSMO:{solvent})" if solvent else " (gas)")
    return EngineResult("pyscf", level,
                        float(e_total) * HARTREE_TO_EV,
                        float(homo) * HARTREE_TO_EV,
                        float(lumo) * HARTREE_TO_EV,
                        charges=charges)


def optimize_geometry(symbols: Sequence[str], coords: Coords, basis: str = "6-31G(d)",
                      xc: str = "b3lyp", charge: int = 0, solvent: str | None = None,
                      maxsteps: int = 100) -> tuple[list[str], list[tuple[float, ...]]]:
    """DFT geometry optimisation with PySCF (geomeTRIC backend). coords in Angstrom.

    Returns (symbols, coords_angstrom) for the relaxed structure — atom order is
    preserved. The intended protocol is *optimise at a modest level, then run the
    production single point* on the relaxed geometry: orbital energies are far more
    sensitive to geometry than to the opt basis, so B3LYP/6-31G(d) gas-phase relaxation
    is a good, cheap default. Pass solvent='water' to relax in implicit solvent
    (slower; gas-phase opt → solvated single point is the standard, robust choice).
    """
    from pyscf import dft, gto
    from pyscf.geomopt.geometric_solver import optimize
    mol = gto.M(atom=[[s, tuple(c)] for s, c in zip(symbols, coords)],
                basis=basis, charge=charge, verbose=0)
    mf = dft.RKS(mol)
    mf.xc = xc
    if solvent:
        from pyscf import solvent as pyscf_solvent  # noqa: F401
        mf = mf.ddCOSMO()
        mf.with_solvent.eps = 78.3553
    mol_eq = optimize(mf, maxsteps=maxsteps)
    opt_symbols = [mol_eq.atom_symbol(i) for i in range(mol_eq.natm)]
    opt_coords = [tuple(float(x) for x in r)
                  for r in mol_eq.atom_coords(unit="Angstrom")]
    return opt_symbols, opt_coords


def thermo_correction(symbols: Sequence[str], coords: Coords, basis: str = "6-31G(d)",
                      xc: str = "b3lyp", charge: int = 0, solvent: str | None = None,
                      temperature: float = 298.15, pressure: float = 101325.0) -> dict:
    """Gibbs free-energy correction ``G_corr = G(T) − E_elec`` (eV) at a *stationary*
    geometry, from an analytic Hessian + ideal-gas rigid-rotor/harmonic-oscillator
    thermochemistry (PySCF). This is the ZPE + thermal-enthalpy − T·S term that the
    electronic-only pKaH (ADR 0005) omits.

    coords in Angstrom and MUST already be optimised at the same (basis, xc, solvent)
    level — harmonic frequencies (hence G_corr) are only meaningful at a minimum.
    Add the returned ``g_corr_ev`` to the electronic energy to get G, or feed it to
    ``corrosim.pka.estimate_pka(g_corr_*_ev=...)`` for a frequency-corrected pKaH. The
    standard protocol is a modest gas-phase level (B3LYP/6-31G(d)) for the correction
    on top of the production single point.

    Returns ``{g_corr_ev, zpe_ev, temperature, n_imag, level}``. ``n_imag`` > 0 flags
    a non-minimum (transition state / unconverged geometry) — the correction is then
    unreliable and the caller should re-optimise.
    """
    from pyscf import dft, gto
    from pyscf.hessian import thermo
    mol = gto.M(atom=[[s, tuple(c)] for s, c in zip(symbols, coords)],
                basis=basis, charge=charge, verbose=0)
    mf = dft.RKS(mol)
    mf.xc = xc
    if solvent:
        from pyscf import solvent as pyscf_solvent  # noqa: F401
        mf = mf.ddCOSMO()
        mf.with_solvent.eps = 78.3553
    e_elec = mf.kernel()
    hess = mf.Hessian().kernel()
    ha = thermo.harmonic_analysis(mol, hess)
    fw = np.asarray(ha["freq_wavenumber"])
    # imaginary modes surface as a negative real part or a non-zero imaginary part
    n_imag = int(np.sum((fw.real < 0) | (np.abs(fw.imag) > 1e-6)))
    info = thermo.thermo(mf, ha["freq_au"], temperature, pressure)
    g_tot = float(info["G_tot"][0])                  # total Gibbs (Hartree), incl. E_elec
    zpe = float(info["ZPE"][0])
    level = f"{xc.upper()}/{basis}" + (f" (ddCOSMO:{solvent})" if solvent else " (gas)")
    return {
        "g_corr_ev": (g_tot - float(e_elec)) * HARTREE_TO_EV,
        "zpe_ev": zpe * HARTREE_TO_EV,
        "temperature": temperature,
        "n_imag": n_imag,
        "level": level,
    }


def run_engine(symbols: Sequence[str], coords: Coords, engine: str = "xtb", charge: int = 0,
               **kwargs) -> EngineResult:
    """Dispatch to the chosen engine. charge: net molecular charge (e.g. +1 for a
    protonated inhibitor in acid).
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
# executable via orca_cmd / gaussian_cmd or the ORCA_CMD / GAUSSIAN_CMD env vars.

def write_orca_input(symbols: Sequence[str], coords: Coords, keywords: str, charge=0, mult=1,
                     solvent: str | None = "water", nprocs: int = 4) -> str:
    """Build an ORCA input deck (keywords + optional CPCM solvent + xyz block)."""
    lines = [f"! {keywords}"]
    if solvent:
        lines.append(f"! CPCM({solvent})")
    if nprocs > 1:
        lines += ["%pal", f"  nprocs {nprocs}", "end"]
    lines.append(f"* xyz {charge} {mult}")
    for s, (x, y, z) in zip(symbols, coords):
        lines.append(f" {s:2s} {x:16.8f} {y:16.8f} {z:16.8f}")
    lines.append("*")
    return "\n".join(lines) + "\n"


def parse_orca_output(text: str) -> tuple[float, float]:
    """Return (homo_ev, lumo_ev) from an ORCA output's ORBITAL ENERGIES block."""
    lines = text.splitlines()
    try:
        i = next(k for k, l in enumerate(lines) if "ORBITAL ENERGIES" in l)
    except StopIteration:
        raise ValueError("No 'ORBITAL ENERGIES' section found in ORCA output.")
    occ, ev = [], []
    for l in lines[i:]:
        p = l.split()
        if len(p) >= 4 and p[0].isdigit():
            try:
                occ.append(float(p[1])); ev.append(float(p[3]))  # E(eV) is col 4
            except ValueError:
                continue
        elif ev and not p:
            break
    if not ev:
        raise ValueError("Could not parse orbital energies from ORCA output.")
    homo_i = max(k for k, o in enumerate(occ) if o > 0.5)
    return ev[homo_i], ev[homo_i + 1]


def run_orca(symbols: Sequence[str], coords: Coords, keywords: str = "B3LYP def2-TZVP",
             solvent: str | None = "water", charge=0, mult=1, nprocs: int = 4,
             orca_cmd: str | None = None, workdir: str | None = None) -> EngineResult:
    """Run an ORCA single point via the local ``orca`` binary and parse HOMO/LUMO."""
    import os
    import subprocess  # nosec B404
    import tempfile
    orca_cmd = orca_cmd or os.environ.get("ORCA_CMD", "orca")
    workdir = workdir or tempfile.mkdtemp(prefix="orca_")
    inp = os.path.join(workdir, "job.inp")
    out = os.path.join(workdir, "job.out")
    with open(inp, "w") as f:
        f.write(write_orca_input(symbols, coords, keywords, charge, mult, solvent, nprocs))
    with open(out, "w") as f:
        # fixed argv (QM binary + generated input file); no shell, no untrusted input
        subprocess.run([orca_cmd, inp], stdout=f, stderr=subprocess.STDOUT, check=True)  # nosec B603
    homo, lumo = parse_orca_output(open(out).read())
    level = f"{keywords}" + (f" CPCM({solvent})" if solvent else "")
    return EngineResult("orca", level, float("nan"), homo, lumo)


def write_gaussian_input(symbols: Sequence[str], coords: Coords, route: str, charge=0, mult=1,
                         solvent: str | None = "water",
                         nprocs: int = 4, mem: str = "2GB") -> str:
    """Build a Gaussian input deck (route + optional PCM solvent + xyz block)."""
    r = route
    if solvent and "scrf" not in route.lower():
        r += f" SCRF=(PCM,solvent={solvent})"
    head = [f"%nprocshared={nprocs}", f"%mem={mem}", f"# {r}", "",
            "corrosim job", "", f"{charge} {mult}"]
    body = [f" {s:2s} {x:16.8f} {y:16.8f} {z:16.8f}" for s, (x, y, z) in zip(symbols, coords)]
    return "\n".join(head + body) + "\n\n"


def parse_gaussian_output(text: str) -> tuple[float, float]:
    """Return (homo_ev, lumo_ev) from a Gaussian log's eigenvalue lines (Hartree->eV)."""
    occ, virt = [], []
    for l in text.splitlines():
        if "Alpha  occ. eigenvalues" in l:
            occ += [float(v) for v in l.split("--")[1].split()]
        elif "Alpha virt. eigenvalues" in l:
            virt += [float(v) for v in l.split("--")[1].split()]
    if not occ or not virt:
        raise ValueError("Could not find Alpha occ./virt. eigenvalues in Gaussian log.")
    return occ[-1] * HARTREE_TO_EV, virt[0] * HARTREE_TO_EV


def run_gaussian(symbols: Sequence[str], coords: Coords, route: str = "B3LYP/6-311++G(d,p)",
                 solvent: str | None = "water", charge=0, mult=1, nprocs: int = 4,
                 mem: str = "2GB", gaussian_cmd: str | None = None,
                 workdir: str | None = None) -> EngineResult:
    """Run a Gaussian single point via the local ``g16`` binary and parse HOMO/LUMO."""
    import os
    import subprocess  # nosec B404
    import tempfile
    gaussian_cmd = gaussian_cmd or os.environ.get("GAUSSIAN_CMD", "g16")
    workdir = workdir or tempfile.mkdtemp(prefix="g16_")
    gjf = os.path.join(workdir, "job.gjf")
    log = os.path.join(workdir, "job.log")
    with open(gjf, "w") as f:
        f.write(write_gaussian_input(symbols, coords, route, charge, mult, solvent, nprocs, mem))
    with open(log, "w") as f:
        # fixed argv (QM binary + generated input file); no shell, no untrusted input
        subprocess.run([gaussian_cmd, gjf], stdout=f, stderr=subprocess.STDOUT, check=True)  # nosec B603
    homo, lumo = parse_gaussian_output(open(log).read())
    level = route + (f" PCM({solvent})" if solvent else "")
    return EngineResult("gaussian", level, float("nan"), homo, lumo)
