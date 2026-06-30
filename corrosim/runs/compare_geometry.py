"""
corrosim.runs.compare_geometry  (M1 refinement — validation)
============================================================
Quantify how the DFT geometry optimisation (run_dft --optimize) changes the
descriptors relative to the force-field geometry, and check that the inhibitor
ranking is preserved. Reads the two descriptor matrices, writes a tidy comparison
CSV and a grouped-bar figure, and prints a summary.

Runs in the venv (no QM container):
    python -m corrosim.runs.compare_geometry \
        --ff results/dft_descriptors.csv --opt results/dft_descriptors_opt.csv \
        --out-csv results/geometry_comparison.csv --out-fig figures/fig8_geometry_comparison.png
"""
from __future__ import annotations
import argparse
import sys

import matplotlib
matplotlib.use("Agg")
import pandas as pd

from corrosim import figures
from corrosim.presets import ARGHEL

ORDER = ARGHEL.molecule_list()
KEYS = ["gap_ev", "hardness_ev", "softness_inv_ev", "delta_n", "tnc"]


def _naq(df, order, phase):
    present = [n for n in order if n in set(df["name"])]
    return (df[(df.form == "neutral") & (df.phase == phase)]
            .set_index("name").loc[present])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="corrosim-compare-geometry")
    p.add_argument("--ff", default="results/dft_descriptors.csv",
                   help="Force-field-geometry descriptor matrix.")
    p.add_argument("--opt", default="results/dft_descriptors_opt.csv",
                   help="DFT-optimised-geometry descriptor matrix.")
    p.add_argument("--phase", default="aqueous", choices=["gas", "aqueous"])
    p.add_argument("--out-csv", default="results/geometry_comparison.csv")
    p.add_argument("--out-fig", default="figures/fig8_geometry_comparison.png")
    args = p.parse_args(argv)
    log = lambda m: print(m, file=sys.stderr)

    ff_full, opt_full = pd.read_csv(args.ff), pd.read_csv(args.opt)
    f, o = _naq(ff_full, ORDER, args.phase), _naq(opt_full, ORDER, args.phase)
    order = [n for n in ORDER if n in f.index and n in o.index]
    f, o = f.loc[order], o.loc[order]

    rows = []
    for n in order:
        for k in KEYS:
            a, b = float(f.loc[n, k]), float(o.loc[n, k])
            rows.append(dict(name=n, descriptor=k, ff=round(a, 3),
                             dft_opt=round(b, 3), delta=round(b - a, 3)))
    comp = pd.DataFrame(rows)
    comp.to_csv(args.out_csv, index=False)

    rank_ff_gap = list(f.sort_values("gap_ev").index)
    rank_op_gap = list(o.sort_values("gap_ev").index)
    rank_ff_dn = list(f.sort_values("delta_n", ascending=False).index)
    rank_op_dn = list(o.sort_values("delta_n", ascending=False).index)

    print(f"\nFF vs DFT-opt geometry (neutral, {args.phase}):\n")
    print(comp.pivot(index="name", columns="descriptor",
                     values="delta").loc[order].to_string())
    print(f"\nRanking by gap (smaller first):"
          f"\n  FF : {rank_ff_gap}\n  opt: {rank_op_gap}"
          f"   [{'PRESERVED' if rank_ff_gap == rank_op_gap else 'CHANGED'}]")
    print(f"Ranking by delta_n (larger first):"
          f"\n  FF : {rank_ff_dn}\n  opt: {rank_op_dn}"
          f"   [{'PRESERVED' if rank_ff_dn == rank_op_dn else 'CHANGED'}]")

    figures.plot_geometry_comparison(ff_full, opt_full, order, phase=args.phase,
                                     out=args.out_fig)
    log(f"\nCSV: {args.out_csv}\nFigure: {args.out_fig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
