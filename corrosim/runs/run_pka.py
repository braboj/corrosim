"""
corrosim.runs.run_pka
=====================
Estimate each inhibitor's conjugate-acid pKa (pKaH) from a DFT thermodynamic cycle
on the aqueous neutral and protonated total energies — the quantity the speciation
layer (ADR 0004) leaves as a free parameter. Runs in the QM container (PySCF).

ELECTRONIC-ENERGY APPROXIMATION (see corrosim.pka / ADR 0005): by default this uses
ddCOSMO single points on the force-field geometries with no frequency calculation —
the absolute pKaH carries a few-units uncertainty, so the result locates the
*regime*, not a calibrated value.

    docker compose run --rm qm python -m corrosim.runs.run_pka \
        --out-json results/pka.json

Pass --freq (issue #18) to add the ZPE/thermal/entropy correction: each species is
gas-phase optimised + a Hessian gives G_corr, and the production single point runs
on the relaxed geometry. Slow (frequency calcs on ~40-atom molecules) — run detached:

    docker compose run -d --name corrosim_pka qm python -m corrosim.runs.run_pka \
        --freq --out-json results/pka.json
"""
from __future__ import annotations

import argparse
import json
import sys

from corrosim.engines import optimize_geometry, run_engine, thermo_correction
from corrosim.molecules import build_molecule
from corrosim.pka import G_AQ_PROTON_EV, estimate_pka
from corrosim.presets import ARGHEL
from corrosim.runs.run_dft import _best_protonation_site


def compute_pka_rows(molecules, basis="6-311++G(d,p)", xc="b3lyp",
                     select_engine="xtb", freq=False, opt_basis="6-31G(d)",
                     opt_xc="b3lyp", temperature=298.15) -> list[dict]:
    """Aqueous DFT energies for the neutral (B) + best-protonated cation (BH⁺) of
    each molecule, and the resulting pKaH.

    With ``freq=True`` (ADR 0005 refinement, issue #18): each species is first
    gas-phase geometry-optimised at ``opt_basis``/``opt_xc``, a Hessian gives the
    Gibbs correction G_corr = ZPE + H_thermal − T·S, and the production aqueous
    single point runs on the relaxed geometry — so the row carries a
    frequency-corrected pKaH alongside the electronic-only one. Returns a row per
    molecule."""
    rows = []
    for name in molecules:
        print(f"[{name}]", file=sys.stderr)
        neutral = build_molecule(name)
        print("  selecting protonation site ...", file=sys.stderr)
        _, cation = _best_protonation_site(name, select_engine)
        nb_sym, nb_xyz = list(neutral.symbols), neutral.coords
        cb_sym, cb_xyz = list(cation.symbols), cation.coords

        g_corr_b = g_corr_bh = 0.0
        tb = tbh = None
        if freq:
            print("  opt+freq neutral (gas) ...", file=sys.stderr)
            nb_sym, nb_xyz = optimize_geometry(neutral.symbols, neutral.coords,
                                               basis=opt_basis, xc=opt_xc, charge=0)
            tb = thermo_correction(nb_sym, nb_xyz, basis=opt_basis, xc=opt_xc,
                                   charge=0, temperature=temperature)
            print("  opt+freq cation (gas) ...", file=sys.stderr)
            cb_sym, cb_xyz = optimize_geometry(cation.symbols, cation.coords,
                                               basis=opt_basis, xc=opt_xc, charge=1)
            tbh = thermo_correction(cb_sym, cb_xyz, basis=opt_basis, xc=opt_xc,
                                    charge=1, temperature=temperature)
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
            "proton_affinity_aq_ev": round(e_b - e_bh, 4),   # ddCOSMO, electronic
            "g_aq_proton_ev": round(G_AQ_PROTON_EV, 4),
            "pkah_electronic": round(pkah_elec, 2),
            "level": f"{xc.upper()}/{basis} (ddCOSMO:water), electronic-only",
        }
        if freq:
            pkah_corr = estimate_pka(e_b, e_bh, g_corr_b, g_corr_bh, temperature)
            row.update({
                "g_corr_neutral_ev": round(g_corr_b, 4),
                "g_corr_cation_ev": round(g_corr_bh, 4),
                "pkah": round(pkah_corr, 2),                  # frequency-corrected
                "n_imag_neutral": tb["n_imag"],
                "n_imag_cation": tbh["n_imag"],
                "temperature_k": temperature,
                "level": f"{xc.upper()}/{basis} (ddCOSMO:water) // "
                         f"{opt_xc.upper()}/{opt_basis} gas opt+freq, "
                         "frequency-corrected",
            })
            imag = tb["n_imag"] + tbh["n_imag"]
            if imag:
                print(f"  WARNING: {imag} imaginary frequency(ies) — not a clean "
                      "minimum; correction unreliable.", file=sys.stderr)
            print(f"  pKaH ≈ {pkah_corr:.2f} (freq-corrected; electronic-only "
                  f"was {pkah_elec:.2f})", file=sys.stderr)
        else:
            print(f"  pKaH ≈ {pkah_elec:.2f} (electronic-only estimate)", file=sys.stderr)
        rows.append(row)
    return rows


def main(argv=None) -> int:
    """CLI entry point: estimate pKaH from a DFT deprotonation cycle (QM container)."""
    p = argparse.ArgumentParser(prog="corrosim-run-pka")
    p.add_argument("--molecules", default=",".join(ARGHEL.molecule_list()),
                   help="Comma-separated names or SMILES.")
    p.add_argument("--basis", default="6-311++G(d,p)")
    p.add_argument("--xc", default="b3lyp")
    p.add_argument("--select-engine", default="xtb")
    p.add_argument("--freq", action="store_true",
                   help="Add the ZPE/thermal/entropy correction from a gas-phase "
                        "opt+frequency calc (slow; QM container). Issue #18 / ADR 0005.")
    p.add_argument("--opt-basis", default="6-31G(d)",
                   help="Basis for the --freq gas opt+frequency step.")
    p.add_argument("--opt-xc", default="b3lyp")
    p.add_argument("--temperature", type=float, default=298.15)
    p.add_argument("--out-json", default=None)
    args = p.parse_args(argv)

    molecules = [m.strip() for m in args.molecules.split(",") if m.strip()]
    rows = compute_pka_rows(molecules, basis=args.basis, xc=args.xc,
                            select_engine=args.select_engine, freq=args.freq,
                            opt_basis=args.opt_basis, opt_xc=args.opt_xc,
                            temperature=args.temperature)

    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"JSON: {args.out_json}", file=sys.stderr)

    if args.freq:
        print("\nname            pKaH(corr)  pKaH(elec)   PA_aq(eV)")
        for r in rows:
            print(f"{r['name']:<15} {r.get('pkah', '—'):>9}   "
                  f"{r['pkah_electronic']:>9}   {r['proton_affinity_aq_ev']:>9}")
    else:
        print("\nname            pKaH(elec)   PA_aq(eV)")
        for r in rows:
            print(f"{r['name']:<15} {r['pkah_electronic']:>9}   "
                  f"{r['proton_affinity_aq_ev']:>9}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
