"""corrosim.qm._backend_pyscf.

Single home for every PySCF import the QM pipeline defers.

PySCF and geomeTRIC ship no Windows wheels and live behind the optional ``qm``
extra that only exists inside the corrosim-qm Docker image, so importing them at
a public module's top would break ``import corrosim`` in the venv where the
whole non-QM pipeline runs. Every PySCF-using call path instead does a single
lazy ``from . import _backend_pyscf`` and reaches the symbols through it, so the
dependency is declared in exactly one place. The guard below turns a missing
extra into a clear "run in the corrosim-qm image" hint rather than a bare
ModuleNotFoundError.
"""
from __future__ import annotations

try:
    # `solvent` is imported for its side effect: it registers the .ddCOSMO()
    # implicit-solvation method onto the mean-field object build_rks builds
    from pyscf import dft, gto, solvent
    from pyscf.geomopt.geometric_solver import optimize
    from pyscf.hessian import thermo
    from pyscf.tools import cubegen
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "the QM engines (pyscf, geometric) run only in the corrosim-qm "
        "Docker image; see CLAUDE.md 1.3"
    ) from exc

__all__ = ["cubegen", "dft", "gto", "optimize", "solvent", "thermo"]
