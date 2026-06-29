"""
corrosim.runs.make_figures  (M5)
================================
Regenerate the full manuscript figure set into figures/. Reads the committed data
(dft_descriptors.csv, *_fukui.json), re-runs the fast classical MC/MD, and renders
orbital isosurfaces from any *_homo.cube / *_lumo.cube present.

Runs in the venv (no QM container needed unless you want fresh orbital cubes):
    python -m corrosim.runs.make_figures
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import matplotlib
matplotlib.use("Agg")

import pandas as pd

from corrosim import build_molecule, figures
from corrosim.fukui import FukuiResult
from corrosim.mc import run_mc
from corrosim.md import run_md

ORDER = ["kaempferol", "quercetin", "isorhamnetin"]


def _fukui_from_json(path):
    rows = json.load(open(path))
    n = max(r["idx"] for r in rows) + 1
    fr = FukuiResult([None] * n, [0.] * n, [0.] * n, [0.] * n, [0.] * n, [0.] * n)
    for r in rows:
        i = r["idx"]
        fr.symbols[i] = r["symbol"]; fr.f_plus[i] = r["f_plus"]
        fr.f_minus[i] = r["f_minus"]; fr.dual[i] = r["dual"]
    return fr


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="corrosim-make-figures")
    p.add_argument("--outdir", default="figures")
    p.add_argument("--steps-mc", type=int, default=5000)
    p.add_argument("--steps-md", type=int, default=6000)
    args = p.parse_args(argv)
    os.makedirs(args.outdir, exist_ok=True)
    out = lambda f: os.path.join(args.outdir, f)
    log = lambda m: print(m, file=sys.stderr)

    log("Fig 1: structures")
    figures.plot_structures(ORDER, out=out("fig1_structures.png"))

    if os.path.exists("dft_descriptors.csv"):
        log("Fig 2/3: FMO energy diagram, descriptors, protonation effect")
        df = pd.read_csv("dft_descriptors.csv")
        naq = (df[(df.form == "neutral") & (df.phase == "aqueous")]
               .set_index("name").loc[ORDER].reset_index())
        rows = naq.to_dict("records")
        figures.plot_mo_energy_diagram(rows, metal="Fe(110)", out=out("fig2_mo_diagram.png"))
        figures.plot_descriptor_comparison(rows, out=out("fig3_descriptors.png"))
        figures.plot_protonation_effect(df, ORDER, out=out("fig3b_protonation.png"))

    log("Fig 4: Fukui maps")
    for name in ORDER:
        jf = f"{name}_fukui.json"
        if os.path.exists(jf):
            figures.plot_fukui(_fukui_from_json(jf), molecule=build_molecule(name),
                               out=out(f"fig4_{name}_fukui.png"),
                               title=f"{name} — condensed Fukui (B3LYP/6-31G(d))")

    log("Fig 5/6: MC pose + annealing, MD RDF (re-running)")
    for name in ORDER:
        m = build_molecule(name)
        mc = run_mc(m, metal="Fe", n_steps=args.steps_mc)
        figures.plot_adsorption_pose(mc, out=out(f"fig5_{name}_mc_pose.png"))
        figures.plot_mc_energy(mc, out=out(f"fig5_{name}_mc_energy.png"))
        md = run_md(m, metal="Fe", n_steps=args.steps_md, start_positions=mc.best_positions)
        figures.plot_rdf(md, out=out(f"fig6_{name}_rdf.png"))

    log("Fig 2b: HOMO/LUMO isosurfaces (from existing cubes)")
    for name in ORDER:
        for which in ("homo", "lumo"):
            cube = f"{name}_{which}.cube"
            if os.path.exists(cube):
                figures.render_orbital(cube, out=out(f"fig2b_{name}_{which}.png"),
                                       title=f"{name} {which.upper()}")

    log("Fig 7: ESP / MEP maps (from existing density+esp cubes)")
    for name in ORDER:
        dens, esp = f"{name}_density.cube", f"{name}_esp.cube"
        if os.path.exists(dens) and os.path.exists(esp):
            figures.render_esp(dens, esp, out=out(f"fig7_{name}_esp.png"),
                               title=f"{name} — ESP on density isosurface")

    print(f"figures written to {args.outdir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
