"""corrosim.runs.run_fukui  (M2 driver).

Condensed Fukui functions / dual descriptor for the flavonoids — Stage-1 local
reactivity (which atoms bind the metal). Writes per-molecule JSON to results/;
figures are rendered separately by make_figures.

Three single points per molecule (N, N-1, N+1) at fixed geometry; needs PySCF.

Container use:
    docker compose run --rm qm python -m corrosim.runs.run_fukui \
        --molecules kaempferol,quercetin,isorhamnetin
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from corrosim import build_molecule
from corrosim.fukui import compute_fukui
from corrosim.presets import ARGHEL

DEFAULT_MOLECULES = ARGHEL.molecule_list()


def main(argv=None) -> int:
    """CLI entry point: compute condensed Fukui / dual descriptors per molecule (M2)."""
    p = argparse.ArgumentParser(prog="corrosim-run-fukui",
                                description="Condensed Fukui / dual descriptor (M2).")
    p.add_argument("--molecules", default=",".join(DEFAULT_MOLECULES),
                   help="Comma-separated names or SMILES.")
    p.add_argument("--basis", default="6-31G(d)",
                   help="Valence basis; diffuse sets break Mulliken-condensed Fukui.")
    p.add_argument("--xc", default="b3lyp")
    p.add_argument("--method", default="fmo", choices=["fmo", "fd"],
                   help="fmo = fast one-SCF frontier-orbital; fd = finite difference.")
    p.add_argument("--outdir", default="results")
    args = p.parse_args(argv)
    os.makedirs(args.outdir, exist_ok=True)

    for name in [m.strip() for m in args.molecules.split(",") if m.strip()]:
        print(f"[{name}] computing Fukui ({args.method}) ...", file=sys.stderr)
        m = build_molecule(name)
        fk = compute_fukui(m, basis=args.basis, xc=args.xc, method=args.method)
        json.dump(fk.as_rows(), open(f"{args.outdir}/{name}_fukui.json", "w"), indent=2)
        print("  top donor (f-) sites — the metal-binding atoms:", file=sys.stderr)
        for r in fk.top_donor_sites(6):
            print("    %2s%-2d  f-=%+.3f  dual=%+.3f"
                  % (r["symbol"], r["idx"], r["f_minus"], r["dual"]), file=sys.stderr)
        print(f"  wrote {name}_fukui.json / {name}_fukui.png", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
