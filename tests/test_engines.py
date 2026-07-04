"""QM-light tests for the engine geometry helpers (no PySCF/Docker).

The imaginary-mode escape used by ``relax_to_minimum`` (issue #34) is two pure
functions — mode selection and displacement — that need no QM engine; only the
orchestration loop and the DFT calls around them do.
"""
import numpy as np

from corrosim.engines import displace_along_mode, imaginary_mode


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
