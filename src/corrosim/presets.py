"""corrosim.presets.

Named **case studies** — the molecule set + substrate + medium for a screening
run, defined in *one* place instead of duplicated across the drivers.

A `CaseStudy` ties together what to screen (`molecules`, by library name or
SMILES), on what (`metal`, a `descriptors.METAL_WORK_FUNCTION` label), in what
(`medium`, a report label that also motivates the protonated-cation modelling).

The study the drivers **default** to is `ARGHEL` — the major *Solenostemma
argel* flavonoid aglycones on mild steel in 1 M HCl. Point the drivers at a
different `CaseStudy` (`--case`, or pass `--molecules/--metal`) to screen
something else.

Every case study here is a **validation** study, `ARGHEL` included: its
`source` names the published paper it reproduces, so the computed descriptors /
adsorption can be checked against that paper's reported values in
`docs/validation.md`. The cases defined below `ARGHEL` are the additional
studies the drivers can screen with `--case`.
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

    # DFT level of theory for the production single points (run_dft / run_pka):
    # the AO basis and exchange-correlation functional the drivers use when
    # --basis / --xc are left unset, keeping the level a per-case property of
    # the single source of truth. Defaults are corrosim's adopted production
    # level, B3LYP/6-311++G(d,p); a case overrides the basis when the diffuse
    # (++) production set is intractable for its molecules (see PHYTIC_ACID).
    basis: str = "6-311++G(d,p)"
    xc: str = "b3lyp"

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
        (``report.html`` / ``report.docx`` / ``figures/`` / ``tables/``) the
        study's report renders into.

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


# --- The default case study (drivers default to it) ------------------------
ARGHEL = CaseStudy(
    name="arghel",
    molecules=("kaempferol", "quercetin", "isorhamnetin"),
    metal="Fe(110)",
    medium="1 M HCl",

    # Flavonoid 4-oxo carbonyl, a very weak base; carbonyl-protonation pKaH
    # clusters around -1 to -2 (Hammett-acidity studies). An ESTIMATE (~+/-1).
    pkah=-1.5,

    # Level of theory stated explicitly so the case self-documents it, as every
    # case study does (here the adopted production B3LYP/6-311++G(d,p), equal to
    # the CaseStudy default).
    basis="6-311++G(d,p)",
    xc="b3lyp",

    description="Major Arghel (Solenostemma argel) flavonoid aglycones vs mild "
                "steel (Fe(110)) in 1 M HCl.",

    source="Mohammed, Corrosion Inhibition of Steel in Acidic Medium by Herbs "
           "Extract (MSc, Alexandria University, 2014); constituents from "
           "El-Shiekh et al., Bull. Fac. Pharm. Cairo Univ. 2024.",
)

# --- Additional validation case studies ------------------------------------
# Like ARGHEL, each reproduces a published study's system so the computed
# descriptors / adsorption can be checked against the paper's reported values
# (recorded in docs/validation.md). Each writes under its own cases/<case>
# subtree, so the studies never collide.
PHYTIC_ACID = CaseStudy(
    name="phytic-acid",
    molecules=("phytic acid",),
    metal="Fe(110)",
    medium="0.5 M H2SO4",

    # Production B3LYP is kept; only the basis is dropped from the diffuse
    # 6-311++G(d,p), which is intractable here: phytic acid folds its six
    # phosphates inward (Rg ~4 A), packing 24 oxygens close together, so the
    # diffuse (++) functions drive near-linear-dependence in the overlap matrix
    # and the SCF diverges. The non-diffuse 6-31G(d) converges; the comparison
    # vs the paper's AM1 is qualitative anyway.
    basis="6-31G(d)",
    xc="b3lyp",

    description="Phytic acid vs Q235 mild steel (Fe(110)) in 0.5 M H2SO4 — the "
                "fully experiment-validated Chidiebere (2014) DFT+MD anchor; "
                "exercises the sulfuric-acid medium and a non-flavonoid "
                "inhibitor.",

    source="Chidiebere, Oguzie, Liu, Li, Wang, Corrosion Inhibition of Q235 "
           "Mild Steel in 0.5 M H2SO4 Solution by Phytic Acid and Synergistic "
           "Iodide Additives, Ind. Eng. Chem. Res. 2014, 53, 7670-7679 "
           "(DOI 10.1021/ie404382v).",
)

PYRAZOLO_PYRIMIDINE = CaseStudy(
    name="pyrazolo-pyrimidine",
    molecules=(
        "pyrazolopyrimidine propanoic acid",
        "pyrazolopyrimidine propanamide",
        "pyrazolopyrimidine ethyl ester",
    ),
    metal="Fe(110)",
    # Concentration not stated in the extracted note ("acidic HCl"); 1 M is the
    # standard carbon-steel/HCl medium and only the label/pH depends on it (both
    # forms are computed regardless). Verify against the paper.
    medium="1 M HCl",

    # The paper's level is corrosim's production level, so the frontier-orbital
    # descriptors compare directly by the number (unlike the AM1 phytic-acid
    # anchor). These ~40-atom aromatics converge fine at the full diffuse basis.
    basis="6-311++G(d,p)",
    xc="b3lyp",

    description="Three 3-methyl-1-phenyl-pyrazolo[3,4-d]pyrimidin-4-yloxy "
                "propanoate derivatives (acid / amide / ethyl-ester lead) vs "
                "carbon steel (Fe(110)) in HCl — a same-level "
                "(B3LYP/6-311++G(d,p)) numeric cross-check of the multiscale "
                "DFT/MC/MD blueprint.",

    source="Awad, Abdel Halim, Atlam, Fawzy, A multiscale computational "
           "investigation for protection of carbon steel surface by "
           "pyrazolo-pyrimidine derivatives, Sci. Rep. 15:32576 (2025), "
           "DOI 10.1038/s41598-025-19022-6.",
)

TMP_SMX = CaseStudy(
    name="tmp-smx",
    molecules=("trimethoprim", "sulfamethoxazole"),

    # First non-Fe validation case: aluminium, exercising the fcc(111) slab and
    # the Al work function (4.26 eV) instead of the bcc(110) Fe default.
    metal="Al(111)",
    medium="1 M HCl",

    # Trimethoprim's diaminopyrimidine N1 is the pair's strongest basic site;
    # its pKaH ~7.1 makes it fully protonated in 1 M HCl (pH ~0). SMX is a
    # weaker base (anilinium pKaH ~1.6) yet at pH 0 it too is ~98% protonated,
    # so this one case value captures both molecules' cationic regime here; a
    # per-molecule pKaH would matter only near neutral, not in 1 M HCl.
    pkah=7.1,

    # The paper's level is corrosim's production level, so the frontier-orbital
    # descriptors compare directly by the number (a same-level cross-check, like
    # the pyrazolo-pyrimidine case). Both molecules (~28 to 39 atoms, one
    # sulfonamide S) converge at the full diffuse basis.
    basis="6-311++G(d,p)",
    xc="b3lyp",

    description="Trimethoprim (TMP) and sulfamethoxazole (SMX), the "
                "co-trimoxazole antibiotic pair, vs aluminium (Al(111)) in "
                "1 M HCl. The first non-Fe validation case: a same-level "
                "(B3LYP/6-311++G(d,p)) numeric cross-check that exercises the "
                "fcc(111) slab and the Al work function.",

    source="Odozi, Mchihi, Olasunkanmi, Abujah, DFT, Monte Carlo, molecular "
           "dynamics, electrochemical, and weight loss study on corrosion "
           "inhibition of aluminum by trimethoprim and sulfamethoxazole in "
           "HCl, Extreme Materials 2 (2026) 100027, "
           "DOI 10.1016/j.exm.2026.100027.",
)

CASE_STUDIES: dict[str, CaseStudy] = {
    "arghel": ARGHEL,
    "argel": ARGHEL,
    "phytic-acid": PHYTIC_ACID,
    "phytic_acid": PHYTIC_ACID,
    "phytic": PHYTIC_ACID,
    "pyrazolo-pyrimidine": PYRAZOLO_PYRIMIDINE,
    "pyrazolo_pyrimidine": PYRAZOLO_PYRIMIDINE,
    "pyrazolo": PYRAZOLO_PYRIMIDINE,
    "ppp": PYRAZOLO_PYRIMIDINE,
    "tmp-smx": TMP_SMX,
    "tmp_smx": TMP_SMX,
    "tmp-smx-al": TMP_SMX,
    "tmpsmx": TMP_SMX,
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
