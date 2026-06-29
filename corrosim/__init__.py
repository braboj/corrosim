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
from .molecules import build_molecule, Molecule, LIBRARY
from .engines import run_engine, EngineResult
from .descriptors import compute_descriptors, METAL_WORK_FUNCTION
from .report import results_dataframe, rank_inhibitors, build_html_report
from .adsorption import (build_adsorption_system, estimate_adsorption_energy,
                         LAMMPS_HANDOFF_NOTE)

__all__ = ["screen", "analyse_one", "build_molecule", "Molecule", "LIBRARY",
           "run_engine", "compute_descriptors", "build_adsorption_system",
           "estimate_adsorption_energy", "METAL_WORK_FUNCTION",
           "LAMMPS_HANDOFF_NOTE", "rank_inhibitors", "build_html_report"]


def analyse_one(name_or_smiles: str, metal: str = "Fe(110)",
                engine: str = "xtb", ff: str = "MMFF",
                adsorption: bool = False, **engine_kwargs) -> dict:
    """Full Stage-1 analysis of a single inhibitor. Returns a flat row dict.

    adsorption=True also adds the fast UFF vdW physisorption estimate (Stage 2).
    """
    mol = build_molecule(name_or_smiles, ff=ff)
    res = run_engine(mol.symbols, mol.coords, engine=engine, **engine_kwargs)
    desc = compute_descriptors(res.homo_ev, res.lumo_ev, metal=metal)
    row = {"name": mol.name, "formula": mol.formula, "n_atoms": mol.n_atoms,
           "smiles": mol.smiles, "level": res.level}
    row.update(desc.as_dict())
    if adsorption:
        metal_symbol = metal.split("(")[0]
        try:
            ads = estimate_adsorption_energy(mol, metal=metal_symbol)
            row["e_ads_kjmol"] = ads["e_ads_kjmol"]
            row["e_ads_ev"] = ads["e_ads_ev"]
        except ValueError as e:
            row["e_ads_kjmol"] = None
            row["e_ads_ev"] = None
    return row


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
