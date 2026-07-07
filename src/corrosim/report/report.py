"""corrosim.report.

Turn the per-molecule results into outputs: a tidy table, comparison plots, a
ranking, and a self-contained HTML report.
"""
from __future__ import annotations

import base64
import datetime
import io
import os
import re
from typing import NamedTuple

# Backend auto-selected: inline in Jupyter, Agg when headless
import matplotlib.pyplot as plt
import pandas as pd

from ..presets import metal_element
from ..qm.descriptors import DESCRIPTOR_META
from . import report_content as _content
from .report_layout import figure_path


def results_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Tidy descriptor table (ordered columns, rounded) from result rows.

    Args:
        rows: Dicts of ``{name, formula, level, **descriptor fields}``.

    Returns:
        A DataFrame with the known descriptor columns, rounded to 3 dp.
    """
    df = pd.DataFrame(rows)
    cols = ["name", "formula", "charge", "level", "homo_ev", "lumo_ev", "gap_ev",
            "hardness_ev", "softness_inv_ev", "electronegativity_ev",
            "electrophilicity_ev", "delta_n", "back_donation_ev", "tnc"]
    if "e_ads_kjmol" in df.columns:
        cols.append("e_ads_kjmol")
    cols = [c for c in cols if c in df.columns]
    return df[cols].round(3)


def rank_inhibitors(df: pd.DataFrame) -> pd.DataFrame:
    """Composite ranking from z-scored gap / hardness / softness.

    Stronger inhibition is associated with a smaller gap, lower hardness and
    higher softness; those are z-scored and combined.

    Args:
        df: A descriptor frame with gap_ev / hardness_ev / softness_inv_ev.

    Returns:
        ``df`` sorted best-first with a ``score`` column (higher = better).
    """
    ranked = df.copy()

    def zscore(series, invert=False):
        std = series.std(ddof=0)
        if std == 0:
            return series * 0
        z = (series - series.mean()) / std
        return -z if invert else z

    # Smaller gap + lower hardness + higher softness => stronger inhibition;
    # the mean of the equally-weighted components keeps score O(1) as they grow
    components = [
        zscore(ranked["gap_ev"], invert=True),
        zscore(ranked["hardness_ev"], invert=True),
        zscore(ranked["softness_inv_ev"]),
    ]
    ranked["score"] = (sum(components) / len(components)).round(3)
    return ranked.sort_values("score", ascending=False).reset_index(drop=True)


def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def plot_homo_lumo(df: pd.DataFrame) -> object:
    """Grouped bar chart of per-molecule HOMO/LUMO energies (eV).

    Args:
        df: A frame with name / homo_ev / lumo_ev columns.

    Returns:
        The matplotlib figure.
    """
    fig, ax = plt.subplots(figsize=(7, 4))
    x = range(len(df))
    ax.bar([i - 0.2 for i in x], df["homo_ev"], width=0.4, label="HOMO", color="#2b6cb0")
    ax.bar([i + 0.2 for i in x], df["lumo_ev"], width=0.4, label="LUMO", color="#dd6b20")
    ax.axhline(0, color="grey", lw=0.6)
    ax.set_xticks(list(x))
    ax.set_xticklabels(df["name"], rotation=20, ha="right")
    ax.set_ylabel("Energy (eV)")
    ax.set_title("Frontier orbital energies")
    ax.legend()
    return fig


def plot_descriptor_bars(df: pd.DataFrame) -> object:
    """Per-molecule bar panels for the key reactivity descriptors.

    Args:
        df: A frame with name + the reactivity-descriptor columns.

    Returns:
        The matplotlib figure.
    """
    keys = ["gap_ev", "hardness_ev", "softness_inv_ev", "electrophilicity_ev"]
    fig, axes = plt.subplots(1, len(keys), figsize=(4 * len(keys), 3.4))
    for ax, k in zip(axes, keys):
        ax.bar(df["name"], df[k], color="#319795")
        ax.set_title(DESCRIPTOR_META.get(k, (k, ""))[0], fontsize=10)
        ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    return fig


_HTML = """<!doctype html><html><head><meta charset="utf-8">
<title>Corrosion-inhibitor report</title>
<style>{style}</style></head><body>
<h1>Corrosion-inhibitor screening report</h1>
<p class="meta">Substrate: <b>{metal}</b> &nbsp;|&nbsp; Medium: <b>{medium}</b>
 &nbsp;|&nbsp; Engine: <b>{level}</b> &nbsp;|&nbsp; Generated {ts}</p>
