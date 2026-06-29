import math
from corrosim.engines import (parse_orca_output, parse_gaussian_output,
                              write_orca_input, write_gaussian_input,
                              HARTREE_TO_EV)

ORCA_OUT = """
----------------
ORBITAL ENERGIES
----------------
  NO   OCC          E(Eh)            E(eV)
   0   2.0000     -19.251285      -523.8540
   1   2.0000      -1.039671       -28.2909
   2   2.0000      -0.540212       -14.7000
   3   0.0000       0.062196         1.6924
   4   0.0000       0.118000         3.2110

------------------
MULLIKEN POPULATION
"""

GAUSSIAN_OUT = """ Alpha  occ. eigenvalues --  -10.1850  -0.9876  -0.5402
 Alpha virt. eigenvalues --   -0.0621   0.1180   0.2500
"""


def test_orca_parser():
    homo, lumo = parse_orca_output(ORCA_OUT)
    assert math.isclose(homo, -14.7000, abs_tol=1e-4)
    assert math.isclose(lumo, 1.6924, abs_tol=1e-4)


def test_gaussian_parser():
    homo, lumo = parse_gaussian_output(GAUSSIAN_OUT)
    assert math.isclose(homo, -0.5402 * HARTREE_TO_EV, abs_tol=1e-3)
    assert math.isclose(lumo, -0.0621 * HARTREE_TO_EV, abs_tol=1e-3)


def test_orca_input_has_solvent_and_geometry():
    inp = write_orca_input(["O", "H", "H"], [(0, 0, 0), (0, 0, 1), (0, 1, 0)],
                           "B3LYP def2-TZVP", solvent="water", nprocs=4)
    assert "! B3LYP def2-TZVP" in inp
    assert "CPCM(water)" in inp
    assert "* xyz 0 1" in inp
    assert inp.count("\n") >= 7


def test_gaussian_input_route_and_charge():
    gjf = write_gaussian_input(["O", "H"], [(0, 0, 0), (0, 0, 1)],
                               "B3LYP/6-311++G(d,p)", solvent="water", charge=0, mult=1)
    assert "# B3LYP/6-311++G(d,p)" in gjf
    assert "SCRF=(PCM,solvent=water)" in gjf
    assert "0 1" in gjf
