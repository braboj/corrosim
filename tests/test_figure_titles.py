"""Figure panel titles are sentence-cased (capitalised first word).

Guards against the lowercase panel titles ('side', 'atom indices') that shipped
in the pose and Fukui figures — every rendered subplot title must lead with a
capital so the manuscript figures read consistently.
"""
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from ase import Atoms

from corrosim import build_molecule
from corrosim.qm.fukui import FukuiResult
from corrosim.report import figures


def _titles(fig):
    """Non-empty subplot titles of a figure, in axis order."""
    return [ax.get_title() for ax in fig.axes if ax.get_title()]


def _leads_capital(title: str) -> bool:
    """True when the title's first character is not a lowercase letter."""
    return not title[0].islower()


class _FakeSystem:
    """Minimal adsorption-system stand-in for the pose renderer."""

    metal = "Fe"
    surface = "(110)"
    combined = Atoms("Fe2O", positions=[[0, 0, 0], [2.5, 0, 0], [1.2, 0, 3.0]])


def test_plot_adsorption_pose_panel_titles_are_capitalised():
    fig = figures.plot_adsorption_pose(_FakeSystem())
    titles = _titles(fig)
    assert titles == ["Fe(110) — top", "Fe(110) — side"]
    assert all(_leads_capital(t) for t in titles)
    plt.close(fig)


def test_plot_fukui_atom_index_panel_is_capitalised():
    pytest.importorskip("PIL")
    mol = build_molecule("tetrazole")
    syms = mol.symbols
    fk = FukuiResult.from_populations(
        symbols=syms,
        f_plus=[0.1] * len(syms),
        f_minus=[0.2] * len(syms),
        softness=1.0,
    )
    fig = figures.plot_fukui(fk, molecule=mol, title="Tetrazole — condensed Fukui")
    titles = _titles(fig)
    # The structure panel (present when RDKit 2D drawing is available) must be
    # 'Atom indices', not the old lowercase 'atom indices'.
    assert "Atom indices" in titles
    assert all(_leads_capital(t) for t in titles)
    plt.close(fig)


def test_plot_protonation_effect_legend_is_capitalised():
    df = pd.DataFrame(
        [
            {"name": "x", "form": "neutral", "phase": "aqueous",
             "gap_ev": 3.0, "delta_n": 0.20},
            {"name": "x+H+", "form": "protonated", "phase": "aqueous",
             "gap_ev": 3.2, "delta_n": 0.10},
        ]
    )
    fig = figures.plot_protonation_effect(df, ["x"])
    legends = {t.get_text()
               for ax in fig.axes if ax.get_legend()
               for t in ax.get_legend().get_texts()}
    assert legends == {"Neutral", "Protonated"}
    plt.close(fig)
