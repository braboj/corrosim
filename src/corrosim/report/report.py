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
from html import escape
from typing import Any, NamedTuple

# Backend auto-selected: inline in Jupyter, Agg when headless
import matplotlib.pyplot as plt
import pandas as pd

from ..molecules import display_name
from ..presets import metal_element
from ..qm.descriptors import DESCRIPTOR_META
from . import report_content as _content
from .ranking import RankingEnsemble, build_ensemble, rank_inhibitors
from .report_layout import figure_path

__all__ = [
    "rank_inhibitors",
    "build_ensemble",
    "RankingEnsemble",
    "results_dataframe",
    "prepare_report_data",
    "PreparedReport",
    "build_pipeline_report",
    "build_html_report",
    "descriptor_matrix",
    "ranking_matrix",
]


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
            "electrophilicity_ev", "delta_n", "back_donation_ev", "dipole_debye",
            "tnc"]
    if "e_ads_kjmol" in df.columns:
        cols.append("e_ads_kjmol")
    cols = [c for c in cols if c in df.columns]
    return df[cols].round(3)


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
        metal=escape(metal), medium=escape(medium), level=escape(level),
        ts=generated_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        caveat=("These molecules are documented major constituents of the extract, "
                "simulated as representatives — not a verified profile of your specific "
                "sample. Confirm with LC-MS/GC-MS for a publication."),
        rank_table=_ranking_table_html(
            ranked[["name", "gap_ev", "hardness_ev", "softness_inv_ev",
                    "delta_n", "score"]],
            "name", DESCRIPTOR_ROW_LABELS),
        full_table=_descriptor_table_html(
            results_dataframe(df.to_dict("records"))),
        img_hl=_fig_to_b64(plot_homo_lumo(df)),
        img_desc=_fig_to_b64(plot_descriptor_bars(df)),
        method=("Descriptors from frontier-orbital energies (Koopmans' theorem). "
                "Engine/level as noted above. ΔN uses the metal work function with "
                "η(metal)=0. Ranking is a screening heuristic, not a substitute for "
                "the Monte Carlo / MD adsorption modelling or for electrochemical "
                "validation."),
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
    cap = f"<figcaption>{escape(caption)}</figcaption>" if caption else ""
    return (f'<figure><img src="data:image/png;base64,{b64}">{cap}</figure>')


def _inline(text: str) -> str:
    """Render the shared content's ``**bold**`` markup to inline HTML.

    The shared prose is HTML-agnostic and weaves in free text (molecule names,
    the metal), so escape each run here — this is the HTML boundary for that
    prose, the way the Word renderer's ``add_run`` is its own escaping boundary.
    """
    return "".join(f"<b>{escape(t)}</b>" if b else escape(t)
                   for t, b in _content.inline_runs(text))


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
        _descriptor_table_html(results_dataframe(acid_cation_rows)),
        f'<p class="meta">Protonated +1 cation descriptors in {escape(medium)}; a '
        "component of the pH-weighted canonical basis (see the Summary), shown "
        "here on its own.</p>",
    ]


