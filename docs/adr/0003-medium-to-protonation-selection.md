# ADR 0003 — Couple the `medium` input to protonation by selection, not speciation

- Status: Accepted
- Date: 2026-06-30

## Context

The pipeline's third input, `medium` (e.g. `"1 M HCl"`), was historically only a
report-header label. The protonated-cation modelling that the docs and the
pipeline diagram tie to "the acidic medium" was actually driven by an independent
`--forms {neutral,protonated,both}` flag on `run_dft`, which never read `medium`.
So `medium="pH 7 buffer"` would still yield protonated cations, silently
(issue #8).

Three options were considered: (a) document the gap and keep them independent;
(b) wire an acidic `medium` to drive `forms` with a mismatch warning; (c) parse
`medium` into pH/species and quantitatively drive protonation.

A key empirical finding shaped the choice. Switching the reported descriptors
from the neutral form to the protonated cation (aqueous, B3LYP/6-311++G(d,p))
**flips the lead inhibitor** and changes the ΔN sign:

| | neutral (headline) | protonated cation |
|---|---|---|
| lead | **quercetin** | **isorhamnetin⁺** |
| gap | 4.08–4.15 eV | 3.13–3.60 eV |
| ΔN | +0.17 … +0.21 | **−0.01 … −0.07** |

The negative ΔN is physically sensible — an electron-poor cation does not donate
to the metal — but it breaks the `0 < ΔN < 3.6 ⇒ inhibition` heuristic the report
uses, so the cation needs a different framing, not a swapped table.

## Decision

Parse `medium` into structured chemistry (`corrosim/medium.py`: pH / species /
`acidic`) and use it for **selection and consistency**, not quantitative
speciation:

1. The **headline ranking stays the neutral form** (the conventional descriptor
   basis). The lead is therefore unchanged (quercetin).
2. When the medium is acidic, the **protonated-cation descriptors are surfaced as
   a labelled in-acid comparison** in the report (table + ΔN caveat), so the
   acid→protonation link is real and visible rather than hidden — but it does not
   silently overturn the conclusion.
3. `run_dft` **warns on a medium/forms mismatch** (protonated requested under a
   non-acidic medium, or an acidic medium run neutral-only).

We deliberately do **not** weight the two forms by site pKa (a Henderson–
Hasselbalch mixture). The flavonoid basic-site pKaH values are uncertain, and the
lead is form-dependent, so a pKa-weighted ranking would rest on weak data. The
acidity test uses a pragmatic pH ≤ 4 cutoff for "model the cation", not a site
pKa.

## Consequences

- `report.html` gains a "Species in the acidic medium (protonated cation)"
  subsection; the headline ranking and lead are unchanged.
- The protonated descriptors (computed but previously unsurfaced) are now visible.
- A future, larger feature could parse `medium` into a quantitative pH-weighted
  speciation — that would require pKa data, validation, and a re-examination of
  the form-dependent lead. Out of scope here (this ADR is the selection layer).
- Do **not** make an acidic `medium` silently switch the headline ranking to the
  protonated form without revisiting the lead-flip and the ΔN framing above.
