"""The shared Scientific-basis walker (report.render) and PreparedReport.bottom_line.

Covers the seam that keeps the HTML and Word reports in lock-step: one
``render_blocks`` dispatcher over ``report_content.SCIENTIFIC_BASIS`` with an
exhaustive kind-set (an unknown block *raises* instead of being silently
dropped), and the shared lead-extraction now on ``PreparedReport``.
"""
import pandas as pd
import pytest

from corrosim import report
from corrosim.report import report_content
from corrosim.report.render import render_blocks


class _Recorder:
    """A BasisRenderer that records the (method, payload) calls it receives."""

    def __init__(self):
        self.calls = []

    def subheading(self, text):
        self.calls.append(("subheading", text))

    def paragraph(self, text):
        self.calls.append(("paragraph", text))

    def table(self, payload):
        self.calls.append(("table", payload))

    def equation_groups(self):
        self.calls.append(("equation_groups", None))


def test_render_blocks_dispatches_each_kind_to_its_method():
    blocks = [
        ("h3", "A heading"),
        ("p", "A paragraph"),
        ("table", {"columns": ["x"], "rows": [["1"]]}),
        ("eqgroups", None),
    ]
    rec = _Recorder()
    render_blocks(blocks, rec)
    assert rec.calls == [
        ("subheading", "A heading"),
        ("paragraph", "A paragraph"),
        ("table", {"columns": ["x"], "rows": [["1"]]}),
        ("equation_groups", None),
    ]


def test_render_blocks_raises_on_unknown_kind():
    # the whole point of the walker: an unhandled kind is loud, not dropped
    with pytest.raises(ValueError, match="unknown scientific-basis block"):
        render_blocks([("h4", "not a real kind")], _Recorder())


def test_render_blocks_raises_on_wrong_payload_type():
    # right kind, wrong payload type (h3 wants str) is also caught
    with pytest.raises(ValueError, match="unknown scientific-basis block"):
        render_blocks([("h3", {"not": "a string"})], _Recorder())


def test_scientific_basis_content_walks_without_error():
    # the real content list must be fully handled by the exhaustive walker
    render_blocks(report_content.SCIENTIFIC_BASIS, _Recorder())


def _descr_row(name, gap, hardness):
    return {
        "name": name, "formula": "C15H10O7", "charge": 0,
        "level": "B3LYP/6-311++G(d,p) (ddCOSMO:water)",
        "homo_ev": -6.0, "lumo_ev": -6.0 + gap, "gap_ev": gap,
        "hardness_ev": hardness, "softness_inv_ev": 1 / hardness,
        "electronegativity_ev": 4.0, "electrophilicity_ev": 4.0,
        "delta_n": 0.2, "back_donation_ev": -0.5, "tnc": -4.0,
    }


def test_bottom_line_names_the_ranked_lead():
    prep = report.prepare_report_data(
        neutral_aq_rows=[_descr_row("quercetin", 4.0, 2.0),
                         _descr_row("kaempferol", 4.4, 2.2)],
        mc_rows=[{"name": "quercetin", "e_ads_kjmol": -16.0}],
        md_rows=[], fukui_by_name={}, metal="Fe(110)", order=None)
    line = prep.bottom_line()
    assert line is not None
    assert "**quercetin**" in line and "Bottom line" in line


def test_bottom_line_is_none_when_no_rows():
    empty = report.PreparedReport(
        df=pd.DataFrame(), ranked=pd.DataFrame(), summary=pd.DataFrame(),
        full=pd.DataFrame(), level="—", m_elem="Fe", fukui_items=[])
    assert empty.bottom_line() is None
