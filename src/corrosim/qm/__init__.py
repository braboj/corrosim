"""corrosim.qm — Stage-1 electronic structure (ADR 0011).

Quantum-engine wrappers (xTB, PySCF), global reactivity descriptors, condensed
Fukui indices, pKa estimation, and pH speciation.
"""
from __future__ import annotations

from .descriptors import (
    DESCRIPTOR_META,
    METAL_WORK_FUNCTION,
    compute_descriptors,
    total_negative_charge,
)
from .engines import EngineResult, run_engine
from .fukui import FukuiResult, compute_fukui
from .pka import G_AQ_PROTON_EV, estimate_pka
from .speciation import analyse_speciation, protonation_fraction

__all__ = ["EngineResult", "run_engine", "compute_descriptors", "total_negative_charge",
           "DESCRIPTOR_META", "METAL_WORK_FUNCTION", "FukuiResult", "compute_fukui",
           "G_AQ_PROTON_EV", "estimate_pka", "analyse_speciation", "protonation_fraction"]
