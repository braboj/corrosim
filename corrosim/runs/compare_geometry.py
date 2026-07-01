"""corrosim.runs.compare_geometry  (M1 refinement — validation).

Quantify how the DFT geometry optimisation (run_dft --optimize) changes the
descriptors relative to the force-field geometry, and check that the inhibitor
ranking is preserved. Reads the two descriptor matrices, writes a tidy comparison
CSV and a grouped-bar figure, and prints a summary.

Runs in the venv (no QM container):
    python -m corrosim.runs.compare_geometry \
        --ff results/dft_descriptors.csv --opt results/dft_descriptors_opt.csv \
        --out-csv results/geometry_comparison.csv \
        --out-fig report/figures/fig8_geometry_comparison.png
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


def _select(df, order, form, phase):
    """Rows for ``form``/``phase`` indexed by the BASE molecule name (strips the
    ``+H+`` protonation suffix), in ``order``. Works for both neutral and
    protonated rows.
    """
    sub = df[(df.form == form) & (df.phase == phase)].copy()
    sub["_base"] = sub["name"].str.replace(r"\+H\+$", "", regex=True)
    present = [n for n in order if n in set(sub["_base"])]
    return sub.set_index("_base").loc[present]


def _compare_form(ff_full, opt_full, form, phase):
    """Build the FF-vs-opt delta table and gap/ΔN ranking check for one ``form``.
    Returns (comp_rows, order, ranking_summary_str) or (None, [], msg) if the form
    is absent from either matrix.
    """
    f = _select(ff_full, ORDER, form, phase)
    o = _select(opt_full, ORDER, form, phase)
    order = [n for n in ORDER if n in f.index and n in o.index]
    if not order:
        return None, [], f"  (no {form} rows in both matrices — skipped)"
    f, o = f.loc[order], o.loc[order]

    comp_rows = []
    for n in order:
        for k in KEYS:
            a, b = float(f.loc[n, k]), float(o.loc[n, k])
            comp_rows.append(dict(form=form, name=n, descriptor=k, ff=round(a, 3),
                                  dft_opt=round(b, 3), delta=round(b - a, 3)))

    rank_ff_gap = list(f.sort_values("gap_ev").index)
    rank_op_gap = list(o.sort_values("gap_ev").index)
    rank_ff_dn = list(f.sort_values("delta_n", ascending=False).index)
    rank_op_dn = list(o.sort_values("delta_n", ascending=False).index)
    summary = (
        f"\nFF vs DFT-opt geometry ({form}, {phase}):\n"
        + pd.DataFrame(comp_rows).pivot(index="name", columns="descriptor",
                                        values="delta").loc[order].to_string()
        + f"\nRanking by gap (smaller first):"
          f"\n  FF : {rank_ff_gap}\n  opt: {rank_op_gap}"
          f"   [{'PRESERVED' if rank_ff_gap == rank_op_gap else 'CHANGED'}]"
        + f"\nRanking by delta_n (larger first):"
          f"\n  FF : {rank_ff_dn}\n  opt: {rank_op_dn}"
          f"   [{'PRESERVED' if rank_ff_dn == rank_op_dn else 'CHANGED'}]")
    return comp_rows, order, summary


def main(argv=None) -> int:
    """CLI entry point: compare FF vs DFT-optimised descriptors and check ranking robustness."""
    p = argparse.ArgumentParser(prog="corrosim-compare-geometry")
    p.add_argument("--ff", default="results/dft_descriptors.csv",
                   help="Force-field-geometry descriptor matrix.")
    p.add_argument("--opt", default="results/dft_descriptors_opt.csv",
                   help="DFT-optimised-geometry descriptor matrix.")
    p.add_argument("--phase", default="aqueous", choices=["gas", "aqueous"])
    p.add_argument("--out-csv", default="results/geometry_comparison.csv")
    p.add_argument("--out-fig", default="report/figures/fig8_geometry_comparison.png")
    args = p.parse_args(argv)
    log = lambda m: print(m, file=sys.stderr)

    ff_full, opt_full = pd.read_csv(args.ff), pd.read_csv(args.opt)

    all_rows, neutral_order = [], []
    for form in ("neutral", "protonated"):
        comp_rows, order, summary = _compare_form(ff_full, opt_full, form, args.phase)
        print(summary)
        if comp_rows:
            all_rows += comp_rows
            if form == "neutral":
                neutral_order = order

    pd.DataFrame(all_rows).to_csv(args.out_csv, index=False)

    # fig8 tracks the neutral headline ranking (the reported lead basis).
    figures.plot_geometry_comparison(ff_full, opt_full, neutral_order,
                                     phase=args.phase, out=args.out_fig)
    log(f"\nCSV: {args.out_csv}\nFigure: {args.out_fig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
