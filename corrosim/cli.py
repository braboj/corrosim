"""corrosim.cli.

Run the screening pipeline from the command line.

Examples:
--------
  # built-in molecules, fast engine, HTML + CSV out
  python -m corrosim --inhibitors kaempferol,quercetin,isorhamnetin \
                     --metal "Fe(110)" --engine xtb \
                     --out report.html --csv results.csv

  # batch from a CSV of molecules (columns: name[,smiles]); add adsorption est.
  python -m corrosim --input molecules.csv --metal "Fe(110)" \
                     --adsorption --out report.html --csv results.csv

  # production DFT via PySCF
  python -m corrosim --input molecules.csv --engine pyscf \
                     --basis "6-311++G(d,p)" --solvent water --out report.html
"""
from __future__ import annotations

import argparse
import csv
import sys


def read_input_csv(path: str) -> list[str]:
    """Read molecules from a CSV. Uses 'smiles' if present, else 'name'.
    Falls back to the first column for a headerless file.
    """
    with open(path, newline="") as f:
        rows = [r for r in csv.reader(f) if any(c.strip() for c in r)]
    if not rows:
        raise SystemExit(f"No molecules found in {path}")

    header = [c.strip().lower() for c in rows[0]]
    out = []
    if "name" in header or "smiles" in header:
        name_i = header.index("name") if "name" in header else None
        smi_i = header.index("smiles") if "smiles" in header else None
        for r in rows[1:]:
            smi = r[smi_i].strip() if smi_i is not None and smi_i < len(r) else ""
            nm = r[name_i].strip() if name_i is not None and name_i < len(r) else ""
            val = smi or nm
            if val:
                out.append(val)
    else:                       # headerless: first column is the molecule
        out = [r[0].strip() for r in rows if r[0].strip()]
    if not out:
        raise SystemExit(f"No molecules found in {path}")
    return out


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the `corrosim` screening CLI."""
    p = argparse.ArgumentParser(
        prog="corrosim",
        description="Automated corrosion-inhibitor screening (free/open-source).")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", metavar="CSV",
                     help="CSV of molecules (columns: name[,smiles]).")
    src.add_argument("--inhibitors", metavar="LIST",
                     help="Comma-separated names or SMILES.")
    p.add_argument("--metal", default="Fe(110)",
                   help="Substrate: Fe(110) | Cu(111) | Al(111). Default Fe(110).")
    p.add_argument("--medium", default="1 M HCl", help="Label for the report header.")
    p.add_argument("--engine", default="xtb",
                   choices=["xtb", "pyscf", "orca", "gaussian"],
                   help="Quantum engine. Default xtb (fast).")
    p.add_argument("--basis", default="6-311++G(d,p)",
                   help="PySCF basis set. Default = adopted template level "
                        "(ADR 0002); use 6-31g for a quick check.")
    p.add_argument("--xc", default="b3lyp", help="PySCF exchange-correlation functional.")
    p.add_argument("--solvent", default="water",
                   help="Implicit solvent ('none' for gas phase).")
    p.add_argument("--adsorption", action="store_true",
                   help="Add the Stage-2 UFF vdW physisorption estimate.")
    p.add_argument("--out", metavar="HTML", default="corrosion_report.html",
                   help="HTML report path. Default corrosion_report.html.")
    p.add_argument("--csv", metavar="CSV", default=None,
                   help="Also write the results table to this CSV.")
    return p


def main(argv=None) -> int:
    """CLI entry point: screen the inhibitors, rank them, and write the report."""
    args = build_parser().parse_args(argv)
    import corrosim

    inhibitors = (read_input_csv(args.input) if args.input
                  else [x.strip() for x in args.inhibitors.split(",") if x.strip()])

    engine_kwargs = {}
    if args.engine == "pyscf":
        solvent = None if args.solvent.lower() == "none" else args.solvent
        engine_kwargs = dict(basis=args.basis, xc=args.xc, solvent=solvent)

    print(f"Screening {len(inhibitors)} molecule(s) on {args.metal} "
          f"with engine='{args.engine}'...", file=sys.stderr)
    df, html = corrosim.screen(inhibitors, metal=args.metal, medium=args.medium,
                               engine=args.engine, adsorption=args.adsorption,
                               out_html=args.out, progress=lambda m: print(m, file=sys.stderr),
                               **engine_kwargs)

    ranked = corrosim.rank_inhibitors(df)
    print("\nRanking (best first):")
    print(ranked[[c for c in ["name", "gap_ev", "hardness_ev", "softness_inv_ev",
                              "delta_n", "e_ads_kjmol", "score"]
                  if c in ranked.columns]].to_string(index=False))
    if args.csv:
        ranked.to_csv(args.csv, index=False)
        print(f"\nResults CSV: {args.csv}")
    print(f"HTML report: {html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
