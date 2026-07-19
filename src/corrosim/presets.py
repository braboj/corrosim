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

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any


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

    # Speed the production SCF with density fitting (RI). Off by default: the RI
    # approximation shifts the descriptors, so it stays a deliberate per-case
    # opt-in for a large molecule whose exact-integral SCF is intractable.
    density_fit: bool = False

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

    def to_dict(self) -> dict[str, Any]:
        """Serialise the study to a JSON-friendly mapping.

        Returns:
            Every field keyed by name, with ``molecules`` as a list so the
            result round-trips through JSON.
        """
        data = {f.name: getattr(self, f.name) for f in fields(self)}
        data["molecules"] = list(self.molecules)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CaseStudy:
        """Build a study from a plain mapping (e.g. decoded JSON), validated.

        Structural validation only: the presence and type of the fields. The
        substrate/element *envelope* (which metals and elements the pipeline
        supports) is checked separately by :func:`validate_study`, so a caller
        can deserialise without pulling the heavy slab/RDKit imports.

        Args:
            data: A mapping keyed by ``CaseStudy`` field name; ``name`` and
                ``molecules`` are required, the rest fall back to the field
                defaults.

        Returns:
            The constructed frozen ``CaseStudy``.

        Raises:
            ValueError: If a required key is missing, an unknown key is
                present, or ``molecules`` is not a non-empty list of strings.
        """
        # Reject unknown keys so a typo ('metals', 'smiles') fails loud
        allowed = {f.name for f in fields(cls)}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(
                f"unknown study field(s): {', '.join(sorted(unknown))}; "
                f"allowed: {', '.join(sorted(allowed))}.")

        # Required identity
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "study 'name' is required and must be a non-empty string.")

        # Required molecule set (library names or SMILES)
        mols = data.get("molecules")
        if (not isinstance(mols, (list, tuple)) or not mols
                or not all(isinstance(m, str) and m.strip() for m in mols)):
            raise ValueError(
                "study 'molecules' is required and must be a non-empty list "
                "of name/SMILES strings.")

        # Everything else falls through to the dataclass defaults
        rest = {k: v for k, v in data.items()
                if k not in ("name", "molecules")}
        return cls(name=name, molecules=tuple(mols), **rest)


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

TETRAZOLES = CaseStudy(
    name="tetrazoles",
    molecules=(
        "tetrazole",
        "5-aminotetrazole",
        "5-phenyltetrazole",
        "1-phenyl-5-mercaptotetrazole",
    ),

    # Second non-Fe substrate (after Al(111)): copper, exercising the fcc(111)
    # slab and the Cu work function (4.94 eV). The scaffold grows worst-to-best
    # inhibitor across the set, the paper's reported order.
    metal="Cu(111)",

    # The source states only "acidic medium" and correlates against the group's
    # prior experimental inhibition efficiencies for these tetrazolic compounds
    # on copper/brass in nitric acid; modelled here as 1 M HNO3 (a
    # representative strong-acid pH so the speciation blend is defined).
    medium="1 M HNO3",

    # Tetrazoles are weak bases (ring-N conjugate-acid pKaH well below zero), so
    # even at pH 0 they stay essentially all-neutral: the default very-weak-base
    # pKaH applies and the pH-weighted basis tracks the neutral one.
    pkah=-1.5,

    # Same functional as the source (B3LYP) but corrosim's larger production
    # basis; the source's absolute frontier levels are on an anomalously
    # shallow scale (HOMO around -2 eV), so the comparison is the descriptor
    # ordering and its correlation with the experimental efficiencies, not the
    # absolute number.
    basis="6-311++G(d,p)",
    xc="b3lyp",

    description="Four tetrazole derivatives (1H-tetrazole, 5-amino, 5-phenyl, "
                "1-phenyl-5-mercapto) vs copper (Cu(111)) in acidic medium. A "
                "second non-Fe validation case: the mercapto / phenyl "
                "substituent series whose reactivity ordering tracks the "
                "measured inhibition efficiencies, exercising the fcc(111) "
                "slab and the Cu work function.",

    source="Bourzi, Oukhrib, El Ibrahimi, Abou Oualid, Abdellaoui, Balkard, "
           "Hilali, El Issami, Understanding of anti-corrosive behavior of "
           "some tetrazole derivatives in acidic medium: adsorption on Cu(111) "
           "surface using quantum chemical calculations and Monte Carlo "
           "simulations, Surface Science 702 (2020) 121692, "
           "DOI 10.1016/j.susc.2020.121692.",
)

