"""corrosim.equations.

The governing equations of the pipeline, in scientific form, rendered to PNG via
matplotlib's built-in mathtext — so both the HTML and the Word report can show
real typeset formulas (fractions, Greek, sub/superscripts) with **no** LaTeX,
MathJax or web dependency. matplotlib is already a core dependency, so this adds
nothing to the install and keeps the HTML report self-contained.

Each :class:`Equation` carries the mathtext source, the quantity it defines and a
one-line meaning; :data:`EQUATION_GROUPS` orders them by pipeline stage for the
report's "Scientific basis" section. Definitions mirror ``descriptors.py``
(Koopmans), ``fukui.py``, ``speciation.py`` (Henderson-Hasselbalch), ``pka.py``
(DFT deprotonation cycle) and the Stage-2/3 adsorption observables.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

# eV -> kJ/mol (mc.run_mc uses this to report e_ads_kjmol).
EV_TO_KJMOL = 96.485


@dataclass(frozen=True)
class Equation:
    """One governing equation: ``latex`` is matplotlib-mathtext (no surrounding $)."""

    key: str
    latex: str
    quantity: str        # short label, e.g. "Chemical hardness η"
    meaning: str         # one-line interpretation


# --- Stage 1: global reactivity descriptors (Koopmans; descriptors.py) --------
_STAGE1 = [
    Equation("gap", r"E_{gap} = E_{LUMO} - E_{HOMO}",
             "Energy gap ΔE",
             "Frontier HOMO-LUMO separation; a smaller gap means a more reactive, "
             "more easily polarised inhibitor."),
    Equation("ip", r"IP = -\,E_{HOMO}",
             "Ionization potential",
             "Koopmans' theorem: the energy to remove the highest-energy electron."),
    Equation("ea", r"EA = -\,E_{LUMO}",
             "Electron affinity",
             "Koopmans' theorem: the energy released on adding an electron."),
    Equation("chi", r"\chi = \frac{IP + EA}{2}",
             "Electronegativity χ",
             "Mulliken electronegativity; drives the direction of charge transfer "
             "to the metal."),
    Equation("eta", r"\eta = \frac{IP - EA}{2} = \frac{E_{gap}}{2}",
             "Chemical hardness η",
             "Resistance to charge redistribution; softer (lower η) molecules "
             "adsorb more readily."),
    Equation("sigma", r"\sigma = \frac{1}{\eta}",
             "Chemical softness σ",
             "Inverse hardness; higher σ tracks stronger adsorption."),
    Equation("mu", r"\mu = -\,\chi",
             "Chemical potential μ",
             "The electronic chemical potential (negative electronegativity)."),
    Equation("omega", r"\omega = \frac{\mu^{2}}{2\,\eta}",
             "Electrophilicity ω",
             "Propensity to accept electron density (back-donation channel)."),
    Equation("delta_n",
             r"\Delta N = \frac{\Phi_{metal} - \chi}{2\,(\eta_{metal} + \eta)}",
             "Fraction of electrons transferred ΔN",
             "Charge donated to the metal; the Lukovits window 0 < ΔN < 3.6 marks "
             "electron donation that strengthens inhibition. Φ is the metal work "
             "function, with η_metal ≈ 0."),
    Equation("back", r"\Delta E_{back} = -\,\frac{\eta}{4}",
             "Back-donation energy ΔE_back",
             "Energy of the metal → molecule back-donation that accompanies "
             "donor-acceptor adsorption."),
]

# --- Stage 1b: local reactivity (condensed Fukui; fukui.py) -------------------
_FUKUI = [
    Equation("f_minus", r"f^{-}_{k} = q_{k}(N-1) - q_{k}(N)",
             "Nucleophilic Fukui f⁻",
             "Per-atom susceptibility to electrophilic attack; the highest-f⁻ "
             "oxygens are the electron-donating, metal-coordinating sites."),
    Equation("f_plus", r"f^{+}_{k} = q_{k}(N) - q_{k}(N+1)",
             "Electrophilic Fukui f⁺",
             "Per-atom susceptibility to nucleophilic attack; the back-donation "
             "(electron-accepting) sites."),
    Equation("dual", r"\Delta f_{k} = f^{+}_{k} - f^{-}_{k}",
             "Dual descriptor Δf",
             "Δf < 0 marks a net electron donor, Δf > 0 a net acceptor."),
]

# --- Speciation / pKaH (speciation.py, pka.py) --------------------------------
_SPECIATION = [
    Equation("henderson", r"f_{prot} = \frac{1}{1 + 10^{\,pH - pK_{aH}}}",
             "Protonated fraction (Henderson-Hasselbalch)",
             "Population of the +1 cation at a given pH for a basic site of "
             "conjugate-acid pKₐH."),
    Equation("pka_cycle",
             r"pK_{aH} = \frac{\Delta G^{*}_{aq}}{RT\,\ln 10}",
             "pKaH from a DFT cycle",
             "Conjugate-acid pKₐH from the aqueous deprotonation free energy."),
    Equation("dg_deprot",
             r"\Delta G^{*}_{aq} = G^{*}(B) + G^{*}(H^{+}) - G^{*}(BH^{+})",
             "Deprotonation free energy",
             "For BH⁺ ⇌ B + H⁺, from ddCOSMO aqueous energies and the standard "
             "aqueous proton free energy."),
]

# --- Stage 2/3: adsorption observables (mc.py, md.py) -------------------------
_ADSORPTION = [
    Equation("e_ads", r"E_{ads} = E_{slab+mol} - (E_{slab} + E_{mol})",
             "Adsorption energy E_ads",
             "Interaction energy of the best Monte-Carlo pose; more negative = a "
             "stronger grip. Values near −16 kJ/mol indicate physisorption."),
    Equation("e_ads_conv",
             r"E_{ads}[\mathrm{kJ\,mol^{-1}}] = 96.485 \times E_{ads}[\mathrm{eV}]",
             "Unit conversion",
             "The Monte-Carlo objective is reported in kJ/mol."),
    Equation("rdf_peak",
             r"r^{*} = \arg\max_{r}\; g_{M-O}(r)",
             "Adsorption distance r*",
             "First-peak position of the metal-O radial distribution g(r) from "
             "the Brownian-MD trajectory; r* ≈ 3.5 Å is physisorption range."),
]

# Ordered groups for the "Scientific basis" section: (heading, equations).
EQUATION_GROUPS: list[tuple[str, list[Equation]]] = [
    ("Stage 1 — global reactivity descriptors (Koopmans' theorem)", _STAGE1),
    ("Stage 1 — local reactivity (condensed Fukui)", _FUKUI),
    ("Acid-base speciation and conjugate-acid pKaH", _SPECIATION),
    ("Stage 2/3 — adsorption observables", _ADSORPTION),
]

# Flat lookup by key.
EQUATIONS: dict[str, Equation] = {
    eq.key: eq for _, group in EQUATION_GROUPS for eq in group
}


def render_equation_png(latex: str, dpi: int = 150, fontsize: int = 18) -> bytes:
    """Render a mathtext expression (no surrounding ``$``) to PNG bytes on a white
    background, tightly cropped. Uses the Agg backend so it is headless-safe.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(0.1, 0.1))
    fig.text(0.0, 0.0, f"${latex}$", fontsize=fontsize)
    buf = io.BytesIO()
    # bbox_inches="tight" crops the canvas to just the rendered text.
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                pad_inches=0.08, facecolor="white")
    plt.close(fig)
    return buf.getvalue()
