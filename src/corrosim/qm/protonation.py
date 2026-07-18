"""corrosim.qm.protonation.

Choose where an inhibitor protonates: enumerate the RDKit protonation sites, run
a fast screening single point on each conjugate acid, and keep the lowest-energy
(most stable) cation. This is chemistry shared by the DFT descriptor matrix
(run_dft) and the pKaH cycle (run_pka), not CLI plumbing, so it lives in the QM
layer. The screen needs a fast engine (GFN2-xTB via run_engine), so it runs in
the corrosim-qm image.
"""
from __future__ import annotations

import math
from collections.abc import Callable

from corrosim.molecules import (
    Molecule,
    build_protonated,
    enumerate_protonation_sites,
)

from .engines import run_engine


def best_protonation_site(
    name: str,
    select_engine: str = "xtb",
    log: Callable[[str], None] | None = None,
) -> tuple[int, Molecule]:
    """Return ``(site_idx, cation)`` for the most stable conjugate acid.

    All protonation isomers share the same atoms, so their total energies are
    directly comparable; the lowest-energy cation is the preferred protonation
    site. Sites that RDKit or the engine reject are skipped.

    Args:
        name: Library name or SMILES of the neutral molecule.
        select_engine: Fast engine for the screen (default GFN2-xTB, via
            ``run_engine``).
        log: Optional sink for per-site progress lines (e.g. a driver's stderr
            logger); ``None`` runs the screen silently.

    Returns:
        ``(site_idx, protonated Molecule)`` for the most stable cation.

    Raises:
        RuntimeError: If no protonation site yields a usable single point, or
            if the selection engine returns no finite total energy to rank on
            (e.g. an engine that reports frontier orbitals only), which cannot
            choose a most-stable cation.
    """
    def _silent(_msg: str) -> None:
        pass

    emit = log if log is not None else _silent
    best: tuple[int, float, Molecule] | None = None
    n_ran = 0
    for idx in enumerate_protonation_sites(name):
        try:
            mol = build_protonated(name, idx)
            res = run_engine(mol.symbols, mol.coords, engine=select_engine,
                             charge=mol.charge)
        except Exception as exc:
            # Skip sites RDKit / the engine reject
            emit(f"    site {idx}: skipped ({exc})")
            continue
        n_ran += 1

        # An engine that reports no total energy returns a non-finite e_total
        # (orca/gaussian are HOMO/LUMO-only), and ``nan < best`` is always
        # False — so ranking on it silently keeps the first-enumerated site.
        # Skip the non-finite result and fail loud below instead.
        if not math.isfinite(res.e_total_ev):
            emit(f"    site {idx}: no finite energy from {select_engine!r}")
            continue
        emit(f"    site {idx}: E = {res.e_total_ev:.3f} eV")
        if best is None or res.e_total_ev < best[1]:
            best = (idx, res.e_total_ev, mol)
    if best is None:
        if n_ran:
            raise RuntimeError(
                f"select_engine {select_engine!r} returned no finite total "
                f"energy for {name!r}, so the most stable protonation site "
                "cannot be chosen; use an engine that reports a total energy "
                "(e.g. xtb) for site selection.")
        raise RuntimeError(f"No usable protonation site for {name!r}")
    return best[0], best[2]