<div class="note">{caveat}</div>
<h2>Ranking</h2>
{rank_table}
<p class="meta">Composite score combines a smaller energy gap, lower hardness,
and higher softness (each z-scored). Higher score = stronger predicted adsorption.</p>
<h2>Descriptor table</h2>
{full_table}
<h2>Frontier orbitals</h2><img src="data:image/png;base64,{img_hl}">
<h2>Key descriptors</h2><img src="data:image/png;base64,{img_desc}">
<h2>Method &amp; caveats</h2>
<p class="meta">{method}</p>
</body></html>"""


def build_html_report(df: pd.DataFrame, metal: str, medium: str, level: str,
                      out_path: str, generated_at: str | None = None) -> str:
    """Write a self-contained screening HTML report (ranking, table, plots).

    Args:
        df: The neutral descriptor frame.
        metal: Substrate label.
        medium: Corrosive medium label.
        level: The engine/level string shown in the header.
        out_path: Destination HTML path.
        generated_at: Timestamp override (a fixed string gives a
            reproducible, churn-free build).

    Returns:
        The output HTML path.
    """
    ranked = rank_inhibitors(df)
    html = _HTML.format(
        style=_REPORT_CSS,
        metal=metal, medium=medium, level=level,
        ts=generated_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        caveat=("These molecules are documented major constituents of the extract, "
                "simulated as representatives — not a verified profile of your specific "
                "sample. Confirm with LC-MS/GC-MS for a publication."),
        rank_table=_html_table(ranked[["name", "gap_ev", "hardness_ev",
                                       "softness_inv_ev", "delta_n", "score"]],
                               best_first_row=True),
        full_table=_html_table(df),
        img_hl=_fig_to_b64(plot_homo_lumo(df)),
        img_desc=_fig_to_b64(plot_descriptor_bars(df)),
        method=("Descriptors from frontier-orbital energies (Koopmans' theorem). "
                "Engine/level as noted above. ΔN uses the metal work function with "
                "η(metal)=0. Ranking is a screening heuristic, not a substitute for "
                "the Stage-2/3 adsorption MD or for electrochemical validation."),
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


# ---------------------------------------------------------------------------
# Full multiscale report (DFT descriptors + Fukui + Monte Carlo + MD)
# ---------------------------------------------------------------------------

def _img_b64_file(path: str | None) -> str | None:
    """Base64-encode an image file, or None if missing."""
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _img_block(figdir: str, fname: str, caption: str = "") -> str:
    """A <figure> embedding the figure inline (from its stage subfolder, see
    report_layout.figure_path), or a placeholder if absent.
    """
    b64 = _img_b64_file(figure_path(figdir, fname))
    if not b64:
        return f'<p class="meta">[figure not found: {fname}]</p>'
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return (f'<figure><img src="data:image/png;base64,{b64}">{cap}</figure>')


def _inline(text: str) -> str:
    """Render the shared content's ``**bold**`` markup to inline HTML."""
    return "".join(f"<b>{t}</b>" if b else t for t, b in _content.inline_runs(text))


