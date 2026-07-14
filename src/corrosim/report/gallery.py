"""Static Pages gallery of the validated case-study reports.

Reads each case's metadata from the single source of truth (``presets``) and
emits a self-contained ``index.html`` that links every case's own self-contained
report, turning the tracked report bundles into a zero-click "see it" showcase
with no regeneration.

::

    presets.CASE_STUDIES --> build_index_html() --> _site/index.html
    cases/<name>/report/report.html  --copy-->     _site/<name>.html

The design encodes the science on a white canvas: each card is accented by its
substrate metal (steel-blue Fe, copper Cu, aluminium Al), and its badge reads
green (validated) or amber (partial). Every card names the published study the
case is validated against, so the gallery reads as corrosim's own results checked
against the literature.
"""
from __future__ import annotations

import html
import os
import shutil
from collections.abc import Iterable, Sequence

from corrosim.presets import CASE_STUDIES, CaseStudy

# Where the source lives, for the colophon links.
_REPO = "https://github.com/braboj/corrosim"

# Validation verdict per case, mirroring the scorecard in docs/validation.md
# (the source of truth). ``tier`` drives the badge colour; a case absent here
# renders without a badge rather than a wrong one.
_STATUS: dict[str, tuple[str, str]] = {
    "arghel": ("Validated", "ok"),
    "phytic-acid": ("Validated · qualitative", "ok"),
    "tetrazoles": ("Validated · qualitative", "ok"),
    "pyrazolo-pyrimidine": ("Partial · quantitative", "partial"),
    "tmp-smx": ("Partial · quantitative", "partial"),
    "pyrazolylnucleosides": ("Partial · qualitative", "partial"),
}

# Human card titles; the slug is the stable id, this is the heading. A slug
# absent here falls back to its title-cased self.
_TITLE: dict[str, str] = {
    "arghel": "Arghel flavonoids",
    "phytic-acid": "Phytic acid",
    "pyrazolo-pyrimidine": "Pyrazolo-pyrimidines",
    "tmp-smx": "Trimethoprim + Sulfamethoxazole",
    "tetrazoles": "Tetrazoles",
    "pyrazolylnucleosides": "Pyrazolyl-nucleosides",
}

# CSS custom-property name per substrate element: the card's accent colour is
# set inline from this, so the three metals are visually distinct.
_METAL_VAR: dict[str, str] = {
    "Fe": "var(--fe)",
    "Cu": "var(--cu)",
    "Al": "var(--al)",
}


def unique_cases() -> list[CaseStudy]:
    """Return each registered case study once, in registry order.

    ``CASE_STUDIES`` maps several aliases to the same study; this collapses them
    to the distinct studies, preserving first-seen order.

    Returns:
        The distinct case studies.
    """
    seen: dict[str, CaseStudy] = {}
    for case in CASE_STUDIES.values():
        seen.setdefault(case.name, case)
    return list(seen.values())


def _report_path(case: CaseStudy) -> str:
    """Path to a case's tracked self-contained report.

    Args:
        case: The case study.

    Returns:
        The ``cases/<name>/report/report.html`` path.
    """
    return f"{case.report_dir}/report.html"


def _card_html(case: CaseStudy, index: int) -> str:
    """Render one case card, accented by its substrate metal.

    Args:
        case: The case study.
        index: Position in the grid, used to stagger the entrance animation.

    Returns:
        The card's HTML (an anchor to ``<name>.html``).
    """
    fallback_title = case.name.replace("-", " ").title()
    title = html.escape(_TITLE.get(case.name, fallback_title))
    accent = _METAL_VAR.get(case.metal_element, "var(--fe)")
    n = len(case.molecules)
    plural = "molecule" if n == 1 else "molecules"

    # optional validation badge
    badge = ""
    if case.name in _STATUS:
        label, tier = _STATUS[case.name]
        badge = (f'<span class="badge badge--{tier}">'
                 f'<span class="dot"></span>{html.escape(label)}</span>')

    # the published study this case is validated against, named in full so the
    # validation relationship is explicit (all shipped cases carry one)
    ref = ""
    if case.source:
        ref = ('<div class="case__ref">'
               '<span class="case__ref-label">Validated against</span>'
               f'<span class="case__ref-src">{html.escape(case.source)}</span>'
               '</div>')

    return (
        f'<a class="case" href="{html.escape(case.name)}.html" '
        f'style="--accent:{accent};animation-delay:{index * 70}ms">'
        f'<span class="case__bar"></span>'
        f'<div class="case__head">'
        f'<span class="chip">{html.escape(case.metal)}</span>{badge}'
        f'</div>'
        f'<h2 class="case__title">{title}</h2>'
        f'<p class="case__meta">{html.escape(case.medium)} '
        f'<span class="dotsep">·</span> {n} {plural}</p>'
        f'<p class="case__desc">{html.escape(case.description)}</p>'
        f'{ref}'
        f'<span class="case__cta">View report <span class="arrow">&rarr;</span>'
        f'</span>'
        f'</a>'
    )


