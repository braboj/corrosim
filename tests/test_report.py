import os

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


def test_top_donor_sites_picks_highest_f_minus():
    rows = [
        {"idx": 0, "symbol": "O", "f_minus": 0.02},
        {"idx": 5, "symbol": "O", "f_minus": 0.09},
        {"idx": 9, "symbol": "C", "f_minus": 0.50},   # carbon: ignored by default
        {"idx": 3, "symbol": "O", "f_minus": 0.07},
    ]
    tops = report.top_donor_sites(rows, "O", n=2)
    assert [t["idx"] for t in tops] == [5, 3]


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
