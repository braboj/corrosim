"""
corrosim.medium
---------------
Parse a free-text electrochemical medium label (e.g. "1 M HCl", "pH 7 buffer")
into structured chemistry: the acid/electrolyte species, its concentration, and
an approximate pH. The pH then says which protonation state of the inhibitor is
chemically relevant — in a strong acid the basic O/N sites take up a proton, so
the +1 cation is present (see ADR 0003).

This is a *selection / consistency* layer over the already-computed DFT forms,
not a quantitative speciation model: it decides whether the protonated cation is
relevant (and lets callers warn on a medium/forms mismatch). It deliberately does
NOT weight by site pKa — the ranking the report leads with stays the neutral form
(ADR 0003).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

# Strong acids we recognise -> count of dissociable protons (for the pH estimate).
_STRONG_ACIDS = {"HCL": 1, "HBR": 1, "HI": 1, "HNO3": 1, "HCLO4": 1, "H2SO4": 2}
# Bases / neutral electrolytes whose presence means "not acidic".
_BASE_OR_NEUTRAL = ("naoh", "koh", "nh4oh", "alkaline", "base", "nacl", "na2so4")
# pH at/below which the inhibitor's basic sites are treated as protonated. A
# pragmatic cutoff for "acidic enough to model the cation", not a site pKa.
ACIDIC_PH_THRESHOLD = 4.0


@dataclass(frozen=True)
class MediumSpec:
    """Parsed medium: the original label plus whatever chemistry we could extract.

    ``ph`` is None when it can't be estimated; ``acidic`` then falls back to a
    keyword guess so callers can still warn rather than silently mismodel.
    """

    label: str
    ph: float | None = None
    acidic: bool = False
    species: str | None = None
    concentration_M: float | None = None


def parse_medium(medium: str) -> MediumSpec:
    """Best-effort parse of a medium label into a :class:`MediumSpec` (never raises).

    Recognises an explicit ``pH <x>``, a ``<conc> M <acid>`` for common strong
    acids (strong-acid pH approximation), and a keyword fallback for everything
    else. Unrecognised media yield ``ph=None`` with an acidity guess from keywords.
    """
    label = medium.strip()
    low = label.lower()

    # explicit pH, e.g. "pH 7 buffer", "ph=1.5"
    m = re.search(r"ph\s*=?\s*([0-9]+(?:\.[0-9]+)?)", low)
    if m:
        ph = float(m.group(1))
        return MediumSpec(label=label, ph=ph, acidic=ph <= ACIDIC_PH_THRESHOLD)

    # "<conc> M <acid>", e.g. "1 M HCl", "0.5 M H2SO4"
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*m\s+([a-z0-9]+)", low)
    if m:
        conc = float(m.group(1))
        species = m.group(2).upper()
        n_h = _STRONG_ACIDS.get(species)
        if n_h and conc > 0:
            ph = round(-math.log10(n_h * conc), 2)        # strong-acid approximation
            return MediumSpec(label=label, ph=ph, acidic=ph <= ACIDIC_PH_THRESHOLD,
                              species=species, concentration_M=conc)
        return MediumSpec(label=label, species=species, concentration_M=conc,
                          acidic=_looks_acidic(low))

    return MediumSpec(label=label, acidic=_looks_acidic(low))


def _looks_acidic(low: str) -> bool:
    """Keyword fallback when no pH can be computed."""
    if any(b in low for b in _BASE_OR_NEUTRAL):
        return False
    return any(a in low for a in ("hcl", "h2so4", "hno3", "acid"))


def relevant_forms(spec: MediumSpec) -> set[str]:
    """Protonation forms chemically present in this medium: the neutral always,
    plus the 'protonated' cation in acid (the basic sites take up H+)."""
    return {"neutral", "protonated"} if spec.acidic else {"neutral"}