def _number_headings(html: str) -> str:
    """Prefix section (h2) and subsection (h3) headings with hierarchical numbers
    (``1.``, ``1.1`` …) in document order. The ``h1`` title and deeper (``h4``)
    headings are left unnumbered. Mirrors report_docx's numbering so the HTML and
    Word reports carry the same section numbers.
    """
    counts = {"h2": 0, "h3": 0}

    def repl(match: re.Match) -> str:
        tag, inner = match.group(1), match.group(2)
        if tag == "h2":
            counts["h2"] += 1
            counts["h3"] = 0
            num = f"{counts['h2']}. "
        else:
            counts["h3"] += 1
            num = f"{counts['h2']}.{counts['h3']} "
        return f"<{tag}>{num}{inner}</{tag}>"

    return re.sub(r"<(h2|h3)>(.*?)</\1>", repl, html, flags=re.DOTALL)


def _grid(blocks: list[str]) -> str:
    return f'<div class="grid">{"".join(blocks)}</div>'


def _geometry_block(figdir: str) -> str:
    """Geometry-refinement subsection — only emitted when the FF-vs-DFT-opt
    comparison figure (fig8) is present, so a report built without the optimised
    matrix simply omits it.
    """
    if not os.path.exists(figure_path(figdir, "fig8_geometry_comparison.png")):
        return ""
    return ("<h3>Geometry refinement (FF vs DFT-optimised)</h3>"
            + _img_block(figdir, "fig8_geometry_comparison.png",
                         "Force-field vs DFT-optimised geometry"))


def _acid_cation_block(acid_cation_rows: list[dict] | None, medium: str) -> list[str]:
    """In-acid comparison section: the protonated-cation descriptors,
    shown alongside the neutral headline ranking rather than replacing it. Returns
    an empty list when there are no cation rows (non-acidic medium).
    """
    if not acid_cation_rows:
        return []
    return [
        "<h3>Species in the acidic medium (protonated cation)</h3>",
        _html_table(results_dataframe(acid_cation_rows)),
        f'<p class="meta">Protonated +1 cation descriptors in {medium}; the '
        "headline ranking stays on the neutral form (see docs/pipeline.md).</p>",
    ]


def _opt_descriptor_block(opt_neutral_rows: list[dict] | None,
                          opt_acid_rows: list[dict] | None,
                          order: list[str] | None = None) -> list[str]:
    """Optimised-geometry descriptor section: the DFT-relaxed
    (B3LYP/6-31G(d)) descriptor matrix — the neutral ranking plus the optimised
    protonated cations — surfaced alongside the FF-geometry headline table.
    Returns [] when no optimised matrix was supplied.
    """
    if not opt_neutral_rows:
        return []
    ndf = pd.DataFrame(opt_neutral_rows)
    if order:
        ndf = (ndf.set_index("name").loc[[n for n in order if n in set(ndf["name"])]]
               .reset_index())
    ranked = rank_inhibitors(ndf)
    summary = ranked[["name", "gap_ev", "hardness_ev", "softness_inv_ev",
                      "delta_n", "tnc", "score"]].round(3)
    out = [
        "<h3>Optimised-geometry descriptors (DFT-relaxed)</h3>",
        _html_table(summary, best_first_row=True),
    ]
    if opt_acid_rows:
        adf = pd.DataFrame(opt_acid_rows)
        if order:
            adf["_b"] = adf["name"].str.replace(r"\+H\+$", "", regex=True)
            adf["_o"] = adf["_b"].map({n: i for i, n in enumerate(order)})
            adf = adf.sort_values("_o").drop(columns=["_b", "_o"])
        out += [
            "<h4>Optimised protonated cations (in-acid)</h4>",
            _html_table(results_dataframe(adf.to_dict("records"))),
        ]
    return out


