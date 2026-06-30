import os

import matplotlib

matplotlib.use("Agg")  # build_html_report renders figures; keep the suite headless

import pandas as pd

from corrosim import report


def _descr_row(name, gap, hardness):
    return {
        "name": name, "formula": "C15H10O6", "charge": 0,
        "level": "B3LYP/6-311++G(d,p) (ddCOSMO:water)",
        "homo_ev": -6.0, "lumo_ev": -6.0 + gap, "gap_ev": gap,
        "hardness_ev": hardness, "softness_inv_ev": 1 / hardness,
        "electronegativity_ev": 4.0, "electrophilicity_ev": 4.0,
        "delta_n": 0.2, "back_donation_ev": -0.5, "tnc": -4.0,
    }


def test_top_donor_sites_of_element_picks_highest_f_minus():
    rows = [
        {"idx": 0, "symbol": "O", "f_minus": 0.02},
        {"idx": 5, "symbol": "O", "f_minus": 0.09},
        {"idx": 9, "symbol": "C", "f_minus": 0.50},   # carbon: ignored by default
        {"idx": 3, "symbol": "O", "f_minus": 0.07},
    ]
    tops = report.top_donor_sites_of_element(rows, "O", n=2)
    assert [t["idx"] for t in tops] == [5, 3]


def test_build_html_report_is_self_contained_and_nan_safe(tmp_path):
    # a missing adsorption estimate (NaN) must render as a blank cell, not "nan"
    df = pd.DataFrame([
        {**_descr_row("quercetin", 4.0, 2.0), "e_ads_kjmol": float("nan")},
        {**_descr_row("kaempferol", 4.4, 2.2), "e_ads_kjmol": -16.5},
    ])
    out = tmp_path / "screen.html"
    report.build_html_report(df, metal="Fe(110)", medium="1 M HCl",
                             level="B3LYP/6-311++G(d,p)", out_path=str(out),
                             generated_at="2026-01-01 00:00")

    html = out.read_text(encoding="utf-8")
    assert os.path.exists(out)
    assert "quercetin" in html and "kaempferol" in html
    assert ">nan<" not in html                       # NaN-safe table (was the style_table bug)
    assert 'class="best"' in html                    # ranking highlight present
    assert "2026-01-01 00:00" in html                # injectable timestamp honoured
    # self-contained: figures inlined as data URIs, no external references
    assert 'src="http' not in html and 'src="figures' not in html
    assert "data:image/png;base64," in html


def test_pipeline_report_is_self_contained(tmp_path):
    rows = [_descr_row("quercetin", 4.0, 2.0), _descr_row("kaempferol", 4.4, 2.2)]
    mc = [{"name": "quercetin", "e_ads_kjmol": -16.0},
          {"name": "kaempferol", "e_ads_kjmol": -16.5}]
    md = [{"name": "quercetin", "metal": "Fe", "metal_O_peak_A": 3.65},
          {"name": "kaempferol", "metal": "Fe", "metal_O_peak_A": 3.35}]
    fukui = {"quercetin": [{"idx": 0, "symbol": "O", "f_minus": 0.09, "f_plus": 0.1}]}

    out = tmp_path / "report.html"
    # figdir intentionally absent -> figures degrade gracefully, file still stands alone
    report.build_pipeline_report(rows, mc, md, fukui, figdir=str(tmp_path / "nope"),
                                 out_path=str(out), order=["quercetin", "kaempferol"])

    html = out.read_text(encoding="utf-8")
    assert os.path.exists(out)
    # quercetin (smaller gap+hardness) ranks first and is highlighted
    assert 'class="best"><td>quercetin' in html
    # adsorption data merged in from MC/MD
    assert "-16.0" in html and "3.65" in html
    # no external resource references — the file is shareable on its own
    assert 'src="http' not in html and 'src="figures' not in html


def test_pipeline_report_reads_legacy_md_key(tmp_path):
    # an old md_rdf.json with the pre-agnostic FeO_peak_A key must still render
    rows = [_descr_row("quercetin", 4.0, 2.0)]
    md = [{"name": "quercetin", "FeO_peak_A": 3.71}]
    out = tmp_path / "report.html"
    report.build_pipeline_report(rows, [], md, {}, figdir=str(tmp_path / "nope"),
                                 out_path=str(out), order=["quercetin"])
    assert "3.71" in out.read_text(encoding="utf-8")


def test_pipeline_report_surfaces_acid_cation_section(tmp_path):
    # given protonated-cation rows (acidic medium), a labelled in-acid comparison
    # appears — but the neutral lead is unchanged (ADR 0003).
    rows = [_descr_row("quercetin", 4.0, 2.0)]
    acid = [{**_descr_row("quercetin+H+", 3.3, 1.6), "delta_n": -0.05}]
    out = tmp_path / "report.html"
    report.build_pipeline_report(rows, [], [], {}, figdir=str(tmp_path / "nope"),
                                 out_path=str(out), medium="1 M HCl",
                                 order=["quercetin"], acid_cation_rows=acid)
    html = out.read_text(encoding="utf-8")
    assert "Species in the acidic medium" in html
    assert "quercetin+H+" in html
    assert 'class="best"><td>quercetin<' in html        # neutral lead still headline

    # no cation rows (non-acidic medium) -> no in-acid section
    out2 = tmp_path / "report2.html"
    report.build_pipeline_report(rows, [], [], {}, figdir=str(tmp_path / "nope"),
                                 out_path=str(out2), medium="pH 7 buffer",
                                 order=["quercetin"], acid_cation_rows=None)
    assert "Species in the acidic medium" not in out2.read_text(encoding="utf-8")


def test_pipeline_report_renders_speciation_section(tmp_path):
    from corrosim.speciation import analyse_speciation
    neutral = [_descr_row("quercetin", 4.0, 2.0), _descr_row("kaempferol", 4.4, 2.2)]
    protonated = [{**_descr_row("quercetin+H+", 3.3, 1.6), "delta_n": -0.05},
                  {**_descr_row("kaempferol+H+", 3.6, 1.8), "delta_n": -0.07}]
    summary = analyse_speciation(
        neutral, protonated, ph=0.0,
        rank_fn=lambda r: report.rank_inhibitors(pd.DataFrame(r)).to_dict("records"))
    out = tmp_path / "report.html"
    report.build_pipeline_report(neutral, [], [], {}, figdir=str(tmp_path / "nope"),
                                 out_path=str(out), medium="1 M HCl",
                                 order=["quercetin", "kaempferol"],
                                 speciation_summary=summary)
    html = out.read_text(encoding="utf-8")
    assert "Speciation in 1 M HCl" in html
    assert "Henderson" in html and "pH-weighted" in html
