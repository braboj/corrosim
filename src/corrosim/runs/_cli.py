"""Shared CLI plumbing for the ``corrosim.runs`` drivers.

The driver scripts (run_dft / run_fukui / run_mc / run_md / run_pka /
make_report / make_figures / make_cubes / compare_geometry) repeated the same
argument parsing, molecule-list splitting, stderr logging, JSON I/O and table
printing. This module single-sources that boilerplate (issue #64) so each
driver stays focused on its pipeline stage. The JSON helpers also close their
file handles via ``with`` (the inline ``open(...)`` calls did not).
"""
from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterable
from typing import Any

from corrosim.presets import ARGHEL

# Sentinel distinguishing "no default given" (missing file -> raise) from an
# explicit default of None in :func:`read_json`.
_REQUIRED = object()


def add_molecules_arg(parser: Any) -> None:
    """Add the shared ``--molecules`` argument (the Arghel set as default).

    Args:
        parser: The argparse parser (or group) to add the argument to.
    """
    parser.add_argument(
        "--molecules", default=",".join(ARGHEL.molecule_list()),
        help="Comma-separated molecule names or SMILES.")


def parse_molecules(spec: str) -> list[str]:
    """Split a comma-separated ``--molecules`` value into clean names.

    Args:
        spec: The raw ``--molecules`` string, e.g. ``"quercetin, kaempferol"``.

    Returns:
        The non-empty, stripped molecule names/SMILES, order preserved.
    """
    return [m.strip() for m in spec.split(",") if m.strip()]


def stderr_log(msg: str) -> None:
    """Print a progress/diagnostic message to stderr (keeps stdout data-clean).

    Args:
        msg: The message to write.
    """
    print(msg, file=sys.stderr)


def write_json(path: str, obj: Any) -> None:
    """Write ``obj`` as indented JSON to ``path``, closing the file handle.

    Args:
        path: Destination file path.
        obj: Any JSON-serialisable object.
    """
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2)


def read_json(path: str, default: Any = _REQUIRED) -> Any:
    """Load JSON from ``path``, closing the file handle.

    Args:
        path: Source file path.
        default: Value to return when ``path`` does not exist. If omitted, a
            missing file propagates the usual ``FileNotFoundError``.

    Returns:
        The decoded JSON, or ``default`` when the file is absent.
    """
    if default is not _REQUIRED and not os.path.exists(path):
        return default
    with open(path) as fh:
        return json.load(fh)


def print_table(data: Any, columns: Iterable[str] | None = None,
                round_to: int | None = None) -> None:
    """Print rows as a plain, index-free table (the drivers' stdout summary).

    Args:
        data: A pandas ``DataFrame`` or a list of row dicts.
        columns: Columns to show, in order; ``None`` shows all.
        round_to: Decimal places to round numeric columns to; ``None`` leaves
            values untouched.
    """
    import pandas as pd

    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    if columns is not None:
        df = df[list(columns)]
    if round_to is not None:
        df = df.round(round_to)
    print(df.to_string(index=False))


def strip_protonation_suffix(names: Any) -> Any:
    """Strip the trailing ``+H+`` protonation tag from molecule names.

    Args:
        names: A pandas ``Series`` of molecule names (some tagged ``<name>+H+``).

    Returns:
        The Series with the ``+H+`` suffix removed, so cations map to their base.
    """
    return names.str.replace(r"\+H\+$", "", regex=True)


__all__ = [
    "add_molecules_arg",
    "parse_molecules",
    "stderr_log",
    "write_json",
    "read_json",
    "print_table",
    "strip_protonation_suffix",
]
