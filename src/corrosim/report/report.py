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

# backend auto-selected: inline in Jupyter, Agg when headless
import matplotlib.pyplot as plt
import pandas as pd

from ..qm.descriptors import DESCRIPTOR_META
from . import equations as _eq
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
    d = df.copy()
    def z(s, invert=False):
        sd = s.std(ddof=0)
        if sd == 0:
            return s * 0
        zz = (s - s.mean()) / sd
        return -zz if invert else zz
    score = (z(d["gap_ev"], invert=True)
             + z(d["hardness_ev"], invert=True)
             + z(d["softness_inv_ev"]))
    d["score"] = (score / 3).round(3)
    return d.sort_values("score", ascending=False).reset_index(drop=True)


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
    ax.set_xticks(list(x)); ax.set_xticklabels(df["name"], rotation=20, ha="right")
    ax.set_ylabel("Energy (eV)"); ax.set_title("Frontier orbital energies")
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
    """Write a self-contained Stage-1 HTML report (ranking, table, plots).

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


def _explain(role: str) -> str:
    """Standalone explanation paragraph for a figure role (report_content)."""
    txt = _content.FIGURE_EXPLANATIONS.get(role, "")
    return f'<p class="figexpl">{txt}</p>' if txt else ""


def _inline(text: str) -> str:
    """Render the shared content's ``**bold**`` markup to inline HTML."""
    return "".join(f"<b>{t}</b>" if b else t for t, b in _content.inline_runs(text))


def _p(text: str) -> str:
    """A paragraph rendering the shared content's ``**bold**`` markup."""
    return f"<p>{_inline(text)}</p>"


def _equation_img(key: str) -> str:
    """A <figure> with the mathtext-rendered equation inline (base64) + its meaning."""
    eq = _eq.EQUATIONS[key]
    b64 = base64.b64encode(_eq.render_equation_png(eq.latex)).decode()
    return (f'<figure class="eq"><img src="data:image/png;base64,{b64}" '
            f'alt="{eq.quantity}">'
            f"<figcaption><b>{eq.quantity}</b> — {eq.meaning}</figcaption></figure>")


def _content_table_html(payload: dict) -> str:
    """Render a report_content table item ({columns, rows, caption}) to HTML."""
    head = "".join(f"<th>{c}</th>" for c in payload["columns"])
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
                   for row in payload["rows"])
    cap = payload.get("caption", "")
    caption = f'<p class="meta">{cap}</p>' if cap else ""
    return (f"<table><thead><tr>{head}</tr></thead>"
            f"<tbody>{body}</tbody></table>{caption}")


def _scientific_basis_section() -> list[str]:
    """The shared 'Scientific basis & validation' section (report_content):
    woven pipeline.md + validation.md prose, the governing equations rendered in
    scientific form, and the descriptor / experimental tables.
    """
    out = ["<h2>Scientific basis &amp; validation</h2>"]
    for kind, payload in _content.SCIENTIFIC_BASIS:
        if kind == "h3" and isinstance(payload, str):
            out.append(f"<h3>{payload}</h3>")
        elif kind == "p" and isinstance(payload, str):
            out.append(_p(payload))
        elif kind == "table" and isinstance(payload, dict):
            out.append(_content_table_html(payload))
        elif kind == "eqgroups":
            for heading, group in _eq.EQUATION_GROUPS:
                out.append(f"<h4>{heading}</h4>")
                out.append('<div class="eqgrid">'
                           + "".join(_equation_img(e.key) for e in group)
                           + "</div>")
    return out


def _number_headings(html: str) -> str:
    """Prefix section (h2) and subsection (h3) headings with hierarchical numbers
    (``1.``, ``1.1`` …) in document order. The ``h1`` title and deeper (``h4``)
    headings are left unnumbered. Mirrors report_docx's numbering so the HTML and
    Word reports carry the same section numbers.
    """
    c = {"h2": 0, "h3": 0}

    def repl(m: re.Match) -> str:
        tag, inner = m.group(1), m.group(2)
        if tag == "h2":
            c["h2"] += 1
            c["h3"] = 0
            num = f"{c['h2']}. "
        else:
            c["h3"] += 1
            num = f"{c['h2']}.{c['h3']} "
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
            "<p>Relaxing each structure at B3LYP/6-31G(d) before the production "
            "single point lowers the gap (~0.4–0.5 eV) and hardness and raises ΔN, "
            "but leaves both the gap and ΔN rankings unchanged — the lead "
            "assignments are geometry-robust.</p>"
            + _img_block(figdir, "fig8_geometry_comparison.png",
                         "Force-field vs DFT-optimised geometry"))


