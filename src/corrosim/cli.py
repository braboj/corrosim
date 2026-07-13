"""corrosim.cli.

Run the screening pipeline from the command line.

Examples:
--------
  # Built-in molecules, fast engine, HTML + CSV out
  python -m corrosim --inhibitors kaempferol,quercetin,isorhamnetin \
                     --metal "Fe(110)" --engine xtb \
                     --out report.html --csv results.csv

  # Batch from a CSV of molecules (columns: name[,smiles]); add adsorption est.
  python -m corrosim --input molecules.csv --metal "Fe(110)" \
                     --adsorption --out report.html --csv results.csv

  # Production DFT via PySCF
  python -m corrosim --input molecules.csv --engine pyscf \
                     --basis "6-311++G(d,p)" --solvent water --out report.html

  # Dry run: print the steps this screen would take, then exit
  python -m corrosim --inhibitors quercetin,kaempferol --engine pyscf --plan
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence


def _nonempty_rows(path: str) -> list[list[str]]:
    """Read a CSV, keeping only rows with at least one non-blank cell.

    Args:
        path: Path to the input CSV.

    Returns:
        The retained rows (each a list of raw cell strings), in file order.
    """
    with open(path, newline="") as f:
        return [r for r in csv.reader(f) if any(c.strip() for c in r)]


def _cell(row: list[str], i: int | None) -> str:
    """A stripped cell value, or '' when the column is absent or out of range.

    Args:
        row: The CSV row.
        i: The column index, or None when that column is not present.

    Returns:
        ``row[i]`` stripped, or '' if ``i`` is None or past the row's end.
    """
    if i is None or i >= len(row):
        return ""
    return row[i].strip()


def _molecules_from_header(rows: list[list[str]],
                           header: list[str]) -> list[str]:
    """Molecule values from a headered CSV: prefer 'smiles', else 'name'.

    Args:
        rows: The non-empty rows, header included at index 0.
        header: The lower-cased header cells.

    Returns:
        The non-blank molecule values from the data rows, in file order.
    """
    name_i = header.index("name") if "name" in header else None
    smi_i = header.index("smiles") if "smiles" in header else None
    out = []
    for r in rows[1:]:
        val = _cell(r, smi_i) or _cell(r, name_i)
        if val:
            out.append(val)
    return out


def _molecules_headerless(rows: list[list[str]]) -> list[str]:
    """Molecule values from a headerless CSV: the non-blank first column.

    Args:
        rows: The non-empty rows.

    Returns:
        The stripped first-column values, in file order.
    """
    return [r[0].strip() for r in rows if r[0].strip()]


def read_input_csv(path: str) -> list[str]:
    """Read molecules from a CSV.

    Uses the 'smiles' column if present, else 'name'; falls back to the first
    column for a headerless file.

    Args:
        path: Path to the input CSV.

    Returns:
        The molecule names/SMILES, in file order.

    Raises:
        SystemExit: If no molecules can be read from ``path``.
    """
    rows = _nonempty_rows(path)
    if not rows:
        raise SystemExit(f"No molecules found in {path}")
    header = [c.strip().lower() for c in rows[0]]
    if "name" in header or "smiles" in header:
        out = _molecules_from_header(rows, header)
    else:
        out = _molecules_headerless(rows)
    if not out:
        raise SystemExit(f"No molecules found in {path}")
    return out


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the `corrosim` screening CLI.

    Returns:
        The configured argparse parser.
    """
    p = argparse.ArgumentParser(
        prog="corrosim",
        description="Automated corrosion-inhibitor screening "
                    "(free/open-source).")

    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", metavar="CSV",
                     help="CSV of molecules (columns: name[,smiles]).")

    src.add_argument("--inhibitors", metavar="LIST",
                     help="Comma-separated names or SMILES.")

    p.add_argument("--metal", default="Fe(110)",
                   help="Substrate: Fe(110) | Cu(111) | Al(111). Default "
                        "Fe(110).")

    p.add_argument("--medium", default="1 M HCl",
                   help="Label for the report header.")

    p.add_argument("--engine", default="xtb",
                   choices=["xtb", "pyscf", "orca", "gaussian"],
                   help="Quantum engine. Default xtb (fast).")

    p.add_argument("--basis", default="6-311++G(d,p)",
                   help="PySCF basis set. Default = the production DFT level; "
                        "use 6-31g for a quick check.")

    p.add_argument("--xc", default="b3lyp",
                   help="PySCF exchange-correlation functional.")

    p.add_argument("--solvent", default="water",
                   help="Implicit solvent ('none' for gas phase).")

    p.add_argument("--adsorption", action="store_true",
                   help="Add the UFF vdW physisorption estimate.")

    p.add_argument("--out", metavar="HTML", default="corrosion_report.html",
                   help="HTML report path. Default corrosion_report.html.")

    p.add_argument("--csv", metavar="CSV", default=None,
                   help="Also write the results table to this CSV.")

    p.add_argument("--plan", action="store_true",
                   help="Print the steps this screen would run (for the given "
                        "options) and exit, without computing anything.")
    return p


