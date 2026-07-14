"""Atom-colour legend on the 3D figures.

The manuscript-style HOMO/LUMO and adsorption-pose figures must carry a
'Color code' key describing which colour is which element (substrate metal
included), driven by one shared palette so it reads the same everywhere.
"""
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from ase import Atoms

from corrosim.report import figures


def _legend_labels(fig):
    """The text labels of the figure-level 'Color code' legend, in order."""
    assert fig.legends, "expected a figure-level legend"
    return [t.get_text() for t in fig.legends[0].get_texts()]


def test_atom_color_legend_orders_metal_first_and_dedupes():
    fig = plt.figure()
    figures._atom_color_legend(fig, ["C", "C", "H", "O", "Fe", "N"])
    # metal leads, then the common organics in the canonical order; duplicates
    # collapse to one entry each
    assert _legend_labels(fig) == ["Fe", "C", "H", "N", "O"]
    plt.close(fig)


def test_atom_color_legend_appends_unknown_element():
    fig = plt.figure()
    figures._atom_color_legend(fig, ["C", "Xx"])
    labels = _legend_labels(fig)
    assert labels[0] == "C" and labels[-1] == "Xx"
    plt.close(fig)


def test_palette_covers_the_validated_metals():
    # every substrate the tool validates against needs a pose colour
    for metal in ("Fe", "Cu", "Al"):
        assert metal in figures._ELEM_COLOR


class _FakeSystem:
    """Minimal stand-in for an AdsorptionSystem/MCResult for pose rendering."""

    def __init__(self, combined, metal, surface):
        self.combined = combined
        self.metal = metal
        self.surface = surface


def test_adsorption_pose_legend_includes_metal_and_atoms(tmp_path):
    # a two-layer Fe patch with a tiny C-O-H adsorbate above it
    combined = Atoms(
        "Fe4COH",
        positions=[
            [0, 0, 0], [2, 0, 0], [0, 2, 0], [2, 2, 0],
            [1, 1, 3], [2, 1, 3], [1, 1, 4],
        ],
        cell=[6, 6, 12],
    )
    system = _FakeSystem(combined, metal="Fe", surface="(110)")
    out = tmp_path / "pose.png"
    fig = figures.plot_adsorption_pose(system, out=None)
    # the legend names the substrate metal and every adsorbate element
    assert set(_legend_labels(fig)) == {"Fe", "C", "O", "H"}
    plt.close(fig)
    # and it still writes a non-trivial PNG through the normal path
    figures.plot_adsorption_pose(system, out=str(out))
    assert out.exists() and out.stat().st_size > 1000
