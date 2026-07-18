"""corrosim.runs.compare_geometry.

Quantify how the DFT geometry optimisation (run_dft --optimize) changes the
descriptors relative to the force-field geometry, and check that the inhibitor
ranking is preserved. Reads the two descriptor matrices, writes a tidy
comparison CSV and a grouped-bar figure, and prints a summary.

Runs in the venv (no QM container); unset paths default to the case's own
cases/<case>/results and cases/<case>/report subtrees:
    python -m corrosim.runs.compare_geometry --case arghel
"""
from __future__ import annotations

import argparse
from collections.abc import Sequence

import matplotlib

matplotlib.use("Agg")
import pandas as pd

from corrosim.report import figures
from corrosim.report.report_layout import figure_path
from corrosim.runs._cli import (
    add_case_arg,
    default_output,
    form_rows_in_order,
    resolve_case,
)
from corrosim.runs._cli import stderr_log as log

KEYS = ["gap_ev", "hardness_ev", "softness_inv_ev", "delta_n", "tnc"]


def _compare_form(ff_full, opt_full, form, phase, order):
    """Build the FF-vs-opt delta table and gap/ΔN ranking check for a ``form``.
    Returns (comp_rows, order, ranking_summary_str) or (None, [], msg) if the
    form is absent from either matrix. ``order`` is the case-study molecule
    order to report in.
    """
    f = form_rows_in_order(ff_full, form, order, phase)
    o = form_rows_in_order(opt_full, form, order, phase)
    order = [n for n in order if n in f.index and n in o.index]
    if not order:
        return None, [], f"  (no {form} rows in both matrices — skipped)"
    f, o = f.loc[order], o.loc[order]

    comp_rows = []
    for n in order:
        for k in KEYS:
            a, b = float(f.loc[n, k]), float(o.loc[n, k])
            comp_rows.append(dict(form=form, name=n, descriptor=k,
                                  ff=round(a, 3), dft_opt=round(b, 3),
                                  delta=round(b - a, 3)))

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


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: compare FF vs DFT-optimised descriptors.

    Also checks that the inhibitor ranking is preserved.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv``).

    Returns:
        The process exit code (0 on success).
    """
    p = argparse.ArgumentParser(prog="corrosim-compare-geometry")
    add_case_arg(p)
    p.add_argument("--ff", default=None,
                   help="Force-field-geometry descriptor matrix; unset uses "
                        "the case's cases/<case>/results subtree.")
    p.add_argument("--opt", default=None,
                   help="DFT-optimised-geometry descriptor matrix; unset uses "
                        "the case's cases/<case>/results subtree.")
    p.add_argument("--phase", default="aqueous", choices=["gas", "aqueous"])
    p.add_argument("--out-csv", default=None)
    p.add_argument("--out-fig", default=None)
    args = p.parse_args(argv)
    case = resolve_case(args)
    default_output(args, "ff", f"{case.results_dir}/dft_descriptors_ff.csv")
    default_output(args, "opt", f"{case.results_dir}/dft_descriptors_opt.csv")
    default_output(args, "out_csv",
                   f"{case.results_dir}/geometry_comparison.csv")
    # fig8 lands in its report_layout stage subfolder (dft/), where the report
    # embeds it — not flat at the figures root.
    default_output(args, "out_fig",
                   figure_path(f"{case.report_dir}/figures",
                               "fig8_geometry_comparison.png"))
    case_order = case.molecule_list()

    ff_full, opt_full = pd.read_csv(args.ff), pd.read_csv(args.opt)

    all_rows, neutral_order = [], []
    for form in ("neutral", "protonated"):
        comp_rows, order, summary = _compare_form(
            ff_full, opt_full, form, args.phase, case_order)
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
