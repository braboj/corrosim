"""corrosim.qm.cubes.

PySCF volumetric cube writers for the report's 3D figures: HOMO/LUMO orbitals,
the molecular electrostatic potential (MEP), and the paired electron-density +
ESP grids. Each runs one DFT SCF (via engines.build_rks, so the grid and
implicit-solvent setup match the descriptor engines) and then calls
pyscf.tools.cubegen — so cube *writing* lives in the QM layer and runs only in
the corrosim-qm image. corrosim.report.figures reads the resulting .cube files
and renders them (matplotlib + scikit-image), and runs anywhere.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import numpy as np

from .engines import build_rks, run_scf

if TYPE_CHECKING:
    import numpy.typing as npt


def _cube_scf(symbols, coords, basis, xc, charge, solvent=None):
    """Run one cube-grade DFT SCF; return the (mol, kerneled mf).

    Delegates to the shared engines.build_rks so the grid + implicit-solvent
    setup matches the descriptor engines exactly, and converges through the
    shared run_scf ladder so a diffuse-basis cube SCF is not left unconverged.
    """
    mf = build_rks(symbols, coords, basis, xc, charge, solvent)
    mf = run_scf(mf, label=f"{xc}/{basis} cube")
    return mf.mol, mf


def write_orbital_cubes(symbols: Sequence[str], coords: npt.ArrayLike,
                        prefix: str = "mol", basis: str = "6-31G(d)",
                        xc: str = "b3lyp", charge: int = 0,
                        nx: int = 70) -> dict:
    """One SCF, then write ``{prefix}_homo.cube`` and ``{prefix}_lumo.cube``.

    A modest basis is enough — orbital *shapes* are basis-insensitive, so this
    stays fast and looks the same as the descriptor-level basis. Run in the QM
    container; render with render_orbital().

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        prefix: Output path prefix.
        basis: The AO basis set.
        xc: The exchange-correlation functional.
        charge: Net molecular charge.
        nx: Grid points per axis.

    Returns:
        The written paths keyed ``'homo'`` / ``'lumo'``.
    """
    from . import _backend_pyscf as _pyscf
    mol, mf = _cube_scf(symbols, coords, basis, xc, charge)
    occ = mf.mo_occ
    homo = int(np.where(occ > 0)[0].max())
    lumo = int(np.where(occ == 0)[0].min())
    paths = {"homo": f"{prefix}_homo.cube", "lumo": f"{prefix}_lumo.cube"}
    _pyscf.cubegen.orbital(mol, paths["homo"], mf.mo_coeff[:, homo],
                           nx=nx, ny=nx, nz=nx)
    _pyscf.cubegen.orbital(mol, paths["lumo"], mf.mo_coeff[:, lumo],
                           nx=nx, ny=nx, nz=nx)
    return paths


def write_density_esp_cubes(symbols: Sequence[str], coords: npt.ArrayLike,
                            prefix: str = "mol", basis: str = "6-31G(d)",
                            xc: str = "b3lyp", charge: int = 0,
                            solvent: str | None = None, nx: int = 80,
                            margin: float = 3.5) -> dict:
    """One SCF, then write the density and ESP cubes on a *shared* grid.

    ``{prefix}_density.cube`` and ``{prefix}_esp.cube``. Pairing the two on the
    same grid lets render_esp() colour the density isosurface by the MEP (the
    classic ESP map). The MEP integral is the slow part — a modest grid
    (nx≈80) and valence basis are plenty for a qualitative map. Run in the QM
    container; render with render_esp().

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        prefix: Output path prefix.
        basis: The AO basis set.
        xc: The exchange-correlation functional.
        charge: Net molecular charge.
        solvent: Implicit solvent ('water') or gas phase (None).
        nx: Grid points per axis.
        margin: Padding around the molecule (Å).

    Returns:
        The written paths keyed ``'density'`` / ``'esp'``.
    """
    from . import _backend_pyscf as _pyscf
    mol, mf = _cube_scf(symbols, coords, basis, xc, charge, solvent=solvent)
    dm = mf.make_rdm1()
    paths = {"density": f"{prefix}_density.cube", "esp": f"{prefix}_esp.cube"}
    # Identical (mol, nx, margin) -> identical grid for both cubes
    _pyscf.cubegen.density(mol, paths["density"], dm, nx=nx, ny=nx, nz=nx,
                           margin=margin)
    _pyscf.cubegen.mep(mol, paths["esp"], dm, nx=nx, ny=nx, nz=nx,
                       margin=margin)
    return paths
