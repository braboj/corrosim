"""QM-light tests for the Pages gallery generator. No engine and no network:
the gallery is pure case metadata plus file copies."""
from __future__ import annotations

from corrosim.presets import CaseStudy
from corrosim.report.gallery import (
    assemble_site,
    build_index_html,
    unique_cases,
)


def test_unique_cases_collapses_aliases():
    names = [c.name for c in unique_cases()]
    # several aliases map to one study, so each name appears exactly once
    assert len(names) == len(set(names))
    assert "arghel" in names and "pyrazolylnucleosides" in names


def test_index_links_and_titles_every_case():
    cases = unique_cases()
    html = build_index_html(cases)
    for case in cases:
        assert f'href="{case.name}.html"' in html
    assert "Arghel flavonoids" in html and "Tetrazoles" in html


def test_index_carries_status_badges_from_the_scorecard():
    html = build_index_html(unique_cases())
    assert "badge--ok" in html and "Validated" in html        # arghel/phytic/tz
    assert "badge--partial" in html and "Partial" in html     # pyrazolo/tmp-smx


def test_index_accents_each_card_by_its_substrate_metal():
    html = build_index_html(unique_cases())
    # the Fe / Cu / Al cases each set their own metal accent variable
    assert "--accent:var(--fe)" in html
    assert "--accent:var(--cu)" in html
    assert "--accent:var(--al)" in html


def test_assemble_site_copies_reports_and_writes_the_index(tmp_path,
                                                           monkeypatch):
    monkeypatch.chdir(tmp_path)
    case = CaseStudy(name="galtest", molecules=("CCO",), metal="Cu(111)")
    report = tmp_path / "cases" / "galtest" / "report" / "report.html"
    report.parent.mkdir(parents=True)
    report.write_text("<html>the report</html>", encoding="utf-8")

    out = tmp_path / "_site"
    shipped = assemble_site(str(out), [case])
    assert shipped == ["galtest"]
    assert (out / "galtest.html").read_text(
        encoding="utf-8") == "<html>the report</html>"
    assert 'href="galtest.html"' in (out / "index.html").read_text(
        encoding="utf-8")


def test_assemble_site_skips_a_case_with_no_rendered_report(tmp_path,
                                                            monkeypatch):
    monkeypatch.chdir(tmp_path)
    case = CaseStudy(name="norep", molecules=("CCO",), metal="Fe(110)")
    out = tmp_path / "_site"
    shipped = assemble_site(str(out), [case])
    # no report on disk, so nothing is copied and the index never links it
    assert shipped == []
    assert not (out / "norep.html").exists()
    assert 'href="norep.html"' not in (out / "index.html").read_text(
        encoding="utf-8")
