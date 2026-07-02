"""The per-stage report layout map (report_layout): figures and tables resolve to
their stage subfolder, and the write side / read side agree."""
from __future__ import annotations

import os

from corrosim import report_layout as L


def test_figure_stage_maps_each_family_to_its_stage():
    assert L.figure_stage("fig0_pipeline.png") == "pipeline"
    assert L.figure_stage("fig1_structures.png") == "dft"
    assert L.figure_stage("fig2b_quercetin_homo.png") == "dft"
    assert L.figure_stage("fig3b_protonation.png") == "dft"
    assert L.figure_stage("fig8_geometry_comparison.png") == "dft"
    assert L.figure_stage("fig4_quercetin_fukui.png") == "fukui"
    assert L.figure_stage("fig5_quercetin_mc_pose.png") == "mc"
    assert L.figure_stage("fig6_quercetin_rdf.png") == "md"
    assert L.figure_stage("fig7_quercetin_esp.png") == "esp"


def test_figure_stage_unknown_falls_back_to_dft():
    assert L.figure_stage("mystery.png") == "dft"


def test_figure_path_nests_under_stage_subfolder():
    p = L.figure_path("report/figures", "fig5_quercetin_mc_pose.png")
    assert p == os.path.join("report/figures", "mc", "fig5_quercetin_mc_pose.png")
    # a full path is reduced to its basename before nesting
    p2 = L.figure_path("out", "/some/where/fig4_x_fukui.png")
    assert p2 == os.path.join("out", "fukui", "fig4_x_fukui.png")


def test_table_stage_and_path():
    assert L.table_stage("ranking.csv") == "dft"
    assert L.table_stage("pka.json") == "pka"
    assert L.table_stage("unknown.csv") == "dft"
    assert L.table_path("report/tables", "pka.json") == \
        os.path.join("report/tables", "pka", "pka.json")


def test_every_declared_stage_is_reachable():
    # each stage in FIGURE_STAGES is actually produced by some figure prefix
    produced = {L.figure_stage(f"{p}_x.png") for p, _ in L._FIG_PREFIX_STAGE}
    assert set(L.FIGURE_STAGES) <= produced
