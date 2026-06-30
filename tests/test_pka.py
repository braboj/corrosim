"""DFT-cycle pKa estimator math (corrosim.pka / ADR 0005)."""
import math

from corrosim.pka import G_AQ_PROTON_EV, estimate_pka, rt_ln10_ev


def test_rt_ln10_ev_room_temperature():
    assert math.isclose(rt_ln10_ev(298.15), 0.05916, abs_tol=1e-4)


def test_pka_zero_when_deprotonation_is_thermoneutral():
    # ΔG_deprot = 0 exactly when (E_B − E_BH⁺) = −G_aq(H⁺)
    e_bh = -100.0
    e_b = e_bh - G_AQ_PROTON_EV
    assert abs(estimate_pka(e_b, e_bh)) < 1e-6


def test_stronger_proton_binding_raises_pka():
    # a more stable cation (lower E_BH⁺) = stronger base = higher pKaH, linearly
    base = estimate_pka(e_neutral_aq_ev=0.0, e_cation_aq_ev=-11.72)
    stronger = estimate_pka(e_neutral_aq_ev=0.0, e_cation_aq_ev=-11.92)
    assert stronger > base
    assert math.isclose(stronger - base, 0.2 / rt_ln10_ev(), abs_tol=1e-6)


def test_cation_zpe_correction_lowers_pka():
    # the extra X–H ZPE raises G(BH⁺) -> easier to deprotonate -> lower pKaH
    no_corr = estimate_pka(0.0, -11.72)
    with_corr = estimate_pka(0.0, -11.72, g_corr_cation_ev=0.22)
    assert with_corr < no_corr
