"""corrosim.report_content.

The small amount of shared *narrative* the lean report still carries: the
headline caveat, a short method caveat, the data-derived bottom-line sentence,
and a one-line scoring note. Both renderers — HTML (``report``) and Word
(``report_docx``) — import these so the two outputs stay identical.

The report itself is deliberately lean: under each stage, just the tables and
figures with minimal captions, no methodology essay. The full methodology lives
in ``docs/pipeline.md`` and the validation record in ``docs/validation.md``;
the report points there rather than duplicating them.
"""
from __future__ import annotations

# --- caveats -----------------------------------------------------------------
HEADLINE_CAVEAT = (
    "The molecules modelled here are screened in silico as representative "
    "candidates, not a verified analysis of any real sample. Confirm the "
    "actual composition experimentally (e.g. by LC-MS/GC-MS) before drawing "
    "firm conclusions."
)

METHOD_CAVEAT = (
    "Global descriptors come from the frontier-orbital energies via Koopmans' "
    "theorem; ΔN uses the metal work function with η(metal) = 0. The "
    "Monte-Carlo and Brownian-MD stages use a classical van-der-Waals "
    "adsorption model — a physics-based screening surrogate, not a substitute "
    "for periodic DFT or for electrochemical validation. The composite ranking "
    "is a heuristic that orders candidates; it does not prove inhibition. Full "
    "methodology: docs/pipeline.md; validation record: docs/validation.md."
)


def inline_runs(text: str) -> list[tuple[str, bool]]:
    """Split ``**bold**`` markup into (text, is_bold) runs for either renderer.

    Args:
        text: Prose with ``**bold**`` spans.

    Returns:
        (chunk, is_bold) runs in order.
    """
    runs: list[tuple[str, bool]] = []
    for i, chunk in enumerate(text.split("**")):
        if chunk:
            runs.append((chunk, i % 2 == 1))
    return runs


def score_note(metal_element: str) -> str:
    """One-line note under the ranking table (the scoring essay moved out).

    The z-score / gap / hardness / softness derivation now lives once in
    ``docs/pipeline.md`` (the Ranking section); the report just points there.

    Args:
        metal_element: The RDF partner element (e.g. Fe) named in the note.

    Returns:
        The note with ``**bold**`` markup.
    """
    return (
        "Scored on the neutral HOMO–LUMO gap, hardness and softness "
        f"(z-scored; **higher = stronger**). E_ads and the {metal_element}–O "
        "distance validate the lead, they do not enter the score. Full method: "
        "docs/pipeline.md."
    )


def bottom_line(n_molecules: int, lead: str, score: float, gap_ev: float,
                e_ads_kjmol: float | None, metal_element: str) -> str:
    """Data-derived headline naming the top-ranked inhibitor.

    Shared by both renderers (``**bold**`` markup only). Every value comes
    from the ranking, so the sentence stays correct if the molecule set or
    substrate changes.

    Args:
        n_molecules: Number of screened molecules.
        lead: The top-ranked inhibitor name.
        score: The lead's composite score.
        gap_ev: The lead's HOMO-LUMO gap (eV).
        e_ads_kjmol: The lead's adsorption energy (kJ/mol), or None.
        metal_element: The substrate element named in the E_ads clause.

    Returns:
        The headline sentence with ``**bold**`` markup.
    """
    eads = (f" It adsorbs flat on {metal_element} in the physisorption regime "
            f"(E_ads ≈ {e_ads_kjmol:.0f} kJ/mol)."
            if e_ads_kjmol is not None else "")
    return (
        f"Of the {n_molecules} molecules screened, "
        f"**{lead}** ranks highest on the composite electronic score "
        f"({score:+.2f}), combining the smallest HOMO–LUMO gap "
        f"({gap_ev:.2f} eV) with the highest softness — the most readily "
        f"polarised, electron-donating candidate of the set.{eads} This is a "
        "computational screening prediction requiring electrochemical "
        "confirmation (see the Method section and caveats)."
    )
