"""corrosim.presets.

Named **case studies** — the molecule set + substrate + medium for a screening
run, defined in *one* place instead of duplicated across the drivers.

A `CaseStudy` ties together what to screen (`molecules`, by library name or
SMILES), on what (`metal`, a `descriptors.METAL_WORK_FUNCTION` label), in what
(`medium`, a report label that also motivates the protonated-cation modelling).

The shipped study is `ARGHEL` — the major *Solenostemma argel* flavonoid
aglycones on mild steel in 1 M HCl. The run drivers default to it; point them at
a different `CaseStudy` (or pass `--molecules/--metal`) to screen something else.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CaseStudy:
    """A named screening case study: molecule set + substrate metal + medium."""

    name: str
    molecules: tuple[str, ...]      # library names or SMILES, in display order
    metal: str = "Fe(110)"          # work-function / slab substrate label
    medium: str = "1 M HCl"         # report label; implies the acidic (protonated) species
    description: str = ""

    @property
    def metal_element(self) -> str:
        """The bare element symbol for slab/RDF code: 'Fe(110)' -> 'Fe'."""
        return self.metal.split("(")[0].strip()

    def molecule_list(self) -> list[str]:
        """Mutable copy of the molecule set (drivers iterate / extend it)."""
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
    """Look up a named case study (e.g. 'arghel'). Raises KeyError if unknown."""
    key = name.strip().lower()
    if key not in CASE_STUDIES:
        raise KeyError(f"Unknown case study {name!r}. "
                       f"Known: {sorted(set(CASE_STUDIES))}.")
    return CASE_STUDIES[key]