PYRAZOLYLNUCLEOSIDES = CaseStudy(
    name="pyrazolylnucleosides",
    molecules=(
        "pyrazolylnucleoside methyl",
        "pyrazolylnucleoside methoxy",
        "pyrazolylnucleoside fluoro",
        "pyrazolylnucleoside chloro",
        "pyrazolylnucleoside bromo",
    ),

    # Copper again (as the tetrazoles case), but the fuller stack: this study
    # runs DFT + Monte Carlo + molecular dynamics with a clean metal-heteroatom
    # RDF, so it exercises the MD/RDF path on Cu(111), not just the descriptors.
    metal="Cu(111)",

    # The source protonates the pyrazole ring in acidic media and its MC/MD box
    # carries hydronium + chloride, i.e. hydrochloric acid; modelled as 1 M HCl.
    medium="1 M HCl",

    # The basic site is the pyrazole ring nitrogen (parent pyrazole pKaH ~2.5);
    # at low pH these nucleosides are largely protonated, the species the source
    # itself models.
    pkah=2.5,

    # The source computes with DMol3 (M-11L / DND / COSMO), a different level,
    # so the descriptor comparison is qualitative. The set spans F / Cl / Br,
    # and the engine's Pople sets (6-31G(d), 6-311++G(d,p)) carry no bromine, so
    # the basis is def2-SVP: all-electron, whole-periodic-table coverage at
    # double-zeta cost, treating the halogen series consistently.
    basis="def2-SVP",
    xc="b3lyp",

    description="Five novel pyrazolylnucleosides (a 2-deoxyribofuranosyl "
                "pyrazole with a cyanomethyl arm and a 4-X-phenyl group, "
                "X = CH3 / OCH3 / F / Cl / Br) vs copper (Cu(111)) in acidic "
                "medium. The fuller non-Fe case: DFT + MC + MD with a clean "
                "metal-heteroatom RDF, exercising the MD/RDF path on copper.",

    source="Oukhrib, Abdellaoui, Berisha, Abou Oualid, Halili, Jusufi, Ait El "
           "Had, Bourzi, El Issami, Asmary, Parmar, Len, DFT, Monte Carlo and "
           "molecular dynamics simulations for the prediction of corrosion "
           "inhibition efficiency of novel pyrazolylnucleosides on Cu(111) "
           "surface in acidic media, Scientific Reports 11 (2021) 3771, "
           "DOI 10.1038/s41598-021-82927-5.",
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
    "tetrazoles": TETRAZOLES,
    "tetrazole": TETRAZOLES,
    "tetrazoles-cu": TETRAZOLES,
    "tz": TETRAZOLES,
    "pyrazolylnucleosides": PYRAZOLYLNUCLEOSIDES,
    "pyrazolylnucleoside": PYRAZOLYLNUCLEOSIDES,
    "pyn": PYRAZOLYLNUCLEOSIDES,
}


def is_study_file(name: str) -> bool:
    """Whether a ``--case`` value names a study file rather than a preset.

    Registry keys are bare words, so a value that ends in ``.json`` or carries a
    path separator is a study file; anything else is a preset lookup. Keying on
    explicit markers (not ``os.path.exists``) keeps a name like ``arghel`` a
    preset even if a file of that name happens to sit in the working directory.

    Args:
        name: The raw ``--case`` value.

    Returns:
        True if ``name`` should be loaded as a study file.
    """
    return name.endswith(".json") or "/" in name or os.sep in name


