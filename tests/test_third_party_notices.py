"""The third-party NOTICE file exists, names every redistributed dependency,
and is shipped inside the published QM image.

The QM container redistributes weak-copyleft packages (``ase`` LGPL-2.1+,
``tblite`` LGPL-3.0+) alongside permissive ones, which carries an attribution
obligation. These checks guard the two ways that attribution silently rots: a
new core or ``qm`` dependency added to ``pyproject.toml`` without a matching
notice entry, and the notice no longer being copied into the image.
"""
from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
NOTICE = (REPO / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
PYPROJECT = (REPO / "pyproject.toml").read_text(encoding="utf-8")
DOCKERFILE = (REPO / "Dockerfile").read_text(encoding="utf-8")


def _package_names(block: str) -> set[str]:
    """Return the base package names quoted inside a pyproject array slice.

    Strips any version, extras, or environment-marker suffix so only the
    distribution name remains.

    Args:
        block: The text between the ``[`` and ``]`` of a dependency array.

    Returns:
        Lower-cased distribution names found in the block.
    """
    names = set()
    for spec in re.findall(r'"([^"]+)"', block):
        name = re.split(r"[<>=!~;\[ ]", spec, maxsplit=1)[0].strip()
        if name:
            names.add(name.lower())
    return names


def _redistributed_packages() -> set[str]:
    """Return the core plus ``qm``-extra packages baked into the QM image."""
    core = re.search(r"^dependencies = \[(.*?)\]", PYPROJECT, re.S | re.M)
    qm = re.search(r"^qm = \[(.*?)\]", PYPROJECT, re.S | re.M)
    assert core and qm, "could not locate the dependency arrays in pyproject"
    return _package_names(core.group(1)) | _package_names(qm.group(1))


def test_notice_names_every_redistributed_dependency():
    notice = NOTICE.lower()
    missing = [
        pkg
        for pkg in _redistributed_packages()
        if not re.search(rf"\b{re.escape(pkg)}\b", notice)
    ]
    assert not missing, f"THIRD_PARTY_NOTICES.md omits: {missing}"


def test_notice_records_the_lgpl_obligations():
    # the two weak-copyleft packages are the actual compliance drivers
    assert re.search(r"\btblite\b", NOTICE)
    assert re.search(r"\base\b", NOTICE, re.I)
    assert "LGPL-2.1" in NOTICE
    assert "LGPL-3.0" in NOTICE


def test_dockerfile_ships_the_notice_in_the_image():
    assert re.search(
        r"^COPY\s+THIRD_PARTY_NOTICES\.md\s+/", DOCKERFILE, re.M
    ), "the Dockerfile must COPY THIRD_PARTY_NOTICES.md into the image"
