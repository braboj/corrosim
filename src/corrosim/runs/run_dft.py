"""corrosim.runs.run_dft  (M1 driver).

Production DFT descriptor matrix for the Arghel flavonoids — the foundation for
the article (see docs/local/article-plan.local.md, milestone M1).

Runs the adopted level (B3LYP/6-311++G(d,p) + ddCOSMO water) over

    molecules  x  {gas, aqueous}  x  {neutral, protonated}

For each molecule the protonation site is chosen as the lowest-energy conjugate
acid (fast screening engine), then the reported descriptors come from DFT.
Results are cached to JSON and printed as a table.

Local use (needs rdkit + pyscf — long jobs are expected). Like every other
driver, an unset --out-json/--out-csv persists to the --case results dir by
default (dft_descriptors_ff for force-field geometries, dft_descriptors_opt for
DFT-relaxed ones), so a DFT run is never computed-and-discarded:

    python -m corrosim.runs.run_dft \
        --molecules kaempferol,quercetin,isorhamnetin --engine pyscf
        # -> cases/arghel/results/dft_descriptors_ff.{json,csv}

Quick smoke (xtb, seconds — NOT for reported numbers; xTB ΔN/χ are unreliable):

    python -m corrosim.runs.run_dft --engine xtb --no-protonated

Pass --check-minimum to verify each --optimize geometry is a true minimum: a
vibrational-frequency check runs after the relaxation and records ``n_imag``
(0 = a minimum) in the provenance, so a first-order saddle never silently feeds
the descriptors. --to-minimum goes further and *drives* each geometry to a
verified minimum (finer grid + imaginary-mode restarts). Both imply --optimize
and are QM-heavy (a Hessian per species) — run detached in the QM container:

    docker compose run -d --name corrosim_dft qm \
        python -m corrosim.runs.run_dft --to-minimum \
        --out-json cases/arghel/results/dft_descriptors_opt.json \
        --out-csv cases/arghel/results/dft_descriptors_opt.csv
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import sys
from collections.abc import Sequence
from typing import Any, cast

import pandas as pd

import corrosim
from corrosim.medium import parse_medium
from corrosim.molecules import (
    Molecule,
    build_molecule,
    write_xyz,
)
from corrosim.qm.engines import (
    MEMORY_BUDGET_ENV,
    MIN_RECIPE,
    min_check_fields,
    optimize_geometry,
    relax_to_minimum,
    thermo_correction,
)
from corrosim.qm.protonation import best_protonation_site
from corrosim.runs._cli import (
    add_case_arg,
    add_molecules_arg,
    default_output,
    parse_molecules,
    print_table,
    resolve_case,
    stderr_log,
    write_json,
)


def _geometry_tag(
    optimize: bool,
    opt_xc: str,
    opt_basis: str,
    opt_solvent: str | None,
    to_minimum: bool,
    check_minimum: bool,
) -> str:
    """Provenance tag recording which geometry fed the single points.

    Args:
        optimize: Whether the geometry was DFT-relaxed.
        opt_xc: Functional used for the relaxation.
        opt_basis: Basis used for the relaxation.
        opt_solvent: Implicit solvent for the relaxation, or None for gas.
        to_minimum: Whether the geometry was driven to a verified minimum.
        check_minimum: Whether a frequency check followed a plain relaxation.

    Returns:
        The ``geometry`` provenance label (e.g. ``FF (MMFF)`` or
        ``DFT-opt b3lyp/6-31G(d) (gas), frequency-checked``).
    """
    if not optimize:
        return "FF (MMFF)"
    tag = (f"DFT-opt {opt_xc}/{opt_basis}"
           + (f" ({opt_solvent})" if opt_solvent else " (gas)"))
    if to_minimum:
        return tag + f", relaxed to true minimum ({MIN_RECIPE})"
    if check_minimum:
        return tag + ", frequency-checked"
    return tag


def _species_forms(
    name: str,
    forms: str,
    select_engine: str,
) -> list[tuple[str, Molecule]]:
    """Build the (form label, molecule) pairs to analyse for one molecule.

    Args:
        name: Library name or SMILES.
        forms: Which species to include ('neutral', 'protonated' or 'both').
        select_engine: Fast engine for protonation-site selection.

    Returns:
        One ``(form, molecule)`` pair per requested species, neutral first.
    """
    pairs = []
    if forms in ("both", "neutral"):
        pairs.append(("neutral", build_molecule(name)))
    if forms in ("both", "protonated"):
        print("  selecting protonation site ...", file=sys.stderr)
        _, prot = best_protonation_site(name, select_engine, log=stderr_log)
        pairs.append(("protonated", prot))
    return pairs


def _optimize_species(
    mol: Molecule,
    form: str,
    opt_basis: str,
    opt_xc: str,
    opt_solvent: str | None,
    opt_maxsteps: int,
    to_minimum: bool,
    check_minimum: bool,
    opt_geom_dir: str | None,
) -> tuple[Molecule, dict]:
    """DFT-relax one species' geometry and read its minimum provenance.

    run_dft's own relax path, deliberately separate from
    ``run_pka._relax_and_thermo``: it relaxes in optional implicit solvent and
    runs the Hessian only when ``check_minimum`` is set, whereas run_pka always
    needs the Gibbs correction. Merging them would trade the split for extra
    branches here.

    Args:
        mol: The force-field-geometry molecule to relax.
        form: Species label ('neutral'/'protonated'), for the log lines.
        opt_basis: Basis for the relaxation.
        opt_xc: Functional for the relaxation.
        opt_solvent: Implicit solvent, or None for gas phase.
        opt_maxsteps: Max geometry-optimisation steps.
        to_minimum: Drive to a verified minimum instead of a single relax.
        check_minimum: Run a frequency check after a plain relaxation.
        opt_geom_dir: Directory to persist ``<name>_opt.xyz``, if any.

    Returns:
        The relaxed molecule and its ``min_check_fields`` provenance (empty
        when no frequency information was produced).
    """
    print(f"  optimising {form} geometry ({opt_xc}/{opt_basis}) ...",
          file=sys.stderr)
    tinfo = None
    if to_minimum:
        _, opt_coords, tinfo = relax_to_minimum(
            mol.symbols, mol.coords, basis=opt_basis, xc=opt_xc,
            charge=mol.charge, solvent=opt_solvent, maxsteps=opt_maxsteps)
    else:
        _, opt_coords = optimize_geometry(
            mol.symbols, mol.coords, basis=opt_basis, xc=opt_xc,
            charge=mol.charge, solvent=opt_solvent, maxsteps=opt_maxsteps)
        if check_minimum:
            print(f"  frequency check {form} ({opt_xc}/{opt_basis}) ...",
                  file=sys.stderr)
            tinfo = thermo_correction(
                list(mol.symbols), opt_coords, basis=opt_basis, xc=opt_xc,
                charge=mol.charge, solvent=opt_solvent)

    # The optimiser returns coordinate triples (looser Coords type)
    mol = dataclasses.replace(mol, coords=cast(list, opt_coords))
    if opt_geom_dir is not None:
        path = write_xyz(
            mol, os.path.join(opt_geom_dir, f"{mol.name}_opt.xyz"))
        print(f"  opt geometry -> {path}", file=sys.stderr)

    # A residual imaginary mode means the geometry is a saddle, not a minimum.
    min_prov = min_check_fields(tinfo)
    if min_prov and min_prov["n_imag"]:
        hint = (" (restart budget exhausted)" if to_minimum
                else " — re-run with --to-minimum to clear it")
        print(f"  WARNING: {form} is not a true minimum: "
              f"{min_prov['n_imag']} imaginary frequency(ies), "
              f"lowest {min_prov['lowest_freq_cm']} cm^-1{hint}.",
              file=sys.stderr)
    elif min_prov:
        print(f"  {form}: true minimum verified (n_imag=0)", file=sys.stderr)
    return mol, min_prov


def _single_points(
    mol: Molecule,
    form: str,
    geom_tag: str,
    min_prov: dict,
    engine: str,
    basis: str,
    xc: str,
    metal: str,
    density_fit: bool = False,
) -> list[dict]:
    """Production single points for one species in gas and aqueous phase.

    Args:
        mol: The (possibly relaxed) molecule.
        form: Species label ('neutral'/'protonated').
        geom_tag: Geometry provenance to stamp on each row.
        min_prov: Minimum-check provenance fields to merge into each row.
        engine: Production engine.
        basis: Production AO basis (pyscf only).
        xc: Exchange-correlation functional (pyscf only).
        metal: Substrate label for ΔN.
        density_fit: Speed the SCF with density fitting (pyscf only).

    Returns:
        One descriptor row per phase (gas, aqueous).
    """
    rows = []
    for phase, solvent in (("gas", None), ("aqueous", "water")):
        print(f"  DFT {form}/{phase} ...", file=sys.stderr)
        kw: dict[str, Any] = (
            dict(basis=basis, xc=xc, solvent=solvent, density_fit=density_fit)
            if engine == "pyscf" else {})
        row = corrosim.analyse_molecule(mol, metal=metal, engine=engine, **kw)
        row.update(form=form, phase=phase, geometry=geom_tag, **min_prov)
        rows.append(row)
    return rows


def analyse_matrix(
    molecules: Sequence[str],
    engine: str = "pyscf",
    metal: str = "Fe(110)",
    basis: str = "6-311++G(d,p)",
    xc: str = "b3lyp",
    forms: str = "both",
    select_engine: str = "xtb",
    optimize: bool = False,
    opt_basis: str = "6-31G(d)",
    opt_xc: str = "b3lyp",
    opt_solvent: str | None = None,
    opt_maxsteps: int = 100,
    opt_geom_dir: str | None = None,
    check_minimum: bool = False,
    to_minimum: bool = False,
    density_fit: bool = False,
) -> list[dict]:
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
        density_fit: Speed the production single point with density fitting.

    Returns:
        One row dict per (molecule, form, phase).
    """
    # Either minimum flag implies a relaxation, so the function is safe to call
    # directly (main derives the same value before passing it in).
    optimize = optimize or check_minimum or to_minimum
    geom_tag = _geometry_tag(optimize, opt_xc, opt_basis, opt_solvent,
                             to_minimum, check_minimum)
    rows: list[dict] = []
    for name in molecules:
        print(f"[{name}]", file=sys.stderr)
        for form, mol in _species_forms(name, forms, select_engine):
            min_prov: dict = {}
            if optimize:
                mol, min_prov = _optimize_species(
                    mol, form, opt_basis, opt_xc, opt_solvent, opt_maxsteps,
                    to_minimum, check_minimum, opt_geom_dir)
            rows.extend(_single_points(mol, form, geom_tag, min_prov, engine,
                                       basis, xc, metal,
                                       density_fit=density_fit))
    return rows


