"""corrosim.runs.make_figures  (M5).

Regenerate the full manuscript figure set into report/figures/. Reads the
committed data (dft_descriptors_ff.csv, *_fukui.json), re-runs the fast
classical MC/MD, and renders orbital isosurfaces from any *_homo.cube /
*_lumo.cube present.

Runs in the venv (no QM container needed unless you want fresh orbital cubes):
    python -m corrosim.runs.make_figures
"""
from __future__ import annotations

import argparse
import os
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")

import pandas as pd

from corrosim import build_molecule
from corrosim.adsorption.mc import run_mc
from corrosim.adsorption.md import run_md
from corrosim.qm.fukui import FukuiResult
from corrosim.report import figures
from corrosim.report.report_layout import figure_path
from corrosim.runs._cli import add_case_arg, read_json, resolve_case
from corrosim.runs._cli import stderr_log as log

if TYPE_CHECKING:
    from corrosim.presets import CaseStudy

# One figure group per helper; each is guarded on its own input data so a
# partial results/ / cubes/ tree renders whatever is available.
_Out = Callable[[str], str]


def _fig_structures(order: list[str], out: _Out) -> None:
    """Fig 1: the 2D molecular structures."""
    log("Fig 1: structures")
    figures.plot_structures(order, out=out("fig1_structures.png"))


def _fig_descriptors(
    args: argparse.Namespace,
    case: CaseStudy,
    order: list[str],
    out: _Out,
) -> None:
    """Fig 2/3: FMO diagram, descriptor comparison, protonation effect."""
    ff_csv = f"{args.datadir}/dft_descriptors_ff.csv"
    if not os.path.exists(ff_csv):
        return
    log("Fig 2/3: FMO energy diagram, descriptors, protonation effect")
    df = pd.read_csv(ff_csv)
    naq = (df[(df.form == "neutral") & (df.phase == "aqueous")]
           .set_index("name").loc[order].reset_index())
    rows = naq.to_dict("records")
    figures.plot_mo_energy_diagram(rows, metal=case.metal,
                                   out=out("fig2_mo_diagram.png"))
    figures.plot_descriptor_comparison(rows, out=out("fig3_descriptors.png"))
    # fig3b prefers the DFT-optimised cations — the more accurate basis for the
    # speciation/pKa story; the FF matrix is the fallback.
    opt_csv = f"{args.datadir}/dft_descriptors_opt.csv"
    if os.path.exists(opt_csv):
        figures.plot_protonation_effect(
            pd.read_csv(opt_csv), order, out=out("fig3b_protonation.png"),
            geometry_label="DFT-optimised, B3LYP/6-311++G(d,p)")
    else:
        figures.plot_protonation_effect(
            df, order, out=out("fig3b_protonation.png"))


def _fig_fukui(args: argparse.Namespace, order: list[str], out: _Out) -> None:
    """Fig 4: condensed Fukui maps from the committed ``*_fukui.json``."""
    log("Fig 4: Fukui maps")
    for name in order:
        jf = f"{args.datadir}/{name}_fukui.json"
        if os.path.exists(jf):
            figures.plot_fukui(
                FukuiResult.from_rows(read_json(jf)),
                molecule=build_molecule(name),
                out=out(f"fig4_{name}_fukui.png"),
                title=f"{name} — condensed Fukui (B3LYP/6-31G(d))")


def _fig_adsorption(
    args: argparse.Namespace,
    case: CaseStudy,
    order: list[str],
    out: _Out,
) -> None:
    """Fig 5/6: MC pose + annealing trace and MD RDF (re-runs MC/MD)."""
    log("Fig 5/6: MC pose + annealing, MD RDF (re-running)")
    for name in order:
        m = build_molecule(name)
        mc = run_mc(m, metal=case.metal_element, n_steps=args.steps_mc)
        figures.plot_adsorption_pose(mc, out=out(f"fig5_{name}_mc_pose.png"))
        figures.plot_mc_energy(mc, out=out(f"fig5_{name}_mc_energy.png"))
        md = run_md(m, metal=case.metal_element, n_steps=args.steps_md,
                    start_positions=mc.best_positions)
        figures.plot_rdf(md, out=out(f"fig6_{name}_rdf.png"))


def _fig_orbitals(args: argparse.Namespace, order: list[str],
                  out: _Out) -> None:
    """Fig 2b: HOMO/LUMO isosurfaces from any existing cubes."""
    log("Fig 2b: HOMO/LUMO isosurfaces (from existing cubes)")
    for name in order:
        for which in ("homo", "lumo"):
            cube = f"{args.cubedir}/{name}_{which}.cube"
            if os.path.exists(cube):
                figures.render_orbital(
                    cube, out=out(f"fig2b_{name}_{which}.png"),
                    title=f"{name} {which.upper()}")


def _fig_esp(args: argparse.Namespace, order: list[str], out: _Out) -> None:
    """Fig 7: ESP / MEP maps from any existing density+esp cubes."""
    log("Fig 7: ESP / MEP maps (from existing density+esp cubes)")
    for name in order:
        dens = f"{args.cubedir}/{name}_density.cube"
        esp = f"{args.cubedir}/{name}_esp.cube"
        if os.path.exists(dens) and os.path.exists(esp):
            figures.render_esp(dens, esp, out=out(f"fig7_{name}_esp.png"),
                               title=f"{name} — ESP on density isosurface")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: regenerate the manuscript figure set.

    Writes into ``report/figures/``.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv``).

    Returns:
        The process exit code (0 on success).
    """
    p = argparse.ArgumentParser(prog="corrosim-make-figures")
    add_case_arg(p)
    p.add_argument("--outdir", default="report/figures")
    p.add_argument("--datadir", default="results",
                   help="Where the descriptor/Fukui data live.")
    p.add_argument("--cubedir", default="cubes",
                   help="Where the volumetric cubes live.")
    p.add_argument("--steps-mc", type=int, default=5000)
    p.add_argument("--steps-md", type=int, default=6000)
    args = p.parse_args(argv)
    case = resolve_case(args)
    order = case.molecule_list()
    os.makedirs(args.outdir, exist_ok=True)

    def out(f: str) -> str:
        # Place each figure in its stage subfolder.
        path = figure_path(args.outdir, f)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    _fig_structures(order, out)
    _fig_descriptors(args, case, order, out)
    _fig_fukui(args, order, out)
    _fig_adsorption(args, case, order, out)
    _fig_orbitals(args, order, out)
    _fig_esp(args, order, out)

    print(f"figures written to {args.outdir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
