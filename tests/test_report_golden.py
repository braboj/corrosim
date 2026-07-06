"""Full-report golden / characterization test.

Renders the whole pipeline report with *every* optional section switched on
(acid cations, speciation, computed pKaH, optimised-geometry descriptors) and
pins the output, so a renderer change is caught byte-for-byte (HTML) and
section-for-section (Word). This is the safety net for the HTML+docx
render-seam refactor (issue #127): the block walker must reproduce these
exactly.

Determinism: the timestamp is pinned and ``figdir`` is absent, so no live clock
and no embedded figures leak in — the output is a pure function of the inputs.

To refresh the goldens after an *intentional* report change, regenerate and
eyeball the diff:

    UPDATE_GOLDENS=1 pytest -q tests/test_report_golden.py
"""
import os
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import pandas as pd
import pytest

from corrosim import report
from corrosim.qm.speciation import analyse_speciation, protonation_fraction

GOLDENS = Path(__file__).parent / "goldens"
FIXED_TS = "2026-01-01 00:00"
METAL = "Fe(110)"
MEDIUM = "1 M HCl"
ORDER = ["quercetin", "kaempferol", "isorhamnetin"]


def _descr_row(name: str, gap: float, hardness: float) -> dict:
    """One full neutral descriptor row (mirrors the run_dft matrix columns)."""
    return {
        "name": name, "formula": "C15H10O7", "charge": 0,
        "level": "B3LYP/6-311++G(d,p) (ddCOSMO:water)",
        "homo_ev": -6.0, "lumo_ev": -6.0 + gap, "gap_ev": gap,
        "hardness_ev": hardness, "softness_inv_ev": 1 / hardness,
        "electronegativity_ev": 4.0, "electrophilicity_ev": 4.0,
        "delta_n": 0.2, "back_donation_ev": -0.5, "tnc": -4.0,
    }


def _full_inputs() -> dict:
    """Every renderer input, with all optional sections populated."""
    neutral = [_descr_row("quercetin", 4.0, 2.0),
               _descr_row("kaempferol", 4.4, 2.2),
               _descr_row("isorhamnetin", 4.6, 2.3)]
    acid = [{**_descr_row("quercetin+H+", 3.3, 1.6), "charge": 1,
             "delta_n": -0.05},
            {**_descr_row("kaempferol+H+", 3.6, 1.8), "charge": 1,
             "delta_n": -0.07},
            {**_descr_row("isorhamnetin+H+", 3.8, 1.9), "charge": 1,
             "delta_n": -0.06}]
    opt_neutral = [_descr_row("quercetin", 3.7, 1.85),
                   _descr_row("kaempferol", 4.1, 2.05),
                   _descr_row("isorhamnetin", 4.3, 2.15)]
    opt_acid = [{**_descr_row("quercetin+H+", 3.1, 1.5), "charge": 1},
                {**_descr_row("kaempferol+H+", 3.4, 1.7), "charge": 1},
                {**_descr_row("isorhamnetin+H+", 3.6, 1.8), "charge": 1}]
    mc = [{"name": "quercetin", "e_ads_kjmol": -16.0},
          {"name": "kaempferol", "e_ads_kjmol": -16.5},
          {"name": "isorhamnetin", "e_ads_kjmol": -16.7}]
    md = [{"name": "quercetin", "metal": "Fe", "metal_O_peak_A": 3.65},
          {"name": "kaempferol", "metal": "Fe", "metal_O_peak_A": 3.35},
          {"name": "isorhamnetin", "metal": "Fe", "metal_O_peak_A": 3.45}]
    fukui = {n: [{"idx": 0, "symbol": "O", "f_minus": 0.09, "f_plus": 0.05},
                 {"idx": 4, "symbol": "O", "f_minus": 0.07, "f_plus": 0.04},
                 {"idx": 9, "symbol": "C", "f_minus": 0.50, "f_plus": 0.30}]
             for n in ORDER}
    summary = analyse_speciation(
        neutral, acid, ph=0.0,
        rank_fn=lambda r: report.rank_inhibitors(
            pd.DataFrame(r)).to_dict("records"))
    computed = [{"name": n, "pkah": pk,
                 "f_protonated": protonation_fraction(0.0, pk)}
                for n, pk in [("quercetin", -12.1), ("kaempferol", -11.2),
                              ("isorhamnetin", -10.8)]]
    return dict(
        neutral_aq_rows=neutral, mc_rows=mc, md_rows=md, fukui_by_name=fukui,
        metal=METAL, medium=MEDIUM, order=ORDER,
        acid_cation_rows=acid, speciation_summary=summary,
        computed_pkah=computed, pka_freq_corrected=True,
        opt_neutral_rows=opt_neutral, opt_acid_rows=opt_acid,
    )


def _check_golden(name: str, produced: str) -> None:
    """Assert ``produced`` equals the committed golden, or refresh it."""
    golden = GOLDENS / name
    if os.environ.get("UPDATE_GOLDENS"):
        golden.parent.mkdir(exist_ok=True)
        golden.write_text(produced, encoding="utf-8")
        pytest.skip(f"golden {name} updated")
    assert produced == golden.read_text(encoding="utf-8"), (
        f"{name} drifted from the golden; if intentional, refresh with "
        "UPDATE_GOLDENS=1 pytest -q tests/test_report_golden.py")


_B64 = re.compile(r"data:image/[a-z]+;base64,[A-Za-z0-9+/=]+")


def _mask_images(html: str) -> str:
    """Replace embedded base64 image payloads with a placeholder.

    The report embeds its equations as matplotlib-rendered PNGs whose exact
    bytes depend on the platform font stack (freetype), so mask them — the
    golden then pins structure / text / ordering (what a renderer refactor
    changes) without wedging on machine-specific image bytes.
    """
    return _B64.sub("data:image/png;base64,MASKED", html)


def test_pipeline_html_matches_golden(tmp_path):
    out = tmp_path / "report.html"
    report.build_pipeline_report(
        **_full_inputs(), figdir=str(tmp_path / "nofig"),
        out_path=str(out), generated_at=FIXED_TS)
    _check_golden("pipeline_report.html",
                  _mask_images(out.read_text(encoding="utf-8")))


def _docx_text(path: str) -> str:
    """Document-order text of a .docx (paragraphs + table cells)."""
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    d = docx.Document(path)
    lines = []
    for child in d.element.body.iterchildren():
        if child.tag.endswith("}p"):
            lines.append(Paragraph(child, d).text)
        elif child.tag.endswith("}tbl"):
            for row in Table(child, d).rows:
                lines.append(" | ".join(c.text for c in row.cells))
    return "\n".join(lines)


def test_pipeline_docx_matches_golden(tmp_path):
    pytest.importorskip("docx")
    from corrosim.report import report_docx

    out = tmp_path / "report.docx"
    report_docx.build_docx_report(
        **_full_inputs(), figdir=str(tmp_path / "nofig"),
        out_path=str(out), generated_at=FIXED_TS)
    _check_golden("pipeline_report_docx.txt", _docx_text(str(out)))