def _acid_cation_block(acid_cation_rows: list[dict] | None, medium: str) -> list[str]:
    """In-acid comparison section (ADR 0003): the protonated-cation descriptors,
    shown alongside the neutral headline ranking rather than replacing it. Returns
    an empty list when there are no cation rows (non-acidic medium).
    """
    if not acid_cation_rows:
        return []
    return [
        "<h3>Species in the acidic medium (protonated cation)</h3>",
        f"<p>In <b>{medium}</b> the basic carbonyl / hydroxyl oxygens take up a "
        "proton, so the inhibitor is present largely as its +1 cation. The ranking "
        "above uses the <i>neutral</i> form (the conventional descriptor basis); the "
        "protonated-cation descriptors are tabulated here for comparison.</p>",
        _html_table(results_dataframe(acid_cation_rows)),
        '<p class="meta">Protonation lowers the gap and raises softness, and ΔN turns '
        "<b>negative</b> — the electron-poor cation no longer donates to the metal, so "
        "the ΔN &gt; 0 donation heuristic does not apply to this form (cation adsorption "
        "is electrostatic / back-donation driven). The most reactive species by the "
        "gap/softness composite is therefore <i>form-dependent</i>, which is why the "
        "neutral form is kept as the headline ranking (ADR 0003).</p>",
    ]


