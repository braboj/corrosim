"""End-to-end smoke tests for the venv-runnable pipeline drivers (issue #31).

These exercise the post-processing and pure-classical drivers — make_figures,
make_report, compare_geometry, run_mc, run_md — against the tracked ``results/``
fixtures, writing every output under ``tmp_path``. No QM engine or Docker is
needed: this is the scoped surface the ``--cov-fail-under`` gate measures, and
running the drivers also covers the figure/report library code they call.
"""
from __future__ import annotations

import pathlib

import matplotlib

matplotlib.use("Agg")  # headless: no display in CI

REPO = pathlib.Path(__file__).resolve().parent.parent
RESULTS = REPO / "results"
FIGURES = REPO / "report" / "figures"

# Small step counts keep the classical MC/MD fast; the goal is code coverage,
# not converged physics (that is validated separately by the tracked artifacts).
STEPS = ["--steps", "60"]


def test_make_figures_renders_pngs_from_results(tmp_path):
    from corrosim.runs import make_figures

    rc = make_figures.main([
        "--outdir", str(tmp_path),
        "--datadir", str(RESULTS),
        "--cubedir", str(tmp_path / "no_cubes"),  # absent -> cube figures skipped
        "--steps-mc", "60", "--steps-md", "60",
    ])
    assert rc == 0
    # figures are nested into per-stage subfolders (report_layout), so glob deep
    assert list(tmp_path.glob("**/*.png")), "expected manuscript figures to be written"
    assert (tmp_path / "dft").is_dir()          # Stage-1 figures land under dft/


def test_make_report_builds_self_contained_html(tmp_path):
    from corrosim.runs import make_report

    out = tmp_path / "report.html"
    docx = tmp_path / "report.docx"
    rc = make_report.main([
        "--descriptors", str(RESULTS / "dft_descriptors.csv"),
        "--opt-descriptors", str(RESULTS / "dft_descriptors_opt.csv"),
        "--mc", str(RESULTS / "mc_adsorption.json"),
        "--md", str(RESULTS / "md_rdf.json"),
        "--datadir", str(RESULTS),
        "--pka", str(RESULTS / "pka.json"),
        "--figdir", str(FIGURES),
        "--out", str(out),
        "--out-docx", str(docx),
        "--tablesdir", str(tmp_path / "tables"),
    ])
    assert rc == 0
    assert out.exists() and out.stat().st_size > 1000
    # Word report is written too (python-docx is a dev dependency)
    assert docx.exists() and docx.stat().st_size > 1000
    # tables are bundled into per-stage subfolders
    assert (tmp_path / "tables" / "dft" / "ranking.csv").exists()


def test_compare_geometry_writes_csv_and_figure(tmp_path):
    from corrosim.runs import compare_geometry

    csv = tmp_path / "geometry_comparison.csv"
    fig = tmp_path / "fig8.png"
    rc = compare_geometry.main([
        "--ff", str(RESULTS / "dft_descriptors.csv"),
        "--opt", str(RESULTS / "dft_descriptors_opt.csv"),
        "--out-csv", str(csv), "--out-fig", str(fig),
    ])
    assert rc == 0
    assert csv.exists() and fig.exists()


def test_run_mc_writes_summary_json(tmp_path):
    from corrosim.runs import run_mc

    rc = run_mc.main(["--molecules", "kaempferol", "--outdir", str(tmp_path)] + STEPS)
    assert rc == 0
    assert (tmp_path / "mc_adsorption.json").exists()


def test_run_md_writes_rdf_json(tmp_path):
    from corrosim.runs import run_md

    rc = run_md.main([
        "--molecules", "kaempferol", "--outdir", str(tmp_path),
        "--steps", "200", "--equil", "50",
    ])
    assert rc == 0
    assert (tmp_path / "md_rdf.json").exists()
