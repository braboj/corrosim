"""corrosim.runs.run_dft  (M1 driver).

Production DFT descriptor matrix for the Arghel flavonoids — the foundation for
the article (see docs/local/article-plan.local.md, milestone M1).

Runs the adopted level (B3LYP/6-311++G(d,p) + ddCOSMO water; ADR 0002) over

    molecules  x  {gas, aqueous}  x  {neutral, protonated}

For each molecule the protonation site is chosen as the lowest-energy conjugate
acid (fast screening engine), then the reported descriptors come from DFT.
Results are cached to JSON and printed as a table.

Local use (needs rdkit + pyscf — long jobs are expected):

    python -m corrosim.runs.run_dft \
        --molecules kaempferol,quercetin,isorhamnetin --engine pyscf \
        --out-json results/dft_descriptors_ff.json \
        --out-csv results/dft_descriptors_ff.csv

Quick smoke (xtb, seconds — NOT for reported numbers; xTB ΔN/χ are unreliable):

    python -m corrosim.runs.run_dft --engine xtb --no-protonated

Pass --check-minimum (issue #41) to verify each --optimize geometry is a true
minimum: a vibrational-frequency check runs after the relaxation and records
``n_imag`` (0 = a minimum) in the provenance, so a first-order saddle never
silently feeds the descriptors. --to-minimum goes further and *drives* each
geometry to a verified minimum (finer grid + imaginary-mode restarts, the #34
recipe). Both imply --optimize and are QM-heavy (a Hessian per species) — run
detached in the QM container:

    docker compose run -d --name corrosim_dft qm \
        python -m corrosim.runs.run_dft --to-minimum \
        --out-json results/dft_descriptors_opt.json \
        --out-csv results/dft_descriptors_opt.csv
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import sys
from collections.abc import Sequence
from typing import Any, cast

import corrosim
from corrosim.medium import parse_medium, relevant_forms
from corrosim.molecules import (
    build_molecule,
    build_protonated,
    enumerate_protonation_sites,
    write_xyz,
)
from corrosim.presets import ARGHEL
from corrosim.qm.engines import (
    min_check_fields,
    optimize_geometry,
    relax_to_minimum,
    run_engine,
    thermo_correction,
)
from corrosim.runs._cli import (
    add_molecules_arg,
    parse_molecules,
    print_table,
    write_json,
)


def _best_protonation_site(name: str, select_engine: str = "xtb"):
    """Return (site_idx, protonated Molecule) for the best conjugate acid.

    All protonation isomers share the same atoms, so total energies are
    directly comparable; the most stable cation is the preferred protonation
    site.
    """
    best = None
    for idx in enumerate_protonation_sites(name):
        try:
            mol = build_protonated(name, idx)
            res = run_engine(mol.symbols, mol.coords, engine=select_engine,
                             charge=mol.charge)
        except Exception as exc:
            # skip sites RDKit / the engine reject
            print(f"    site {idx}: skipped ({exc})", file=sys.stderr)
            continue
        print(f"    site {idx}: E = {res.e_total_ev:.3f} eV", file=sys.stderr)
        if best is None or res.e_total_ev < best[1]:
            best = (idx, res.e_total_ev, mol)
    if best is None:
        raise RuntimeError(f"No usable protonation site for {name!r}")
    return best[0], best[2]


def analyse_matrix(molecules: Sequence[str], engine: str = "pyscf",
                   metal: str = "Fe(110)", basis: str = "6-311++G(d,p)",
                   xc: str = "b3lyp", forms: str = "both",
                   select_engine: str = "xtb", optimize: bool = False,
                   opt_basis: str = "6-31G(d)", opt_xc: str = "b3lyp",
                   opt_solvent: str | None = None, opt_maxsteps: int = 100,
                   opt_geom_dir: str | None = None, check_minimum: bool = False,
                   to_minimum: bool = False) -> list[dict]:
    """Run the {neutral, protonated} x {gas, aqueous} DFT matrix.

    If ``optimize`` is set, each species' geometry is DFT-relaxed once (at
    ``opt_basis``/``opt_xc``, gas-phase by default) before the production single
    points, replacing the force-field geometry; a ``geometry`` provenance field
    records which was used, and ``opt_geom_dir`` persists the relaxed geometry
    as ``<molecule>_opt.xyz``. ``check_minimum`` runs a frequency check and
    records ``n_imag`` + ``lowest_freq_cm`` so a saddle never silently feeds the
    descriptors; ``to_minimum`` instead drives each geometry to a verified
    minimum (finer grid + imaginary-mode restarts) and supersedes it.

    Args:
        molecules: Library names or SMILES to process.
        engine: Production engine ('pyscf'/'xtb'/...).
        metal: Substrate label for ΔN.
        basis: Production AO basis.
        xc: Exchange-correlation functional.
        forms: Which species to run ('neutral', 'protonated' or 'both').
        select_engine: Fast engine for protonation-site selection.
        optimize: DFT-relax each geometry before the single point.
        opt_basis: Basis for the relaxation.
        opt_xc: Functional for the relaxation.
        opt_solvent: Relax in implicit solvent, or gas phase (None).
        opt_maxsteps: Max geometry-optimisation steps.
        opt_geom_dir: Directory to persist ``<molecule>_opt.xyz``, if any.
        check_minimum: Run a frequency check and record the provenance.
        to_minimum: Drive each geometry to a verified true minimum.

    Returns:
        One row dict per (molecule, form, phase).
    """
    if optimize:
        geom_tag = (f"DFT-opt {opt_xc}/{opt_basis}"
                    + (f" ({opt_solvent})" if opt_solvent else " (gas)"))
        if to_minimum:
            geom_tag += ", relaxed to true minimum (grid 4, imag-mode restarts)"
        elif check_minimum:
            geom_tag += ", frequency-checked"
    else:
        geom_tag = "FF (MMFF)"
    want_neutral = forms in ("both", "neutral")
    want_prot = forms in ("both", "protonated")
    rows = []
    for name in molecules:
        print(f"[{name}]", file=sys.stderr)
        form_list = []
        if want_neutral:
            form_list.append(("neutral", build_molecule(name)))
        if want_prot:
            print("  selecting protonation site ...", file=sys.stderr)
            _, prot = _best_protonation_site(name, select_engine)
            form_list.append(("protonated", prot))
        for form, mol in form_list:
            min_prov = {}
            if optimize:
                print(f"  optimising {form} geometry "
                      f"({opt_xc}/{opt_basis}) ...", file=sys.stderr)
                tinfo = None
                if to_minimum:
                    _, opt_coords, tinfo = relax_to_minimum(
                        mol.symbols, mol.coords, basis=opt_basis, xc=opt_xc,
                        charge=mol.charge, solvent=opt_solvent,
                        maxsteps=opt_maxsteps)
                else:
                    _, opt_coords = optimize_geometry(
                        mol.symbols, mol.coords, basis=opt_basis, xc=opt_xc,
                        charge=mol.charge, solvent=opt_solvent,
                        maxsteps=opt_maxsteps)
                    if check_minimum:
                        print(f"  frequency check {form} "
                              f"({opt_xc}/{opt_basis}) ...", file=sys.stderr)
                        tinfo = thermo_correction(
                            list(mol.symbols), opt_coords, basis=opt_basis,
                            xc=opt_xc, charge=mol.charge, solvent=opt_solvent)
                # the optimiser returns coordinate triples (looser Coords type)
                mol = dataclasses.replace(mol, coords=cast(list, opt_coords))
                if opt_geom_dir is not None:
                    path = write_xyz(
                        mol, os.path.join(opt_geom_dir, f"{mol.name}_opt.xyz"))
                    print(f"  opt geometry -> {path}", file=sys.stderr)
                min_prov = min_check_fields(tinfo)
                if min_prov and min_prov["n_imag"]:
                    hint = (" (restart budget exhausted)" if to_minimum
                            else " — re-run with --to-minimum to clear it")
                    print(f"  WARNING: {form} is not a true minimum: "
                          f"{min_prov['n_imag']} imaginary frequency(ies), "
                          f"lowest {min_prov['lowest_freq_cm']} cm^-1{hint}.",
                          file=sys.stderr)
                elif min_prov:
                    print(f"  {form}: true minimum verified (n_imag=0)",
                          file=sys.stderr)
            for phase, solvent in (("gas", None), ("aqueous", "water")):
                print(f"  DFT {form}/{phase} ...", file=sys.stderr)
                kw: dict[str, Any] = (dict(basis=basis, xc=xc, solvent=solvent)
                                      if engine == "pyscf" else {})
                row = corrosim.analyse_molecule(mol, metal=metal,
                                                engine=engine, **kw)
                row.update(form=form, phase=phase, geometry=geom_tag,
                           **min_prov)
                rows.append(row)
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: compute the production DFT descriptor matrix (M1).

    Args:
        argv: Command-line arguments (defaults to ``sys.argv``).

    Returns:
        The process exit code (0 on success).
    """
    p = argparse.ArgumentParser(
        prog="corrosim-run-dft",
        description="Production DFT descriptor matrix (M1).",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    add_molecules_arg(p)
    p.add_argument("--engine", default="pyscf",
                   choices=["pyscf", "xtb", "orca", "gaussian"])
    p.add_argument("--metal", default=ARGHEL.metal)
    p.add_argument("--medium", default=ARGHEL.medium,
                   help="Medium label (e.g. '1 M HCl'); checked against "
                        "--forms to flag a protonation/medium mismatch.")
    p.add_argument("--basis", default="6-311++G(d,p)", help="PySCF basis set.")
    p.add_argument("--xc", default="b3lyp", help="PySCF XC functional.")
    p.add_argument("--forms", default="both",
                   choices=["both", "neutral", "protonated"],
                   help="Which species to run (default both). 'protonated' "
                        "alone completes an existing neutral-only matrix.")
    p.add_argument("--no-protonated", action="store_true",
                   help="Shortcut for --forms neutral (skip the acid-relevant "
                        "cations).")
    p.add_argument("--select-engine", default="xtb",
                   help="Fast engine for protonation-site selection.")
    p.add_argument("--optimize", action="store_true",
                   help="DFT-relax each geometry before the single point (M1 "
                        "refinement).")
    p.add_argument("--check-minimum", action="store_true",
                   help="Verify each optimised geometry is a true minimum: run "
                        "a vibrational-frequency check and record n_imag "
                        "(0 = minimum) + lowest_freq_cm in the provenance, "
                        "warning on any imaginary mode so a saddle never "
                        "silently feeds the descriptors. Implies --optimize. "
                        "Slow (a Hessian per species; QM container).")
    p.add_argument("--to-minimum", action="store_true",
                   help="Drive each geometry to a *verified* true minimum "
                        "(finer DFT grid + imaginary-mode restarts) instead of "
                        "a single relaxation. Implies --optimize; supersedes "
                        "--check-minimum.")
    p.add_argument("--opt-basis", default="6-31G(d)",
                   help="Basis for the geometry optimisation (kept small on "
                        "purpose).")
    p.add_argument("--opt-xc", default="b3lyp",
                   help="XC functional for the optimisation.")
    p.add_argument("--opt-solvent", default=None,
                   help="Relax in implicit solvent (e.g. 'water'); default gas "
                        "phase.")
    p.add_argument("--opt-maxsteps", type=int, default=100,
                   help="Max geometry-optimisation steps.")
    p.add_argument("--opt-xyz-dir", default=None,
                   help="Directory for the persisted DFT-optimised geometries "
                        "(<molecule>_opt.xyz), written only with --optimize. "
                        "Defaults to the --out-csv/--out-json directory, else "
                        "'results'.")
    p.add_argument("--out-json", default=None,
                   help="Cache rows to this JSON file.")
    p.add_argument("--out-csv", default=None,
                   help="Also write the table to CSV.")
    args = p.parse_args(argv)

    molecules = parse_molecules(args.molecules)
    forms = "neutral" if args.no_protonated else args.forms

    # The frequency check only makes sense on a stationary geometry, so both
    # minimum flags imply --optimize; --to-minimum (drive-to-minimum)
    # supersedes the plain --check-minimum (detect-and-flag).
    to_minimum = args.to_minimum
    check_minimum = args.check_minimum and not to_minimum
    optimize = args.optimize or check_minimum or to_minimum

    # Consistency check: does the requested protonation match the medium?
    spec = parse_medium(args.medium)
    ph_str = f" (pH ~{spec.ph})" if spec.ph is not None else ""
    want_prot = forms in ("both", "protonated")
    medium_wants_prot = "protonated" in relevant_forms(spec)
    if want_prot and not medium_wants_prot:
        print(f"warning: --forms includes the protonated cation, but medium "
              f"{args.medium!r}{ph_str} is not acidic — the cation may not be "
              f"the relevant species there.", file=sys.stderr)
    elif medium_wants_prot and not want_prot:
        print(f"warning: medium {args.medium!r}{ph_str} is acidic — the "
              f"inhibitor is largely protonated there; consider --forms both.",
              file=sys.stderr)
    # Persist the DFT-optimised geometries alongside the descriptors. Default
    # the location only for geometry-PRODUCING runs (--optimize / --to-minimum);
    # a bare --check-minimum re-optimises from the force-field geometry only to
    # verify it, so it must not clobber a tracked <molecule>_opt.xyz unless
    # --opt-xyz-dir is given.
    opt_geom_dir = None
    if args.opt_xyz_dir:
        opt_geom_dir = args.opt_xyz_dir
    elif args.optimize or to_minimum:
        opt_geom_dir = (os.path.dirname(args.out_csv or args.out_json or "")
                        or "results")

    rows = analyse_matrix(molecules, engine=args.engine, metal=args.metal,
                          basis=args.basis, xc=args.xc,
                          forms=forms,
                          select_engine=args.select_engine,
                          optimize=optimize, opt_basis=args.opt_basis,
                          opt_xc=args.opt_xc, opt_solvent=args.opt_solvent,
                          opt_maxsteps=args.opt_maxsteps,
                          opt_geom_dir=opt_geom_dir,
                          check_minimum=check_minimum, to_minimum=to_minimum)

    if args.out_json:
        write_json(args.out_json, rows)
        print(f"JSON: {args.out_json}", file=sys.stderr)

    import pandas as pd
    df = pd.DataFrame(rows)
    show = [c for c in ["name", "form", "phase", "charge", "homo_ev",
                        "lumo_ev", "gap_ev", "hardness_ev", "softness_inv_ev",
                        "electronegativity_ev", "electrophilicity_ev",
                        "delta_n", "back_donation_ev", "tnc", "n_imag"]
            if c in df.columns]
    print()
    print_table(df, show, round_to=3)
    if args.out_csv:
        df.to_csv(args.out_csv, index=False)
        print(f"CSV: {args.out_csv}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
