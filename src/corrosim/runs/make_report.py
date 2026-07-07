"""corrosim.runs.make_report  (M5).

Build one self-contained HTML report consolidating the full multiscale pipeline
(DFT descriptors + Fukui + Monte Carlo + MD) and the committed figure set into a
single shareable file. Reads the committed result data and embeds the figures
from report/figures/ inline (base64), so the report stands alone. Also copies
the source CSV/JSON tables into report/tables/ so the report/ bundle is
complete.

Runs in the venv (no QM container needed):
    python -m corrosim.runs.make_report
    python -m corrosim.runs.make_report --out report/report.html \
        --figdir report/figures
"""
from __future__ import annotations

import argparse
import os
import shutil
from collections.abc import Sequence

import pandas as pd

from corrosim import report
from corrosim.medium import MediumSpec, parse_medium
from corrosim.qm.speciation import analyse_speciation, protonation_fraction
from corrosim.report.report_layout import table_path
from corrosim.runs._cli import (
    add_case_arg,
    form_rows_in_order,
    read_json,
    resolve_case,
)
from corrosim.runs._cli import stderr_log as log


def _load_json(path: str):
    return read_json(path, [])


def _rank_blend(blend_rows: list[dict]) -> list[dict]:
    """Rank a population-blended descriptor set for the speciation summary.

    Args:
        blend_rows: Blended descriptor rows to rank.

    Returns:
        The ranked rows as record dicts.
    """
    return report.rank_inhibitors(pd.DataFrame(blend_rows)).to_dict("records")


def _bundle_one(tablesdir: str, src: str, name: str | None = None) -> None:
    """Copy one source table into the bundle's per-stage subfolder.

    Args:
        tablesdir: The report bundle's tables root.
        src: Source file to copy.
        name: Destination basename; defaults to ``src``'s basename.
    """
    dst = table_path(tablesdir, name or os.path.basename(src))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(src, dst)


def _neutral_rows(
    df: pd.DataFrame,
    order: list[str],
) -> tuple[list[dict], list[str]]:
    """Neutral aqueous descriptor rows in case-study order.

    Args:
        df: The force-field descriptor matrix.
        order: The case-study molecule order.

    Returns:
        ``(rows, present)`` — the neutral aqueous rows and the molecule names
        actually present, both in ``order``.
    """
    neutral = form_rows_in_order(df, "neutral", order)
    present = list(neutral.index)
    rows = neutral.reset_index(drop=True).to_dict("records")
    return rows, present


def _acid_cation_rows(
    df: pd.DataFrame,
    present: list[str],
    spec: MediumSpec,
) -> list[dict] | None:
    """Protonated-cation aqueous rows for the in-acid comparison.

    In an acidic medium the inhibitor protonates; surface the cation
    descriptors as a labelled comparison (the headline ranking stays neutral).

    Args:
        df: The force-field descriptor matrix.
        present: The neutral molecules present, in order.
        spec: The parsed medium.

    Returns:
        The cation rows in ``present`` order, or None when the medium is not
        acidic or no cation rows exist.
    """
    if not (spec.acidic and {"form", "phase"} <= set(df.columns)):
        return None
    cations = form_rows_in_order(df, "protonated", present)
    return cations.reset_index(drop=True).to_dict("records") or None


def _speciation_summary(
    rows: list[dict],
    acid_rows: list[dict] | None,
    spec: MediumSpec,
) -> dict | None:
    """Population-weighted speciation blend + lead-crossover sensitivity.

    Args:
        rows: Neutral descriptor rows.
        acid_rows: Protonated-cation rows, or None.
        spec: The parsed medium (needs a numeric pH).

    Returns:
        The speciation summary, or None without an acid comparison or pH.
    """
    if not (acid_rows and spec.ph is not None):
        return None
    return analyse_speciation(rows, acid_rows, spec.ph, _rank_blend)


