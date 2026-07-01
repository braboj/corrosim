"""corrosim.runs.run_md  (M4 driver).

Brownian (overdamped-Langevin) rigid-body MD of the inhibitor over the metal slab
at 298 K -> metal-X radial distribution (adsorption distance) + thermal-averaged
interaction energy. Pure classical (numpy + ASE); runs anywhere.

    python -m corrosim.runs.run_md --molecules kaempferol,quercetin,isorhamnetin \
        --metal Fe --steps 6000
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from corrosim import build_molecule
from corrosim.mc import run_mc
from corrosim.md import run_md
from corrosim.presets import ARGHEL

DEFAULT_MOLECULES = ARGHEL.molecule_list()


def main(argv=None) -> int:
    """CLI entry point: run Brownian MD to the metal-X RDF / adsorption distance (M4)."""
    p = argparse.ArgumentParser(prog="corrosim-run-md",
                                description="Brownian MD -> RDF (M4).")
    p.add_argument("--molecules", default=",".join(DEFAULT_MOLECULES))
    p.add_argument("--metal", default=ARGHEL.metal_element)
    p.add_argument("--steps", type=int, default=6000)
    p.add_argument("--equil", type=int, default=1500)
    p.add_argument("--temperature", type=float, default=298.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--outdir", default="results")
    args = p.parse_args(argv)
    os.makedirs(args.outdir, exist_ok=True)

    summary = []
    for name in [m.strip() for m in args.molecules.split(",") if m.strip()]:
        print(f"[{name}] MD ({args.steps} steps, {args.temperature:.0f} K) ...", file=sys.stderr)
        m = build_molecule(name)
        mc = run_mc(m, metal=args.metal, n_steps=2000, seed=args.seed)  # adsorbed start
        r = run_md(m, metal=args.metal, n_steps=args.steps, equil=args.equil,
                   temperature=args.temperature, seed=args.seed,
                   start_positions=mc.best_positions)
        summary.append(dict(name=name, metal=r.metal, surface=f"{r.metal}{r.surface}",
                            e_mean_kjmol=r.e_mean_kjmol,
                            metal_O_peak_A=r.first_peak_metal_O,
                            metal_N_peak_A=r.first_peak_metal_N))
        print(f"  <E> = {r.e_mean_kjmol:.1f} kJ/mol | {r.metal}-O peak {r.first_peak_metal_O} Å",
              file=sys.stderr)

    json.dump(summary, open(f"{args.outdir}/md_rdf.json", "w"), indent=2)
    import pandas as pd
    print(pd.DataFrame(summary).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