def _opt_descriptor_block(opt_neutral_rows: list[dict] | None,
                          opt_acid_rows: list[dict] | None,
                          order: list[str] | None = None) -> list[str]:
    """DFT-relaxed-geometry sensitivity panel: the optimised descriptor matrix
    (neutral + protonated cations) shown as the geometry axis of the ranking's
    sensitivity ensemble, not a competing ranking — so no score row or winner
    marks. The headline scores this basis (when present) on the canonical table
    above. Returns [] when no optimised matrix was supplied.
    """
    if not opt_neutral_rows:
        return []
    ndf = pd.DataFrame(opt_neutral_rows)
    if order:
        ndf = (ndf.set_index("name").loc[[n for n in order if n in set(ndf["name"])]]
               .reset_index())
    out = [
        "<h3>Optimised-geometry descriptors (DFT-relaxed)</h3>",
        _descriptor_table_html(results_dataframe(ndf.to_dict("records"))),
        '<p class="meta">Sensitivity: descriptors on the DFT-relaxed geometry '
        "(the geometry axis of the ranking ensemble). The headline ranks on the "
        "canonical basis; see the Summary.</p>",
    ]
    if opt_acid_rows:
        adf = pd.DataFrame(opt_acid_rows)
        if order:
            adf["_b"] = adf["name"].str.replace(r"\+H\+$", "", regex=True)
            adf["_o"] = adf["_b"].map({n: i for i, n in enumerate(order)})
            adf = adf.sort_values("_o").drop(columns=["_b", "_o"])
        out += [
            "<h4>Optimised protonated cations (in-acid)</h4>",
            _descriptor_table_html(results_dataframe(adf.to_dict("records"))),
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
    head = "<th></th>" + "".join(
        f"<th>{escape(display_name(r['name']))}</th>" for r in computed_pkah)
    row_pkah = "<th>computed pKaH</th>" + "".join(
        f"<td>{r['pkah']:.1f}</td>" for r in computed_pkah)
    row_prot = "<th>% protonated @ this pH</th>" + "".join(
        f"<td>{r['f_protonated'] * 100:.2f}%</td>" for r in computed_pkah)
    basis = "frequency-corrected" if freq_corrected else "electronic-only"
    return [
        "<h4>Computed pKaH (DFT deprotonation cycle)</h4>",
        f'<div class="tw"><table><thead><tr>{head}</tr></thead>'
        f"<tbody><tr>{row_pkah}</tr><tr>{row_prot}</tr></tbody></table></div>",
        f'<p class="meta">B3LYP/6-311++G(d,p) + ddCOSMO deprotonation cycle '
        f"({basis}).</p>",
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
        f"<h3>Speciation in {escape(medium)} (pH ≈ {spec.ph:.1f})</h3>",
        f'<p class="meta"><b>{spec.f_neutral:.0%} neutral / '
        f"{spec.f_protonated:.0%} protonated</b> at this pH — the "
        f"{spec.dominant} form dominates. Population-weighted descriptors "
        "(the speciation axis of the ranking ensemble; the headline ranks on "
        "the canonical basis):</p>",
        _descriptor_table_html(results_dataframe(summary["blended_rows"])),
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


# Every descriptor/ranking table is shown transposed: molecules as columns, each
# quantity a labelled row. With one to a few molecules and many quantities that
# keeps the table inside the page width and lets each row name carry its unit.
# The constant-per-table charge/level fields are dropped from descriptor tables —
# they are stated in the section context, not repeated down every column.
DESCRIPTOR_ROW_LABELS = {
    "formula": "Formula",
    "homo_ev": "HOMO (eV)",
    "lumo_ev": "LUMO (eV)",
    "gap_ev": "Gap ΔE (eV)",
    "hardness_ev": "η hardness (eV)",
    "softness_inv_ev": "σ softness (1/eV)",
    "electronegativity_ev": "χ electronegativity (eV)",
    "electrophilicity_ev": "ω electrophilicity (eV)",
    "delta_n": "ΔN",
    "back_donation_ev": "E_back-donation (eV)",
    "dipole_debye": "Dipole (D)",
    "tnc": "TNC",
    "e_ads_kjmol": "E_ads (kJ/mol)",
    "score": "Score",
}

_DESCRIPTOR_DROP = ("charge", "level")


def _matrix(
    df: pd.DataFrame,
    name_col: str,
    label_map: dict[str, str] | None,
    drop: tuple[str, ...],
    corner: str,
) -> tuple[list[str], list[list[str]]]:
    """Transpose a frame to molecule-columns / quantity-rows form.

    Args:
        df: The source frame.
        name_col: Column whose values become the (molecule) column headers.
        label_map: Optional raw-key -> display-label map for the row names.
        drop: Columns to skip (e.g. constant charge/level).
        corner: The top-left corner cell label.

    Returns:
        ``(headers, rows)`` with ``headers = [corner, *names]`` and one
        ``[label, *cell strings]`` per remaining column; NaN renders as "".
    """
    names = [display_name(str(n)) for n in df[name_col]]
    headers = [corner, *names]
    rows = []
    for col in df.columns:
        if col == name_col or col in drop:
            continue
        label = (label_map or {}).get(col, col)
        cells = ["" if pd.isna(v) else str(v) for v in df[col]]
        rows.append([label, *cells])
    return headers, rows


def descriptor_matrix(df: pd.DataFrame) -> tuple[list[str], list[list[str]]]:
    """Transpose a descriptor frame to molecule-columns / descriptor-rows form.

    Shared by the HTML and Word renderers so both show the identical shape:
    each molecule a column, each descriptor a labelled row (unit in the label),
    with the constant charge/level fields dropped.

    Args:
        df: A :func:`results_dataframe`-shaped frame with a ``name`` column.

    Returns:
        ``(headers, rows)``; see :func:`_matrix`.
    """
    return _matrix(df, "name", DESCRIPTOR_ROW_LABELS, _DESCRIPTOR_DROP,
                   "Descriptor")


# Which direction is "better" for a ranking metric: 'min' (smaller wins) or
# 'max' (larger wins). Metrics absent here (ΔN, the metal-O distance, TNC) have
# no single defensible best, so their row is left unmarked. Keyed by both the
# raw descriptor key (optimised-geometry frame) and the display label (headline
# summary frame), whichever names the column.
_RANKING_BETTER = {
    "gap_ev": "min",
    "hardness_ev": "min",
    "softness_inv_ev": "max",
    "e_ads_kjmol": "min",
    "score": "max",
    "Gap (eV)": "min",
    "Hardness η (eV)": "min",
    "Softness σ (1/eV)": "max",
    "E_ads (kJ/mol)": "min",
    "Score": "max",
}


def _row_winner(series: pd.Series, col: str) -> int | None:
    """0-based index of the winning molecule in a ranking-metric column.

    'Winning' is the smallest value for a min-metric and the largest for a
    max-metric; a metric with no defined direction (absent from
    ``_RANKING_BETTER``) returns None so its row carries no checkmark.

    Args:
        series: The metric's per-molecule values, in column order.
        col: The frame column name (raw key or display label).

    Returns:
        The winning molecule's 0-based index, or None.
    """
    direction = _RANKING_BETTER.get(col)
    if direction is None:
        return None
    vals = pd.to_numeric(series, errors="coerce").reset_index(drop=True)
    if vals.isna().all():
        return None
    return int(vals.idxmin() if direction == "min" else vals.idxmax())


def ranking_matrix(
    df: pd.DataFrame,
    name_col: str,
    label_map: dict[str, str] | None = None,
) -> tuple[list[str], list[list[str]], list[int | None]]:
    """Transpose a best-first ranking frame to molecule-columns / metric-rows.

    Molecules keep their (best-first) order, so the winning column comes first.
    Pass ``label_map`` to prettify raw metric keys; pass None when the columns
    are already display labels.

    Args:
        df: A ranking frame sorted best-first, with ``name_col`` plus metrics.
        name_col: Column whose values become the column headers.
        label_map: Optional raw-key -> display-label map for the metric rows.

    Returns:
        ``(headers, rows, winners)``: ``headers`` and ``rows`` as in
        :func:`_matrix`; ``winners[i]`` is the 0-based molecule-column index
        that wins metric row ``i``, or None when the metric has no defined
        better direction.
    """
    names = [display_name(str(n)) for n in df[name_col]]
    headers = ["", *names]
    rows: list[list[str]] = []
    winners: list[int | None] = []
    for col in df.columns:
        if col == name_col:
            continue
        label = (label_map or {}).get(col, col)
        rows.append([label, *["" if pd.isna(v) else str(v) for v in df[col]]])
        winners.append(_row_winner(df[col], col))
    return headers, rows, winners


def _transposed_table_html(
    headers: list[str],
    rows: list[list[str]],
    highlight_col: int | None = None,
    winners: list[int | None] | None = None,
) -> str:
    """Render a transposed ``(headers, rows)`` matrix as HTML.

    ``headers[0]`` is the corner label and ``headers[1:]`` the molecule names;
    each row is ``[label, *values]``. When ``highlight_col`` is given (a 0-based
    index into the molecule columns), that column's header and cells carry the
    ``best`` class. When ``winners`` is given, ``winners[i]`` marks the winning
    cell of row ``i`` with a checkmark.
    """

    def cls(entity_idx: int) -> str:
        return (' class="best"'
                if highlight_col is not None and entity_idx == highlight_col
                else "")

    # Escape the free-text cells (molecule-name headers, formula and value
    # strings) here at the HTML boundary; the ``cls``/``mark`` spans are trusted
    # markup added outside the escaped text. The shared descriptor_matrix /
    # ranking_matrix builders stay un-escaped so the Word renderer, which
    # escapes via python-docx, does not double-escape.
    head = f"<th>{escape(headers[0])}</th>" + "".join(
        f"<th{cls(j)}>{escape(h)}</th>" for j, h in enumerate(headers[1:]))
    body_rows = []
    for i, r in enumerate(rows):
        win = winners[i] if winners is not None else None
        cells = "<th>" + escape(r[0]) + "</th>"
        for j, v in enumerate(r[1:]):
            mark = ' <span class="win">✓</span>' if j == win else ""
            cells += f"<td{cls(j)}>{escape(str(v))}{mark}</td>"
        body_rows.append(f"<tr>{cells}</tr>")
    return (f'<div class="tw"><table><thead><tr>{head}</tr></thead>'
            f"<tbody>{''.join(body_rows)}</tbody></table></div>")


def _descriptor_table_html(df: pd.DataFrame) -> str:
    """Render a descriptor frame as a transposed HTML table (no highlight)."""
    headers, rows = descriptor_matrix(df)
    return _transposed_table_html(headers, rows)


def _ranking_table_html(
    df: pd.DataFrame,
    name_col: str,
    label_map: dict[str, str] | None = None,
    mark_winners: bool = True,
) -> str:
    """Render a best-first ranking frame transposed.

    With ``mark_winners`` the winning column is highlighted and the best value
    in each directional metric row is checkmarked. When the lead is a tie within
    method resolution, pass ``mark_winners=False`` to render a plain table — no
    highlight, no checkmarks — so no molecule is visually crowned.
    """
    headers, rows, winners = ranking_matrix(df, name_col, label_map)
    if not mark_winners:
        return _transposed_table_html(headers, rows)
    return _transposed_table_html(headers, rows, highlight_col=0, winners=winners)


_REPORT_CSS = """
 html{background:#f4f5f7;}
 body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
       max-width:920px;margin:2.5rem auto;color:#1a202c;line-height:1.5;
       background:#fff;border:1px solid #e5e7ea;border-radius:10px;
       padding:clamp(1.6rem,5vw,3.5rem);
       box-shadow:0 1px 3px rgba(9,30,66,.12),0 0 1px rgba(9,30,66,.2);}
 body>*:first-child{margin-top:0}
 @media (max-width:640px){body{margin:0;border:0;border-radius:0}}
 h1{font-size:1.6rem;margin-bottom:.2rem}
 h2{font-size:1.2rem;margin-top:2rem;border-bottom:2px solid #e2e8f0;padding-bottom:.3rem}
 h3{font-size:1rem;margin-top:1.2rem;color:#2d3748}
 .tw{overflow-x:auto;max-width:100%;margin:.6rem 0}
 table{border-collapse:collapse;width:100%;font-size:.88rem;margin:.6rem 0}
 th,td{border:1px solid #e2e8f0;padding:.38rem .55rem;text-align:right}
 th:first-child,td:first-child{text-align:left}
 thead{background:#f7fafc} tr:nth-child(even){background:#fbfdff}
 .best{background:#f0fff4!important;font-weight:600}
 .win{color:#2f855a;font-weight:700;margin-left:.2rem}
 .meta{color:#718096;font-size:.85rem}
 figure{margin:.6rem 0} img{max-width:100%;border:1px solid #edf2f7;border-radius:4px}
 figcaption{color:#718096;font-size:.82rem;margin-top:.25rem}
 .grid{display:flex;flex-direction:column;gap:1rem;align-items:flex-start}
 .grid figure{width:600px;max-width:100%}
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
    outputs draw on the same adsorption columns and Fukui summary.

    The headline ranking is not carried here: it is computed per canonical basis
    by :func:`report_ensemble` (the neutral force-field rows are only one of the
    bases), and the adsorption columns on ``df`` are grafted onto whichever basis
    wins by :func:`canonical_summary`.
    """

    # Ordered neutral rows + e_ads/ads_dist
    df: pd.DataFrame
    # Full descriptor table
    full: pd.DataFrame
    level: str
    # "Fe(110)" -> "Fe"
    m_elem: str
    # (molecule, "O5 (f⁻=0.090), ...")
    fukui_items: list[tuple[str, str]]

    @classmethod
    def derive(cls, neutral_aq_rows: list[dict], mc_rows: list[dict],
               md_rows: list[dict], fukui_by_name: dict[str, list[dict]],
               metal: str, order: list[str] | None) -> PreparedReport:
        """Build the shared report data once, for both renderers.

        Orders the neutral frame, merges the adsorption columns (Monte-Carlo
        E_ads + Brownian-MD metal-O first peak), and summarises the Fukui top
        donors. Construction lives on the type as a factory classmethod;
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
            # The metal-O RDF first peak: the current metal-agnostic key, then
            # the pre-rename per-metal legacy key (FeO_peak_A / CuO_peak_A / …)
            # derived from this case's element rather than hardcoded to iron.
            row = md_by.get(n) or {}
            return row.get("metal_O_peak_A", row.get(f"{m_elem}O_peak_A"))

        df["e_ads_kjmol"] = df["name"].map(lambda n: (mc_by.get(n) or {}).get("e_ads_kjmol"))
        df["ads_dist_A"] = df["name"].map(_md_peak)
        # Coerce first: an all-missing column (no MD data) is object dtype and would
        # break Series.round on the None values — to_numeric makes it NaN-safe.
        df["ads_dist_A"] = pd.to_numeric(df["ads_dist_A"], errors="coerce").round(2)

        level = str(df["level"].iloc[0]) if "level" in df.columns and len(df) else "—"
        full = results_dataframe(df.to_dict("records"))

        fukui_items = []
        for name in df["name"]:
            rows = fukui_by_name.get(name)
            if not rows:
                continue
            tops = top_donor_sites_of_element(rows, "O", 3)
            sites = ", ".join(
                f"{t.get('symbol', 'O')}{t['idx']} "
                f"(f⁻={t.get('f_minus', 0.0):.3f})"
                for t in tops)
            fukui_items.append((display_name(name), sites))
        return cls(df, full, level, m_elem, fukui_items)


# Human-readable headers for the headline summary table (display only; the raw
# result keys stay on the full descriptor table). ads_dist_A is labelled with the
# actual metal in canonical_summary.
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


def report_ensemble(
    neutral_aq_rows: list[dict],
    acid_cation_rows: list[dict] | None,
    opt_neutral_rows: list[dict] | None,
    opt_acid_rows: list[dict] | None,
    speciation_summary: dict | None,
) -> RankingEnsemble:
    """Build the ranking ensemble both renderers score the headline against.

    Selects the canonical basis and judges the lead's robustness from the rows
    already threaded to the report; the protonated-population weight is read off
    the speciation summary (it depends only on pH and pKaH, so it applies to the
    force-field and DFT-relaxed blends alike).

    Args:
        neutral_aq_rows: Force-field neutral aqueous descriptor rows.
        acid_cation_rows: Force-field protonated-cation rows, or None.
        opt_neutral_rows: DFT-relaxed neutral rows, or None.
        opt_acid_rows: DFT-relaxed protonated-cation rows, or None.
        speciation_summary: The pH-speciation summary (source of the population
            weight), or None when the medium is non-ionising.

    Returns:
        The :class:`RankingEnsemble` for the headline + sensitivity panel.
    """
    f_protonated = (speciation_summary["speciation"].f_protonated
                    if speciation_summary else None)
    return build_ensemble(neutral_aq_rows, acid_cation_rows, opt_neutral_rows,
                          opt_acid_rows, f_protonated)


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
        f'<p class="meta">Substrate <b>{escape(metal)}</b> &nbsp;|&nbsp; '
        f"Medium <b>{escape(medium)}</b>"
        f' &nbsp;|&nbsp; DFT level <b>{escape(prep.level)}</b>'
        f" &nbsp;|&nbsp; Generated {ts}</p>",
        f'<div class="note">{_content.HEADLINE_CAVEAT}</div>',
    ]


def _overview_section(figdir: str) -> list[str]:
    """Overview heading + the pipeline diagram (methodology lives in pipeline.md)."""
    return [
        "<h2>Overview</h2>",
        _img_block(figdir, "fig0_pipeline.png", "corrosim pipeline"),
    ]


def _eads_by_name(prep: PreparedReport) -> dict[str, Any]:
    """Map molecule name -> adsorption energy (kJ/mol), for the summary merge."""
    return dict(zip(prep.df["name"], prep.df["e_ads_kjmol"]))


def canonical_summary(prep: PreparedReport,
                      ensemble: RankingEnsemble) -> pd.DataFrame:
    """Headline summary frame for the canonical basis.

    Ranks on the canonical basis (best geometry x pH-weighted speciation) and
    grafts the per-molecule adsorption columns (Monte-Carlo E_ads + Brownian-MD
    metal-O distance, keyed by name) onto it — those validate the lead but do
    not enter the score, so they attach to whichever basis is canonical.

    Args:
        prep: The shared report data (source of the adsorption columns).
        ensemble: The ranking ensemble (source of the canonical ranking).

    Returns:
        A best-first summary frame with the headline columns, display-labelled.
    """
    ranked = ensemble.canonical.ranked.copy()
    eads, dist = _eads_by_name(prep), dict(
        zip(prep.df["name"], prep.df["ads_dist_A"]))
    ranked["e_ads_kjmol"] = ranked["name"].map(eads)
    ranked["ads_dist_A"] = ranked["name"].map(dist)
    cols = ["name", "gap_ev", "hardness_ev", "softness_inv_ev", "delta_n",
            "e_ads_kjmol", "ads_dist_A", "score"]
    return ranked[cols].round(3).rename(
        columns={**_SUMMARY_LABELS, "ads_dist_A": f"{prep.m_elem}–O (Å)"})


def summary_sentence(prep: PreparedReport,
                     ensemble: RankingEnsemble) -> str | None:
    """The headline sentence: a single robust lead, or a tie within resolution.

    Args:
        prep: The shared report data (molecule count, substrate element).
        ensemble: The ranking ensemble carrying the robustness verdict.

    Returns:
        The ``**bold**``-marked sentence, or None when there are no ranked rows.
    """
    v = ensemble.verdict
    n = len(prep.df)
    if not len(ensemble.canonical.ranked):
        return None
    if v.robust and v.lead is not None:
        lead_row = ensemble.canonical.ranked.iloc[0]
        eads = _eads_by_name(prep).get(v.lead)
        return _content.bottom_line(
            n, v.lead, float(lead_row["score"]), float(lead_row["gap_ev"]),
            float(eads) if eads is not None and pd.notna(eads) else None,
            prep.m_elem, v.n_bases)
    return _content.bottom_line_tie(n, v.coleaders, v.laggard, v.n_bases)


def _lead_by_basis_block(ensemble: RankingEnsemble) -> list[str]:
    """The lead-by-basis sensitivity table + a one-line robustness note.

    Emitted only when more than one basis exists (a single basis has nothing to
    compare against), it shows which candidate tops each basis so a lead that
    flips with geometry or protonation is visible at a glance.
    """
    v = ensemble.verdict
    if v.n_bases < 2:
        return []
    body = "".join(
        f"<tr><th>{escape(lbl)}</th>"
        f"<td>{escape(display_name(lead))}</td></tr>"
        for lbl, lead in ensemble.lead_by_basis())
    note = _content.robustness_note(v.robust, v.n_bases)
    return [
        '<div class="tw"><table><thead><tr><th>Ranking basis</th>'
        f"<th>Top candidate</th></tr></thead><tbody>{body}</tbody></table></div>",
        f'<p class="meta">{_inline(note)}</p>',
    ]


def _summary_section(prep: PreparedReport,
                     ensemble: RankingEnsemble) -> list[str]:
    """Headline sentence + the canonical ranking table + robustness panel.

    The table is checkmarked only when the lead is robust; when the leaders flip
    across bases it renders plain (no crowned winner), and the lead-by-basis
    table shows the disagreement.
    """
    sentence = summary_sentence(prep, ensemble)
    return [
        "<h2>Summary &amp; ranking</h2>",
        f"<p>{_inline(sentence)}</p>" if sentence else "",
        _ranking_table_html(canonical_summary(prep, ensemble), "Inhibitor",
                            mark_winners=ensemble.verdict.robust),
        *_lead_by_basis_block(ensemble),
        f'<p class="meta">'
        f"{_inline(_content.score_note(prep.m_elem, ensemble.canonical.label))}"
        "</p>",
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
        _descriptor_table_html(prep.full),
        _geometry_block(figdir),
    ]


def _fukui_section(prep: PreparedReport, figdir: str) -> list[str]:
    """Local-reactivity (Fukui) subsection: donor-site list + per-molecule maps.

    Fukui and the ESP map are facets of the isolated-molecule QM analysis, so
    they are h3 subsections here, not separate pipeline stages.
    """
    fukui_summary = (
        "<ul>" + "".join(f"<li><b>{escape(n)}</b>: {s}</li>"
                         for n, s in prep.fukui_items)
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
    """Brownian-MD metal-donor RDF subsection."""
    return [
        f"<h2>Brownian MD — {prep.m_elem}–donor RDF</h2>",
        _grid([_img_block(figdir, f"fig6_{n}_rdf.png",
                          f"{n} — {prep.m_elem}–donor RDF")
               for n in prep.df["name"]]),
    ]


def _method_section(level: str) -> list[str]:
    """Method & caveats footer."""
    return [
        "<h2>Method &amp; caveats</h2>",
        f'<p class="meta">DFT level: {escape(level)}. {_content.METHOD_CAVEAT}</p>',
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
    ranking uses the canonical basis (best geometry x pH-weighted speciation)
    and is gated on robustness; the other bases are surfaced as labelled
    sensitivity panels.

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
    ensemble = report_ensemble(neutral_aq_rows, acid_cation_rows,
                               opt_neutral_rows, opt_acid_rows,
                               speciation_summary)

    # Assemble the document shell + each section in order, then number the
    # headings once over the joined string. Section order mirrors the Word
    # builder (report_docx.build_docx_report) so the two outlines stay diffable.
    parts = [
        '<!doctype html><html><head><meta charset="utf-8">',
        "<title>corrosim — multiscale inhibitor report</title>",
        f"<style>{_REPORT_CSS}</style></head><body>",
        *_header_section(metal, medium, prep, generated_at),
        *_overview_section(figdir),
        *_summary_section(prep, ensemble),
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
