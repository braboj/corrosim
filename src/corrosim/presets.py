"""corrosim.presets.

Named **case studies** — the molecule set + substrate + medium for a screening
run, defined in *one* place instead of duplicated across the drivers.

A `CaseStudy` ties together what to screen (`molecules`, by library name or
SMILES), on what (`metal`, a `descriptors.METAL_WORK_FUNCTION` label), in what
(`medium`, a report label that also motivates the protonated-cation modelling).

The shipped study is `ARGHEL` — the major *Solenostemma argel* flavonoid
aglycones on mild steel in 1 M HCl. The run drivers default to it; point them
at a different `CaseStudy` (`--case`, or pass `--molecules/--metal`) to screen
something else.

Alongside it are **validation presets** — each reproduces a published study's
system (its `source` names the paper) so the computed descriptors / adsorption
can be checked against that paper's reported values in `docs/validation.md`.
"""
from __future__ import annotations

from dataclasses import dataclass


def metal_element(metal: str) -> str:
    """Bare element symbol from a possibly facet-qualified metal label.

    The single home for the facet strip (kept here, a stdlib-only leaf, so the
    slab/report/facade code can share it without a heavy import).

    Args:
        metal: A metal label, optionally facet-qualified (e.g. ``"Fe(110)"``).

    Returns:
        The element symbol before any facet suffix (e.g. ``"Fe"``).
    """
    return metal.split("(")[0].strip()


@dataclass(frozen=True)
class CaseStudy:
    """A named screening case study: molecule set + substrate metal + medium."""

    name: str
    # Library names or SMILES, in display order
    molecules: tuple[str, ...]
    # Work-function / slab substrate label
    metal: str = "Fe(110)"
    # Report label; implies the acidic (protonated) species
    medium: str = "1 M HCl"
    description: str = ""
    # Provenance: the paper/thesis this system reproduces (citation or DOI).
    # Empty for an original screen; set for a validation preset so the reported
    # target values in docs/validation.md are traceable to their source.
    source: str = ""
    # Conjugate-acid pKaH of the inhibitor's most basic protonation site: the
    # value that drives Henderson-Hasselbalch speciation in an acidic medium.
    # Defaults to a very-weak-base estimate (~-1.5), so an inhibitor whose basic
    # site is unspecified is treated as ~all-neutral in mild acid; override per
    # study when the basic site is stronger.
    pkah: float = -1.5

    @property
    def metal_element(self) -> str:
        """Bare element symbol for the slab/RDF code.

        Returns:
            The metal symbol with any facet suffix stripped, e.g.
            ``Fe(110)`` -> ``Fe``.
        """
        return metal_element(self.metal)

    @property
    def case_dir(self) -> str:
        """Co-location root for everything this study produces.

        Both the computed data and the rendered report nest under this one
        directory, so a whole study can be browsed, shared, or removed as a
        unit and the owning study is visible from every output path (no
        unlabelled study at a shared ``results/``/``report/`` root).

        Returns:
            ``cases/<name>``, e.g. ``cases/arghel``.
        """
        return f"cases/{self.name}"

    @property
    def results_dir(self) -> str:
        """Per-case directory for computed data (descriptors, MC, MD, pKa).

        The tracked *source data* half of :attr:`case_dir`; the report is
        rendered from it.

        Returns:
            ``cases/<name>/results``, e.g. ``cases/arghel/results``.
        """
        return f"{self.case_dir}/results"

    @property
    def report_dir(self) -> str:
        """Per-case directory for the report bundle.

        The regenerable *deliverable* half of :attr:`case_dir`: the bundle
        (``report.html`` / ``report.docx`` / ``figures/`` / ``tables/``). A
        validation cross-check leaves it unpopulated; the shipped study renders
        into it.

        Returns:
            ``cases/<name>/report``, e.g. ``cases/arghel/report``.
        """
        return f"{self.case_dir}/report"

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
    # Flavonoid 4-oxo carbonyl, a very weak base; carbonyl-protonation pKaH
    # clusters around -1 to -2 (Hammett-acidity studies). An ESTIMATE (~+/-1).
    pkah=-1.5,
    description="Major Arghel (Solenostemma argel) flavonoid aglycones vs mild "
                "steel (Fe(110)) in 1 M HCl.",
    source="Mohammed, Corrosion Inhibition of Steel in Acidic Medium by Herbs "
           "Extract (MSc, Alexandria University, 2014); constituents from "
           "El-Shiekh et al., Bull. Fac. Pharm. Cairo Univ. 2024.",
)

# --- Validation presets ----------------------------------------------------
# Each reproduces a published simulation study's system so the computed
# descriptors / adsorption can be checked against the paper's reported values
# (recorded in docs/validation.md). Each study writes under its own
# cases/<case> subtree, so the presets never collide.
PHYTIC_ACID = CaseStudy(
    name="phytic-acid",
    molecules=("phytic acid",),
    metal="Fe(110)",
    medium="0.5 M H2SO4",
    description="Phytic acid vs Q235 mild steel (Fe(110)) in 0.5 M H2SO4 — the "
                "fully experiment-validated Chidiebere (2014) DFT+MD anchor; "
                "exercises the sulfuric-acid medium and a non-flavonoid "
                "inhibitor.",
    source="Chidiebere, Oguzie, Liu, Li, Wang, Corrosion Inhibition of Q235 "
           "Mild Steel in 0.5 M H2SO4 Solution by Phytic Acid and Synergistic "
           "Iodide Additives, Ind. Eng. Chem. Res. 2014, 53, 7670-7679 "
           "(DOI 10.1021/ie404382v).",
)

CASE_STUDIES: dict[str, CaseStudy] = {
    "arghel": ARGHEL,
    "argel": ARGHEL,
    "phytic-acid": PHYTIC_ACID,
    "phytic_acid": PHYTIC_ACID,
    "phytic": PHYTIC_ACID,
}


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
