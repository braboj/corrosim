"""corrosim.runs.run_mc.

Monte Carlo adsorption pose search (simulated annealing) for the flavonoids on
the metal slab. Writes a summary JSON to the case's cases/<case>/results dir;
figures are rendered separately by make_figures. Pure classical (numpy + ASE);
runs anywhere, no QM.

    python -m corrosim.runs.run_mc \
        --molecules kaempferol,quercetin,isorhamnetin --metal Fe --steps 4000
"""
from __future__ import annotations

import argparse
from collections.abc import Sequence

from corrosim.adsorption.mc import run_mc
from corrosim.runs._cli import (
    add_case_arg,
    add_molecules_arg,
    default_output,
    iter_molecules,
    print_table,
    resolve_case,
    stderr_log,
    write_json,
)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: run the Monte Carlo adsorption pose search.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv``).

    Returns:
        The process exit code (0 on success).
    """
    p = argparse.ArgumentParser(prog="corrosim-run-mc",
                                description="Monte Carlo adsorption pose "
                                            "search.")
    add_molecules_arg(p)
    add_case_arg(p)
    p.add_argument("--metal", default=None, help="Fe | Cu | Al")
    p.add_argument("--steps", type=int, default=4000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--outdir", default=None,
                   help="Output directory; unset uses the case's "
                        "cases/<case>/results subtree.")
    args = p.parse_args(argv)
    case = resolve_case(args, metal="element")
    default_output(args, "outdir", case.results_dir)

    summary = []
    for name, m in iter_molecules(args):
        stderr_log(f"[{name}] MC pose search ({args.steps} steps) ...")
        r = run_mc(m, metal=args.metal, n_steps=args.steps, seed=args.seed)
        summary.append(dict(name=name, surface=f"{r.metal}{r.surface}",
                            e_ads_ev=r.e_ads_ev, e_ads_kjmol=r.e_ads_kjmol,
                            best_height_A=r.best_height_A,
                            accept_ratio=round(r.n_accept / r.n_steps, 3)))
        stderr_log(f"  E_ads = {r.e_ads_ev:.3f} eV "
                   f"({r.e_ads_kjmol:.1f} kJ/mol) at {r.best_height_A} Å")

    write_json(f"{args.outdir}/mc_adsorption.json", summary)
    print_table(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