def format_plan(args: argparse.Namespace, molecules: Sequence[str]) -> str:
    """Describe the steps the quick screen will run, for ``--plan`` (a dry run).

    Names the ordered steps this ``corrosim`` invocation performs for the given
    options and, explicitly, what it does *not* run (the multiscale pipeline),
    so the two entry points never get conflated.

    Args:
        args: The parsed CLI arguments.
        molecules: The resolved molecule list.

    Returns:
        A newline-separated, human-readable plan.
    """
    # Engine-specific descriptor step (single point in every case).
    if args.engine == "xtb":
        descr = "single-point GFN2-xTB (tblite)"
    elif args.engine == "pyscf":
        phase = ("gas phase" if args.solvent.lower() == "none"
                 else f"ddCOSMO:{args.solvent}")
        descr = f"single-point DFT (pyscf): {args.xc}/{args.basis} ({phase})"
    else:
        binvar = "ORCA_CMD" if args.engine == "orca" else "GAUSSIAN_CMD"
        descr = f"single-point via {args.engine} (external ${binvar})"

    # Ordered steps, adapting to the flags actually given.
    steps = [
        ("geometry", "MMFF force-field 3D embed (RDKit), per molecule"),
        ("descriptors", descr),
    ]
    if args.adsorption:
        steps.append(("adsorption",
                      "UFF van-der-Waals height-scan -> e_ads_kjmol"))
    steps.append(("rank",
                  "composite z-score of gap / hardness / softness / delta_n"))
    report = f"self-contained HTML -> {args.out}"
    if args.csv:
        report += f"; results table -> {args.csv}"
    steps.append(("report", report))

    lines = [f"Plan - quick screen of {len(molecules)} molecule(s) on "
             f"{args.metal}, medium {args.medium!r}:"]
    lines += [f"  {i}. {name:<11} {desc}"
              for i, (name, desc) in enumerate(steps, 1)]
    if args.engine in ("xtb", "pyscf"):
        lines.append("  (xtb/pyscf have no Windows wheels -> run inside the "
                     "corrosim-qm container on Windows)")
    lines.append("Not run here: Fukui, ESP, Monte Carlo pose search, MD RDF, "
                 "pKa.")
    lines.append("  -> the full multiscale report is the pipeline: "
                 "runs.run_dft / run_fukui / run_mc / run_md -> make_report "
                 "(see docs/PLAYBOOK.md)")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: screen the inhibitors, rank them, write the report.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv``).

    Returns:
        The process exit code (0 on success).
    """
    args = build_parser().parse_args(argv)

    inhibitors = (
        read_input_csv(args.input) if args.input
        else [x.strip() for x in args.inhibitors.split(",") if x.strip()])

    # A dry run: describe the steps and stop before importing/running anything
    # heavy — so it works even where the QM engine is not installed.
    if args.plan:
        print(format_plan(args, inhibitors))
        return 0

    import corrosim

    engine_kwargs = {}
    if args.engine == "pyscf":
        solvent = None if args.solvent.lower() == "none" else args.solvent
        engine_kwargs = dict(basis=args.basis, xc=args.xc, solvent=solvent)

    print(f"Screening {len(inhibitors)} molecule(s) on {args.metal} "
          f"with engine='{args.engine}'...", file=sys.stderr)
    df, html = corrosim.screen(
        inhibitors, metal=args.metal, medium=args.medium,
        engine=args.engine, adsorption=args.adsorption, out_html=args.out,
        progress=lambda m: print(m, file=sys.stderr), **engine_kwargs)

    ranked = corrosim.rank_inhibitors(df)
    print("\nRanking (best first):")
    cols = [c for c in ["name", "gap_ev", "hardness_ev", "softness_inv_ev",
                        "delta_n", "e_ads_kjmol", "score"]
            if c in ranked.columns]
    print(ranked[cols].to_string(index=False))
    if args.csv:
        ranked.to_csv(args.csv, index=False)
        print(f"\nResults CSV: {args.csv}")
    print(f"HTML report: {html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
