"""Smoke test for the FF-vs-DFT-optimised geometry comparison plotter."""
import matplotlib
matplotlib.use("Agg")

import pandas as pd
from corrosim import figures


def _frame(gap_by_name):
    rows = []
    for name, gap in gap_by_name.items():
        rows.append(dict(name=name, form="neutral", phase="aqueous",
                         gap_ev=gap, hardness_ev=gap / 2,
                         softness_inv_ev=2 / gap, delta_n=0.2, tnc=-5.0))
    return pd.DataFrame(rows)


def test_plot_geometry_comparison_writes_png(tmp_path):
    order = ["kaempferol", "quercetin"]
    ff = _frame({"kaempferol": 4.15, "quercetin": 4.08})
    opt = _frame({"kaempferol": 3.69, "quercetin": 3.60})
    out = tmp_path / "fig8.png"
    res = figures.plot_geometry_comparison(ff, opt, order, out=str(out))
    assert res == str(out)
    assert out.exists() and out.stat().st_size > 1000
