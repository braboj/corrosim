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

ORDER = ["kaempferol", "quercetin", "isorhamnetin"]


def _load_json(path: str):
    return json.load(open(path)) if os.path.exists(path) else []


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="corrosim-make-report")
    p.add_argument("--descriptors", default="dft_descriptors.csv")
    p.add_argument("--mc", default="mc_adsorption.json")
    p.add_argument("--md", default="md_rdf.json")
    p.add_argument("--figdir", default="figures")
    p.add_argument("--out", default="report.html")
    p.add_argument("--metal", default="Fe(110)")
    p.add_argument("--medium", default="1 M HCl")
    args = p.parse_args(argv)
    log = lambda m: print(m, file=sys.stderr)

    if not os.path.exists(args.descriptors):
        log(f"error: {args.descriptors} not found — run run_dft first.")
        return 1

    df = pd.read_csv(args.descriptors)
    naq = df[(df.form == "neutral") & (df.phase == "aqueous")]
    present = [n for n in ORDER if n in set(naq["name"])]
    rows = naq.set_index("name").loc[present].reset_index().to_dict("records")

    mc_rows = _load_json(args.mc)
    md_rows = _load_json(args.md)
    fukui_by_name = {n: _load_json(f"{n}_fukui.json") for n in present}

    log(f"DFT rows: {len(rows)} | MC: {len(mc_rows)} | MD: {len(md_rows)} | "
        f"Fukui: {sum(1 for v in fukui_by_name.values() if v)}")

    out = report.build_pipeline_report(
        rows, mc_rows, md_rows, fukui_by_name,
        figdir=args.figdir, out_path=args.out,
        metal=args.metal, medium=args.medium, order=present,
    )
    size_kb = os.path.getsize(out) / 1024
    print(f"report written to {out} ({size_kb:.0f} kB, self-contained)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
