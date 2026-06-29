"""
corrosim.engines
----------------
Uniform wrappers around the two quantum engines used by the tool.

  * 'xtb'   -> GFN2-xTB via tblite. Sub-second, great for screening/ranking.
  * 'pyscf' -> real DFT (default B3LYP). Minutes per molecule; use for the
              final, publication-grade descriptors.

Both return the same EngineResult so the rest of the pipeline is engine-agnostic.
Energies in the result are reported in eV.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

HARTREE_TO_EV = 27.211386245988
ANG_TO_BOHR = 1.8897259886


@dataclass
class EngineResult:
    engine: str
    level: str               # e.g. "GFN2-xTB" or "B3LYP/6-31G"
    e_total_ev: float
    homo_ev: float
    lumo_ev: float

    @property
    def gap_ev(self) -> float:
        return self.lumo_ev - self.homo_ev


def run_xtb(symbols, coords) -> EngineResult:
    """GFN2-xTB single point. coords in Angstrom."""
    from tblite.interface import Calculator
    from ase.data import atomic_numbers
    Z = np.array([atomic_numbers[s] for s in symbols])
    xyz_bohr = np.asarray(coords, dtype=float) * ANG_TO_BOHR
    calc = Calculator("GFN2-xTB", Z, xyz_bohr)
    calc.set("verbosity", 0)
    res = calc.singlepoint()
    orb = np.asarray(res.get("orbital-energies"))      # Hartree
    occ = np.asarray(res.get("orbital-occupations"))
    e_total = float(res.get("energy"))
    homo_i = np.where(occ > 0.5)[0].max()
    homo = orb[homo_i]
    lumo = orb[homo_i + 1]
    return EngineResult("xtb", "GFN2-xTB",
                        e_total * HARTREE_TO_EV,
                        homo * HARTREE_TO_EV,
                        lumo * HARTREE_TO_EV)


def run_pyscf(symbols, coords, basis: str = "6-31g",
              xc: str = "b3lyp", solvent: str | None = "water") -> EngineResult:
    """
    DFT single point with PySCF. coords in Angstrom.

    solvent: None for gas phase, or a solvent name to switch on the ddCOSMO
             implicit-solvation model (mirrors the PCM/COSMO used in the papers).
    """
    from pyscf import gto, dft
    mol = gto.M(atom=[[s, tuple(c)] for s, c in zip(symbols, coords)],
                basis=basis, verbose=0)
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
    level = f"{xc.upper()}/{basis}" + (f" (ddCOSMO:{solvent})" if solvent else " (gas)")
    return EngineResult("pyscf", level,
                        float(e_total) * HARTREE_TO_EV,
                        float(homo) * HARTREE_TO_EV,
                        float(lumo) * HARTREE_TO_EV)


def run_engine(symbols, coords, engine: str = "xtb", **kwargs) -> EngineResult:
    """Dispatch to the chosen engine."""
    engine = engine.lower()
    if engine == "xtb":
        return run_xtb(symbols, coords)
    if engine == "pyscf":
        return run_pyscf(symbols, coords, **kwargs)
    if engine == "orca":
        return run_orca(symbols, coords, **kwargs)
    if engine == "gaussian":
        return run_gaussian(symbols, coords, **kwargs)
    raise ValueError(f"Unknown engine '{engine}'. "
                     "Use 'xtb', 'pyscf', 'orca', or 'gaussian'.")


# --- Production engines: ORCA / Gaussian ----------------------------------
# These shell out to a locally installed binary (not bundled). The input
# writers and output parsers below are the automated part; point them at your
# executable via orca_cmd / gaussian_cmd or the ORCA_CMD / GAUSSIAN_CMD env vars.

def write_orca_input(symbols, coords, keywords: str, charge=0, mult=1,
                     solvent: str | None = "water", nprocs: int = 4) -> str:
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


def parse_orca_output(text: str):
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


def run_orca(symbols, coords, keywords: str = "B3LYP def2-TZVP",
             solvent: str | None = "water", charge=0, mult=1, nprocs: int = 4,
             orca_cmd: str | None = None, workdir: str | None = None) -> EngineResult:
    import os, subprocess, tempfile
    orca_cmd = orca_cmd or os.environ.get("ORCA_CMD", "orca")
    workdir = workdir or tempfile.mkdtemp(prefix="orca_")
    inp = os.path.join(workdir, "job.inp")
    out = os.path.join(workdir, "job.out")
    with open(inp, "w") as f:
        f.write(write_orca_input(symbols, coords, keywords, charge, mult, solvent, nprocs))
    with open(out, "w") as f:
        subprocess.run([orca_cmd, inp], stdout=f, stderr=subprocess.STDOUT, check=True)
    homo, lumo = parse_orca_output(open(out).read())
    level = f"{keywords}" + (f" CPCM({solvent})" if solvent else "")
    return EngineResult("orca", level, float("nan"), homo, lumo)


def write_gaussian_input(symbols, coords, route: str, charge=0, mult=1,
                         solvent: str | None = "water",
                         nprocs: int = 4, mem: str = "2GB") -> str:
    r = route
    if solvent and "scrf" not in route.lower():
        r += f" SCRF=(PCM,solvent={solvent})"
    head = [f"%nprocshared={nprocs}", f"%mem={mem}", f"# {r}", "",
            "corrosim job", "", f"{charge} {mult}"]
    body = [f" {s:2s} {x:16.8f} {y:16.8f} {z:16.8f}" for s, (x, y, z) in zip(symbols, coords)]
    return "\n".join(head + body) + "\n\n"


def parse_gaussian_output(text: str):
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


def run_gaussian(symbols, coords, route: str = "B3LYP/6-311++G(d,p)",
                 solvent: str | None = "water", charge=0, mult=1, nprocs: int = 4,
                 mem: str = "2GB", gaussian_cmd: str | None = None,
                 workdir: str | None = None) -> EngineResult:
    import os, subprocess, tempfile
    gaussian_cmd = gaussian_cmd or os.environ.get("GAUSSIAN_CMD", "g16")
    workdir = workdir or tempfile.mkdtemp(prefix="g16_")
    gjf = os.path.join(workdir, "job.gjf")
    log = os.path.join(workdir, "job.log")
    with open(gjf, "w") as f:
        f.write(write_gaussian_input(symbols, coords, route, charge, mult, solvent, nprocs, mem))
    with open(log, "w") as f:
        subprocess.run([gaussian_cmd, gjf], stdout=f, stderr=subprocess.STDOUT, check=True)
    homo, lumo = parse_gaussian_output(open(log).read())
    level = route + (f" PCM({solvent})" if solvent else "")
    return EngineResult("gaussian", level, float("nan"), homo, lumo)
