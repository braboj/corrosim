"""
corrosim.runs.run_mc  (M3 driver)
=================================
Monte Carlo adsorption pose search (simulated annealing) for the flavonoids on the
metal slab — Stage-2. Writes a best-pose figure, an annealing energy-trace figure,
and a summary JSON. Pure classical (numpy + ASE); runs anywhere, no QM container.

    python -m corrosim.runs.run_mc --molecules kaempferol,quercetin,isorhamnetin \
        --metal Fe --steps 4000
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")

from corrosim import build_molecule, figures
from corrosim.mc import run_mc
from corrosim.presets import ARGHEL

DEFAULT_MOLECULES = ARGHEL.molecule_list()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="corrosim-run-mc",
                                description="Monte Carlo adsorption pose search (M3).")
    p.add_argument("--molecules", default=",".join(DEFAULT_MOLECULES))
    p.add_argument("--metal", default=ARGHEL.metal_element, help="Fe | Cu | Al")
    p.add_argument("--steps", type=int, default=4000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--outdir", default="results")
    args = p.parse_args(argv)
    os.makedirs(args.outdir, exist_ok=True)

    summary = []
    for name in [m.strip() for m in args.molecules.split(",") if m.strip()]:
        print(f"[{name}] MC pose search ({args.steps} steps) ...", file=sys.stderr)
        m = build_molecule(name)
        r = run_mc(m, metal=args.metal, n_steps=args.steps, seed=args.seed)
        figures.plot_adsorption_pose(r, out=f"{args.outdir}/{name}_mc_pose.png")
        figures.plot_mc_energy(r, out=f"{args.outdir}/{name}_mc_energy.png")
        summary.append(dict(name=name, surface=f"{r.metal}{r.surface}",
                            e_ads_ev=r.e_ads_ev, e_ads_kjmol=r.e_ads_kjmol,
                            best_height_A=r.best_height_A,
                            accept_ratio=round(r.n_accept / r.n_steps, 3)))
        print(f"  E_ads = {r.e_ads_ev:.3f} eV ({r.e_ads_kjmol:.1f} kJ/mol) "
              f"at {r.best_height_A} Å", file=sys.stderr)

    json.dump(summary, open(f"{args.outdir}/mc_adsorption.json", "w"), indent=2)
    import pandas as pd
    print(pd.DataFrame(summary).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