def load_study(path: str) -> CaseStudy:
    """Load a case study from a JSON file (the fields of :class:`CaseStudy`).

    Args:
        path: Path to a study JSON file.

    Returns:
        The deserialised study, structurally validated by
        :meth:`CaseStudy.from_dict`; call :func:`validate_study` for the
        substrate/element envelope check.

    Raises:
        ValueError: If the file is structurally malformed.
    """
    with open(path, encoding="utf-8") as fh:
        return CaseStudy.from_dict(json.load(fh))


def save_study(case: CaseStudy, path: str) -> None:
    """Write a case study to a JSON file, creating parent directories.

    Args:
        case: The study to serialise.
        path: Destination path; its parent directory is created if absent.
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(case.to_dict(), fh, indent=2)


def case_study(name: str) -> CaseStudy:
    """Resolve a case study by registry name, or load it from a study file.

    A bare word (``"arghel"``, aliases accepted) is looked up in
    :data:`CASE_STUDIES`; a value that names a file (see :func:`is_study_file`)
    is loaded as a study JSON, so a user can run their own study without editing
    this module.

    Args:
        name: A registry key, or a path to a study JSON file.

    Returns:
        The matching or loaded :class:`CaseStudy`.

    Raises:
        KeyError: If ``name`` is a bare word not registered in CASE_STUDIES.
        ValueError: If ``name`` is a study file that is malformed.
    """
    if is_study_file(name):
        return load_study(name)
    key = name.strip().lower()
    if key not in CASE_STUDIES:
        raise KeyError(f"Unknown case study {name!r}. "
                       f"Known: {sorted(set(CASE_STUDIES))}.")
    return CASE_STUDIES[key]


# A name safe as the cases/<name>/ directory component: alphanumeric plus the
# dash/underscore separators the shipped case names use.
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def validate_study(case: CaseStudy, *, check_elements: bool = False) -> None:
    """Check a study lies inside the pipeline's supported envelope.

    Guards a user-supplied study before any stage runs, so an unsupported metal
    or element fails immediately with a clear message instead of three stages
    deep. The substrate table and the UFF element set are imported lazily, so
    this module stays a stdlib-only leaf at import time.

    Args:
        case: The study to validate.
        check_elements: Also build each molecule and check its elements are in
            the UFF van-der-Waals table (needs RDKit; skip for a dry run).

    Raises:
        ValueError: If the name is not filesystem-safe, the metal is not a
            supported substrate, or (when ``check_elements``) a molecule carries
            an element with no UFF parameters.
    """
    # Filesystem-safe name (it becomes the cases/<name>/ output directory)
    if not _SAFE_NAME.match(case.name):
        raise ValueError(
            f"study name {case.name!r} must be alphanumeric with '-'/'_' only "
            f"(it becomes the cases/<name>/ output directory).")

    # Supported substrate: only a metal with a slab lattice runs the full
    # pipeline (the MC/MD stages need the slab, the DFT stage its work function)
    from corrosim.adsorption.surface import METAL_LATTICE, UFF

    if case.metal_element not in METAL_LATTICE:
        raise ValueError(
            f"metal {case.metal!r} is not supported; the slab builder knows "
            f"{', '.join(sorted(METAL_LATTICE))}. Add a lattice to extend it.")
    if not check_elements:
        return

    # Supported chemistry: every atom needs a UFF parameter for the vdW field
    from corrosim.molecules import build_molecule

    known = set(UFF)
    for spec in case.molecule_list():
        missing = sorted(set(build_molecule(spec).symbols) - known)
        if missing:
            raise ValueError(
                f"molecule {spec!r} carries element(s) "
                f"{', '.join(missing)} with no UFF parameters; supported "
                f"elements: {', '.join(sorted(known))}.")
