import math
from corrosim.descriptors import compute_descriptors, METAL_WORK_FUNCTION


def test_descriptor_values():
    # HOMO=-6, LUMO=-2  ->  closed-form expectations
    d = compute_descriptors(homo_ev=-6.0, lumo_ev=-2.0, metal="Fe(110)")
    assert d.gap_ev == 4.0
    assert d.ip_ev == 6.0 and d.ea_ev == 2.0
    assert d.electronegativity_ev == 4.0          # (IP+EA)/2
    assert d.hardness_ev == 2.0                    # (IP-EA)/2 = gap/2
    assert d.softness_inv_ev == 0.5                # 1/eta
    assert d.chemical_potential_ev == -4.0
    assert d.electrophilicity_ev == 4.0            # mu^2/(2 eta)
    assert math.isclose(d.back_donation_ev, -0.5)  # -eta/4


def test_hardness_is_half_gap():
    d = compute_descriptors(-5.3, -1.9)
    assert math.isclose(d.hardness_ev, d.gap_ev / 2)


def test_delta_n_uses_work_function():
    phi = METAL_WORK_FUNCTION["Fe(110)"]
    d = compute_descriptors(-6.0, -2.0, metal="Fe(110)")
    expected = (phi - d.electronegativity_ev) / (2 * d.hardness_ev)
    assert math.isclose(d.delta_n, expected)


def test_metal_override():
    d = compute_descriptors(-6.0, -2.0, metal="Cu(111)", phi_metal_ev=10.0)
    assert d.phi_metal_ev == 10.0
