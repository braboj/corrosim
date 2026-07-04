"""corrosim.runs.run_mc  (M3 driver).

Monte Carlo adsorption pose search (simulated annealing) for the flavonoids on the
metal slab — Stage-2. Writes a summary JSON to results/; figures are rendered
separately by make_figures. Pure classical (numpy + ASE); runs anywhere, no QM.

    python -m corrosim.runs.run_mc --molecules kaempferol,quercetin,isorhamnetin \
        --metal Fe --steps 4000
"""
from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from corrosim import build_molecule
from corrosim.adsorption.mc import run_mc
from corrosim.presets import ARGHEL
from corrosim.runs._cli import (
    add_molecules_arg,
    parse_molecules,
    print_table,
    stderr_log,
    write_json,
)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: run the Monte Carlo adsorption pose search (M3)."""
    p = argparse.ArgumentParser(prog="corrosim-run-mc",
                                description="Monte Carlo adsorption pose search (M3).")
    add_molecules_arg(p)
    p.add_argument("--metal", default=ARGHEL.metal_element, help="Fe | Cu | Al")
    p.add_argument("--steps", type=int, default=4000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--outdir", default="results")
    args = p.parse_args(argv)
    os.makedirs(args.outdir, exist_ok=True)

    summary = []
    for name in parse_molecules(args.molecules):
        stderr_log(f"[{name}] MC pose search ({args.steps} steps) ...")
        m = build_molecule(name)
        r = run_mc(m, metal=args.metal, n_steps=args.steps, seed=args.seed)
        summary.append(dict(name=name, surface=f"{r.metal}{r.surface}",
                            e_ads_ev=r.e_ads_ev, e_ads_kjmol=r.e_ads_kjmol,
                            best_height_A=r.best_height_A,
                            accept_ratio=round(r.n_accept / r.n_steps, 3)))
        stderr_log(f"  E_ads = {r.e_ads_ev:.3f} eV ({r.e_ads_kjmol:.1f} kJ/mol) "
                   f"at {r.best_height_A} Å")

    write_json(f"{args.outdir}/mc_adsorption.json", summary)
    print_table(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
