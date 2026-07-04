"""corrosim.pka.

Conjugate-acid pKa (pKaH) of the inhibitor's basic site from a DFT thermodynamic
cycle, to pin the protonation state the speciation layer (ADR 0004) leaves as a
free parameter.

For the deprotonation  BH⁺ ⇌ B + H⁺  the aqueous free energy is

    ΔG*_aq = G*_aq(B) + G*_aq(H⁺) − G*_aq(BH⁺)        (1 M standard state)
    pKaH   = ΔG*_aq / (RT ln 10)

G*_aq(H⁺) is the well-established aqueous proton free energy; the molecular terms
come from ddCOSMO single points.

APPROXIMATION (read before trusting an absolute number). With ``g_corr_*`` left at
0 this uses the *electronic* aqueous energies only and omits the ZPE / thermal /
entropy of B and BH⁺ (no frequency calculation), and the geometries are the
force-field ones used for the descriptor matrix. Each of these — plus the implicit
solvation error for the charged BH⁺ and the ~±2 kcal/mol uncertainty in G*_aq(H⁺)
— shifts the absolute pKaH by a few units. Treat the result as locating the
*regime* (how weak a base), not as a calibrated pKa. See ADR 0005.
"""
from __future__ import annotations

import math

# 1 kcal/mol in eV.
_KCAL_PER_MOL_IN_EV = 0.0433641
# Universal gas constant in kcal/(mol·K).
_R_KCAL = 1.987204e-3

# Aqueous free energy of the proton at 298.15 K, 1 M standard state (kcal/mol):
#   G_gas(H⁺) −6.28  +  ΔG_solv(H⁺) −265.9  +  ΔG(1 atm→1 M) +1.89  =  −270.29.
# The widely used convention (Tissandier et al.); ~±2 kcal/mol systematic spread.
G_AQ_PROTON_KCAL = -270.29
G_AQ_PROTON_EV = G_AQ_PROTON_KCAL * _KCAL_PER_MOL_IN_EV


def rt_ln10_ev(temperature: float = 298.15) -> float:
    """RT·ln10 in eV — the pKa unit (≈0.0592 eV at 298.15 K)."""
    return _R_KCAL * temperature * math.log(10.0) * _KCAL_PER_MOL_IN_EV


def estimate_pka(e_neutral_aq_ev: float, e_cation_aq_ev: float,
                 g_corr_neutral_ev: float = 0.0, g_corr_cation_ev: float = 0.0,
                 temperature: float = 298.15,
                 g_aq_proton_ev: float = G_AQ_PROTON_EV) -> float:
    """Conjugate-acid pKaH from the aqueous total energies of the neutral (B) and
    protonated cation (BH⁺), via the deprotonation thermodynamic cycle.

    ``e_*_aq_ev`` are aqueous (ddCOSMO) electronic energies in eV. ``g_corr_*`` are
    optional ZPE+thermal+entropy free-energy corrections (eV) from a frequency
    calculation; left at 0 they give the electronic-only estimate (see the module
    docstring on accuracy). Returns the pKaH.
    """
    g_b = e_neutral_aq_ev + g_corr_neutral_ev
    g_bh = e_cation_aq_ev + g_corr_cation_ev
    dg_deprot_ev = g_b + g_aq_proton_ev - g_bh           # ΔG*_aq for BH⁺ → B + H⁺
    return dg_deprot_ev / rt_ln10_ev(temperature)
