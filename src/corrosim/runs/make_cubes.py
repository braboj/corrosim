"""corrosim.runs.make_cubes (QM container step).

Generate the volumetric cubes the 3D figures need: HOMO/LUMO orbitals and the
electron-density + electrostatic-potential pair for the ESP map. This is the
only figure input that needs PySCF, so it runs in the QM container; the cubes
land in the bind-mounted repo and are then rendered (anywhere) by make_figures.

    docker compose run --rm qm python -m corrosim.runs.make_cubes \
        --molecules quercetin --what orbital,esp

The ESP/MEP integral is the slow part; default grid nx=80 + 6-31G(d) keeps it
to a few minutes per molecule. Long jobs: run in the background (see CLAUDE.md
1.3).
"""
from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from corrosim import build_molecule
from corrosim.qm import cubes
from corrosim.runs._cli import parse_molecules, safe_path_component
from corrosim.runs._cli import stderr_log as log


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: write HOMO/LUMO and density+ESP .cube files.

    Needs PySCF (runs in the QM container).

    Args:
        argv: Command-line arguments (defaults to ``sys.argv``).

    Returns:
        The process exit code (0 on success).
    """
    p = argparse.ArgumentParser(prog="corrosim-make-cubes")
    p.add_argument("--molecules", default="quercetin",
                   help="Comma-separated names/SMILES (default: quercetin).")
    p.add_argument("--what", default="orbital,esp",
                   help="Which cubes: any of orbital,esp (comma-separated).")
    p.add_argument("--outdir", default="cubes",
                   help="Directory for the .cube files (gitignored, "
                        "regenerable).")
    p.add_argument("--basis", default="6-31G(d)",
                   help="Cube basis (shapes are basis-insensitive; keep it "
                        "small).")
    p.add_argument("--xc", default="b3lyp")
    p.add_argument("--nx", type=int, default=80, help="Grid points per axis.")
    args = p.parse_args(argv)
    what = {w.strip().lower() for w in args.what.split(",") if w.strip()}
    names = parse_molecules(args.molecules)
    os.makedirs(args.outdir, exist_ok=True)

    for name in names:
        m = build_molecule(name)
        prefix = os.path.join(args.outdir, safe_path_component(name))
        if "orbital" in what:
            log(f"[{name}] HOMO/LUMO cubes ...")
            paths = cubes.write_orbital_cubes(
                m.symbols, m.coords, prefix=prefix, basis=args.basis,
                xc=args.xc, charge=m.charge, nx=args.nx)
            log(f"    {paths['homo']}, {paths['lumo']}")
        if "esp" in what:
            log(f"[{name}] density + ESP cubes (MEP integral, slow) ...")
            paths = cubes.write_density_esp_cubes(
                m.symbols, m.coords, prefix=prefix, basis=args.basis,
                xc=args.xc, charge=m.charge, nx=args.nx)
            log(f"    {paths['density']}, {paths['esp']}")
    print("cubes written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