def _computed_pkah(
    pka_path: str,
    present: list[str],
    spec: MediumSpec,
) -> tuple[list[dict] | None, bool]:
    """Computed per-molecule pKaH populations that resolve the lead crossover.

    Args:
        pka_path: Path to the run_pka JSON.
        present: The neutral molecules present, in order.
        spec: The parsed medium (needs a numeric pH).

    Returns:
        ``(computed_pkah, freq_corrected)`` — the ordered pKaH population rows
        (or None) and whether every row carries a frequency-corrected pKaH.
    """
    if not (spec.ph is not None and os.path.exists(pka_path)):
        return None, False
    order_ix = {n: i for i, n in enumerate(present)}
    pka_rows = [r for r in _load_json(pka_path) if r["name"] in order_ix]
    # Prefer the frequency-corrected pKaH ("pkah") when run_pka --freq produced
    # it, else the electronic-only value.
    freq_corrected = bool(pka_rows) and all("pkah" in r for r in pka_rows)
    computed = sorted(
        ({"name": r["name"], "pkah": r.get("pkah", r["pkah_electronic"]),
          "f_protonated": protonation_fraction(
              spec.ph, r.get("pkah", r["pkah_electronic"]))}
         for r in pka_rows),
        key=lambda r: order_ix[r["name"]]) or None
    return computed, freq_corrected


def _opt_geometry_rows(
    opt_path: str,
    order: list[str],
    spec: MediumSpec,
) -> tuple[list[dict] | None, list[dict] | None]:
    """DFT-optimised-geometry neutral ranking + optimised protonated cations.

    Surfaced alongside the FF headline when the optimised matrix is present.

    Args:
        opt_path: Path to the DFT-optimised descriptor matrix.
        order: The case-study molecule order.
        spec: The parsed medium.

    Returns:
        ``(opt_neutral_rows, opt_acid_rows)`` — either may be None when absent.
    """
    if not os.path.exists(opt_path):
        return None, None
    odf = pd.read_csv(opt_path)
    neutral = form_rows_in_order(odf, "neutral", order)
    on_present = list(neutral.index)
    opt_neutral_rows = neutral.reset_index(drop=True).to_dict("records") or None
    opt_acid_rows = None
    if spec.acidic:
        cations = form_rows_in_order(odf, "protonated", on_present)
        opt_acid_rows = (cations.reset_index(drop=True)
                         .to_dict("records") or None)
    return opt_neutral_rows, opt_acid_rows


def _render_reports(
    rows: list[dict],
    mc_rows: list[dict],
    md_rows: list[dict],
    fukui_by_name: dict[str, list[dict]],
    args: argparse.Namespace,
    common: dict,
) -> None:
    """Build the HTML report and, unless skipped, the Word mirror.

    Args:
        rows: Neutral descriptor rows.
        mc_rows: Monte-Carlo adsorption rows.
        md_rows: MD RDF rows.
        fukui_by_name: Per-molecule Fukui rows.
        args: Parsed CLI arguments (output paths).
        common: The shared renderer keyword arguments.
    """
    out = report.build_pipeline_report(rows, mc_rows, md_rows, fukui_by_name,
                                       out_path=args.out, **common)
    size_kb = os.path.getsize(out) / 1024
    print(f"report written to {out} ({size_kb:.0f} kB, self-contained)")

    # Word (.docx) report — same content, needs python-docx (`report` extra).
    if args.out_docx:
        try:
            from corrosim.report import report_docx
            docx_out = report_docx.build_docx_report(
                rows, mc_rows, md_rows, fukui_by_name, out_path=args.out_docx,
                **common)
            print(f"word report written to {docx_out} "
                  f"({os.path.getsize(docx_out) / 1024:.0f} kB)")
        except ImportError:
            log("python-docx not installed; skipped .docx "
                "(install it with: pip install -e .[report])")


