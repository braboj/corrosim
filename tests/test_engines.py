"""QM-light tests for the engine geometry helpers (no PySCF/Docker).

The imaginary-mode escape used by ``relax_to_minimum`` (issue #34) is two pure
functions — mode selection and displacement — that need no QM engine; only the
orchestration loop and the DFT calls around them do.
"""
import numpy as np
import pytest

from corrosim.qm.engines import (
    AU_TO_DEBYE,
    HARTREE_TO_EV,
    EngineResult,
    dipole_magnitude_debye,
    displace_along_mode,
    imaginary_mode,
    min_check_fields,
    parse_gaussian_output,
    parse_orca_output,
    require_virtual_orbital,
    write_gaussian_input,
    write_orca_input,
)


def test_require_virtual_orbital_passes_when_a_virtual_exists():
    # a normal molecule has unoccupied orbitals -> no error, returns None
    assert require_virtual_orbital(np.array([2.0, 2.0, 0.0, 0.0])) is None


def test_require_virtual_orbital_raises_when_fully_occupied():
    # #267: a fully occupied system has no LUMO; every LUMO-index site (run_xtb,
    # run_pyscf, ORCA parse, FMO Fukui, orbital cubes) guards on this so a raw
    # IndexError/ValueError never escapes.
    with pytest.raises(ValueError, match="no virtual"):
        require_virtual_orbital(np.array([2.0, 2.0]))


def test_dipole_magnitude_debye_scales_atomic_units():
    # a 3-4-0 vector has magnitude 5 a.u.; in Debye that is 5 * AU_TO_DEBYE
    got = dipole_magnitude_debye([3.0, 4.0, 0.0], in_atomic_units=True)
    assert abs(got - 5.0 * AU_TO_DEBYE) < 1e-9


def test_dipole_magnitude_debye_passes_through_debye():
    # a vector already in Debye is only reduced to its magnitude, not rescaled
    got = dipole_magnitude_debye([0.0, 0.0, 2.5], in_atomic_units=False)
    assert abs(got - 2.5) < 1e-9


def test_dipole_magnitude_debye_none_when_absent_or_short():
    assert dipole_magnitude_debye(None, in_atomic_units=True) is None
    assert dipole_magnitude_debye([1.0, 2.0], in_atomic_units=False) is None


def test_engine_result_dipole_defaults_to_none():
    res = EngineResult("xtb", "GFN2-xTB", -1.0, -6.0, -2.0)
    assert res.dipole_debye is None
    res2 = EngineResult("xtb", "GFN2-xTB", -1.0, -6.0, -2.0, dipole_debye=3.14)
    assert res2.dipole_debye == 3.14


def test_imaginary_mode_returns_none_at_a_minimum():
    # all real (positive) frequencies -> already a minimum, nothing to step along
    freq = np.array([120.0, 300.0, 1600.0])
    modes = np.random.default_rng(0).normal(size=(3, 4, 3))
    assert imaginary_mode(freq, modes) is None


def test_imaginary_mode_picks_the_softest_negative():
    # two imaginary modes: the softer (more negative) one is the escape direction
    freq = np.array([-15.0, 200.0, -80.0, 500.0])
    modes = np.arange(4 * 2 * 3, dtype=float).reshape(4, 2, 3)
    picked = imaginary_mode(freq, modes)
    assert np.array_equal(picked, modes[2])   # index 2 has freq -80 (most negative)


def test_imaginary_mode_detects_complex_encoded_frequency():
    # PySCF may encode an imaginary mode as a non-zero imaginary part, not a sign
    freq = np.array([50.0 + 0j, 0.0 + 30.0j, 900.0 + 0j])
    modes = np.ones((3, 2, 3))
    assert imaginary_mode(freq, modes) is not None


def test_displace_along_mode_scales_to_amplitude():
    coords = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
    mode = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0)]     # peak component 2.0
    out = np.asarray(displace_along_mode(coords, mode, amplitude_ang=0.3))
    # largest atomic move is exactly the requested amplitude
    assert np.isclose(np.abs(out - np.asarray(coords)).max(), 0.3)
    assert out[1][0] == 1.3                        # atom 1 moved +0.3 along x


def test_displace_along_mode_flat_mode_is_a_noop():
    coords = [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)]
    out = displace_along_mode(coords, np.zeros((2, 3)), amplitude_ang=0.3)
    assert np.array_equal(np.asarray(out), np.asarray(coords))