def _build_parser() -> argparse.ArgumentParser:
    """Construct the run_dft argument parser.

    Returns:
        The configured argument parser.
    """
    p = argparse.ArgumentParser(
        prog="corrosim-run-dft",
        description="Production DFT descriptor matrix (M1).",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    add_molecules_arg(p)
    add_case_arg(p)
    p.add_argument("--engine", default="pyscf",
                   choices=["pyscf", "xtb", "orca", "gaussian"])
    p.add_argument("--metal", default=None)
    p.add_argument("--medium", default=None,
                   help="Medium label (e.g. '1 M HCl'); checked against "
                        "--forms to flag a protonation/medium mismatch.")
    p.add_argument("--basis", default=None,
                   help="PySCF basis set; unset uses the --case study's basis "
                        "(default production 6-311++G(d,p)).")
    p.add_argument("--xc", default=None,
                   help="PySCF XC functional; unset uses the --case study's "
                        "functional (default b3lyp).")
    p.add_argument("--density-fit", action="store_true", default=None,
                   help="Speed the SCF with density fitting (RI); unset uses "
                        "the --case study's setting (default off). The RI "
                        "approximation shifts the descriptors, so enable it "
                        "only for a large molecule whose exact-integral SCF is "
                        "intractable.")
    p.add_argument("--max-memory-mb", type=int, default=None,
                   help="SCF memory budget (MB); unset auto-detects from the "
                        "host / container memory limit.")
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
                   help="Cache rows to this JSON file; unset persists to the "
                        "case's results dir (dft_descriptors_ff/opt.json). The "
                        "xtb smoke engine is exempt and writes only when set.")
    p.add_argument("--out-csv", default=None,
                   help="Also write the table to CSV; unset persists to the "
                        "case's results dir (dft_descriptors_ff/opt.csv).")
    return p


