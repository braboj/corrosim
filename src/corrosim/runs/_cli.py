"""Shared CLI plumbing for the ``corrosim.runs`` drivers.

The driver scripts (run_dft / run_fukui / run_mc / run_md / run_pka /
make_report / make_figures / make_cubes / compare_geometry) repeated the same
argument parsing, molecule-list splitting, stderr logging, JSON I/O and table
printing. This module single-sources that boilerplate (issue #64) so each
driver stays focused on its pipeline stage. The JSON helpers also close their
file handles via ``with`` (the inline ``open(...)`` calls did not).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from corrosim.presets import CaseStudy, case_study

if TYPE_CHECKING:
    import pandas as pd

# Sentinel distinguishing "no default given" (missing file -> raise) from an
# explicit default of None in :func:`read_json`.
_REQUIRED = object()

# The case study a driver screens when --case is not given.
_DEFAULT_CASE = "arghel"


def add_case_arg(parser: argparse.ArgumentParser) -> None:
    """Add the shared ``--case`` argument (selects a named case study).

    Args:
        parser: The argparse parser to add the argument to.
    """
    parser.add_argument(
        "--case", default=_DEFAULT_CASE,
        help="Named case study from presets.CASE_STUDIES (default: arghel); "
             "its molecule set / metal / medium fill any unset "
             "--molecules / --metal / --medium.")


def add_molecules_arg(parser: argparse.ArgumentParser) -> None:
    """Add the shared ``--molecules`` argument (unset -> the case-study set).

    Args:
        parser: The argparse parser to add the argument to.
    """
    parser.add_argument(
        "--molecules", default=None,
        help="Comma-separated molecule names or SMILES; unset uses the "
             "--case study's set.")


def resolve_case(args: argparse.Namespace, metal: str = "label") -> CaseStudy:
    """Resolve ``--case`` and backfill unset molecule/metal/medium arguments.

    Reads ``args.case`` and fills ``args.molecules``, ``args.metal`` and
    ``args.medium`` from that case study wherever the driver left them unset,
    so an explicit flag always overrides the case default.

    Args:
        args: The parsed argument namespace (mutated in place).
        metal: ``"label"`` fills ``args.metal`` with the facet label
            (``Fe(110)``); ``"element"`` fills the bare symbol (``Fe``) used by
            the slab/RDF drivers.

    Returns:
        The resolved case study.
    """
    case = case_study(getattr(args, "case", _DEFAULT_CASE))
    if hasattr(args, "molecules") and args.molecules is None:
        args.molecules = ",".join(case.molecule_list())
    if hasattr(args, "metal") and args.metal is None:
        args.metal = case.metal if metal == "label" else case.metal_element
    if hasattr(args, "medium") and args.medium is None:
        args.medium = case.medium
    return case


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


def write_json(path: str, obj: object) -> None:
    """Write ``obj`` as indented JSON to ``path``, closing the file handle.

    Args:
        path: Destination file path.
        obj: Any JSON-serialisable object.
    """
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2)


# ``default``/return are the decoded JSON payload — genuinely dynamic, so the
# return is the one justified ``Any`` in this module.
def read_json(path: str, default: object = _REQUIRED) -> Any:  # noqa: ANN401
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


def print_table(data: pd.DataFrame | list[dict[str, object]],
                columns: Iterable[str] | None = None,
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


def strip_protonation_suffix(names: pd.Series) -> pd.Series:
    """Strip the trailing ``+H+`` protonation tag from molecule names.

    Args:
        names: A pandas ``Series`` of molecule names (some tagged
            ``<name>+H+``).

    Returns:
        The Series with the ``+H+`` suffix removed, so cations map to their
        base name.
    """
    return names.str.replace(r"\+H\+$", "", regex=True)


__all__ = [
    "add_case_arg",
    "add_molecules_arg",
    "resolve_case",
    "parse_molecules",
    "stderr_log",
    "write_json",
    "read_json",
    "print_table",
    "strip_protonation_suffix",
]
