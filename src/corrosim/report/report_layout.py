"""corrosim.report_layout.

Single source of truth for the *per-stage* layout of the ``report/<case>/``
bundle: the figures and tables are grouped into pipeline-stage subfolders
(``report/<case>/figures/dft/``, ``.../mc/`` …) so a reader can navigate the
output by stage rather than a flat pile of ``figN_*`` files. The figure
generator (``runs.make_figures``), the report builders (``report`` /
``report_docx``) and
the table bundler (``runs.make_report``) all resolve paths through this module
so the write side and the read side never drift.

The scheme nests one extra level under the existing ``report/figures`` and
``report/tables`` roots; the ``figN_`` manuscript numbering is kept as the file
name so figure references stay stable.
"""
from __future__ import annotations

import os

# Stage subfolders under report/<case>/figures/, in pipeline order.
FIGURE_STAGES = ("pipeline", "dft", "fukui", "esp", "mc", "md")

# Figure-filename prefix -> stage subfolder. The per-molecule families
# (fig2b/fig4/fig5/fig6/fig7_<name>_*) map by their numeric prefix.
_FIG_PREFIX_STAGE = (
    # Pipeline diagram
    ("fig0", "pipeline"),
    # 2D structures
    ("fig1", "dft"),
    # MO diagram + fig2b HOMO/LUMO isosurfaces
    ("fig2", "dft"),
    # Descriptor bars + fig3b protonation effect
    ("fig3", "dft"),
    # Condensed Fukui maps
    ("fig4", "fukui"),
    # MC pose + annealing trace
    ("fig5", "mc"),
    # Metal-O RDF
    ("fig6", "md"),
    # ESP / MEP maps
    ("fig7", "esp"),
    # FF-vs-DFT-opt geometry comparison
    ("fig8", "dft"),
)

# Table-filename -> stage subfolder.
TABLE_STAGE = {
    "dft_descriptors_ff.csv": "dft",
    "dft_descriptors_opt.csv": "dft",
    "ranking.csv": "dft",
    "geometry_comparison.csv": "dft",
    "pka.json": "pka",
}


def figure_stage(filename: str) -> str:
    """Return the stage subfolder for a figure file name.

    Args:
        filename: A figure file name, e.g. ``fig4_x.png``.

    Returns:
        The stage subfolder (e.g. ``'fukui'``); unknown names fall back to
        ``'dft'`` (the DFT catch-all).
    """
    base = os.path.basename(filename)
    for prefix, stage in _FIG_PREFIX_STAGE:
        if base.startswith(prefix):
            return stage
    return "dft"


def figure_path(figdir: str, filename: str) -> str:
    """Resolve a figure's path inside its stage subfolder.

    Args:
        figdir: The figures root (e.g. ``report/figures``).
        filename: The figure file name.

    Returns:
        ``<figdir>/<stage>/<name>``.
    """
    return os.path.join(figdir, figure_stage(filename),
                        os.path.basename(filename))


def table_stage(filename: str) -> str:
    """Return the stage subfolder for a table file name.

    Args:
        filename: A table file name.

    Returns:
        The stage subfolder; unknown names fall back to ``'dft'``.
    """
    return TABLE_STAGE.get(os.path.basename(filename), "dft")


def table_path(tablesdir: str, filename: str) -> str:
    """Resolve a table's path inside its stage subfolder.

    Args:
        tablesdir: The tables root (e.g. ``report/tables``).
        filename: The table file name.

    Returns:
        ``<tablesdir>/<stage>/<name>``.
    """
    return os.path.join(tablesdir, table_stage(filename),
                        os.path.basename(filename))