def _warn_medium_mismatch(forms: str, medium: str) -> None:
    """Warn on stderr when the requested protonation and the medium disagree.

    Args:
        forms: The resolved species selection ('both'/'neutral'/'protonated').
        medium: The medium label to parse and report.
    """
    spec = parse_medium(medium)
    ph_str = f" (pH ~{spec.ph})" if spec.ph is not None else ""
    want_prot = forms in ("both", "protonated")
    medium_wants_prot = "protonated" in spec.relevant_forms()
    if want_prot and not medium_wants_prot:
        print(f"warning: --forms includes the protonated cation, but medium "
              f"{medium!r}{ph_str} is not acidic — the cation may not be "
              f"the relevant species there.", file=sys.stderr)
    elif medium_wants_prot and not want_prot:
        print(f"warning: medium {medium!r}{ph_str} is acidic — the "
              f"inhibitor is largely protonated there; consider --forms both.",
              file=sys.stderr)


def _opt_geom_dir(
    args: argparse.Namespace,
    to_minimum: bool,
    results_dir: str,
) -> str | None:
    """Directory to persist DFT-optimised geometries, if this run makes them.

    Defaults a location only for geometry-PRODUCING runs (--optimize /
    --to-minimum); a bare --check-minimum re-optimises from the force-field
    geometry only to verify it, so it must not clobber a tracked
    ``<molecule>_opt.xyz`` unless --opt-xyz-dir is given.

    Args:
        args: Parsed CLI arguments.
        to_minimum: The resolved drive-to-minimum flag.
        results_dir: The case's results directory, used when neither
            --out-csv/--out-json nor --opt-xyz-dir pins a location.

    Returns:
        The output directory, or None when the run produces no geometries.
    """
    if args.opt_xyz_dir:
        return args.opt_xyz_dir
    if args.optimize or to_minimum:
        return (os.path.dirname(args.out_csv or args.out_json or "")
                or results_dir)
    return None


