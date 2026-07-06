"""corrosim.fukui.

Stage-1 local reactivity: condensed Fukui functions, the dual descriptor and
local softness — they pinpoint *which atoms* donate/accept electrons, i.e. the
adsorption centres, completing the Stage-1 picture the methodology template
reports. Needs PySCF.

Two methods (same FukuiResult, same interpretation):

  * 'fmo' (default) — frozen-orbital approximation from ONE neutral SCF: the
    condensed Fukui are the per-atom Mulliken populations of the frontier
    orbitals.
        f-_k = HOMO population on atom k   (DONATES electrons -> binds metal)
        f+_k = LUMO population on atom k   (ACCEPTS electrons)
    Fast, robust, and the form most green-inhibitor papers actually report.

  * 'fd' — finite differences over N, N-1, N+1 at fixed geometry
    (Yang-Mortier):
        f+_k = q_k(N)   - q_k(N+1) ;  f-_k = q_k(N-1) - q_k(N)
    More rigorous but needs the (often ill-converged) N+1 anion SCF.

Dual descriptor df_k = f+_k - f-_k  (>0 electrophilic site, <0 nucleophilic
site); local softness s±_k = f±_k * sigma (global softness, 1/eV).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from corrosim.molecules import Molecule


@dataclass
class FukuiResult:
    """Per-atom condensed Fukui functions, dual descriptor, and local
    softness.
    """

    symbols: list[str]
    # nucleophilic (electron-accepting)
    f_plus: list[float]
    # electrophilic (electron-donating)
    f_minus: list[float]
    # f+ - f-
    dual: list[float]
    s_plus: list[float]
    s_minus: list[float]
    basis: str = ""

    @classmethod
    def from_populations(
        cls,
        symbols: Sequence[str],
        f_plus: Sequence[float],
        f_minus: Sequence[float],
        softness: float | None,
        basis: str = "",
    ) -> FukuiResult:
        """Build from per-atom f± populations, deriving dual + local softness.

        Args:
            symbols: Element symbols.
            f_plus: Per-atom f+ (nucleophilic / electron-accepting).
            f_minus: Per-atom f- (electrophilic / electron-donating).
            softness: Global softness (1/eV) scaling s±; 1.0 if None.
            basis: The basis-set label recorded on the result.

        Returns:
            The assembled result (``dual = f+ - f-``, ``s± = f± · softness``).
        """
        dual = [p - m for p, m in zip(f_plus, f_minus)]
        s = softness if softness is not None else 1.0
        return cls(
            list(symbols),
            list(f_plus),
            list(f_minus),
            dual,
            [p * s for p in f_plus],
            [m * s for m in f_minus],
            basis=basis,
        )

    @classmethod
    def from_rows(cls, rows: Sequence[dict]) -> FukuiResult:
        """Reconstruct from :meth:`as_rows` output (the round-trip inverse).

        Args:
            rows: Per-atom dicts as produced by :meth:`as_rows` — each with
                ``idx``, ``symbol``, ``f_plus``, ``f_minus``, ``dual`` and,
                when present, ``s_plus`` / ``s_minus``.

        Returns:
            The reconstructed result; ``basis`` is not carried in the rows and
            defaults to ``""``.
        """
        n = max(r["idx"] for r in rows) + 1
        symbols = [""] * n
        f_plus = [0.0] * n
        f_minus = [0.0] * n
        dual = [0.0] * n
        s_plus = [0.0] * n
        s_minus = [0.0] * n
        for r in rows:
            i = r["idx"]
            symbols[i] = r["symbol"]
            f_plus[i] = r["f_plus"]
            f_minus[i] = r["f_minus"]
            dual[i] = r["dual"]
            s_plus[i] = r.get("s_plus", 0.0)
            s_minus[i] = r.get("s_minus", 0.0)
        return cls(symbols, f_plus, f_minus, dual, s_plus, s_minus)

    def as_rows(self) -> list[dict]:
        """Per-atom indices as a list of rounded dicts.

        Returns:
            One dict per atom with ``idx``, ``symbol``, ``f_plus``,
            ``f_minus``, ``dual`` and ``s_plus`` / ``s_minus``.
        """
        return [dict(idx=i, symbol=s, f_plus=round(fp, 4),
                     f_minus=round(fm, 4), dual=round(d, 4),
                     s_plus=round(sp, 4), s_minus=round(sm, 4))
                for i, (s, fp, fm, d, sp, sm) in enumerate(zip(
                    self.symbols, self.f_plus, self.f_minus, self.dual,
                    self.s_plus, self.s_minus))]

    def top_donor_sites(self, n: int = 5) -> list[dict]:
        """Heavy atoms with the largest f- (surface-binding / donor centres).

        Args:
            n: Number of top sites to return.

        Returns:
            The ``n`` non-hydrogen rows with the largest ``f_minus``.
        """
        rows = [r for r in self.as_rows() if r["symbol"] != "H"]
        return sorted(rows, key=lambda r: r["f_minus"], reverse=True)[:n]


def _atom_pop(mol, mo_coeff, S):
    """Gross Mulliken population of one MO, summed per atom.

    Args:
        mol: The PySCF molecule (for the per-atom AO slices).
        mo_coeff: The MO coefficient vector (one orbital column).
        S: The AO overlap matrix.

    Returns:
        The per-atom summed Mulliken population as an ndarray.
    """
    pmu = mo_coeff * (S @ mo_coeff)
    sl = mol.aoslice_by_atom()
    return np.array([pmu[sl[a, 2]:sl[a, 3]].sum() for a in range(mol.natm)])


def _scf(symbols, coords, charge, spin, basis, xc):
    """Run one (U/R)KS SCF, with a second-order fallback if unconverged.

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        charge: Net molecular charge.
        spin: Number of unpaired electrons (0 -> RKS, else UKS).
        basis: The AO basis set.
        xc: The exchange-correlation functional.

    Returns:
        ``(mol, mf)`` — the PySCF molecule and the converged mean field.
    """
    from . import _backend_pyscf as _pyscf
    mol = _pyscf.gto.M(atom=[[s, tuple(c)] for s, c in zip(symbols, coords)],
                       basis=basis, charge=charge, spin=spin, verbose=0)
    mf = (_pyscf.dft.RKS(mol) if spin == 0 else _pyscf.dft.UKS(mol))
    mf.xc = xc
    mf.kernel()
    if not mf.converged:
        # second-order fallback
        mf = mf.newton()
        mf.kernel()
    return mol, mf


def _mulliken_charges(symbols, coords, charge, spin, basis, xc):
    """Per-atom Mulliken charges (q = Z - population) from one SCF.

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        charge: Net molecular charge.
        spin: Number of unpaired electrons (0 -> RKS, else UKS).
        basis: The AO basis set.
        xc: The exchange-correlation functional.

    Returns:
        The per-atom Mulliken charges as an ndarray.
    """
    _, mf = _scf(symbols, coords, charge, spin, basis, xc)
    return np.asarray(mf.mulliken_pop(verbose=0)[1])


def compute_fukui(molecule: Molecule, basis: str = "6-31G(d)",
                  xc: str = "b3lyp", method: str = "fmo",
                  softness: float | None = None) -> FukuiResult:
    """Condensed Fukui indices for a molecule (its .charge is the reference N).

    6-31G(d) is used by default — diffuse functions make Mulliken populations
    ill-defined and slow the anion SCF.

    Args:
        molecule: The molecule (symbols, coords, charge).
        basis: The AO basis set.
        xc: The exchange-correlation functional.
        method: 'fmo' (fast, one SCF, frontier-orbital populations) or 'fd'
            (finite difference over N/N-1/N+1).
        softness: Global softness (1/eV) scaling the local softness; 1.0 if
            None.

    Returns:
        The per-atom :class:`FukuiResult`.

    Raises:
        ValueError: If ``method`` is not 'fmo' or 'fd'.
    """
    sym, coords, q0 = molecule.symbols, molecule.coords, molecule.charge
    if method == "fmo":
        mol, mf = _scf(sym, coords, q0, 0, basis, xc)
        S = mf.get_ovlp()
        homo = int(np.where(mf.mo_occ > 0)[0].max())
        # HOMO population -> donor sites; LUMO population -> acceptor sites
        f_minus = _atom_pop(mol, mf.mo_coeff[:, homo], S).tolist()
        f_plus = _atom_pop(mol, mf.mo_coeff[:, homo + 1], S).tolist()
        return FukuiResult.from_populations(
            sym, f_plus, f_minus, softness, f"{basis} (FMO)")
    if method == "fd":
        # Yang-Mortier finite differences over N, N-1, N+1 at fixed geometry.
        # mulliken_pop()[1] yields CHARGES (q = Z - population), so the N/N±1
        # differences below are taken on charges directly and the signs already
        # come out right — do not "correct" them.
        qN = _mulliken_charges(sym, coords, q0, 0, basis, xc)
        qcat = _mulliken_charges(sym, coords, q0 + 1, 1, basis, xc)
        qan = _mulliken_charges(sym, coords, q0 - 1, 1, basis, xc)
        return FukuiResult.from_populations(
            sym, (qN - qan).tolist(), (qcat - qN).tolist(),
            softness, f"{basis} (FD)")
    raise ValueError(f"Unknown method {method!r}; use 'fmo' or 'fd'.")
