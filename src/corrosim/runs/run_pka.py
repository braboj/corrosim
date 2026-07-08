"""corrosim.runs.run_pka.

Estimate each inhibitor's conjugate-acid pKa (pKaH) from a DFT thermodynamic
cycle on the aqueous neutral and protonated total energies — the quantity the
speciation layer leaves as a free parameter. Runs in the QM
container (PySCF).

ELECTRONIC-ENERGY APPROXIMATION (see corrosim.pka): by default this
uses ddCOSMO single points on the force-field geometries with no frequency
calculation — the absolute pKaH carries a few-units uncertainty, so the result
locates the *regime*, not a calibrated value.

    docker compose run --rm qm python -m corrosim.runs.run_pka \
        --out-json cases/arghel/results/pka.json

Pass --freq to add the ZPE/thermal/entropy correction: each species
is gas-phase optimised + a Hessian gives G_corr, and the production single
point runs on the relaxed geometry. Slow (frequency calcs on ~40-atom
molecules) — run detached:

    docker compose run -d --name corrosim_pka qm \
        python -m corrosim.runs.run_pka --freq \
        --out-json cases/arghel/results/pka.json

Add --tight to drive a floppy rotor to a true minimum — finer DFT
grid (level 4) + imaginary-mode restarts — e.g. to clear the lone imaginary
frequency on the isorhamnetin cation:

    docker compose run -d --name corrosim_pka qm \
        python -m corrosim.runs.run_pka --freq --tight \
        --molecules isorhamnetin \
        --out-json cases/arghel/results/pka_isorhamnetin.json
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from corrosim.molecules import build_molecule
from corrosim.qm.engines import (
    MIN_RECIPE,
    Coords,
    optimize_geometry,
    relax_to_minimum,
    run_engine,
    thermo_correction,
)
from corrosim.qm.pka import G_AQ_PROTON_EV, estimate_pka
from corrosim.qm.protonation import best_protonation_site
from corrosim.runs._cli import (
    add_case_arg,
    add_molecules_arg,
    parse_molecules,
    resolve_case,
    stderr_log,
    write_json,
)


def _relax_and_thermo(symbols, coords, charge, opt_basis, opt_xc, temperature,
                      tight) -> tuple[list[str], Coords, dict]:
    """Gas-phase geometry + Gibbs correction for one species.

    The default path is a single opt + Hessian; ``tight=True`` uses
    :func:`relax_to_minimum` (finer grid, tight convergence, imaginary-mode
    restarts) to drive a floppy rotor to a true minimum.
    """
    if tight:
        return relax_to_minimum(symbols, coords, basis=opt_basis, xc=opt_xc,
                                charge=charge, temperature=temperature)
    sym, xyz = optimize_geometry(symbols, coords, basis=opt_basis, xc=opt_xc,
                                 charge=charge)
    info = thermo_correction(sym, xyz, basis=opt_basis, xc=opt_xc,
                             charge=charge, temperature=temperature)
    return sym, xyz, info


def compute_pka_rows(molecules: Sequence[str], basis: str = "6-311++G(d,p)",
                     xc: str = "b3lyp", select_engine: str = "xtb",
                     freq: bool = False, opt_basis: str = "6-31G(d)",
                     opt_xc: str = "b3lyp", temperature: float = 298.15,
                     tight: bool = False) -> list[dict]:
    """Aqueous pKaH rows for the neutral (B) + best cation (BH⁺) per molecule.

    With ``freq=True`` each species is first gas-phase geometry-optimised at
    ``opt_basis``/``opt_xc``, a Hessian gives the Gibbs correction
    G_corr = ZPE + H_thermal − T·S, and the production aqueous single point runs
    on the relaxed geometry — so the row carries a frequency-corrected pKaH
    alongside the electronic-only one. ``tight=True`` drives each species to a
    true minimum (finer grid + imaginary-mode restarts) — for the isorhamnetin
    cation, whose flat methoxy torsion tips imaginary under the default grid.

    Args:
        molecules: Library names or SMILES to process.
        basis: Production AO basis for the aqueous single points.
        xc: Exchange-correlation functional.
        select_engine: Fast engine for protonation-site selection.
        freq: Add the frequency (Gibbs) correction.
        opt_basis: Basis for the ``freq`` gas opt+frequency step.
        opt_xc: Functional for the ``freq`` step.
        temperature: Temperature (K).
        tight: Drive each ``freq`` geometry to a verified true minimum.

    Returns:
        One row dict per molecule with the pKaH and its provenance.
    """
    rows = []
    for name in molecules:
        print(f"[{name}]", file=sys.stderr)
        neutral = build_molecule(name)
        print("  selecting protonation site ...", file=sys.stderr)
        _, cation = best_protonation_site(name, select_engine, log=stderr_log)
        nb_sym: list[str]
        cb_sym: list[str]
        nb_xyz: Coords
        cb_xyz: Coords
        nb_sym, nb_xyz = list(neutral.symbols), neutral.coords
        cb_sym, cb_xyz = list(cation.symbols), cation.coords

        g_corr_b = g_corr_bh = 0.0
        tb: dict = {}
        tbh: dict = {}
        if freq:
            print("  opt+freq neutral (gas) ...", file=sys.stderr)
            nb_sym, nb_xyz, tb = _relax_and_thermo(
                neutral.symbols, neutral.coords, 0, opt_basis, opt_xc,
                temperature, tight)
            print("  opt+freq cation (gas) ...", file=sys.stderr)
            cb_sym, cb_xyz, tbh = _relax_and_thermo(
                cation.symbols, cation.coords, 1, opt_basis, opt_xc,
                temperature, tight)
            g_corr_b, g_corr_bh = tb["g_corr_ev"], tbh["g_corr_ev"]

        print("  DFT neutral/aqueous ...", file=sys.stderr)
        e_b = run_engine(nb_sym, nb_xyz, engine="pyscf", charge=0,
                         basis=basis, xc=xc, solvent="water").e_total_ev
        print("  DFT cation/aqueous ...", file=sys.stderr)
        e_bh = run_engine(cb_sym, cb_xyz, engine="pyscf", charge=1,
                          basis=basis, xc=xc, solvent="water").e_total_ev

        pkah_elec = estimate_pka(e_b, e_bh)
        row = {
            "name": name,
            "e_neutral_aq_ev": round(e_b, 4),
            "e_cation_aq_ev": round(e_bh, 4),
            # ddCOSMO, electronic
            "proton_affinity_aq_ev": round(e_b - e_bh, 4),
            "g_aq_proton_ev": round(G_AQ_PROTON_EV, 4),
            "pkah_electronic": round(pkah_elec, 2),
            "level": f"{xc.upper()}/{basis} (ddCOSMO:water), electronic-only",
        }
        if freq:
            pkah_corr = estimate_pka(e_b, e_bh, g_corr_b, g_corr_bh,
                                     temperature)
            row.update({
                "g_corr_neutral_ev": round(g_corr_b, 4),
                "g_corr_cation_ev": round(g_corr_bh, 4),
                # Frequency-corrected
                "pkah": round(pkah_corr, 2),
                "n_imag_neutral": tb["n_imag"],
                "n_imag_cation": tbh["n_imag"],
                "temperature_k": temperature,
                "level": f"{xc.upper()}/{basis} (ddCOSMO:water) // "
                         f"{opt_xc.upper()}/{opt_basis} gas opt+freq"
                         + (f" ({MIN_RECIPE})" if tight else "")
                         + ", frequency-corrected",
            })
            imag = tb["n_imag"] + tbh["n_imag"]
            if imag:
                print(f"  WARNING: {imag} imaginary frequency(ies) — not a "
                      "clean minimum; correction unreliable.", file=sys.stderr)
            print(f"  pKaH ≈ {pkah_corr:.2f} (freq-corrected; electronic-only "
                  f"was {pkah_elec:.2f})", file=sys.stderr)
        else:
            print(f"  pKaH ≈ {pkah_elec:.2f} (electronic-only estimate)",
                  file=sys.stderr)
        rows.append(row)
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: estimate pKaH from a DFT deprotonation cycle.

    Runs in the QM container (PySCF).

    Args:
        argv: Command-line arguments (defaults to ``sys.argv``).

    Returns:
        The process exit code (0 on success).
    """
    p = argparse.ArgumentParser(prog="corrosim-run-pka")
    add_molecules_arg(p)
    add_case_arg(p)
    p.add_argument("--basis", default="6-311++G(d,p)")
    p.add_argument("--xc", default="b3lyp")
    p.add_argument("--select-engine", default="xtb")
    p.add_argument("--freq", action="store_true",
                   help="Add the ZPE/thermal/entropy correction from a "
                        "gas-phase opt+frequency calc (slow; QM container).")
    p.add_argument("--opt-basis", default="6-31G(d)",
                   help="Basis for the --freq gas opt+frequency step.")
    p.add_argument("--opt-xc", default="b3lyp")
    p.add_argument("--tight", action="store_true",
                   help="Drive each --freq geometry to a true minimum: finer "
                        "DFT grid (level 4) + imaginary-mode restarts. Clears "
                        "a floppy-rotor imaginary mode.")
    p.add_argument("--temperature", type=float, default=298.15)
    p.add_argument("--out-json", default=None)
    args = p.parse_args(argv)
    resolve_case(args)

    molecules = parse_molecules(args.molecules)
    rows = compute_pka_rows(molecules, basis=args.basis, xc=args.xc,
                            select_engine=args.select_engine, freq=args.freq,
                            opt_basis=args.opt_basis, opt_xc=args.opt_xc,
                            temperature=args.temperature, tight=args.tight)

    if args.out_json:
        write_json(args.out_json, rows)
        print(f"JSON: {args.out_json}", file=sys.stderr)

    if args.freq:
        print("\nname            pKaH(corr)  pKaH(elec)   PA_aq(eV)")
        for r in rows:
            print(f"{r['name']:<15} {r.get('pkah', '—'):>9}   "
                  f"{r['pkah_electronic']:>9}   "
                  f"{r['proton_affinity_aq_ev']:>9}")
    else:
        print("\nname            pKaH(elec)   PA_aq(eV)")
        for r in rows:
            print(f"{r['name']:<15} {r['pkah_electronic']:>9}   "
                  f"{r['proton_affinity_aq_ev']:>9}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
