r"""corrosim.report.ranking.

The composite inhibitor ranking and the selection of the one *canonical basis*
it is reported on. A descriptor can be evaluated on several bases — a cross
product of geometry model (force-field single-point vs DFT-relaxed) and
speciation state (neutral vs the pH-weighted population) — and each basis yields
its own z-score ordering. Reporting several of them side by side lets a report
name several "best" molecules at once, so this module picks exactly one basis as
authoritative and treats the rest as a sensitivity ensemble whose only job is to
say whether the lead is robust.

::

    ff_neutral   opt_neutral        each basis -> rank_inhibitors -> a lead
    ff_blend     opt_blend                 |
        \_________________/                v
                 |                   canonical = best geometry x pH-weighted
                 v                          |
        leaders across all bases ----------+--> robust lead  (all agree)
                                                tie-within-noise (they differ)

The rule: a single lead is asserted only when every available basis puts the
same molecule first. When they disagree the ordering is finer than the method's
resolution, so the report names a tie and only the robust laggard.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..qm.speciation import blend_descriptors


def rank_inhibitors(df: pd.DataFrame) -> pd.DataFrame:
    """Composite ranking from z-scored gap / hardness / softness.

    Stronger inhibition is associated with a smaller gap, lower hardness and
    higher softness; those are z-scored and combined.

    Args:
        df: A descriptor frame with gap_ev / hardness_ev / softness_inv_ev.

    Returns:
        ``df`` sorted best-first with a ``score`` column (higher = better).
    """
    ranked = df.copy()

    def zscore(series, invert=False):
        std = series.std(ddof=0)
        if std == 0:
            return series * 0
        z = (series - series.mean()) / std
        return -z if invert else z

    # Smaller gap + lower hardness + higher softness => stronger inhibition;
    # the mean of the equally-weighted components keeps score O(1) as they grow
    components = [
        zscore(ranked["gap_ev"], invert=True),
        zscore(ranked["hardness_ev"], invert=True),
        zscore(ranked["softness_inv_ev"]),
    ]
    ranked["score"] = (sum(components) / len(components)).round(3)
    return ranked.sort_values("score", ascending=False).reset_index(drop=True)


@dataclass(frozen=True)
class Basis:
    """One evaluation basis and the ranking it produces.

    Attributes:
        key: A stable machine key (``ff_neutral``, ``opt_blend`` …).
        label: A human label for the geometry + speciation of this basis.
        ranked: The best-first ranking frame (from :func:`rank_inhibitors`).
    """

    key: str
    label: str
    ranked: pd.DataFrame

    @property
    def lead(self) -> str:
        """The top-ranked molecule name on this basis.

        Returns:
            The name in row 0 of ``ranked``.
        """
        return str(self.ranked.iloc[0]["name"])


@dataclass(frozen=True)
class LeadVerdict:
    """Whether the lead survives a change of basis (the robustness gate).

    Attributes:
        robust: True when every available basis names the same lead.
        lead: The agreed lead when robust, else None.
        coleaders: The distinct leads across bases when not robust (else empty).
        laggard: The molecule ranked last on every basis, or None.
        n_bases: How many bases were compared.
        margin: The canonical basis' top-to-runner-up score gap (None with a
            single molecule).
    """

    robust: bool
    lead: str | None
    coleaders: tuple[str, ...]
    laggard: str | None
    n_bases: int
    margin: float | None


@dataclass(frozen=True)
class RankingEnsemble:
    """The canonical ranking plus the sensitivity ensemble it is judged against.

    Attributes:
        canonical: The authoritative basis (best geometry x pH-weighted).
        bases: Every available basis, in baseline-to-perturbation display order.
        verdict: The robustness verdict across ``bases``.
    """

    canonical: Basis
    bases: tuple[Basis, ...]
    verdict: LeadVerdict

    def lead_by_basis(self) -> list[tuple[str, str]]:
        """The lead each basis names, for the sensitivity table.

        Returns:
            ``(basis label, lead name)`` pairs in ``bases`` order.
        """
        return [(b.label, b.lead) for b in self.bases]


# Canonical preference: DFT-relaxed geometry beats the force-field single-point,
# and the pH-weighted population beats the bare neutral form. Higher sort key
# wins, so the best available basis is picked without hardcoding a single name.
_GEOMETRY_RANK = {"ff": 0, "opt": 1}
_SPECIATION_RANK = {"neutral": 0, "blend": 1}


def _basis_priority(key: str) -> tuple[int, int]:
    """Sort key that ranks a basis by geometry then speciation quality.

    Args:
        key: A basis key of the form ``<geometry>_<speciation>``.

    Returns:
        ``(geometry rank, speciation rank)``; larger is more canonical.
    """
    geometry, speciation = key.split("_", 1)
    return _GEOMETRY_RANK[geometry], _SPECIATION_RANK[speciation]


def _blend(neutral_rows: list[dict], protonated_rows: list[dict],
           f_protonated: float) -> list[dict]:
    """Population-weighted rows pairing each neutral form with its cation.

    Args:
        neutral_rows: Neutral descriptor rows.
        protonated_rows: Protonated-cation rows (named ``<mol>+H+``).
        f_protonated: The protonated-population weight in [0, 1].

    Returns:
        One blended row per molecule that has both forms, in neutral order.
    """
    cation_by_base = {r["name"].removesuffix("+H+"): r for r in protonated_rows}
    return [blend_descriptors(n, cation_by_base[n["name"]], f_protonated)
            for n in neutral_rows if n["name"] in cation_by_base]


def _laggard(bases: tuple[Basis, ...]) -> str | None:
    """The molecule ranked last on every basis, if one exists.

    Args:
        bases: The available bases.

    Returns:
        The unanimously worst molecule name, or None when the tail disagrees.
    """
    tails = {str(b.ranked.iloc[-1]["name"]) for b in bases}
    return tails.pop() if len(tails) == 1 else None


def build_ensemble(
    neutral_rows: list[dict],
    protonated_rows: list[dict] | None,
    opt_neutral_rows: list[dict] | None,
    opt_protonated_rows: list[dict] | None,
    f_protonated: float | None,
) -> RankingEnsemble:
    """Assemble every available basis, pick the canonical one, judge robustness.

    The bases are the cross product of the geometries supplied (always the
    force-field rows; the DFT-relaxed rows when present) and the speciation
    states (always neutral; the pH-weighted blend when a protonated set and a
    population weight are available). The canonical basis is the best geometry
    combined with the pH-weighted population; the lead is robust only when every
    basis agrees on it.

    Args:
        neutral_rows: Force-field neutral descriptor rows.
        protonated_rows: Force-field protonated-cation rows, or None.
        opt_neutral_rows: DFT-relaxed neutral rows, or None.
        opt_protonated_rows: DFT-relaxed protonated-cation rows, or None.
        f_protonated: The protonated-population weight at the medium pH, or None
            when the medium is non-ionising or the pH is unknown.

    Returns:
        The :class:`RankingEnsemble` (canonical basis + sensitivity bases +
        robustness verdict).
    """
    # Build every basis the supplied rows support, in baseline-to-perturbation
    # display order (force-field before relaxed, neutral before blended).
    specs = [
        ("ff_neutral", "force-field geometry, neutral", neutral_rows),
    ]
    if protonated_rows and f_protonated is not None:
        specs.append(("ff_blend", "force-field geometry, pH-weighted",
                      _blend(neutral_rows, protonated_rows, f_protonated)))
    if opt_neutral_rows:
        specs.append(("opt_neutral", "DFT-relaxed geometry, neutral",
                      opt_neutral_rows))
    if opt_neutral_rows and opt_protonated_rows and f_protonated is not None:
        specs.append(("opt_blend", "DFT-relaxed geometry, pH-weighted",
                      _blend(opt_neutral_rows, opt_protonated_rows,
                             f_protonated)))
    bases = tuple(Basis(key, label, rank_inhibitors(pd.DataFrame(rows)))
                  for key, label, rows in specs if rows)

    # Canonical = the highest-priority basis present; the rest are sensitivity.
    canonical = max(bases, key=lambda b: _basis_priority(b.key))

    # Robust only when every basis names the same lead; otherwise the ordering
    # is finer than the method resolves, so report a tie + the robust laggard.
    leaders = {b.lead for b in bases}
    top = canonical.ranked["score"]
    margin = (round(float(top.iloc[0] - top.iloc[1]), 3)
              if len(top) > 1 else None)
    verdict = LeadVerdict(
        robust=len(leaders) == 1,
        lead=canonical.lead if len(leaders) == 1 else None,
        coleaders=() if len(leaders) == 1 else tuple(sorted(leaders)),
        laggard=_laggard(bases),
        n_bases=len(bases),
        margin=margin,
    )
    return RankingEnsemble(canonical=canonical, bases=bases, verdict=verdict)