def build_index_html(cases: Sequence[CaseStudy]) -> str:
    """Render the gallery landing page linking every case report.

    Args:
        cases: The case studies to show, in display order.

    Returns:
        A complete, self-contained HTML document.
    """
    cards = "\n".join(_card_html(c, i) for i, c in enumerate(cases))

    return (
        _HEAD
        + '<div class="wrap">'
        + '<header class="masthead">'
        + '<h1 class="wordmark">corrosim</h1>'
        + '<p class="lede">Each report is a full corrosim screening (DFT '
          'reactivity, adsorption, and molecular dynamics), validated against a '
          'published corrosion-inhibitor study.</p>'
        + '</header>'
        + f'<main class="grid">{cards}</main>'
        + '<footer class="colophon">'
        + '<p>Each report is self-contained HTML rendered by '
          '<code>corrosim</code>. Source and method on '
          f'<a href="{_REPO}">GitHub</a>; per-case validation in '
          f'<a href="{_REPO}/blob/main/docs/validation.md">validation.md</a>.'
          '</p>'
        + '</footer>'
        + '</div></body></html>'
    )


def assemble_site(
    out_dir: str,
    cases: Iterable[CaseStudy] | None = None,
) -> list[str]:
    """Build the Pages site: copy each report and write the gallery index.

    A case whose report is not rendered yet is skipped, so the index never links
    a missing file.

    Args:
        out_dir: Destination directory for the site (created if absent).
        cases: The case studies to publish; defaults to every registered study.

    Returns:
        The names of the cases actually published, in order.
    """
    studies = list(cases) if cases is not None else unique_cases()
    os.makedirs(out_dir, exist_ok=True)

    # copy only the cases whose self-contained report exists
    shipped = []
    for case in studies:
        src = _report_path(case)
        if not os.path.exists(src):
            continue
        shutil.copyfile(src, os.path.join(out_dir, f"{case.name}.html"))
        shipped.append(case)

    index = build_index_html(shipped)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index)
    return [c.name for c in shipped]


