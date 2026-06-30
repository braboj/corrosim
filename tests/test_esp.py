"""ESP-map renderer test. Uses synthetic density+ESP cubes (no PySCF/QM container):
validates that render_esp marches the density isosurface, samples the potential on
the shared grid, and writes a non-trivial PNG."""
import matplotlib

matplotlib.use("Agg")

import numpy as np
from ase import Atoms
from ase.io.cube import write_cube

from corrosim import figures


def _write_synthetic_cubes(tmp_path):
    # two oxygens 2 A apart in a 6 A box, on a shared 20^3 grid
    atoms = Atoms("OO", positions=[[2, 3, 3], [4, 3, 3]], cell=[6, 6, 6])
    n = 20
    xs = np.linspace(0, 6, n, endpoint=False)
    X, Y, Z = np.meshgrid(xs, xs, xs, indexing="ij")
    rho = (np.exp(-((X - 2) ** 2 + (Y - 3) ** 2 + (Z - 3) ** 2))
           + np.exp(-((X - 4) ** 2 + (Y - 3) ** 2 + (Z - 3) ** 2)))
    esp = (X - 3) * 0.05                      # gradient: negative left, positive right
    dpath, epath = tmp_path / "m_density.cube", tmp_path / "m_esp.cube"
    with open(dpath, "w") as f:
        write_cube(f, atoms, data=rho)
    with open(epath, "w") as f:
        write_cube(f, atoms, data=esp)
    return str(dpath), str(epath)


def test_render_esp_writes_png(tmp_path):
    dens, esp = _write_synthetic_cubes(tmp_path)
    out = tmp_path / "esp.png"
    res = figures.render_esp(dens, esp, out=str(out), iso=0.3, title="synthetic")
    assert res == str(out)
    assert out.exists() and out.stat().st_size > 1000


def test_render_esp_falls_back_when_iso_absent(tmp_path):
    # an iso level above the density max should fall back to a present quantile,
    # not raise
    dens, esp = _write_synthetic_cubes(tmp_path)
    out = tmp_path / "esp2.png"
    figures.render_esp(dens, esp, out=str(out), iso=999.0)
    assert out.exists()