def _computed_pka_block(computed_pkah: list[dict] | None,
                        freq_corrected: bool = False) -> list[str]:
    """Computed-pKaH table: per-molecule DFT-cycle pKaH and the resulting
    protonated populations. ``computed_pkah`` rows carry name / pkah /
    f_protonated; ``freq_corrected`` flips the one-line basis caption between
    electronic-only and frequency-corrected. Empty if absent.
    """
    if not computed_pkah:
        return []
    head = "<tr><th>molecule</th><th>computed pKaH</th><th>% protonated @ this pH</th></tr>"
    body = "".join(
        f"<tr><td>{r['name']}</td><td>{r['pkah']:.1f}</td>"
        f"<td>{r['f_protonated'] * 100:.2f}%</td></tr>"
        for r in computed_pkah
    )
    basis = "frequency-corrected" if freq_corrected else "electronic-only"
    return [
        "<h4>Computed pKaH (DFT deprotonation cycle)</h4>",
        f"<table><thead>{head}</thead><tbody>{body}</tbody></table>",
        f'<p class="meta">B3LYP/6-311++G(d,p) + ddCOSMO deprotonation cycle '
        f"({basis}); results/pka.json.</p>",
    ]


def _speciation_block(summary: dict | None, medium: str,
                      computed_pkah: list[dict] | None = None,
                      pka_freq_corrected: bool = False) -> list[str]:
    """Quantitative pH-speciation section: the neutral/protonated population at
    the medium pH, the population-weighted descriptor table, and the computed
    pKaH table. Empty when no summary is supplied (non-acidic medium or unknown
    pH).
    """
    if not summary:
        return []
    spec = summary["speciation"]
    return [
        f"<h3>Speciation in {medium} (pH ≈ {spec.ph:.1f})</h3>",
        f'<p class="meta"><b>{spec.f_neutral:.0%} neutral / '
        f"{spec.f_protonated:.0%} protonated</b> at this pH — the "
        f"{spec.dominant} form dominates. Population-weighted descriptors "
        f"(blended lead <b>{summary['blended_lead']}</b>):</p>",
        _html_table(results_dataframe(summary["blended_rows"])),
        *_computed_pka_block(computed_pkah, pka_freq_corrected),
    ]


def top_donor_sites_of_element(fukui_rows: list[dict], element: str = "O",
                               n: int = 3) -> list[dict]:
    """Atoms of one element most susceptible to electrophilic attack (top f⁻).

    The electron-donating sites that coordinate the metal; defaults to oxygens.
    (Distinct from FukuiResult.top_donor_sites, which ranks all non-H atoms;
    this one filters by element.)

    Args:
        fukui_rows: Per-atom Fukui dicts (with symbol / f_minus).
        element: The element symbol to filter by.
        n: Number of top sites to return.

    Returns:
        The ``n`` rows of ``element`` with the largest ``f_minus``.
    """
    sel = [r for r in fukui_rows if r.get("symbol") == element]
    sel.sort(key=lambda r: r.get("f_minus", 0.0), reverse=True)
    return sel[:n]


def _html_table(d: pd.DataFrame, best_first_row: bool = False) -> str:
    rows = []
    for i, (_, r) in enumerate(d.iterrows()):
        cls = ' class="best"' if (best_first_row and i == 0) else ""
        cells = "".join(f"<td>{'' if pd.isna(r[c]) else r[c]}</td>" for c in d.columns)
        rows.append(f"<tr{cls}>{cells}</tr>")
    head = "".join(f"<th>{c}</th>" for c in d.columns)
    return (f"<table><thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>")


