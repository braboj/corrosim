"""
corrosim.report
----------------
Turn the per-molecule results into outputs: a tidy table, comparison plots, a
ranking, and a self-contained HTML report.
"""
from __future__ import annotations
import base64, datetime, io, os
import pandas as pd
import matplotlib.pyplot as plt   # backend auto-selected: inline in Jupyter, Agg headless

from .descriptors import DESCRIPTOR_META


def results_dataframe(rows: list[dict]) -> pd.DataFrame:
    """rows: list of {name, formula, level, **descriptor fields}."""
    df = pd.DataFrame(rows)
    cols = ["name", "formula", "charge", "level", "homo_ev", "lumo_ev", "gap_ev",
            "hardness_ev", "softness_inv_ev", "electronegativity_ev",
            "electrophilicity_ev", "delta_n", "back_donation_ev", "tnc"]
    if "e_ads_kjmol" in df.columns:
        cols.append("e_ads_kjmol")
    cols = [c for c in cols if c in df.columns]
    return df[cols].round(3)


def rank_inhibitors(df: pd.DataFrame) -> pd.DataFrame:
    """
    Simple composite ranking: stronger inhibition is associated with a smaller
    gap, lower hardness, and higher softness. We z-score those and combine.
    Returns df sorted best-first with a 'score' column (higher = better).
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


def plot_homo_lumo(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 4))
    x = range(len(df))
    ax.bar([i - 0.2 for i in x], df["homo_ev"], width=0.4, label="HOMO", color="#2b6cb0")
    ax.bar([i + 0.2 for i in x], df["lumo_ev"], width=0.4, label="LUMO", color="#dd6b20")
    ax.axhline(0, color="grey", lw=0.6)
    ax.set_xticks(list(x)); ax.set_xticklabels(df["name"], rotation=20, ha="right")
    ax.set_ylabel("Energy (eV)"); ax.set_title("Frontier orbital energies")
    ax.legend()
    return fig


def plot_descriptor_bars(df: pd.DataFrame):
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
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
       max-width:980px;margin:2rem auto;color:#1a202c;padding:0 1rem;}}
 h1{{font-size:1.5rem}} h2{{font-size:1.15rem;margin-top:1.8rem;border-bottom:1px solid #e2e8f0;padding-bottom:.3rem}}
 table{{border-collapse:collapse;width:100%;font-size:.9rem;margin:.6rem 0}}
 th,td{{border:1px solid #e2e8f0;padding:.4rem .6rem;text-align:right}}
 th:first-child,td:first-child{{text-align:left}}
 thead{{background:#f7fafc}} tr:nth-child(even){{background:#fbfdff}}
 .best{{background:#f0fff4!important;font-weight:600}}
 .meta{{color:#718096;font-size:.85rem}} img{{max-width:100%;margin:.5rem 0}}
 .note{{background:#fffaf0;border:1px solid #feebc8;padding:.6rem .9rem;border-radius:6px;font-size:.88rem}}
</style></head><body>
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
                      out_path: str) -> str:
    ranked = rank_inhibitors(df)

    def style_table(d, best_first_row=False):
        rows = []
        for i, (_, r) in enumerate(d.iterrows()):
            cls = ' class="best"' if (best_first_row and i == 0) else ""
            cells = "".join(f"<td>{r[c]}</td>" for c in d.columns)
            rows.append(f"<tr{cls}>{cells}</tr>")
        head = "".join(f"<th>{c}</th>" for c in d.columns)
        return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"

    html = _HTML.format(
        metal=metal, medium=medium, level=level,
        ts=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        caveat=("These molecules are documented major constituents of the extract, "
                "simulated as representatives — not a verified profile of your specific "
                "sample. Confirm with LC-MS/GC-MS for a publication."),
        rank_table=style_table(ranked[["name", "gap_ev", "hardness_ev",
                                       "softness_inv_ev", "delta_n", "score"]],
                               best_first_row=True),
        full_table=style_table(df),
        img_hl=_fig_to_b64(plot_homo_lumo(df)),
        img_desc=_fig_to_b64(plot_descriptor_bars(df)),
        method=("Descriptors from frontier-orbital energies (Koopmans' theorem). "
                "Engine/level as noted above. ΔN uses the metal work function with "
                "η(metal)=0. Ranking is a screening heuristic, not a substitute for "
                "the Stage-2/3 adsorption MD or for electrochemical validation."),
    )
    with open(out_path, "w") as f:
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
    """A <figure> embedding figures/<fname> inline, or a placeholder if absent."""
    b64 = _img_b64_file(os.path.join(figdir, fname))
    if not b64:
        return f'<p class="meta">[figure not found: {fname}]</p>'
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return (f'<figure><img src="data:image/png;base64,{b64}">{cap}</figure>')


def _grid(blocks: list[str]) -> str:
    return f'<div class="grid">{"".join(blocks)}</div>'


def top_donor_sites(fukui_rows: list[dict], element: str = "O", n: int = 3) -> list[dict]:
    """Atoms most susceptible to electrophilic attack (highest f⁻) — the
    electron-donating sites that coordinate the metal. Defaults to oxygens."""
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


_PIPELINE_CSS = """
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
"""


def build_pipeline_report(neutral_aq_rows: list[dict], mc_rows: list[dict],
                          md_rows: list[dict], fukui_by_name: dict[str, list[dict]],
                          figdir: str, out_path: str,
                          metal: str = "Fe(110)", medium: str = "1 M HCl",
                          order: list[str] | None = None) -> str:
    """
    Assemble one self-contained HTML report spanning the whole multiscale
    pipeline. Tables are built from the committed result data; figures are
    embedded inline (base64) from ``figdir`` so the file stands alone.
    """
    df = pd.DataFrame(neutral_aq_rows).copy()
    if order:
        df = (df.set_index("name").loc[[n for n in order if n in set(df["name"])]]
              .reset_index())
    mc_by = {r["name"]: r for r in mc_rows}
    md_by = {r["name"]: r for r in md_rows}
    df["e_ads_kjmol"] = df["name"].map(lambda n: mc_by.get(n, {}).get("e_ads_kjmol"))
    df["feo_peak_a"] = df["name"].map(lambda n: md_by.get(n, {}).get("FeO_peak_A"))
    df["feo_peak_a"] = df["feo_peak_a"].round(2)

    ranked = rank_inhibitors(df)
    level = str(df["level"].iloc[0]) if "level" in df.columns and len(df) else "—"

    summary = ranked[["name", "gap_ev", "hardness_ev", "softness_inv_ev",
                      "delta_n", "e_ads_kjmol", "feo_peak_a", "score"]].round(3)
    full = results_dataframe(df.to_dict("records"))

    # --- Fukui textual summary: top donor oxygens per molecule -------------
    fukui_items = []
    for name in df["name"]:
        rows = fukui_by_name.get(name)
        if not rows:
            continue
        tops = top_donor_sites(rows, "O", 3)
        sites = ", ".join(f"O{t['idx']} (f⁻={t['f_minus']:.3f})" for t in tops)
        fukui_items.append(f"<li><b>{name}</b>: {sites}</li>")
    fukui_summary = (f"<ul>{''.join(fukui_items)}</ul>" if fukui_items
                     else '<p class="meta">No Fukui data found.</p>')

    parts = [
        '<!doctype html><html><head><meta charset="utf-8">',
        "<title>corrosim — multiscale inhibitor report</title>",
        f"<style>{_PIPELINE_CSS}</style></head><body>",
        "<h1>corrosim — multiscale corrosion-inhibitor report</h1>",
        f'<p class="meta">Substrate <b>{metal}</b> &nbsp;|&nbsp; Medium <b>{medium}</b>'
        f' &nbsp;|&nbsp; DFT level <b>{level}</b>'
        f' &nbsp;|&nbsp; Generated {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}</p>',
        '<div class="note">Flavonoids modelled here (kaempferol, quercetin, '
        "isorhamnetin) are documented major constituents of the extract, simulated "
        "as <i>representatives</i> — not a verified profile of a specific sample. "
        "Confirm composition by LC-MS/GC-MS before publication.</div>",

        # Summary / ranking ------------------------------------------------
        "<h2>Summary &amp; ranking</h2>",
        _html_table(summary, best_first_row=True),
        '<p class="meta">Composite score z-scores a smaller gap, lower hardness and '
        "higher softness (higher = stronger predicted reactivity). E<sub>ads</sub> "
        "(Stage&nbsp;2 Monte Carlo) and the Fe–O distance (Stage&nbsp;3 MD) are shown "
        "alongside for the adsorption picture.</p>",

        # Stage 1 ----------------------------------------------------------
        '<h2><span class="stage">Stage 1</span> &nbsp;DFT electronic descriptors</h2>',
        _grid([
            _img_block(figdir, "fig1_structures.png", "Modelled flavonoids"),
            _img_block(figdir, "fig2_mo_diagram.png",
                       "Frontier-orbital energies vs Fe(110) work function"),
        ]),
        "<h3>Frontier-orbital isosurfaces (HOMO / LUMO)</h3>",
        _grid([_img_block(figdir, f"fig2b_{n}_homo.png", f"{n} HOMO")
               for n in df["name"]]),
        _grid([_img_block(figdir, f"fig2b_{n}_lumo.png", f"{n} LUMO")
               for n in df["name"]]),
        _grid([
            _img_block(figdir, "fig3_descriptors.png", "Reactivity descriptors"),
            _img_block(figdir, "fig3b_protonation.png",
                       "Protonation effect (1 M HCl)"),
        ]),
        "<h3>Full descriptor table (neutral, aqueous)</h3>",
        _html_table(full),

        # Stage 1b — Fukui -------------------------------------------------
        '<h2><span class="stage">Stage 1b</span> &nbsp;Local reactivity (Fukui)</h2>',
        "<p>Condensed Fukui / dual-descriptor maps locate the donor and acceptor "
        "atoms. The strongest electron-donating oxygens (highest f⁻) are the "
        "metal-coordinating sites:</p>",
        fukui_summary,
        _grid([_img_block(figdir, f"fig4_{n}_fukui.png", f"{n} — condensed Fukui")
               for n in df["name"]]),

        # Stage 1c — ESP / MEP map ----------------------------------------
        '<h3>Electrostatic-potential (ESP) map</h3>',
        "<p>The electron-density isosurface coloured by the molecular electrostatic "
        "potential. Red (negative) regions over the catechol and carbonyl oxygens are "
        "the electron-rich, metal-coordinating sites — corroborating the Fukui "
        "donor analysis above.</p>",
        _grid([_img_block(figdir, f"fig7_{n}_esp.png", f"{n} — ESP map")
               for n in df["name"]]),

        # Stage 2 — Monte Carlo -------------------------------------------
        '<h2><span class="stage">Stage 2</span> &nbsp;Monte Carlo adsorption</h2>',
        "<p>Metropolis/annealing pose search on the metal surface. Flavonoids settle "
        "flat/parallel; E<sub>ads</sub> ≈ −16 kJ/mol indicates physisorption.</p>",
        _grid([_img_block(figdir, f"fig5_{n}_mc_pose.png", f"{n} — best pose")
               for n in df["name"]]),
        _grid([_img_block(figdir, f"fig5_{n}_mc_energy.png", f"{n} — MC annealing")
               for n in df["name"]]),

        # Stage 3 — MD -----------------------------------------------------
        '<h2><span class="stage">Stage 3</span> &nbsp;Brownian MD — Fe–O RDF</h2>',
        "<p>Rigid-body Brownian dynamics from the best MC pose; the first Fe–O "
        "radial-distribution peak (~3.5 Å) sets the adsorption distance.</p>",
        _grid([_img_block(figdir, f"fig6_{n}_rdf.png", f"{n} — Fe–O RDF")
               for n in df["name"]]),

        # Method -----------------------------------------------------------
        "<h2>Method &amp; caveats</h2>",
        f'<p class="meta">Descriptors from frontier-orbital energies (Koopmans). '
        f"DFT level: {level}. ΔN uses the metal work function with η(metal)=0. "
        "Monte Carlo / Brownian MD use a classical van-der-Waals adsorption model — "
        "a screening surrogate, not a substitute for periodic DFT or electrochemical "
        "validation. The composite ranking is a heuristic.</p>",
        "</body></html>",
    ]
    html = "".join(parts)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
