"""The governing-equation catalog renders to real PNGs via matplotlib mathtext
(no LaTeX/MathJax), so both report formats can show equations in scientific form."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from corrosim import equations as E

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_catalog_is_grouped_and_indexed():
    assert E.EQUATION_GROUPS, "expected ordered equation groups"
    flat = [eq for _, group in E.EQUATION_GROUPS for eq in group]
    # the flat lookup covers exactly the grouped equations
    assert set(E.EQUATIONS) == {eq.key for eq in flat}
    # the key descriptors are present
    for key in ("gap", "eta", "delta_n", "f_minus", "henderson", "e_ads", "rdf_peak"):
        assert key in E.EQUATIONS


def test_every_equation_renders_to_png():
    for key, eq in E.EQUATIONS.items():
        png = E.render_equation_png(eq.latex)
        assert png[:8] == _PNG_MAGIC, f"{key} did not render to PNG"
        assert len(png) > 200


def test_render_is_deterministic_for_same_input():
    a = E.render_equation_png(E.EQUATIONS["delta_n"].latex)
    b = E.render_equation_png(E.EQUATIONS["delta_n"].latex)
    assert a == b