_REPORT_CSS = """
 body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
       max-width:1040px;margin:2rem auto;color:#1a202c;padding:0 1rem;line-height:1.5;}
 h1{font-size:1.6rem;margin-bottom:.2rem}
 h2{font-size:1.2rem;margin-top:2rem;border-bottom:2px solid #e2e8f0;padding-bottom:.3rem}
 h3{font-size:1rem;margin-top:1.2rem;color:#2d3748}
 table{border-collapse:collapse;width:100%;font-size:.88rem;margin:.6rem 0}
 th,td{border:1px solid #e2e8f0;padding:.38rem .55rem;text-align:right}
 th:first-child,td:first-child{text-align:left}
 thead{background:#f7fafc} tr:nth-child(even){background:#fbfdff}
 .best{background:#f0fff4!important;font-weight:600}
 .meta{color:#718096;font-size:.85rem}
 figure{margin:.6rem 0} img{max-width:100%;border:1px solid #edf2f7;border-radius:4px}
 figcaption{color:#718096;font-size:.82rem;margin-top:.25rem}
 .grid{display:flex;flex-wrap:wrap;gap:1rem}
 .grid figure{flex:1 1 300px;min-width:280px}
 .note{background:#fffaf0;border:1px solid #feebc8;padding:.6rem .9rem;border-radius:6px;font-size:.88rem}
 .stage{color:#2b6cb0;font-weight:600;font-size:.8rem;letter-spacing:.04em;text-transform:uppercase}
 ul{font-size:.9rem}
 h4{font-size:.95rem;margin:1rem 0 .3rem;color:#2d3748}
 .figexpl{background:#f7fafc;border-left:3px solid #cbd5e0;padding:.5rem .8rem;
          margin:.4rem 0 1rem;font-size:.9rem;color:#2d3748}
 .eqgrid{display:flex;flex-wrap:wrap;gap:1rem;align-items:flex-start}
 figure.eq{flex:1 1 300px;min-width:260px;background:#fbfdff;border:1px solid #edf2f7;
           border-radius:6px;padding:.6rem .8rem;text-align:center}
 figure.eq img{border:none;max-height:64px;width:auto}
 figure.eq figcaption{text-align:left;margin-top:.4rem}
"""


class PreparedReport(NamedTuple):
    """The report's derived data, shared by the HTML and Word renderers so both
    outputs draw on the same ranking / merged adsorption columns / Fukui summary.
    """

    # Ordered neutral rows + e_ads/ads_dist
    df: pd.DataFrame
    # Best-first with score
    ranked: pd.DataFrame
    # Headline summary columns
    summary: pd.DataFrame
    # Full descriptor table
    full: pd.DataFrame
    level: str
    # "Fe(110)" -> "Fe"
    m_elem: str
    # (molecule, "O5 (f⁻=0.090), ...")
    fukui_items: list[tuple[str, str]]

    def bottom_line(self) -> str | None:
        """Data-derived headline naming the top-ranked inhibitor, or None.

        Reads the lead straight off the ranking (never hardcoded), so the
        sentence stays correct if the molecule set or substrate changes. Both
        renderers wrap the returned prose in their own note box; the extraction
        lives here so it is not duplicated. See ``report_content.bottom_line``.

        Returns:
            The headline sentence (``**bold**`` markup), or None when there are
            no ranked rows.
        """
        if not len(self.ranked):
            return None
        lead = self.ranked.iloc[0]
        eads = lead.get("e_ads_kjmol")
        return _content.bottom_line(
            len(self.df),
            str(lead["name"]),
            float(lead["score"]),
            float(lead["gap_ev"]),
            float(eads) if eads is not None and pd.notna(eads) else None,
            self.m_elem,
        )

    @classmethod
    def derive(cls, neutral_aq_rows: list[dict], mc_rows: list[dict],
               md_rows: list[dict], fukui_by_name: dict[str, list[dict]],
               metal: str, order: list[str] | None) -> PreparedReport:
        """Build the shared report data once, for both renderers.

        Orders the neutral frame, merges the adsorption columns (Monte-Carlo
        E_ads + Brownian-MD metal-O first peak), ranks, and summarises the Fukui
        top donors. Construction lives on the type as a factory classmethod;
        ``prepare_report_data`` is the stable public wrapper.

        Args:
            neutral_aq_rows: Neutral aqueous descriptor rows.
            mc_rows: Monte Carlo adsorption summary rows.
            md_rows: Brownian-MD RDF summary rows.
            fukui_by_name: Per-molecule Fukui rows keyed by name.
            metal: Substrate label.
            order: Molecule display order, or None to keep the input order.

        Returns:
            The derived :class:`PreparedReport`.
        """
        df = pd.DataFrame(neutral_aq_rows).copy()
        if order:
            df = (df.set_index("name").loc[[n for n in order if n in set(df["name"])]]
                  .reset_index())
        m_elem = metal_element(str(metal))
        mc_by = {r["name"]: r for r in mc_rows}
        md_by = {r["name"]: r for r in md_rows}

        def _md_peak(n):
            # Generic key, legacy fallback
            row = md_by.get(n) or {}
            return row.get("metal_O_peak_A", row.get("FeO_peak_A"))

        df["e_ads_kjmol"] = df["name"].map(lambda n: (mc_by.get(n) or {}).get("e_ads_kjmol"))
        df["ads_dist_A"] = df["name"].map(_md_peak)
        # Coerce first: an all-missing column (no MD data) is object dtype and would
        # break Series.round on the None values — to_numeric makes it NaN-safe.
        df["ads_dist_A"] = pd.to_numeric(df["ads_dist_A"], errors="coerce").round(2)

        ranked = rank_inhibitors(df)
        level = str(df["level"].iloc[0]) if "level" in df.columns and len(df) else "—"
        summary = ranked[["name", "gap_ev", "hardness_ev", "softness_inv_ev",
                          "delta_n", "e_ads_kjmol", "ads_dist_A", "score"]].round(3)
        summary = summary.rename(columns={**_SUMMARY_LABELS,
                                          "ads_dist_A": f"{m_elem}–O (Å)"})
        full = results_dataframe(df.to_dict("records"))

        fukui_items = []
        for name in df["name"]:
            rows = fukui_by_name.get(name)
            if not rows:
                continue
            tops = top_donor_sites_of_element(rows, "O", 3)
            sites = ", ".join(f"O{t['idx']} (f⁻={t['f_minus']:.3f})" for t in tops)
            fukui_items.append((name, sites))
        return cls(df, ranked, summary, full, level, m_elem, fukui_items)