# The document head + all styling. Kept as one constant (no interpolation) so
# the CSS braces never collide with the f-strings that build the body.
_HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>corrosim — validation gallery</title>
<meta name="description" content="corrosim screenings validated against published corrosion-inhibitor studies.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;450;500&display=swap" rel="stylesheet">
<style>
  /* White canvas; each card accented by its substrate metal (steel-blue Fe,
     copper Cu, aluminium Al); badges green (validated) / amber (partial). Light
     is the default; dark keeps the same accents on a near-black ground. */
  :root {
    --bg: #f5f6f7; --panel: #ffffff; --ink: #16191c; --muted: #55606a;
    --faint: #8b949c; --line: #e5e7ea;
    --fe: #4d6f8a; --cu: #a9662f; --al: #6f7c85;
    --ok: #2f9d68; --ok-bg: rgba(47,157,104,.10);
    --warn: #b5811f; --warn-bg: rgba(181,129,31,.12);
    --display: "Fraunces", Georgia, "Times New Roman", serif;
    --mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, monospace;
    --sans: "IBM Plex Sans", system-ui, sans-serif;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0e0f12; --panel: #17191d; --ink: #f1f3f5; --muted: #9aa3ab;
      --faint: #69717a; --line: #24272c;
      --fe: #6f92ad; --cu: #cc8a54; --al: #a9b6bd;
      --ok: #63c08d; --ok-bg: rgba(99,192,141,.14);
      --warn: #d8a94f; --warn-bg: rgba(216,169,79,.13);
    }
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: var(--sans); font-weight: 400;
    line-height: 1.55; letter-spacing: .002em;
    -webkit-font-smoothing: antialiased;
    background-image:
      radial-gradient(900px 460px at 50% -8%, rgba(77,111,138,.06), transparent 62%),
      linear-gradient(to right, var(--line) 1px, transparent 1px),
      linear-gradient(to bottom, var(--line) 1px, transparent 1px);
    background-size: 100% 100%, 46px 46px, 46px 46px;
    background-attachment: fixed, fixed, fixed;
  }
  @media (prefers-color-scheme: dark) {
    body { background-image:
      radial-gradient(900px 460px at 50% -8%, rgba(111,146,173,.10), transparent 62%),
      linear-gradient(to right, var(--line) 1px, transparent 1px),
      linear-gradient(to bottom, var(--line) 1px, transparent 1px); }
  }
  .wrap { max-width: 1120px; margin: 0 auto; padding: 0 clamp(1.1rem, 4vw, 2.5rem); }
  .masthead { padding: clamp(2.4rem, 6vw, 4.2rem) 0 clamp(1.6rem, 4vw, 2.6rem); }
  .wordmark {
    font-family: var(--display); font-weight: 600;
    font-size: clamp(3.4rem, 12vw, 6.5rem); line-height: .92;
    letter-spacing: -.02em; margin: 0; color: var(--ink);
  }
  @supports (-webkit-background-clip: text) or (background-clip: text) {
    .wordmark {
      background: linear-gradient(180deg, var(--ink), color-mix(in oklab, var(--ink) 62%, var(--muted)));
      -webkit-background-clip: text; background-clip: text; color: transparent;
    }
  }
  .lede {
    max-width: 46ch; margin: 1.3rem 0 0; color: var(--muted);
    font-size: clamp(1rem, 2.1vw, 1.16rem); line-height: 1.5;
  }
  .dotsep { color: var(--faint); padding: 0 .15em; }
  .grid {
    display: grid; gap: 1.15rem;
    grid-template-columns: repeat(auto-fill, minmax(325px, 1fr));
    padding-bottom: 3rem;
  }
  .case {
    position: relative; display: flex; flex-direction: column;
    background: var(--panel); border: 1px solid var(--line);
    border-radius: 12px; padding: 1.5rem 1.45rem 1.35rem;
    text-decoration: none; color: inherit; overflow: hidden;
    transition: transform .28s cubic-bezier(.2,.7,.2,1),
                box-shadow .28s, border-color .28s;
    opacity: 0; transform: translateY(14px);
    animation: rise .7s cubic-bezier(.2,.7,.2,1) forwards;
  }
  .case__bar {
    position: absolute; inset: 0 0 auto 0; height: 3px; background: var(--accent);
    opacity: .9;
  }
  .case:hover {
    transform: translateY(-5px);
    border-color: color-mix(in oklab, var(--accent) 55%, var(--line));
    box-shadow: 0 20px 44px -26px rgba(20,30,45,.28),
                0 0 0 1px color-mix(in oklab, var(--accent) 26%, transparent);
  }
  .case__head {
    display: flex; align-items: center; justify-content: space-between;
    gap: .6rem; margin-bottom: 1rem;
  }
  .chip {
    font-family: var(--mono); font-size: .74rem; font-weight: 500;
    letter-spacing: .04em; color: var(--accent);
    border: 1px solid color-mix(in oklab, var(--accent) 40%, var(--line));
    background: color-mix(in oklab, var(--accent) 9%, transparent);
    padding: .16rem .5rem; border-radius: 6px; white-space: nowrap;
  }
  .badge {
    display: inline-flex; align-items: center; gap: .4em;
    font-family: var(--mono); font-size: .68rem; letter-spacing: .02em;
    padding: .18rem .5rem; border-radius: 999px; white-space: nowrap;
  }
  .badge .dot { width: .46em; height: .46em; border-radius: 50%; }
  .badge--ok { color: var(--ok); background: var(--ok-bg); }
  .badge--ok .dot { background: var(--ok); }
  .badge--partial { color: var(--warn); background: var(--warn-bg); }
  .badge--partial .dot { background: var(--warn); }
  .case__title {
    font-family: var(--display); font-weight: 600;
    font-size: 1.42rem; line-height: 1.12; letter-spacing: -.01em;
    margin: 0 0 .5rem;
  }
  .case__meta {
    font-family: var(--mono); font-size: .78rem; color: var(--muted);
    margin: 0 0 .85rem;
  }
  .case__desc {
    font-size: .92rem; color: var(--muted); margin: 0 0 1.1rem;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .case__ref {
    margin: 0 0 1.2rem; padding-top: .95rem;
    border-top: 1px solid var(--line);
  }
  .case__ref-label {
    display: block; font-family: var(--mono); font-size: .62rem;
    letter-spacing: .16em; text-transform: uppercase; color: var(--faint);
    margin-bottom: .35rem;
  }
  .case__ref-src {
    font-family: var(--mono); font-size: .69rem; line-height: 1.5;
    color: var(--muted);
  }
  .case__cta {
    margin-top: auto; font-family: var(--mono); font-size: .8rem;
    font-weight: 500; color: var(--accent);
    display: inline-flex; align-items: center; gap: .45em;
  }
  .arrow { transition: transform .25s; }
  .case:hover .arrow { transform: translateX(4px); }
  .colophon {
    border-top: 1px solid var(--line); padding: 2rem 0 3.5rem;
    color: var(--faint); font-size: .84rem;
  }
  .colophon a { color: var(--muted); text-decoration: none;
    border-bottom: 1px solid var(--line); }
  .colophon a:hover { color: var(--ink); border-color: var(--muted); }
  .colophon code { font-family: var(--mono); font-size: .9em; color: var(--muted); }
  @keyframes rise { to { opacity: 1; transform: none; } }
  @media (prefers-reduced-motion: reduce) {
    .case { animation: none; opacity: 1; transform: none; }
    .arrow, .case { transition: none; }
  }
</style>
</head>
<body>
"""
