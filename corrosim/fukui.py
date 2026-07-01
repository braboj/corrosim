"""corrosim.fukui.

Stage-1 local reactivity: condensed Fukui functions, the dual descriptor and local
softness — they pinpoint *which atoms* donate/accept electrons, i.e. the adsorption
centres, completing the Stage-1 picture the methodology template reports (ADR 0002).
Needs PySCF.

Two methods (same FukuiResult, same interpretation):

  * 'fmo' (default) — frozen-orbital approximation from ONE neutral SCF: the
    condensed Fukui are the per-atom Mulliken populations of the frontier orbitals.
        f-_k = HOMO population on atom k   (where it DONATES electrons -> binds metal)
        f+_k = LUMO population on atom k   (where it ACCEPTS electrons)
    Fast, robust, and the form most green-inhibitor papers actually report.

  * 'fd' — finite differences over N, N-1, N+1 at fixed geometry (Yang-Mortier):
        f+_k = q_k(N)   - q_k(N+1) ;  f-_k = q_k(N-1) - q_k(N)
    More rigorous but needs the (often ill-converged) N+1 anion SCF.

Dual descriptor df_k = f+_k - f-_k  (>0 electrophilic site, <0 nucleophilic site);
local softness s±_k = f±_k * sigma (global softness, 1/eV).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class FukuiResult:
    """Per-atom condensed Fukui functions, dual descriptor, and local softness."""

    symbols: list
    f_plus: list      # nucleophilic (electron-accepting)
    f_minus: list     # electrophilic (electron-donating)
    dual: list        # f+ - f-
    s_plus: list
    s_minus: list
    basis: str = ""

    def as_rows(self) -> list:
        """Per-atom indices as a list of rounded dicts (idx, symbol, f±, dual, s±)."""
        return [dict(idx=i, symbol=s, f_plus=round(fp, 4), f_minus=round(fm, 4),
                     dual=round(d, 4), s_plus=round(sp, 4), s_minus=round(sm, 4))
                for i, (s, fp, fm, d, sp, sm) in enumerate(zip(
                    self.symbols, self.f_plus, self.f_minus, self.dual,
                    self.s_plus, self.s_minus))]

    def top_donor_sites(self, n: int = 5) -> list:
        """Heavy atoms with the largest f- (the surface-binding / donor centres)."""
        rows = [r for r in self.as_rows() if r["symbol"] != "H"]
        return sorted(rows, key=lambda r: r["f_minus"], reverse=True)[:n]


def _atom_pop(mol, c, S):
    """Gross Mulliken population of one MO (coeff vector c), summed per atom."""
    pmu = c * (S @ c)
    sl = mol.aoslice_by_atom()
    return np.array([pmu[sl[a, 2]:sl[a, 3]].sum() for a in range(mol.natm)])


def _scf(symbols, coords, charge, spin, basis, xc):
    from pyscf import dft, gto
    mol = gto.M(atom=[[s, tuple(c)] for s, c in zip(symbols, coords)],
                basis=basis, charge=charge, spin=spin, verbose=0)
    mf = (dft.RKS(mol) if spin == 0 else dft.UKS(mol))
    mf.xc = xc
    mf.kernel()
    if not mf.converged:                      # second-order fallback
        mf = mf.newton()
        mf.kernel()
    return mol, mf


def _result(symbols, f_plus, f_minus, softness, basis):
    dual = [p - m for p, m in zip(f_plus, f_minus)]
    s = softness if softness is not None else 1.0
    return FukuiResult(list(symbols), list(f_plus), list(f_minus), dual,
                       [p * s for p in f_plus], [m * s for m in f_minus], basis=basis)


def compute_fukui(molecule, basis: str = "6-31G(d)", xc: str = "b3lyp",
                  method: str = "fmo", softness: float | None = None) -> FukuiResult:
    """Condensed Fukui indices for a Molecule (its .charge is the reference N).

    method: 'fmo' (fast, one SCF, frontier-orbital populations) or 'fd' (finite
    difference over N/N-1/N+1). 6-31G(d) is used by default — diffuse functions
    make Mulliken populations ill-defined and slow the anion SCF.
    """
    sym, c, q0 = molecule.symbols, molecule.coords, molecule.charge
    if method == "fmo":
        mol, mf = _scf(sym, c, q0, 0, basis, xc)
        S = mf.get_ovlp()
        homo = int(np.where(mf.mo_occ > 0)[0].max())
        f_minus = _atom_pop(mol, mf.mo_coeff[:, homo], S).tolist()      # HOMO -> donor
        f_plus = _atom_pop(mol, mf.mo_coeff[:, homo + 1], S).tolist()   # LUMO -> acceptor
        return _result(sym, f_plus, f_minus, softness, f"{basis} (FMO)")
    if method == "fd":
        qN = np.asarray(_scf(sym, c, q0, 0, basis, xc)[1].mulliken_pop(verbose=0)[1])
        qcat = np.asarray(_scf(sym, c, q0 + 1, 1, basis, xc)[1].mulliken_pop(verbose=0)[1])
        qan = np.asarray(_scf(sym, c, q0 - 1, 1, basis, xc)[1].mulliken_pop(verbose=0)[1])
        return _result(sym, (qN - qan).tolist(), (qcat - qN).tolist(),
                       softness, f"{basis} (FD)")
    raise ValueError(f"Unknown method {method!r}; use 'fmo' or 'fd'.")
