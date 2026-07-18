"""Shared CLI plumbing for the ``corrosim.runs`` drivers.

The driver scripts (run_dft / run_fukui / run_mc / run_md / run_pka /
make_report / make_figures / make_cubes / compare_geometry) repeated the same
argument parsing, molecule-list splitting, stderr logging, JSON I/O and table
printing. This module single-sources that boilerplate so each
driver stays focused on its pipeline stage. The JSON helpers also close their
file handles via ``with`` (the inline ``open(...)`` calls did not).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Iterable, Iterator, Sequence
from typing import TYPE_CHECKING, Any

from corrosim.presets import CaseStudy, case_study

if TYPE_CHECKING:
    import pandas as pd

    from corrosim.molecules import Molecule

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
        help="Named case study from presets.CASE_STUDIES (default: arghel), or "
             "a path to a study JSON file; its molecule set / metal / medium "
             "fill any unset --molecules / --metal / --medium.")


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
    """Resolve ``--case`` and backfill unset case-derived arguments.

    Reads ``args.case`` and fills ``args.molecules``, ``args.metal``,
    ``args.medium`` and the DFT level (``args.basis`` / ``args.xc`` /
    ``args.density_fit``) from that case study wherever the driver left them
    unset, so an explicit flag always overrides the case default. Each backfill
    is guarded by ``hasattr`` and a ``None`` check, so only drivers that expose
    the flag with a ``None`` default opt in (a driver whose ``--basis`` carries
    its own small default keeps it).

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
    if hasattr(args, "basis") and args.basis is None:
        args.basis = case.basis
    if hasattr(args, "xc") and args.xc is None:
        args.xc = case.xc
    if hasattr(args, "density_fit") and args.density_fit is None:
        args.density_fit = case.density_fit
    return case


def default_output(
    args: argparse.Namespace,
    attr: str,
    value: str,
) -> None:
    """Backfill an unset output-path argument from the case's own directory.

    The run drivers default their ``--out*`` / ``--outdir`` / ``--datadir``
    flags to ``None`` so an explicit flag always wins; this fills the ones left
    unset with the per-case default, keeping each study's output under its own
    ``cases/<case>/`` subtree instead of a shared root.

    Args:
        args: The parsed argument namespace (mutated in place).
        attr: The argument attribute name, e.g. ``"outdir"``.
        value: The per-case default path to use when ``attr`` is unset.
    """
    if getattr(args, attr, None) is None:
        setattr(args, attr, value)


def parse_molecules(spec: str) -> list[str]:
    """Split a comma-separated ``--molecules`` value into clean names.

    Args:
        spec: The raw ``--molecules`` string, e.g. ``"quercetin, kaempferol"``.

    Returns:
        The non-empty, stripped molecule names/SMILES, order preserved.
    """
    return [m.strip() for m in spec.split(",") if m.strip()]


# Filesystem-unsafe characters for a single path component: the path
# separators, the Windows-reserved set, and control characters.
_UNSAFE_PATH_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def safe_path_component(name: str) -> str:
    r"""Sanitise a molecule name/SMILES for use as a filesystem path component.

    A non-library ``--molecules`` entry is used verbatim as its own name, and
    isomeric SMILES routinely carry ``/`` and ``\\`` (E/Z stereo, e.g.
    ``C/C=C/C``), so a raw name can inject path separators — or Windows-reserved
    characters — into an output path and break the write with a
    ``FileNotFoundError`` on a directory that was never created. Replace every
    unsafe character with ``_`` so the name stays a single, safe component; a
    name that sanitises to nothing falls back to ``"molecule"``.

    Args:
        name: The molecule library name or SMILES.

    Returns:
        A safe single path component (never empty, never a separator).
    """
    safe = _UNSAFE_PATH_CHARS.sub("_", name).strip()

    # An all-unsafe name collapses to underscores only (or nothing); fall back
    # to a stable stub rather than yield a separator-free but meaningless "___".
    if not safe.strip("_"):
        return "molecule"
    return safe


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


def form_rows_in_order(
    df: pd.DataFrame,
    form: str,
    order: Sequence[str],
    phase: str = "aqueous",
) -> pd.DataFrame:
    """Select one ``(form, phase)`` block, keyed by base name, in ``order``.

    Filters ``df`` to the given form and phase, strips the ``+H+`` protonation
    suffix to a base molecule name, keeps only the molecules named in ``order``
    that are actually present, and returns them in ``order`` — the row-selection
    the descriptor consumers (make_report, compare_geometry) share. Works for
    both neutral and protonated rows: a neutral name has no suffix, so its base
    is itself.

    Args:
        df: A descriptor matrix with ``form`` / ``phase`` / ``name`` columns.
        form: The species form, e.g. ``"neutral"`` or ``"protonated"``.
        order: The base molecule names to keep, and the order to return them in.
        phase: The phase to select (``"aqueous"`` or ``"gas"``).

    Returns:
        The selected rows as a DataFrame indexed by base molecule name, in
        ``order``; the original columns (including the suffixed ``name``) are
        retained.
    """
    sub = df[(df.form == form) & (df.phase == phase)].copy()
    sub["_base"] = strip_protonation_suffix(sub["name"])
    present = [n for n in order if n in set(sub["_base"])]
    return sub.set_index("_base").loc[present]


def iter_molecules(args: argparse.Namespace) -> Iterator[tuple[str, Molecule]]:
    """Yield ``(name, molecule)`` for each ``--molecules`` entry.

    Ensures ``args.outdir`` exists, then builds each molecule from the parsed
    ``--molecules`` list — the shared open of the run_mc / run_md / run_fukui
    per-molecule loops.

    Args:
        args: Parsed CLI arguments; reads ``args.outdir`` and
            ``args.molecules``.

    Returns:
        An iterator of ``(name, molecule)`` pairs, in ``--molecules`` order.
    """
    from corrosim import build_molecule
    os.makedirs(args.outdir, exist_ok=True)
    for name in parse_molecules(args.molecules):
        yield name, build_molecule(name)


__all__ = [
    "add_case_arg",
    "add_molecules_arg",
    "resolve_case",
    "default_output",
    "parse_molecules",
    "safe_path_component",
    "stderr_log",
    "write_json",
    "read_json",
    "print_table",
    "strip_protonation_suffix",
    "form_rows_in_order",
    "iter_molecules",
]
