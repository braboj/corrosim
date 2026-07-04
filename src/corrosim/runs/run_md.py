"""corrosim.runs.run_md  (M4 driver).

Brownian (overdamped-Langevin) rigid-body MD of the inhibitor over the metal
slab at 298 K -> metal-X radial distribution (adsorption distance) +
thermal-averaged interaction energy. Pure classical (numpy + ASE); runs
anywhere.

    python -m corrosim.runs.run_md \
        --molecules kaempferol,quercetin,isorhamnetin --metal Fe --steps 6000
"""
from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from corrosim import build_molecule
from corrosim.adsorption.mc import run_mc
from corrosim.adsorption.md import run_md
from corrosim.presets import ARGHEL
from corrosim.runs._cli import (
    add_molecules_arg,
    parse_molecules,
    print_table,
    stderr_log,
    write_json,
)

# MC steps used only to relax the molecule onto the slab before the MD run
# (a converged adsorbed start), not the sampled MC search itself.
MC_WARMUP_STEPS = 2000


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: run Brownian MD to the metal-X RDF (M4).

    Args:
        argv: Command-line arguments (defaults to ``sys.argv``).

    Returns:
        The process exit code (0 on success).
    """
    p = argparse.ArgumentParser(prog="corrosim-run-md",
                                description="Brownian MD -> RDF (M4).")
    add_molecules_arg(p)
    p.add_argument("--metal", default=ARGHEL.metal_element)
    p.add_argument("--steps", type=int, default=6000)
    p.add_argument("--equil", type=int, default=1500)
    p.add_argument("--temperature", type=float, default=298.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--outdir", default="results")
    args = p.parse_args(argv)
    os.makedirs(args.outdir, exist_ok=True)

    summary = []
    for name in parse_molecules(args.molecules):
        stderr_log(f"[{name}] MD ({args.steps} steps, "
                   f"{args.temperature:.0f} K) ...")
        m = build_molecule(name)
        mc = run_mc(m, metal=args.metal, n_steps=MC_WARMUP_STEPS,
                    seed=args.seed)
        r = run_md(m, metal=args.metal, n_steps=args.steps, equil=args.equil,
                   temperature=args.temperature, seed=args.seed,
                   start_positions=mc.best_positions)
        summary.append(dict(name=name, metal=r.metal,
                            surface=f"{r.metal}{r.surface}",
                            e_mean_kjmol=r.e_mean_kjmol,
                            metal_O_peak_A=r.first_peak_metal_O,
                            metal_N_peak_A=r.first_peak_metal_N))
        stderr_log(f"  <E> = {r.e_mean_kjmol:.1f} kJ/mol | "
                   f"{r.metal}-O peak {r.first_peak_metal_O} Å")

    write_json(f"{args.outdir}/md_rdf.json", summary)
    print_table(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