def _default_descriptor_outputs(
    args: argparse.Namespace,
    results_dir: str,
    optimize: bool,
) -> None:
    """Route an unset --out-json/--out-csv to the case's own results dir.

    Persists the descriptor matrix by default, like every other driver, so a
    DFT run is never computed-and-discarded. The force-field vs DFT-optimised
    geometry selects the filename stem the report consumers read back
    (``dft_descriptors_ff`` / ``dft_descriptors_opt``). The xtb smoke engine is
    exempt: its numbers are not reportable and would clobber the tracked
    production descriptors at the shared path, so it persists only with an
    explicit flag.

    Args:
        args: Parsed CLI arguments (mutated in place).
        results_dir: The case's results directory.
        optimize: Whether the run used a DFT-relaxed geometry.
    """
    if args.engine == "xtb":
        return
    stem = "dft_descriptors_opt" if optimize else "dft_descriptors_ff"
    default_output(args, "out_json", f"{results_dir}/{stem}.json")
    default_output(args, "out_csv", f"{results_dir}/{stem}.csv")


def _write_outputs(rows: list[dict], args: argparse.Namespace) -> None:
    """Cache rows to JSON/CSV and print the descriptor summary table.

    Args:
        rows: The descriptor rows from :func:`analyse_matrix`.
        args: Parsed CLI arguments (for the output paths).
    """
    # Ensure the target dir exists so a first run into a fresh case persists
    # rather than raising after the whole (expensive) matrix has finished.
    for path in (args.out_json, args.out_csv):
        if path:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if args.out_json:
        write_json(args.out_json, rows)
        print(f"JSON: {args.out_json}", file=sys.stderr)
    df = pd.DataFrame(rows)
    show = [c for c in ["name", "form", "phase", "charge", "homo_ev",
                        "lumo_ev", "gap_ev", "hardness_ev", "softness_inv_ev",
                        "electronegativity_ev", "electrophilicity_ev",
                        "delta_n", "back_donation_ev", "dipole_debye", "tnc",
                        "n_imag"]
            if c in df.columns]
    print()
    print_table(df, show, round_to=3)
    if args.out_csv:
        df.to_csv(args.out_csv, index=False)
        print(f"CSV: {args.out_csv}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: compute the production DFT descriptor matrix (M1).

    Args:
        argv: Command-line arguments (defaults to ``sys.argv``).

    Returns:
        The process exit code (0 on success).
    """
    args = _build_parser().parse_args(argv)
    case = resolve_case(args, metal="label")

    molecules = parse_molecules(args.molecules)
    forms = "neutral" if args.no_protonated else args.forms

    # The frequency check only makes sense on a stationary geometry, so both
    # minimum flags imply --optimize; --to-minimum (drive-to-minimum)
    # supersedes the plain --check-minimum (detect-and-flag).
    to_minimum = args.to_minimum
    check_minimum = args.check_minimum and not to_minimum
    optimize = args.optimize or check_minimum or to_minimum

    _warn_medium_mismatch(forms, args.medium)
    _default_descriptor_outputs(args, case.results_dir, optimize)
    opt_geom_dir = _opt_geom_dir(args, to_minimum, case.results_dir)

    # Pin the SCF memory budget for every engine call this run makes (single
    # points, optimisation, frequencies) via the env budget lever build_rks
    # reads back.
    if args.max_memory_mb:
        os.environ[MEMORY_BUDGET_ENV] = str(args.max_memory_mb)

    rows = analyse_matrix(molecules, engine=args.engine, metal=args.metal,
                          basis=args.basis, xc=args.xc,
                          forms=forms,
                          select_engine=args.select_engine,
                          optimize=optimize, opt_basis=args.opt_basis,
                          opt_xc=args.opt_xc, opt_solvent=args.opt_solvent,
                          opt_maxsteps=args.opt_maxsteps,
                          opt_geom_dir=opt_geom_dir,
                          check_minimum=check_minimum, to_minimum=to_minimum,
                          density_fit=bool(args.density_fit))

    _write_outputs(rows, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