# Human-readable headers for the headline summary table (display only; the raw
# result keys stay on the full descriptor table). ads_dist_A is labelled with the
# actual metal in PreparedReport.derive.
_SUMMARY_LABELS = {
    "name": "Inhibitor",
    "gap_ev": "Gap (eV)",
    "hardness_ev": "Hardness η (eV)",
    "softness_inv_ev": "Softness σ (1/eV)",
    "delta_n": "ΔN",
    "e_ads_kjmol": "E_ads (kJ/mol)",
    "score": "Score",
}


def prepare_report_data(neutral_aq_rows: list[dict], mc_rows: list[dict],
                        md_rows: list[dict], fukui_by_name: dict[str, list[dict]],
                        metal: str, order: list[str] | None) -> PreparedReport:
    """Derive the shared report data once, for both renderers.

    The stable entry point the drivers import; delegates construction to the
    factory classmethod :meth:`PreparedReport.derive`.

    Args:
        neutral_aq_rows: Neutral aqueous descriptor rows.
        mc_rows: Monte Carlo adsorption summary rows.
        md_rows: Brownian-MD RDF summary rows.
        fukui_by_name: Per-molecule Fukui rows keyed by name.
        metal: Substrate label.
        order: Molecule display order, or None to keep the input order.

    Returns:
        The derived :class:`PreparedReport`.
    """
    return PreparedReport.derive(neutral_aq_rows, mc_rows, md_rows,
                                 fukui_by_name, metal, order)


# The HTML report is assembled section by section (each helper returns its HTML
# fragments), mirroring report_docx's _*_section builders so the two outlines
# stay diffable. build_pipeline_report joins them and numbers the headings.

def _header_section(metal: str, medium: str, prep: PreparedReport,
                    generated_at: str | None) -> list[str]:
    """Title, run-metadata line and the headline caveat.

    The data-derived headline sentence is placed in the Summary & ranking
    section (:func:`_summary_section`), not here.
    """
    ts = generated_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return [
        "<h1>corrosim — multiscale corrosion-inhibitor report</h1>",
        f'<p class="meta">Substrate <b>{metal}</b> &nbsp;|&nbsp; Medium <b>{medium}</b>'
        f' &nbsp;|&nbsp; DFT level <b>{prep.level}</b>'
        f" &nbsp;|&nbsp; Generated {ts}</p>",
        f'<div class="note">{_content.HEADLINE_CAVEAT}</div>',
    ]


