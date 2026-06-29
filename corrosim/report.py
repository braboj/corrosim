"""
corrosim.report
----------------
Turn the per-molecule results into outputs: a tidy table, comparison plots, a
ranking, and a self-contained HTML report.
"""
from __future__ import annotations
import base64, datetime, io
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
