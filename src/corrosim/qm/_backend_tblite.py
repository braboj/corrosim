"""corrosim.qm._backend_tblite.

Single home for the tblite (GFN2-xTB) import the QM pipeline defers.

tblite ships no Windows wheels and lives behind the optional ``qm`` extra that
only exists inside the corrosim-qm Docker image, so run_xtb reaches it through a
single lazy ``from . import _backend_tblite`` instead of importing it at a
public module's top. The guard turns a missing extra into a clear "run in the
corrosim-qm image" hint rather than a bare ModuleNotFoundError.
"""
from __future__ import annotations

try:
    from tblite.interface import Calculator
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "the xTB engine (tblite) runs only in the corrosim-qm Docker "
        "image; see CLAUDE.md 1.3"
    ) from exc

__all__ = ["Calculator"]
