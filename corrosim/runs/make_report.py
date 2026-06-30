"""
corrosim.runs.make_report  (M5)
===============================
Build one self-contained HTML report consolidating the full multiscale pipeline
(DFT descriptors + Fukui + Monte Carlo + MD) and the committed figure set into a
single shareable file. Reads the committed result data and embeds the figures
from figures/ inline (base64), so report.html stands alone.

Runs in the venv (no QM container needed):
    python -m corrosim.runs.make_report
    python -m corrosim.runs.make_report --out report.html --figdir figures
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

from corrosim import report
from corrosim.medium import parse_medium
from corrosim.presets import ARGHEL
from corrosim.speciation import analyse_speciation

ORDER = ARGHEL.molecule_list()


def _load_json(path: str):
    return json.load(open(path)) if os.path.exists(path) else []


def main(argv=None) -> int:
    """CLI entry point: build the self-contained multiscale HTML pipeline report."""
    p = argparse.ArgumentParser(prog="corrosim-make-report")
    p.add_argument("--descriptors", default="results/dft_descriptors.csv")
    p.add_argument("--mc", default="results/mc_adsorption.json")
    p.add_argument("--md", default="results/md_rdf.json")
    p.add_argument("--datadir", default="results",
                   help="Where per-molecule Fukui JSON live.")
    p.add_argument("--figdir", default="figures")
    p.add_argument("--out", default="report.html")
    p.add_argument("--metal", default=ARGHEL.metal)
    p.add_argument("--medium", default=ARGHEL.medium)
    args = p.parse_args(argv)
    log = lambda m: print(m, file=sys.stderr)

    if not os.path.exists(args.descriptors):
        log(f"error: {args.descriptors} not found — run run_dft first.")
        return 1

    df = pd.read_csv(args.descriptors)
    naq = df[(df.form == "neutral") & (df.phase == "aqueous")]
    present = [n for n in ORDER if n in set(naq["name"])]
    rows = naq.set_index("name").loc[present].reset_index().to_dict("records")

    # In an acidic medium the inhibitor protonates; surface the cation descriptors
    # as a labelled in-acid comparison (the headline ranking stays neutral — ADR 0003).
    spec = parse_medium(args.medium)
    acid_rows = None
    if spec.acidic and {"form", "phase"} <= set(df.columns):
        paq = df[(df.form == "protonated") & (df.phase == "aqueous")].copy()
        paq["_base"] = paq["name"].str.replace(r"\+H\+$", "", regex=True)
        paq = paq[paq["_base"].isin(present)]
        paq["_ord"] = paq["_base"].map({n: i for i, n in enumerate(present)})
        acid_rows = paq.sort_values("_ord").drop(columns=["_base", "_ord"]).to_dict("records") \
            or None

    # Quantitative pH-speciation: population-weighted descriptors + lead-crossover
    # sensitivity to the protonation pKa (ADR 0004). Needs a numeric pH.
    speciation_summary = None
    if acid_rows and spec.ph is not None:
        def _rank(blend_rows):
            return report.rank_inhibitors(pd.DataFrame(blend_rows)).to_dict("records")
        speciation_summary = analyse_speciation(rows, acid_rows, spec.ph, _rank)

    mc_rows = _load_json(args.mc)
    md_rows = _load_json(args.md)
    fukui_by_name = {n: _load_json(f"{args.datadir}/{n}_fukui.json") for n in present}

    log(f"DFT rows: {len(rows)} | MC: {len(mc_rows)} | MD: {len(md_rows)} | "
        f"Fukui: {sum(1 for v in fukui_by_name.values() if v)} | "
        f"medium: {args.medium!r} acidic={spec.acidic} "
        f"acid-cation rows: {len(acid_rows) if acid_rows else 0}")

    out = report.build_pipeline_report(
        rows, mc_rows, md_rows, fukui_by_name,
        figdir=args.figdir, out_path=args.out,
        metal=args.metal, medium=args.medium, order=present,
        acid_cation_rows=acid_rows, speciation_summary=speciation_summary,
    )
    size_kb = os.path.getsize(out) / 1024
    print(f"report written to {out} ({size_kb:.0f} kB, self-contained)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
