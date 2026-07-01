"""corrosim.runs.make_report  (M5).

Build one self-contained HTML report consolidating the full multiscale pipeline
(DFT descriptors + Fukui + Monte Carlo + MD) and the committed figure set into a
single shareable file. Reads the committed result data and embeds the figures
from report/figures/ inline (base64), so the report stands alone. Also copies the
source CSV/JSON tables into report/tables/ so the report/ bundle is complete.

Runs in the venv (no QM container needed):
    python -m corrosim.runs.make_report
    python -m corrosim.runs.make_report --out report/report.html --figdir report/figures
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

import pandas as pd

from corrosim import report
from corrosim.medium import parse_medium
from corrosim.presets import ARGHEL
from corrosim.speciation import analyse_speciation, protonation_fraction

ORDER = ARGHEL.molecule_list()


def _load_json(path: str):
    return json.load(open(path)) if os.path.exists(path) else []


def main(argv=None) -> int:
    """CLI entry point: build the self-contained multiscale HTML pipeline report."""
    p = argparse.ArgumentParser(prog="corrosim-make-report")
    p.add_argument("--descriptors", default="results/dft_descriptors.csv")
    p.add_argument("--opt-descriptors", default="results/dft_descriptors_opt.csv",
                   help="DFT-optimised-geometry matrix; surfaced as a labelled "
                        "section (neutral ranking + protonated cations) when present.")
    p.add_argument("--mc", default="results/mc_adsorption.json")
    p.add_argument("--md", default="results/md_rdf.json")
    p.add_argument("--datadir", default="results",
                   help="Where per-molecule Fukui JSON live.")
    p.add_argument("--pka", default="results/pka.json",
                   help="Computed-pKaH JSON (run_pka); shown in the speciation section.")
    p.add_argument("--figdir", default="report/figures")
    p.add_argument("--out", default="report/report.html")
    p.add_argument("--tablesdir", default="report/tables",
                   help="Copy the report's source CSV/JSON tables here for the bundle.")
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

    # Computed per-molecule pKaH (run_pka, DFT cycle) -> populations that resolve
    # the crossover (ADR 0005).
    computed_pkah = None
    pka_freq_corrected = False
    if spec.ph is not None and os.path.exists(args.pka):
        order_ix = {n: i for i, n in enumerate(present)}
        pka_rows = [r for r in _load_json(args.pka) if r["name"] in order_ix]
        # prefer the frequency-corrected pKaH ("pkah") when run_pka --freq produced it,
        # else the electronic-only value (issue #18 / ADR 0005).
        pka_freq_corrected = bool(pka_rows) and all("pkah" in r for r in pka_rows)
        computed_pkah = sorted(
            ({"name": r["name"], "pkah": r.get("pkah", r["pkah_electronic"]),
              "f_protonated": protonation_fraction(
                  spec.ph, r.get("pkah", r["pkah_electronic"]))}
             for r in pka_rows),
            key=lambda r: order_ix[r["name"]]) or None

    # Optimised-geometry matrix (#19): surface the DFT-relaxed neutral ranking and
    # the optimised protonated cations alongside the FF headline, when available.
    opt_neutral_rows = opt_acid_rows = None
    if os.path.exists(args.opt_descriptors):
        odf = pd.read_csv(args.opt_descriptors)
        on = odf[(odf.form == "neutral") & (odf.phase == "aqueous")]
        on_present = [n for n in ORDER if n in set(on["name"])]
        opt_neutral_rows = on.set_index("name").loc[on_present].reset_index() \
            .to_dict("records") or None
        if spec.acidic:
            op = odf[(odf.form == "protonated") & (odf.phase == "aqueous")].copy()
            op["_base"] = op["name"].str.replace(r"\+H\+$", "", regex=True)
            op = op[op["_base"].isin(on_present)]
            op["_ord"] = op["_base"].map({n: i for i, n in enumerate(on_present)})
            opt_acid_rows = op.sort_values("_ord").drop(columns=["_base", "_ord"]) \
                .to_dict("records") or None

    mc_rows = _load_json(args.mc)
    md_rows = _load_json(args.md)
    fukui_by_name = {n: _load_json(f"{args.datadir}/{n}_fukui.json") for n in present}

    log(f"DFT rows: {len(rows)} | MC: {len(mc_rows)} | MD: {len(md_rows)} | "
        f"Fukui: {sum(1 for v in fukui_by_name.values() if v)} | "
        f"medium: {args.medium!r} acidic={spec.acidic} "
        f"acid-cation rows: {len(acid_rows) if acid_rows else 0} | "
        f"opt rows: {len(opt_neutral_rows) if opt_neutral_rows else 0} neutral / "
        f"{len(opt_acid_rows) if opt_acid_rows else 0} protonated")

    out = report.build_pipeline_report(
        rows, mc_rows, md_rows, fukui_by_name,
        figdir=args.figdir, out_path=args.out,
        metal=args.metal, medium=args.medium, order=present,
        acid_cation_rows=acid_rows, speciation_summary=speciation_summary,
        computed_pkah=computed_pkah, pka_freq_corrected=pka_freq_corrected,
        opt_neutral_rows=opt_neutral_rows, opt_acid_rows=opt_acid_rows,
    )
    # Bundle the source tables next to the report so report/ is self-describing.
    os.makedirs(args.tablesdir, exist_ok=True)
    report.rank_inhibitors(pd.DataFrame(rows)).to_csv(
        os.path.join(args.tablesdir, "ranking.csv"), index=False)
    for src in (args.descriptors, args.opt_descriptors,
                "results/geometry_comparison.csv", args.pka):
        if os.path.exists(src):
            shutil.copy(src, os.path.join(args.tablesdir, os.path.basename(src)))

    size_kb = os.path.getsize(out) / 1024
    print(f"report written to {out} ({size_kb:.0f} kB, self-contained); "
          f"tables in {args.tablesdir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
