"""corrosim.runs.make_pages.

Build the static GitHub Pages gallery: copy each case's self-contained report
into the site directory and generate the index that links them. The case set is
read from ``presets``, so a newly added case appears in the gallery with no edit
here.

::

    presets.CASE_STUDIES --> report.gallery.assemble_site --> <out>/index.html
                                                              <out>/<name>.html
"""
from __future__ import annotations

import argparse
from collections.abc import Sequence

from corrosim.report.gallery import assemble_site, unique_cases
from corrosim.runs._cli import stderr_log


def _build_parser() -> argparse.ArgumentParser:
    """Construct the make_pages argument parser.

    Returns:
        The configured argument parser.
    """
    p = argparse.ArgumentParser(
        prog="make_pages",
        description="Build the static Pages gallery of the case reports.")
    p.add_argument(
        "--out", default="_site",
        help="Output site directory (default: _site).")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: assemble the Pages gallery site.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv``).

    Returns:
        The process exit code (0 on success).
    """
    args = _build_parser().parse_args(argv)

    all_names = [c.name for c in unique_cases()]
    shipped = assemble_site(args.out)

    stderr_log(f"gallery: {len(shipped)} case(s) -> {args.out}/index.html")
    skipped = [n for n in all_names if n not in shipped]
    if skipped:
        stderr_log(
            f"gallery: skipped (no rendered report): {', '.join(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
