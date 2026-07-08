"""corrosim.runs.run_fukui  (M2 driver).

Condensed Fukui functions / dual descriptor for the flavonoids — local
reactivity (which atoms bind the metal). Writes per-molecule JSON to the case's
results/<case> subtree; figures are rendered separately by make_figures.

Three single points per molecule (N, N-1, N+1) at fixed geometry; needs PySCF.

Container use:
    docker compose run --rm qm python -m corrosim.runs.run_fukui \
        --molecules kaempferol,quercetin,isorhamnetin
"""
from __future__ import annotations

import argparse
from collections.abc import Sequence

from corrosim.qm.fukui import compute_fukui
from corrosim.runs._cli import (
    add_case_arg,
    add_molecules_arg,
    default_output,
    iter_molecules,
    resolve_case,
    stderr_log,
    write_json,
)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: compute condensed Fukui / dual descriptors (M2).

    Args:
        argv: Command-line arguments (defaults to ``sys.argv``).

    Returns:
        The process exit code (0 on success).
    """
    p = argparse.ArgumentParser(
        prog="corrosim-run-fukui",
        description="Condensed Fukui / dual descriptor (M2).")
    add_molecules_arg(p)
    add_case_arg(p)
    p.add_argument("--basis", default="6-31G(d)",
                   help="Valence basis; diffuse sets break Mulliken-condensed "
                        "Fukui.")
    p.add_argument("--xc", default="b3lyp")
    p.add_argument("--method", default="fmo", choices=["fmo", "fd"],
                   help="fmo = fast one-SCF frontier-orbital; fd = finite "
                        "difference.")
    p.add_argument("--outdir", default=None,
                   help="Output directory; unset uses the case's "
                        "results/<case> subtree.")
    args = p.parse_args(argv)
    case = resolve_case(args)
    default_output(args, "outdir", case.results_dir)

    for name, m in iter_molecules(args):
        stderr_log(f"[{name}] computing Fukui ({args.method}) ...")
        fk = compute_fukui(m, basis=args.basis, xc=args.xc, method=args.method)
        write_json(f"{args.outdir}/{name}_fukui.json", fk.as_rows())
        stderr_log("  top donor (f-) sites — the metal-binding atoms:")
        for r in fk.top_donor_sites(6):
            stderr_log("    %2s%-2d  f-=%+.3f  dual=%+.3f"
                       % (r["symbol"], r["idx"], r["f_minus"], r["dual"]))
        stderr_log(f"  wrote {name}_fukui.json / {name}_fukui.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