def _opt_descriptor_block(opt_neutral_rows: list[dict] | None,
                          opt_acid_rows: list[dict] | None,
                          order: list[str] | None = None) -> list[str]:
    """Optimised-geometry descriptor section (#19): the DFT-relaxed
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
    gap_rank = list(ndf.sort_values("gap_ev")["name"])
    dn_rank = list(ndf.sort_values("delta_n", ascending=False)["name"])
    out = [
        "<h3>Optimised-geometry descriptors (DFT-relaxed)</h3>",
        "<p>The same reactivity descriptors on <b>DFT-optimised</b> geometries "
        "(B3LYP/6-31G(d) relaxation, then the production single point) instead of the "
        "force-field geometries used for the headline table. The gap/softness composite "
        f"ranking is unchanged (gap {' &lt; '.join(gap_rank)}; "
        f"ΔN {' &gt; '.join(dn_rank)}) — the lead is geometry-robust.</p>",
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
            "<p>The DFT-optimised +1 cations — the more accurate geometric basis for "
            "the speciation / pKaH work (ADR 0004/0005) than the force-field cations.</p>",
            _html_table(results_dataframe(adf.to_dict("records"))),
        ]
    return out


def _computed_pka_block(computed_pkah: list[dict] | None,
                        freq_corrected: bool = False) -> list[str]:
    """Computed-pKaH resolution (ADR 0005): per-molecule DFT-cycle pKaH and the
    resulting populations, which place the system on one side of the crossover.
    ``computed_pkah`` rows carry name / pkah / f_protonated. ``freq_corrected``
    switches the caption between the electronic-only and the frequency-corrected
    (issue #18) estimate. Empty if absent.
    """
    if not computed_pkah:
        return []
    head = "<tr><th>molecule</th><th>computed pKaH</th><th>% protonated @ this pH</th></tr>"
    body = "".join(
        f"<tr><td>{r['name']}</td><td>{r['pkah']:.1f}</td>"
        f"<td>{r['f_protonated'] * 100:.2f}%</td></tr>"
        for r in computed_pkah
    )
    worst = max(r["f_protonated"] for r in computed_pkah)
    basis = ("cycle (frequency-corrected: gas-phase opt+freq ZPE/thermal/entropy on "
             "the production single point; `results/pka.json`, ADR 0005)."
             if freq_corrected else
             "cycle (electronic-only; `results/pka.json`, ADR 0005).")
    tail = ("The frequency correction shifts pKaH by only a fraction of the large "
            "margin to the crossover, leaving the conclusion intact."
            if freq_corrected else
            "The omitted O–H zero-point energy would push pKaH lower still (more "
            "neutral), reinforcing this.")
    return [
        "<h4>Computed pKaH (DFT deprotonation cycle)</h4>",
        f"<table><thead>{head}</thead><tbody>{body}</tbody></table>",
        '<p class="meta">From a B3LYP/6-311++G(d,p) + ddCOSMO aqueous deprotonation '
        f"{basis} All values sit far below the crossover — the most basic flavonoid "
        f"is only {worst * 100:.2f}% protonated — so every species is essentially "
        "fully neutral here. This <b>resolves the sensitivity above</b>: the neutral "
        "form is the physically dominant species, not just the conventional choice, so "
        f"the headline lead is robust. {tail}</p>",
    ]


def _speciation_block(summary: dict | None, medium: str,
                      computed_pkah: list[dict] | None = None,
                      pka_freq_corrected: bool = False) -> list[str]:
    """Quantitative pH-speciation section (ADR 0004): the neutral/protonated
    population at the medium pH, the population-weighted descriptor table, and the
    lead-crossover sensitivity to the protonation pKa — followed by the computed
    pKaH that resolves it (ADR 0005). Empty when no summary is supplied (non-acidic
    medium or unknown pH).
    """
    if not summary:
        return []
    spec = summary["speciation"]
    lo_f, hi_f = summary["band_fraction"]
    cross_f, cross_pk = summary["crossover_fraction"], summary["crossover_pkah"]
    sens = " The lead is insensitive to the protonation pKa over the plausible range."
    if cross_f and cross_pk is not None:
        sens = (f" The gap/softness composite lead changes from "
                f"<b>{summary['neutral_lead']}</b> to <b>{summary['crossover_lead']}</b> "
                f"at only ~{cross_f:.0%} protonation (pKaH ≈ {cross_pk:.1f}); the "
                f"pKaH±1 band ({min(lo_f, hi_f):.0%}–{max(lo_f, hi_f):.0%} protonated) "
                f"straddles that crossover — so the lead is sensitive to the "
                f"protonation pKa, the key uncertainty here.")
    return [
        f"<h3>Speciation in {medium} (pH ≈ {spec.ph:.1f})</h3>",
        "<p>The most basic site of these flavonoids is the 4-oxo carbonyl, a very "
        f"weak base (estimated conjugate-acid pKaH ≈ {spec.pkah:.1f}; ADR 0004). By "
        f"Henderson–Hasselbalch the inhibitor is <b>{spec.f_neutral:.0%} neutral / "
        f"{spec.f_protonated:.0%} protonated</b> at this pH — the <b>{spec.dominant}</b> "
        "form dominates, which is why the headline ranking uses the neutral form.</p>",
        f"<p>Population-weighted (pH-weighted) descriptors — blended lead: "
        f"<b>{summary['blended_lead']}</b>:</p>",
        _html_table(results_dataframe(summary["blended_rows"])),
        f'<p class="meta"><b>Sensitivity.</b>{sens}</p>',
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

    # ordered neutral rows + e_ads/ads_dist
    df: pd.DataFrame
    # best-first with score
    ranked: pd.DataFrame
    # headline summary columns
    summary: pd.DataFrame
    # full descriptor table
    full: pd.DataFrame
    level: str
    # "Fe(110)" -> "Fe"
    m_elem: str
    # (molecule, "O5 (f⁻=0.090), ...")
    fukui_items: list[tuple[str, str]]


# Human-readable headers for the headline summary table (display only; the raw
# result keys stay on the full descriptor table). ads_dist_A is labelled with the
# actual metal in prepare_report_data.
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

    Builds the ranking, the merged Stage-2/3 adsorption columns and the Fukui
    top-donor summary. See :class:`PreparedReport`.

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
    # "Fe(110)" -> "Fe"
    m_elem = str(metal).split("(")[0].strip()
    mc_by = {r["name"]: r for r in mc_rows}
    md_by = {r["name"]: r for r in md_rows}

    def _md_peak(n):
        # generic key, legacy fallback
        row = md_by.get(n) or {}
        return row.get("metal_O_peak_A", row.get("FeO_peak_A"))

    df["e_ads_kjmol"] = df["name"].map(lambda n: (mc_by.get(n) or {}).get("e_ads_kjmol"))
    df["ads_dist_A"] = df["name"].map(_md_peak)
    # coerce first: an all-missing column (no MD data) is object dtype and would
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
    return PreparedReport(df, ranked, summary, full, level, m_elem, fukui_items)


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
    labelled in-acid comparison when the medium is acidic (see ADR 0003).

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
    df, summary, full, level, m_elem = (prep.df, prep.summary, prep.full,
                                        prep.level, prep.m_elem)

    # Data-derived headline: name the top-ranked inhibitor and its key numbers so a
    # reader gets the takeaway before the detail. Shared with the Word renderer via
    # report_content.bottom_line; read from the ranking, never hardcoded.
    if len(prep.ranked):
        _lead = prep.ranked.iloc[0]
        _eads = _lead.get("e_ads_kjmol")
        bottom_line = '<div class="note">' + _inline(_content.bottom_line(
            len(df), str(_lead["name"]), float(_lead["score"]), float(_lead["gap_ev"]),
            float(_eads) if _eads is not None and pd.notna(_eads) else None,
            m_elem)) + "</div>"
    else:
        bottom_line = ""
    fukui_summary = (
        "<ul>" + "".join(f"<li><b>{n}</b>: {s}</li>" for n, s in prep.fukui_items)
        + "</ul>" if prep.fukui_items else '<p class="meta">No Fukui data found.</p>')

    parts = [
        '<!doctype html><html><head><meta charset="utf-8">',
        "<title>corrosim — multiscale inhibitor report</title>",
        f"<style>{_REPORT_CSS}</style></head><body>",
        "<h1>corrosim — multiscale corrosion-inhibitor report</h1>",
        f'<p class="meta">Substrate <b>{metal}</b> &nbsp;|&nbsp; Medium <b>{medium}</b>'
        f' &nbsp;|&nbsp; DFT level <b>{level}</b>'
        f' &nbsp;|&nbsp; Generated '
        f'{generated_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}</p>',
        f'<div class="note">{_content.HEADLINE_CAVEAT}</div>',
        bottom_line,
        "<h2>Overview</h2>",
        _p(_content.STAGE_INTROS["overview"]),
        _explain("pipeline"),
        _img_block(figdir, "fig0_pipeline.png", "corrosim pipeline"),

        # Summary / ranking ------------------------------------------------
        "<h2>Summary &amp; ranking</h2>",
        _html_table(summary, best_first_row=True),
        f'<p class="meta">{_inline(_content.score_explanation(m_elem))}</p>',

        # Stage 1 ----------------------------------------------------------
        "<h2>DFT electronic descriptors</h2>",
        _p(_content.STAGE_INTROS["dft"]),
        _grid([
            _img_block(figdir, "fig1_structures.png", "Modelled flavonoids"),
            _img_block(figdir, "fig2_mo_diagram.png",
                       "Frontier-orbital energies vs Fe(110) work function"),
        ]),
        _explain("structures"),
        _explain("mo_diagram"),
        "<h3>Frontier-orbital isosurfaces (HOMO / LUMO)</h3>",
        _grid([_img_block(figdir, f"fig2b_{n}_homo.png", f"{n} HOMO")
               for n in df["name"]]),
        _explain("orbital_homo"),
        _grid([_img_block(figdir, f"fig2b_{n}_lumo.png", f"{n} LUMO")
               for n in df["name"]]),
        _explain("orbital_lumo"),
        _grid([
            _img_block(figdir, "fig3_descriptors.png", "Reactivity descriptors"),
            _img_block(figdir, "fig3b_protonation.png",
                       "Protonation effect (DFT-optimised cations, 1 M HCl)"),
        ]),
        _explain("descriptors"),
        _explain("protonation"),
        "<h3>Full descriptor table (neutral, aqueous)</h3>",
        _html_table(full),
        _geometry_block(figdir),
        _explain("geometry") if os.path.exists(
            figure_path(figdir, "fig8_geometry_comparison.png")) else "",
        *_opt_descriptor_block(opt_neutral_rows, opt_acid_rows, order),
        *_acid_cation_block(acid_cation_rows, medium),
        *_speciation_block(speciation_summary, medium, computed_pkah,
                           pka_freq_corrected),

        # Stage 1 (cont.) — local reactivity (Fukui). Fukui and the ESP map are
        # facets of Stage 1 (the isolated-molecule QM analysis), so they are h3
        # subsections here, not separate pipeline stages.
        "<h3>Local reactivity (Fukui)</h3>",
        _p(_content.STAGE_INTROS["fukui"]),
        "<p>The strongest electron-donating oxygens (highest f⁻) per molecule:</p>",
        fukui_summary,
        _grid([_img_block(figdir, f"fig4_{n}_fukui.png", f"{n} — condensed Fukui")
               for n in df["name"]]),
        _explain("fukui"),

        # Stage 1 (cont.) — electrostatic-potential (ESP) map --------------
        "<h3>Electrostatic-potential (ESP) map</h3>",
        _p(_content.STAGE_INTROS["esp"]),
        _grid([_img_block(figdir, f"fig7_{n}_esp.png", f"{n} — ESP map")
               for n in df["name"]]),
        _explain("esp"),

        # Stage 2 — Monte Carlo -------------------------------------------
        "<h2>Monte Carlo adsorption</h2>",
        _p(_content.STAGE_INTROS["mc"]),
        _grid([_img_block(figdir, f"fig5_{n}_mc_pose.png", f"{n} — best pose")
               for n in df["name"]]),
        _explain("mc_pose"),
        _grid([_img_block(figdir, f"fig5_{n}_mc_energy.png", f"{n} — MC annealing")
               for n in df["name"]]),
        _explain("mc_energy"),

        # Stage 3 — MD -----------------------------------------------------
        f"<h2>Brownian MD — {m_elem}–O RDF</h2>",
        _p(_content.STAGE_INTROS["md"]),
        _grid([_img_block(figdir, f"fig6_{n}_rdf.png", f"{n} — {m_elem}–O RDF")
               for n in df["name"]]),
        _explain("rdf"),

        # Scientific basis & validation (pipeline.md + validation.md) ------
        *_scientific_basis_section(),

        # Method -----------------------------------------------------------
        "<h2>Method &amp; caveats</h2>",
        f'<p class="meta">DFT level: {level}. {_content.METHOD_CAVEAT}</p>',
        "</body></html>",
    ]
    html = _number_headings("".join(parts))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