def test_displace_along_mode_accepts_flat_mode_vector():
    # a (natom*3,) mode is reshaped to the coords shape
    coords = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
    mode = [0.0, 0.0, 0.0, 0.5, 0.0, 0.0]
    out = displace_along_mode(coords, mode, amplitude_ang=0.3)
    assert np.isclose(out[1][0], 1.3)


# --- min_check_fields: the true-minimum provenance condenser (issue #41) ----------

def test_min_check_fields_empty_when_no_check_ran():
    # a plain --optimize row carries no frequency check -> no extra provenance
    assert min_check_fields(None) == {}
    assert min_check_fields({}) == {}


def test_min_check_fields_clean_minimum_reports_zero_n_imag():
    thermo = {"n_imag": 0, "freq_cm": np.array([55.0, 210.0, 1590.0])}
    assert min_check_fields(thermo) == {"n_imag": 0, "lowest_freq_cm": 55.0}


def test_min_check_fields_flags_a_saddle_with_the_softest_frequency():
    # a first-order saddle: n_imag carried through, lowest freq is the negative one
    thermo = {"n_imag": 1, "freq_cm": np.array([-42.3, 200.0, 1600.0])}
    assert min_check_fields(thermo) == {"n_imag": 1, "lowest_freq_cm": -42.3}


def test_min_check_fields_handles_complex_encoded_imaginary():
    # PySCF may encode an imaginary mode as a pure-imaginary number (real part 0); it
    # must surface as a NEGATIVE signed wavenumber, not 0.0, to agree with n_imag
    thermo = {"n_imag": 1, "freq_cm": np.array([0.0 + 30.0j, 240.0, 1500.0])}
    out = min_check_fields(thermo)
    assert out["n_imag"] == 1 and out["lowest_freq_cm"] == -30.0


# --- ORCA / Gaussian deck writers + output parsers (no QM binary) ------------

WATER = "water"


def test_orca_and_gaussian_writers_share_the_xyz_block():
    # both decks embed the identical aligned geometry block (shared _xyz_block)
    symbols = ["O", "H"]
    coords = [(0.0, 0.0, 0.0), (0.0, 0.0, 0.96)]
    orca = write_orca_input(symbols, coords, "B3LYP def2-TZVP")
    gauss = write_gaussian_input(symbols, coords, "B3LYP/6-31G(d)")

    def atom_lines(deck):
        return [ln for ln in deck.splitlines()
                if ln.strip().startswith(("O ", "H "))]

    assert atom_lines(orca) == atom_lines(gauss)
    # the format contract: element in a 2-wide field, coords in 16.8f columns
    assert atom_lines(orca)[1] == (
        f" {'H':2s} {0.0:16.8f} {0.0:16.8f} {0.96:16.8f}")


def test_write_orca_input_emits_cpcm_and_charge_mult():
    deck = write_orca_input(["C"], [(0.0, 0.0, 0.0)], "B3LYP def2-SVP",
                            charge=1, mult=2, solvent=WATER)
    assert "! B3LYP def2-SVP" in deck
    assert "! CPCM(water)" in deck
    assert "* xyz 1 2" in deck


def test_parse_orca_output_picks_homo_lumo_from_occupations():
    text = "\n".join([
        "----------------",
        "ORBITAL ENERGIES",
        "----------------",
        "  NO   OCC          E(Eh)            E(eV)",
        "   0   2.0000     -10.000000     -272.000000",
        "   1   2.0000      -1.000000      -20.000000",
        "   2   0.0000       0.500000       10.000000",
        "   3   0.0000       1.000000       20.000000",
        "",
    ])
    # HOMO = last occupied (row 1), LUMO = first virtual (row 2), values in eV
    assert parse_orca_output(text) == (-20.0, 10.0)


def test_parse_gaussian_output_converts_hartree_to_ev():
    text = "\n".join([
        " Alpha  occ. eigenvalues --  -10.00000   -1.00000",
        " Alpha virt. eigenvalues --    0.50000    1.00000",
    ])
    homo, lumo = parse_gaussian_output(text)
    # HOMO = highest occupied (-1 Eh), LUMO = lowest virtual (0.5 Eh)
    assert np.isclose(homo, -1.0 * HARTREE_TO_EV)
    assert np.isclose(lumo, 0.5 * HARTREE_TO_EV)