def _overview_section(figdir: str) -> list[str]:
    """Overview heading + the pipeline diagram (methodology lives in pipeline.md)."""
    return [
        "<h2>Overview</h2>",
        _img_block(figdir, "fig0_pipeline.png", "corrosim pipeline"),
    ]


def _summary_section(prep: PreparedReport) -> list[str]:
    """Headline sentence + the ranking table + the one-line scoring note."""
    bl = prep.bottom_line()
    return [
        "<h2>Summary &amp; ranking</h2>",
        f"<p>{_inline(bl)}</p>" if bl else "",
        _html_table(prep.summary, best_first_row=True),
        f'<p class="meta">{_inline(_content.score_note(prep.m_elem))}</p>',
    ]


def _dft_section(prep: PreparedReport, figdir: str) -> list[str]:
    """DFT descriptors: structures, MO diagram, per-molecule HOMO/LUMO
    isosurfaces, descriptor charts, the full table and the optional
    geometry-refinement figure.
    """
    names = list(prep.df["name"])
    return [
        "<h2>DFT electronic descriptors</h2>",
        _grid([
            _img_block(figdir, "fig1_structures.png", "Modelled molecules"),
            _img_block(figdir, "fig2_mo_diagram.png",
                       "Frontier-orbital energies vs the metal work function"),
        ]),
        "<h3>Frontier-orbital isosurfaces (HOMO / LUMO)</h3>",
        _grid([_img_block(figdir, f"fig2b_{n}_homo.png", f"{n} HOMO")
               for n in names]),
        _grid([_img_block(figdir, f"fig2b_{n}_lumo.png", f"{n} LUMO")
               for n in names]),
        _grid([
            _img_block(figdir, "fig3_descriptors.png", "Reactivity descriptors"),
            _img_block(figdir, "fig3b_protonation.png",
                       "Protonation effect (DFT-optimised cations)"),
        ]),
        "<h3>Full descriptor table (neutral, aqueous)</h3>",
        _html_table(prep.full),
        _geometry_block(figdir),
    ]


def _fukui_section(prep: PreparedReport, figdir: str) -> list[str]:
    """Local-reactivity (Fukui) subsection: donor-site list + per-molecule maps.

    Fukui and the ESP map are facets of the isolated-molecule QM analysis, so
    they are h3 subsections here, not separate pipeline stages.
    """
    fukui_summary = (
        "<ul>" + "".join(f"<li><b>{n}</b>: {s}</li>" for n, s in prep.fukui_items)
        + "</ul>" if prep.fukui_items else '<p class="meta">No Fukui data found.</p>')
    return [
        "<h3>Local reactivity (Fukui)</h3>",
        '<p class="meta">Strongest electron-donating oxygens (highest f⁻) per '
        "molecule:</p>",
        fukui_summary,
        _grid([_img_block(figdir, f"fig4_{n}_fukui.png", f"{n} — condensed Fukui")
               for n in prep.df["name"]]),
    ]


def _esp_section(prep: PreparedReport, figdir: str) -> list[str]:
    """Electrostatic-potential (ESP) map subsection."""
    return [
        "<h3>Electrostatic-potential (ESP) map</h3>",
        _grid([_img_block(figdir, f"fig7_{n}_esp.png", f"{n} — ESP map")
               for n in prep.df["name"]]),
    ]


def _mc_section(prep: PreparedReport, figdir: str) -> list[str]:
    """Monte Carlo adsorption: per-molecule pose + annealing figures."""
    return [
        "<h2>Monte Carlo adsorption</h2>",
        _grid([_img_block(figdir, f"fig5_{n}_mc_pose.png", f"{n} — best pose")
               for n in prep.df["name"]]),
        _grid([_img_block(figdir, f"fig5_{n}_mc_energy.png", f"{n} — MC annealing")
               for n in prep.df["name"]]),
    ]


