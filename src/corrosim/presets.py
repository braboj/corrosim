"""corrosim.presets.

Named **case studies** — the molecule set + substrate + medium for a screening
run, defined in *one* place instead of duplicated across the drivers.

A `CaseStudy` ties together what to screen (`molecules`, by library name or
SMILES), on what (`metal`, a `descriptors.METAL_WORK_FUNCTION` label), in what
(`medium`, a report label that also motivates the protonated-cation modelling).

The shipped study is `ARGHEL` — the major *Solenostemma argel* flavonoid
aglycones on mild steel in 1 M HCl. The run drivers default to it; point them
at a different `CaseStudy` (or pass `--molecules/--metal`) to screen something
else.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CaseStudy:
    """A named screening case study: molecule set + substrate metal + medium."""

    name: str
    # library names or SMILES, in display order
    molecules: tuple[str, ...]
    # work-function / slab substrate label
    metal: str = "Fe(110)"
    # report label; implies the acidic (protonated) species
    medium: str = "1 M HCl"
    description: str = ""

    @property
    def metal_element(self) -> str:
        """Bare element symbol for the slab/RDF code.

        Returns:
            The metal symbol with any facet suffix stripped, e.g.
            ``Fe(110)`` -> ``Fe``.
        """
        return self.metal.split("(")[0].strip()

    def molecule_list(self) -> list[str]:
        """Return a fresh mutable copy of the molecule set.

        Returns:
            The molecule names/SMILES as a new list, so a driver can iterate
            or extend it without mutating the frozen preset.
        """
        return list(self.molecules)


# --- The shipped case study ------------------------------------------------
ARGHEL = CaseStudy(
    name="arghel",
    molecules=("kaempferol", "quercetin", "isorhamnetin"),
    metal="Fe(110)",
    medium="1 M HCl",
    description="Major Arghel (Solenostemma argel) flavonoid aglycones vs mild "
                "steel (Fe(110)) in 1 M HCl.",
)

CASE_STUDIES: dict[str, CaseStudy] = {"arghel": ARGHEL, "argel": ARGHEL}


def case_study(name: str) -> CaseStudy:
    """Look up a named case study by its (case-insensitive) name.

    Args:
        name: The case-study key, e.g. ``"arghel"`` (aliases accepted).

    Returns:
        The matching :class:`CaseStudy`.

    Raises:
        KeyError: If no case study is registered under ``name``.
    """
    key = name.strip().lower()
    if key not in CASE_STUDIES:
        raise KeyError(f"Unknown case study {name!r}. "
                       f"Known: {sorted(set(CASE_STUDIES))}.")
    return CASE_STUDIES[key]
