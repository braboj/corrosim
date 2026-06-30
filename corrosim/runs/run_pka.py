"""
corrosim.runs.run_pka
=====================
Estimate each inhibitor's conjugate-acid pKa (pKaH) from a DFT thermodynamic cycle
on the aqueous neutral and protonated total energies — the quantity the speciation
layer (ADR 0004) leaves as a free parameter. Runs in the QM container (PySCF).

ELECTRONIC-ENERGY APPROXIMATION (see corrosim.pka / ADR 0005): ddCOSMO single
points on the force-field geometries, no frequency calculation — the absolute pKaH
carries a few-units uncertainty, so the result locates the *regime*, not a
calibrated value.

    docker compose run --rm qm python -m corrosim.runs.run_pka \
        --out-json results/pka.json
"""
from __future__ import annotations

import argparse
import json
import sys

from corrosim.engines import run_engine
from corrosim.molecules import build_molecule
from corrosim.pka import G_AQ_PROTON_EV, estimate_pka
from corrosim.presets import ARGHEL
from corrosim.runs.run_dft import _best_protonation_site


def compute_pka_rows(molecules, basis="6-311++G(d,p)", xc="b3lyp",
                     select_engine="xtb") -> list[dict]:
    """Aqueous DFT energies for the neutral + best-protonated cation of each
    molecule, and the resulting pKaH. Returns a row dict per molecule."""
    rows = []
    for name in molecules:
        print(f"[{name}]", file=sys.stderr)
        neutral = build_molecule(name)
        print("  selecting protonation site ...", file=sys.stderr)
        _, cation = _best_protonation_site(name, select_engine)

        print("  DFT neutral/aqueous ...", file=sys.stderr)
        e_b = run_engine(neutral.symbols, neutral.coords, engine="pyscf", charge=0,
                         basis=basis, xc=xc, solvent="water").e_total_ev
        print("  DFT cation/aqueous ...", file=sys.stderr)
        e_bh = run_engine(cation.symbols, cation.coords, engine="pyscf", charge=1,
                          basis=basis, xc=xc, solvent="water").e_total_ev

        pkah = estimate_pka(e_b, e_bh)
        rows.append({
            "name": name,
            "e_neutral_aq_ev": round(e_b, 4),
            "e_cation_aq_ev": round(e_bh, 4),
            "proton_affinity_aq_ev": round(e_b - e_bh, 4),   # ddCOSMO, electronic
            "g_aq_proton_ev": round(G_AQ_PROTON_EV, 4),
            "pkah_electronic": round(pkah, 2),
            "level": f"{xc.upper()}/{basis} (ddCOSMO:water), electronic-only",
        })
        print(f"  pKaH ≈ {pkah:.2f} (electronic-only estimate)", file=sys.stderr)
    return rows


def main(argv=None) -> int:
    """CLI entry point: estimate pKaH from a DFT deprotonation cycle (QM container)."""
    p = argparse.ArgumentParser(prog="corrosim-run-pka")
    p.add_argument("--molecules", default=",".join(ARGHEL.molecule_list()),
                   help="Comma-separated names or SMILES.")
    p.add_argument("--basis", default="6-311++G(d,p)")
    p.add_argument("--xc", default="b3lyp")
    p.add_argument("--select-engine", default="xtb")
    p.add_argument("--out-json", default=None)
    args = p.parse_args(argv)

    molecules = [m.strip() for m in args.molecules.split(",") if m.strip()]
    rows = compute_pka_rows(molecules, basis=args.basis, xc=args.xc,
                            select_engine=args.select_engine)

    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"JSON: {args.out_json}", file=sys.stderr)

    print("\nname            pKaH(elec)   PA_aq(eV)")
    for r in rows:
        print(f"{r['name']:<15} {r['pkah_electronic']:>9}   {r['proton_affinity_aq_ev']:>9}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
