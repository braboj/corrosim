"""
corrosim — automated corrosion-inhibitor screening
===================================================
Pipeline: SMILES/name -> 3D geometry -> QM (xTB or DFT) -> reactivity
descriptors -> report, plus Stage-2 adsorption-structure prep.

Quick use:
    from corrosim import screen
    df, report = screen(["kaempferol", "quercetin", "isorhamnetin"],
                        metal="Fe(110)", engine="xtb",
                        out_html="report.html")
"""
from __future__ import annotations

from .adsorption import LAMMPS_HANDOFF_NOTE, build_adsorption_system, estimate_adsorption_energy
from .descriptors import METAL_WORK_FUNCTION, compute_descriptors, total_negative_charge
from .engines import EngineResult, run_engine
from .fukui import FukuiResult, compute_fukui
from .molecules import (
    LIBRARY,
    Molecule,
    build_molecule,
    build_protonated,
    enumerate_protonation_sites,
)
from .presets import ARGHEL, CaseStudy, case_study
from .report import build_html_report, rank_inhibitors, results_dataframe

__all__ = ["screen", "analyse_one", "analyse_molecule", "build_molecule",
           "build_protonated", "enumerate_protonation_sites", "Molecule",
           "LIBRARY", "run_engine", "EngineResult", "compute_descriptors",
           "total_negative_charge", "compute_fukui", "FukuiResult",
           "build_adsorption_system",
           "estimate_adsorption_energy", "METAL_WORK_FUNCTION",
           "LAMMPS_HANDOFF_NOTE", "rank_inhibitors", "build_html_report",
           "CaseStudy", "ARGHEL", "case_study"]


def analyse_molecule(mol: Molecule, metal: str = "Fe(110)",
                     engine: str = "xtb", adsorption: bool = False,
                     **engine_kwargs) -> dict:
    """Full Stage-1 analysis of a pre-built Molecule. Returns a flat row dict.

    Respects mol.charge (e.g. +1 for a protonated inhibitor in acid) and records
    TNC when the engine returns atomic charges. adsorption=True also adds the fast
    UFF vdW physisorption estimate (Stage 2).
    """
    res = run_engine(mol.symbols, mol.coords, engine=engine, charge=mol.charge,
                     **engine_kwargs)
    desc = compute_descriptors(res.homo_ev, res.lumo_ev, metal=metal)
    row = {"name": mol.name, "formula": mol.formula, "n_atoms": mol.n_atoms,
           "smiles": mol.smiles, "charge": mol.charge, "level": res.level}
    row.update(desc.as_dict())
    row["e_total_ev"] = res.e_total_ev          # total SCF energy (for pKa cycles)
    row["tnc"] = total_negative_charge(res.charges)
    if adsorption:
        metal_symbol = metal.split("(")[0]
        try:
            ads = estimate_adsorption_energy(mol, metal=metal_symbol)
            row["e_ads_kjmol"] = ads["e_ads_kjmol"]
            row["e_ads_ev"] = ads["e_ads_ev"]
        except ValueError:
            row["e_ads_kjmol"] = None
            row["e_ads_ev"] = None
    return row


def analyse_one(name_or_smiles: str, metal: str = "Fe(110)",
                engine: str = "xtb", ff: str = "MMFF",
                adsorption: bool = False, **engine_kwargs) -> dict:
    """Build a single inhibitor from a name/SMILES, then analyse it (Stage 1)."""
    mol = build_molecule(name_or_smiles, ff=ff)
    return analyse_molecule(mol, metal=metal, engine=engine,
                            adsorption=adsorption, **engine_kwargs)


def screen(inhibitors, metal: str = "Fe(110)", medium: str = "1 M HCl",
           engine: str = "xtb", ff: str = "MMFF", adsorption: bool = False,
           out_html: str | None = None, progress=print, **engine_kwargs):
    """
    Screen a list of inhibitors. Returns (DataFrame, html_path_or_None).
    Set adsorption=True to add the Stage-2 UFF vdW physisorption estimate.
    """
    rows = []
    for inh in inhibitors:
        if progress:
            progress(f"  analysing {inh} ...")
        rows.append(analyse_one(inh, metal=metal, engine=engine, ff=ff,
                                adsorption=adsorption, **engine_kwargs))
    df = results_dataframe(rows)
    level = rows[0]["level"] if rows else engine
    html_path = None
    if out_html:
        html_path = build_html_report(df, metal=metal, medium=medium,
                                      level=level, out_path=out_html)
    return df, html_path