def _bundle_tables(args: argparse.Namespace, rows: list[dict]) -> None:
    """Copy the report's source tables next to it, so the bundle stands alone.

    Args:
        args: Parsed CLI arguments (paths + the tables root).
        rows: Neutral descriptor rows, for the ranking table.
    """
    ranking_dst = table_path(args.tablesdir, "ranking.csv")
    os.makedirs(os.path.dirname(ranking_dst), exist_ok=True)
    report.rank_inhibitors(pd.DataFrame(rows)).to_csv(ranking_dst, index=False)
    for src in (args.descriptors, args.opt_descriptors,
                "results/geometry_comparison.csv", args.pka):
        if os.path.exists(src):
            _bundle_one(args.tablesdir, src)
    print(f"tables in {args.tablesdir}/ (per-stage subfolders)")


def _build_parser() -> argparse.ArgumentParser:
    """Construct the make_report argument parser.

    Returns:
        The configured argument parser.
    """
    p = argparse.ArgumentParser(prog="corrosim-make-report")
    add_case_arg(p)
    p.add_argument("--descriptors", default="results/dft_descriptors_ff.csv")
    p.add_argument("--opt-descriptors",
                   default="results/dft_descriptors_opt.csv",
                   help="DFT-optimised-geometry matrix; surfaced as a labelled "
                        "section (neutral ranking + protonated cations) when "
                        "present.")
    p.add_argument("--mc", default="results/mc_adsorption.json")
    p.add_argument("--md", default="results/md_rdf.json")
    p.add_argument("--datadir", default="results",
                   help="Where per-molecule Fukui JSON live.")
    p.add_argument("--pka", default="results/pka.json",
                   help="Computed-pKaH JSON (run_pka); shown in the speciation "
                        "section.")
    p.add_argument("--figdir", default="report/figures")
    p.add_argument("--out", default="report/report.html")
    p.add_argument("--out-docx", default="report/report.docx",
                   help="Word (.docx) report path; pass '' to skip the Word "
                        "build.")
    p.add_argument("--tablesdir", default="report/tables",
                   help="Copy the report's source CSV/JSON tables here for the "
                        "bundle (nested into per-stage subfolders).")
    p.add_argument("--metal", default=None)
    p.add_argument("--medium", default=None)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: build the self-contained multiscale HTML report.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv``).

    Returns:
        The process exit code (0 on success; 1 if descriptors are missing).
    """
    args = _build_parser().parse_args(argv)
    order = resolve_case(args, metal="label").molecule_list()

    if not os.path.exists(args.descriptors):
        log(f"error: {args.descriptors} not found — run run_dft first.")
        return 1

    df = pd.read_csv(args.descriptors)
    rows, present = _neutral_rows(df, order)
    spec = parse_medium(args.medium)
    acid_rows = _acid_cation_rows(df, present, spec)
    speciation_summary = _speciation_summary(rows, acid_rows, spec)
    computed_pkah, pka_freq_corrected = _computed_pkah(args.pka, present, spec)
    opt_neutral_rows, opt_acid_rows = _opt_geometry_rows(
        args.opt_descriptors, order, spec)

    mc_rows = _load_json(args.mc)
    md_rows = _load_json(args.md)
    fukui_by_name = {n: _load_json(f"{args.datadir}/{n}_fukui.json")
                     for n in present}

    log(f"DFT rows: {len(rows)} | MC: {len(mc_rows)} | MD: {len(md_rows)} | "
        f"Fukui: {sum(1 for v in fukui_by_name.values() if v)} | "
        f"medium: {args.medium!r} acidic={spec.acidic} "
        f"acid-cation rows: {len(acid_rows) if acid_rows else 0} | "
        f"opt rows: {len(opt_neutral_rows) if opt_neutral_rows else 0} "
        f"neutral / "
        f"{len(opt_acid_rows) if opt_acid_rows else 0} protonated")

    # Both renderers take the same inputs (report_docx mirrors the HTML build).
    common = dict(
        figdir=args.figdir, metal=args.metal, medium=args.medium, order=present,
        acid_cation_rows=acid_rows, speciation_summary=speciation_summary,
        computed_pkah=computed_pkah, pka_freq_corrected=pka_freq_corrected,
        opt_neutral_rows=opt_neutral_rows, opt_acid_rows=opt_acid_rows,
    )
    _render_reports(rows, mc_rows, md_rows, fukui_by_name, args, common)
    _bundle_tables(args, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
