"""The Overview pipeline diagram (fig0) ships as package data and the figure
driver copies it into a case bundle.

fig0 is the one figure that is not plotted from case data — it is the same
case-agnostic schematic for every substrate, shipped inside the package and
placed into each bundle by ``figures.place_pipeline_diagram``. These tests guard
the two ways it used to go missing: the asset not shipping, and a rendered
report bundle lacking the figure the manual copy step used to provide.
"""
from __future__ import annotations

import os

from corrosim.presets import CASE_STUDIES
from corrosim.report import figures
from corrosim.report.report_layout import figure_path

# The 8-byte PNG file signature; a real render starts with it.
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_place_pipeline_diagram_writes_a_png(tmp_path):
    out = os.path.join(tmp_path, "fig0_pipeline.png")
    ret = figures.place_pipeline_diagram(out)
    assert ret == out
    data = open(out, "rb").read()
    assert data.startswith(_PNG_MAGIC)
    assert len(data) > 1000


def test_place_pipeline_diagram_is_idempotent(tmp_path):
    out = os.path.join(tmp_path, "fig0_pipeline.png")
    first = open(figures.place_pipeline_diagram(out), "rb").read()
    second = open(figures.place_pipeline_diagram(out), "rb").read()
    # re-running the driver over an existing bundle reproduces the same bytes
    assert first == second


def test_every_rendered_bundle_has_the_pipeline_diagram():
    # every case whose report has actually been rendered must carry fig0 in its
    # bundle, the regression the manual copy step used to leave to chance
    rendered = [
        c for c in CASE_STUDIES.values()
        if os.path.exists(os.path.join(c.report_dir, "report.html"))
    ]
    assert rendered, "expected at least one rendered case bundle"
    missing = [
        c.name for c in rendered
        if not os.path.exists(
            figure_path(f"{c.report_dir}/figures", "fig0_pipeline.png"))
    ]
    assert not missing, f"bundles missing fig0_pipeline.png: {missing}"
