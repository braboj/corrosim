"""corrosim.speciation.

Quantitative acid–base speciation (issue #8 follow-up; ADR 0004): turn the medium
pH into the *population* of the neutral vs protonated inhibitor and blend their
descriptors by that population, so a ranking can reflect the actual species mix
rather than an arbitrary form choice.

The protonation equilibrium  B + H⁺ ⇌ BH⁺  is governed by the conjugate-acid pKa
(pKaH) of the inhibitor's most basic site. The protonated fraction follows
Henderson–Hasselbalch:

    f_prot = 1 / (1 + 10**(pH − pKaH))

For the Arghel flavonoids the most basic site is the 4-oxo carbonyl, a *very weak*
base (pKaH ≈ −1.5; an ESTIMATE, see ADR 0004), so even in 1 M HCl (pH ≈ 0) the
neutral form dominates. But f_prot is exponentially sensitive to pKaH and the
gap/softness composite lead crosses over at only a few-percent protonation — so
this module reports the sensitivity band, not a single confident number. Treat the
point pKaH as illustrative.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Estimated conjugate-acid pKa of the flavonoid 4-oxo carbonyl (most basic site).
# Flavones/chromones are very weak bases; carbonyl-protonation pKaH values cluster
# around −1 to −2 (Hammett-acidity studies). ESTIMATE, ~±1 uncertainty (ADR 0004).
FLAVONOID_CARBONYL_PKAH = -1.5

# Descriptor fields that are population-averaged in a blend (energies / indices).
_BLEND_FIELDS = (
    "homo_ev", "lumo_ev", "gap_ev", "ip_ev", "ea_ev", "electronegativity_ev",
    "hardness_ev", "softness_inv_ev", "chemical_potential_ev",
    "electrophilicity_ev", "delta_n", "back_donation_ev", "tnc",
)


def protonation_fraction(ph: float, pkah: float = FLAVONOID_CARBONYL_PKAH) -> float:
    """Protonated (cationic) fraction at this pH, from Henderson–Hasselbalch:
    ``f_prot = 1 / (1 + 10**(pH − pKaH))``.
    """
    return 1.0 / (1.0 + 10.0 ** (ph - pkah))


def pkah_for_fraction(ph: float, f_prot: float) -> float:
    """Inverse of :func:`protonation_fraction`: the pKaH that gives ``f_prot`` at
    ``ph``. Useful for expressing a population crossover as a pKaH.
    """
    f_prot = min(max(f_prot, 1e-9), 1 - 1e-9)
    return ph + math.log10(f_prot / (1.0 - f_prot))


@dataclass(frozen=True)
class Speciation:
    """Neutral/protonated population split at a given pH (fractions sum to 1)."""

    ph: float
    pkah: float
    f_protonated: float
    f_neutral: float

    @property
    def dominant(self) -> str:
        """'protonated' or 'neutral' — whichever holds the majority population."""
        return "protonated" if self.f_protonated >= 0.5 else "neutral"


def speciate(ph: float, pkah: float = FLAVONOID_CARBONYL_PKAH) -> Speciation:
    """Populations at ``ph`` for a site of conjugate-acid pKa ``pkah``."""
    fp = protonation_fraction(ph, pkah)
    return Speciation(ph=ph, pkah=pkah, f_protonated=fp, f_neutral=1.0 - fp)


def blend_descriptors(neutral_row: dict, protonated_row: dict,
                      f_protonated: float) -> dict:
    """Population-weighted average of the two forms' numeric descriptors.

    Identity/label fields are taken from the neutral row; ``form`` is marked
    'pH-weighted'. Fields missing (or non-numeric) in either row are left as the
    neutral value.
    """
    out = dict(neutral_row)
    fn = 1.0 - f_protonated
    for k in _BLEND_FIELDS:
        nv, pv = neutral_row.get(k), protonated_row.get(k)
        if isinstance(nv, (int, float)) and not isinstance(nv, bool) \
                and isinstance(pv, (int, float)) and not isinstance(pv, bool):
            out[k] = round(fn * nv + f_protonated * pv, 4)
    out["form"] = "pH-weighted"
    return out


def _align(neutral_rows: list[dict], protonated_rows: list[dict]) -> list[tuple[dict, dict]]:
    """Pair each neutral row with its protonated cation (name '<mol>+H+')."""
    pro_by_base = {r["name"].removesuffix("+H+"): r for r in protonated_rows}
    return [(n, pro_by_base[n["name"]]) for n in neutral_rows
            if n["name"] in pro_by_base]


def analyse_speciation(neutral_rows: list[dict], protonated_rows: list[dict],
                       ph: float, rank_fn, pkah: float = FLAVONOID_CARBONYL_PKAH,
                       band: float = 1.0) -> dict:
    """Full pH-speciation summary for the report (ADR 0004).

    ``rank_fn`` ranks a list of descriptor rows and returns them best-first (it is
    injected — typically ``report.rank_inhibitors`` wrapped for list I/O — to avoid
    a circular import). Returns the population split at ``pkah``, the
    population-weighted ('pH-weighted') rows and their lead, the ``pkah ± band``
    sensitivity range, and the protonation fraction at which the composite lead
    first changes (the crossover), expressed as both a fraction and a pKaH.
    """
    pairs = _align(neutral_rows, protonated_rows)

    def lead_at(f: float) -> str:
        blended = [blend_descriptors(n, p, f) for n, p in pairs]
        return rank_fn(blended)[0]["name"]

    spec = speciate(ph, pkah)
    blended_rows = [blend_descriptors(n, p, spec.f_protonated) for n, p in pairs]

    base_lead = lead_at(0.0)
    crossover_f: float | None = None
    crossover_lead: str | None = None
    f = 0.0
    while f <= 1.0 + 1e-9:                       # scan in 1% steps for the first flip
        if lead_at(f) != base_lead:
            crossover_f = round(f, 3)
            crossover_lead = lead_at(f)
            break
        f += 0.01

    return {
        "speciation": spec,
        "blended_rows": blended_rows,
        "blended_lead": lead_at(spec.f_protonated),
        "neutral_lead": base_lead,
        "band_pkah": (pkah - band, pkah + band),
        "band_fraction": (protonation_fraction(ph, pkah - band),
                          protonation_fraction(ph, pkah + band)),
        "crossover_fraction": crossover_f,
        "crossover_pkah": pkah_for_fraction(ph, crossover_f) if crossover_f else None,
        "crossover_lead": crossover_lead,
    }
