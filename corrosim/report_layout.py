"""corrosim.report_layout.

Single source of truth for the *per-stage* layout of the ``report/`` bundle: the
figures and tables are grouped into pipeline-stage subfolders
(``report/figures/dft/``, ``.../mc/`` …) so a reader can navigate the output by
stage rather than a flat pile of ``figN_*`` files. The figure generator
(``runs.make_figures``), the report builders (``report`` / ``report_docx``) and
the table bundler (``runs.make_report``) all resolve paths through this module so
the write side and the read side never drift.

The scheme nests one extra level under the existing ``report/figures`` and
``report/tables`` roots; the ``figN_`` manuscript numbering is kept as the file
name so figure references stay stable.
"""
from __future__ import annotations

import os

# Stage subfolders under report/figures/, in pipeline order.
FIGURE_STAGES = ("pipeline", "dft", "fukui", "esp", "mc", "md")

# Figure-filename prefix -> stage subfolder. The per-molecule families
# (fig2b/fig4/fig5/fig6/fig7_<name>_*) map by their numeric prefix.
_FIG_PREFIX_STAGE = (
    ("fig0", "pipeline"),   # pipeline diagram
    ("fig1", "dft"),        # 2D structures
    ("fig2", "dft"),        # MO diagram + fig2b HOMO/LUMO isosurfaces
    ("fig3", "dft"),        # descriptor bars + fig3b protonation effect
    ("fig4", "fukui"),      # condensed Fukui maps
    ("fig5", "mc"),         # MC pose + annealing trace
    ("fig6", "md"),         # metal-O RDF
    ("fig7", "esp"),        # ESP / MEP maps
    ("fig8", "dft"),        # FF-vs-DFT-opt geometry comparison
)

# Table-filename -> stage subfolder.
TABLE_STAGE = {
    "dft_descriptors.csv": "dft",
    "dft_descriptors_opt.csv": "dft",
    "ranking.csv": "dft",
    "geometry_comparison.csv": "dft",
    "pka.json": "pka",
}


def figure_stage(filename: str) -> str:
    """Return the stage subfolder for a figure file name (e.g. ``fig4_x.png`` ->
    ``'fukui'``). Unknown names fall back to ``'dft'`` (the Stage-1 catch-all).
    """
    base = os.path.basename(filename)
    for prefix, stage in _FIG_PREFIX_STAGE:
        if base.startswith(prefix):
            return stage
    return "dft"


def figure_path(figdir: str, filename: str) -> str:
    """Path of a figure inside its stage subfolder: ``<figdir>/<stage>/<name>``."""
    return os.path.join(figdir, figure_stage(filename), os.path.basename(filename))


def table_stage(filename: str) -> str:
    """Return the stage subfolder for a table file name; unknown -> ``'dft'``."""
    return TABLE_STAGE.get(os.path.basename(filename), "dft")


def table_path(tablesdir: str, filename: str) -> str:
    """Path of a table inside its stage subfolder: ``<tablesdir>/<stage>/<name>``."""
    return os.path.join(tablesdir, table_stage(filename), os.path.basename(filename))
