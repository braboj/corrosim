"""Render an executed .ipynb to a clean, fully self-contained HTML page."""
import html as _html
import sys

import markdown as md
import nbformat

CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
 max-width:980px;margin:1.5rem auto;color:#1a202c;padding:0 1rem;line-height:1.55}
h1{font-size:1.6rem}h2{font-size:1.2rem;margin-top:1.8rem;border-bottom:1px solid #e2e8f0;padding-bottom:.3rem}
h3{font-size:1.05rem}
pre{background:#f7fafc;border:1px solid #e2e8f0;border-radius:6px;padding:.7rem .9rem;
 overflow-x:auto;font-size:.85rem;line-height:1.4}
pre.code{background:#1f2430;color:#e6edf3;border-color:#2d333b}
pre.out{background:#fbfdff}
.cell{margin:1rem 0}
.prompt{color:#a0aec0;font-size:.72rem;font-family:monospace;margin-bottom:.2rem}
table{border-collapse:collapse;font-size:.85rem;margin:.4rem 0}
th,td{border:1px solid #e2e8f0;padding:.35rem .55rem;text-align:right}
th:first-child,td:first-child{text-align:left}
thead tr,table tr:first-child{background:#f7fafc}
img{max-width:100%;margin:.4rem 0;border:1px solid #edf2f7;border-radius:4px}
code{background:#edf2f7;padding:.05rem .3rem;border-radius:3px;font-size:.85em}
pre code{background:none;padding:0}
.banner{background:#ebf8ff;border:1px solid #bee3f8;border-radius:6px;padding:.5rem .9rem;
 font-size:.85rem;color:#2c5282;margin-bottom:1.2rem}
"""

def render(nb_path, out_path):
    nb = nbformat.read(nb_path, as_version=4)
    parts = ["<!doctype html><html><head><meta charset='utf-8'>",
             "<meta name='viewport' content='width=device-width,initial-scale=1'>",
             f"<title>{_html.escape(nb_path)}</title><style>{CSS}</style></head><body>",
             "<div class='banner'>Static render of the executed notebook — "
             "code, tables and plots are shown with their real outputs. "
             "To edit and re-run, open the .ipynb in Jupyter.</div>"]
    for cell in nb.cells:
        if cell.cell_type == "markdown":
            parts.append("<div class='cell'>" +
                         md.markdown(cell.source, extensions=["fenced_code", "tables"]) +
                         "</div>")
        elif cell.cell_type == "code":
            if not cell.source.strip():
                continue
            ec = cell.get("execution_count")
            parts.append("<div class='cell'>")
            parts.append(f"<div class='prompt'>In [{ec if ec is not None else ' '}]:</div>")
            parts.append(f"<pre class='code'><code>{_html.escape(cell.source)}</code></pre>")
            for o in cell.get("outputs", []):
                parts.append(_render_output(o))
            parts.append("</div>")
    parts.append("</body></html>")
    with open(out_path, "w") as f:
        f.write("\n".join(parts))
    return out_path

def _render_output(o):
    t = o.get("output_type")
    if t == "stream":
        return f"<pre class='out'>{_html.escape(o.get('text',''))}</pre>"
    if t in ("execute_result", "display_data"):
        data = o.get("data", {})
        if "image/png" in data:
            png = data["image/png"]
            if isinstance(png, list):
                png = "".join(png)
            return f"<img src='data:image/png;base64,{png}'>"
        if "text/html" in data:                       # dataframes, etc.
            h = data["text/html"]
            return h if isinstance(h, str) else "".join(h)
        if "text/plain" in data:
            txt = data["text/plain"]
            if isinstance(txt, list):
                txt = "".join(txt)
            return f"<pre class='out'>{_html.escape(txt)}</pre>"
    if t == "error":
        return f"<pre class='out' style='color:#c53030'>{_html.escape(chr(10).join(o.get('traceback',[])))}</pre>"
    return ""

if __name__ == "__main__":
    print(render(sys.argv[1], sys.argv[2]))
