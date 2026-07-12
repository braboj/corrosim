"""corrosim.report — reporting and visualisation.

HTML/DOCX pipeline reports, the report-bundle layout helpers, narrative
content, equation rendering, and figures. `figures` and `report_docx` are NOT
imported eagerly — they stay plain submodules so the viz/docx optional extras
are only required when actually used (`from corrosim.report import figures`).
"""
from __future__ import annotations

from .ranking import RankingEnsemble
from .report import (
    PreparedReport,
    build_html_report,
    build_pipeline_report,
    prepare_report_data,
    rank_inhibitors,
    report_ensemble,
    results_dataframe,
    top_donor_sites_of_element,
)
from .report_layout import figure_path, table_path

__all__ = ["PreparedReport", "RankingEnsemble", "build_html_report",
           "build_pipeline_report", "prepare_report_data", "rank_inhibitors",
           "report_ensemble", "results_dataframe", "top_donor_sites_of_element",
           "figure_path", "table_path"]