def _md_section(prep: PreparedReport, figdir: str) -> list[str]:
    """Brownian-MD metal-O RDF subsection."""
    return [
        f"<h2>Brownian MD — {prep.m_elem}–O RDF</h2>",
        _grid([_img_block(figdir, f"fig6_{n}_rdf.png", f"{n} — {prep.m_elem}–O RDF")
               for n in prep.df["name"]]),
    ]


def _method_section(level: str) -> list[str]:
    """Method & caveats footer."""
    return [
        "<h2>Method &amp; caveats</h2>",
        f'<p class="meta">DFT level: {level}. {_content.METHOD_CAVEAT}</p>',
    ]


def build_pipeline_report(neutral_aq_rows: list[dict], mc_rows: list[dict],
                          md_rows: list[dict], fukui_by_name: dict[str, list[dict]],
                          figdir: str, out_path: str,
                          metal: str = "Fe(110)", medium: str = "1 M HCl",
                          order: list[str] | None = None,
                          generated_at: str | None = None,
                          acid_cation_rows: list[dict] | None = None,
                          speciation_summary: dict | None = None,
                          computed_pkah: list[dict] | None = None,
                          pka_freq_corrected: bool = False,
                          opt_neutral_rows: list[dict] | None = None,
                          opt_acid_rows: list[dict] | None = None) -> str:
    """Assemble one self-contained HTML report for the whole pipeline.

    Tables are built from the committed result data; figures are embedded
    inline (base64) from ``figdir`` so the file stands alone. The headline
    ranking uses the neutral form; ``acid_cation_rows`` are surfaced as a
    labelled in-acid comparison when the medium is acidic.

    Args:
        neutral_aq_rows: Neutral aqueous descriptor rows.
        mc_rows: Monte Carlo adsorption summary rows.
        md_rows: Brownian-MD RDF summary rows.
        fukui_by_name: Per-molecule Fukui rows keyed by name.
        figdir: The figures root directory.
        out_path: Destination HTML path.
        metal: Substrate label.
        medium: Corrosive medium label.
        order: Molecule display order (defaults to the input order).
        generated_at: Timestamp override (a fixed string gives a
            reproducible, churn-free build).
        acid_cation_rows: Protonated-cation descriptor rows, if any.
        speciation_summary: The pH-speciation summary dict, if any.
        computed_pkah: Computed-pKaH rows, if any.
        pka_freq_corrected: Whether the pKaH is frequency-corrected.
        opt_neutral_rows: DFT-optimised neutral rows, if any.
        opt_acid_rows: DFT-optimised protonated-cation rows, if any.

    Returns:
        The output HTML path.
    """
    prep = prepare_report_data(neutral_aq_rows, mc_rows, md_rows, fukui_by_name,
                               metal, order)

    # Assemble the document shell + each section in order, then number the
    # headings once over the joined string. Section order mirrors the Word
    # builder (report_docx.build_docx_report) so the two outlines stay diffable.
    parts = [
        '<!doctype html><html><head><meta charset="utf-8">',
        "<title>corrosim — multiscale inhibitor report</title>",
        f"<style>{_REPORT_CSS}</style></head><body>",
        *_header_section(metal, medium, prep, generated_at),
        *_overview_section(figdir),
        *_summary_section(prep),
        *_dft_section(prep, figdir),
        *_opt_descriptor_block(opt_neutral_rows, opt_acid_rows, order),
        *_acid_cation_block(acid_cation_rows, medium),
        *_speciation_block(speciation_summary, medium, computed_pkah,
                           pka_freq_corrected),
        *_fukui_section(prep, figdir),
        *_esp_section(prep, figdir),
        *_mc_section(prep, figdir),
        *_md_section(prep, figdir),
        *_method_section(prep.level),
        "</body></html>",
    ]
    html = _number_headings("".join(parts))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
