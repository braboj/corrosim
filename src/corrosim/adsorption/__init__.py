"""corrosim.adsorption — Stage-2/3 classical adsorption (ADR 0011).

Shared slab/vdW primitives (`surface`), the UFF physisorption estimate
(`adsorption`), the Monte Carlo pose search (`mc`), and Brownian MD (`md`).
"""
from __future__ import annotations

from .adsorption import LAMMPS_HANDOFF_NOTE, build_adsorption_system, estimate_adsorption_energy
from .mc import run_mc
from .md import run_md
from .surface import (
    EV_TO_KJMOL,
    SURFACE_FACET,
    UFF,
    build_slab,
    initial_adsorption_pose,
    orient_flat,
    rot,
    uff_mixing,
    uff_vdw_energy,
    uff_vdw_forces,
)

__all__ = ["LAMMPS_HANDOFF_NOTE", "build_adsorption_system", "estimate_adsorption_energy",
           "run_mc", "run_md", "EV_TO_KJMOL", "SURFACE_FACET", "UFF", "build_slab",
           "initial_adsorption_pose", "orient_flat", "rot",
           "uff_mixing", "uff_vdw_energy", "uff_vdw_forces"]
