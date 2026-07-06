"""corrosim.molecules.

Turn an inhibitor (a built-in name or any SMILES string) into a 3D geometry
ready for a quantum-chemistry engine. No network required: structures are
generated from SMILES by RDKit.

The built-in library focuses on the major documented constituents of Arghel
(Solenostemma argel) plus a couple of reference inhibitors for comparison.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from rdkit import Chem
from rdkit.Chem import AllChem

# --- Built-in inhibitor library -------------------------------------------
# Arghel (S. argel) major flavonoids + common reference inhibitors.
# SMILES are canonicalised by RDKit on load, so these only need to be valid.
LIBRARY = {
    # Arghel major flavonoids (aglycones) -- the practical simulation targets
    "kaempferol":  "O=c1c(O)c(-c2ccc(O)cc2)oc2cc(O)cc(O)c12",
    "quercetin":   "O=c1c(O)c(-c2ccc(O)c(O)c2)oc2cc(O)cc(O)c12",
    "isorhamnetin":"O=c1c(O)c(-c2ccc(O)c(OC)c2)oc2cc(O)cc(O)c12",
    # Reference / benchmark inhibitors (optional comparison)
    "benzotriazole": "c1ccc2[nH]nnc2c1",
    "caffeine":      "Cn1cnc2c1c(=O)n(C)c(=O)n2C",
}

# Single-molecule synonyms (name -> library key). "arghel"/"argel" is NOT here:
# Arghel is a *set* of flavonoids, not one molecule — see
# corrosim.presets.ARGHEL.
ALIASES: dict[str, str] = {}


@dataclass
class Molecule:
    """A prepared inhibitor: identity + 3D geometry."""

    name: str
    smiles: str
    symbols: list[str]
    # Angstrom
    coords: list[tuple[float, float, float]]
    # net charge (+1 = protonated cation)
    charge: int = 0
    rdkit_mol: Chem.Mol | None = field(repr=False, default=None)

    @classmethod
    def from_smiles(cls, name_or_smiles: str, *, seed: int = 42,
                    ff: str = "MMFF") -> Molecule:
        """Build a 3D-embedded, force-field-relaxed molecule from a name/SMILES.

        Args:
            name_or_smiles: A library name, alias, or SMILES string.
            seed: RNG seed for the ETKDG embedding.
            ff: Force field for the geometry pre-optimisation ('MMFF' or 'UFF').

        Returns:
            The prepared molecule.

        Raises:
            ValueError: If the SMILES cannot be parsed.
        """
        name, smiles = resolve_smiles(name_or_smiles)
        rdmol = Chem.MolFromSmiles(smiles)
        if rdmol is None:
            raise ValueError(f"RDKit could not parse SMILES: {smiles}")
        return cls._embed_and_relax(rdmol, name=name, charge=0, seed=seed,
                                    ff=ff)

    @classmethod
    def protonated(cls, name_or_smiles: str, site_idx: int, *,
                   seed: int = 42, ff: str = "MMFF") -> Molecule:
        """Protonate a neutral O/N site (add H+), returning a +1 cation.

        The species relevant in acidic media (1 M HCl). Pick ``site_idx`` from
        :func:`enumerate_protonation_sites`; the DFT driver selects the
        lowest-energy site.

        Args:
            name_or_smiles: A library name, alias, or SMILES string.
            site_idx: The O/N atom index to protonate.
            seed: RNG seed for the ETKDG embedding.
            ff: Force field for the geometry pre-optimisation ('MMFF' or 'UFF').

        Returns:
            The +1 cation molecule.

        Raises:
            ValueError: If the SMILES cannot be parsed or ``site_idx`` is not
                an O/N site.
        """
        name, smiles = resolve_smiles(name_or_smiles)
        base = Chem.MolFromSmiles(smiles)
        if base is None:
            raise ValueError(f"RDKit could not parse SMILES: {smiles}")
        rw = Chem.RWMol(base)
        atom = rw.GetAtomWithIdx(site_idx)
        if atom.GetSymbol() not in ("O", "N"):
            raise ValueError(f"Atom {site_idx} ({atom.GetSymbol()}) is not an "
                             "O/N protonation site.")
        atom.SetFormalCharge(atom.GetFormalCharge() + 1)
        atom.SetNumExplicitHs(atom.GetTotalNumHs() + 1)
        atom.SetNoImplicit(True)
        rdmol = rw.GetMol()
        Chem.SanitizeMol(rdmol)
        return cls._embed_and_relax(rdmol, name=f"{name}+H+", charge=1,
                                    seed=seed, ff=ff)

    @classmethod
    def _embed_and_relax(cls, rdmol, name: str, charge: int, seed: int,
                         ff: str) -> Molecule:
        """Add Hs, ETKDG-embed, force-field relax, and pack into a Molecule.

        ff: 'MMFF' or 'UFF' (geometry pre-optimisation before any QM step).
        """
        rdmol = Chem.AddHs(rdmol)
        if AllChem.EmbedMolecule(rdmol, randomSeed=seed) != 0:
            # Retry with random coords if ETKDG fails.
            AllChem.EmbedMolecule(rdmol, randomSeed=seed, useRandomCoords=True)
        if ff.upper() == "MMFF" and AllChem.MMFFHasAllMoleculeParams(rdmol):
            AllChem.MMFFOptimizeMolecule(rdmol)
        else:
            AllChem.UFFOptimizeMolecule(rdmol)

        conf = rdmol.GetConformer()
        symbols = [a.GetSymbol() for a in rdmol.GetAtoms()]
        coords = [(conf.GetAtomPosition(i).x,
                   conf.GetAtomPosition(i).y,
                   conf.GetAtomPosition(i).z)
                  for i in range(rdmol.GetNumAtoms())]
        # Canonical SMILES without explicit Hs for display.
        disp_smiles = Chem.MolToSmiles(Chem.RemoveHs(rdmol))
        return cls(name=name, smiles=disp_smiles, symbols=symbols,
                   coords=coords, charge=charge, rdkit_mol=rdmol)

    @property
    def n_atoms(self) -> int:
        """Number of atoms in the prepared geometry.

        Returns:
            The atom count (explicit Hs included).
        """
        return len(self.symbols)

    @property
    def formula(self) -> str:
        """Molecular formula (Hill notation), from ``rdkit_mol``.

        Returns:
            The Hill-notation formula.

        Raises:
            ValueError: If this molecule carries no ``rdkit_mol`` (build it via
                :meth:`from_smiles` / :meth:`protonated`).
        """
        if self.rdkit_mol is None:
            raise ValueError("formula requires rdkit_mol; build via "
                             "Molecule.from_smiles / .protonated.")
        from rdkit.Chem import rdMolDescriptors
        return rdMolDescriptors.CalcMolFormula(self.rdkit_mol)

    def atoms_for_pyscf(self) -> list:
        """Geometry in the layout ``pyscf.gto.M`` expects.

        Returns:
            ``[[symbol, (x, y, z)], ...]``.
        """
        return [[s, c] for s, c in zip(self.symbols, self.coords)]

    def to_xyz(self) -> str:
        """Serialise to a standard XYZ block (coordinates in Å).

        Returns:
            The XYZ block as text.
        """
        lines = [str(self.n_atoms), self.name]
        for s, (x, y, z) in zip(self.symbols, self.coords):
            lines.append(f"{s:2s} {x:14.8f} {y:14.8f} {z:14.8f}")
        return "\n".join(lines)

    def write_xyz(self, path: str) -> str:
        """Write this molecule to ``path`` as a standard XYZ file (Å).

        Creates the parent directory if needed.

        Args:
            path: Destination ``.xyz`` path.

        Returns:
            The written ``path``.
        """
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_xyz() + "\n")
        return path


def write_xyz(mol: Molecule, path: str) -> str:
    """Write ``mol`` to ``path`` as a standard XYZ file (coordinates in Å).

    Creates the parent directory if needed. The file-name convention is the
    caller's concern (the DFT driver persists each optimised geometry as
    ``<molecule>_opt.xyz``).

    Args:
        mol: The molecule to serialise.
        path: Destination .xyz path.

    Returns:
        The written ``path``.
    """
    return mol.write_xyz(path)


def resolve_smiles(name_or_smiles: str) -> tuple[str, str]:
    """Resolve a library name, alias, or raw SMILES to ``(name, smiles)``.

    Args:
        name_or_smiles: A library name, alias, or SMILES string.

    Returns:
        ``(display_name, smiles)``.

    Raises:
        ValueError: If the input is neither a known name nor a valid SMILES.
    """
    key = name_or_smiles.strip().lower()
    if key in ALIASES:
        key = ALIASES[key]
    if key in LIBRARY:
        return key, LIBRARY[key]
    # treat the input as a SMILES string
    if Chem.MolFromSmiles(name_or_smiles) is not None:
        return name_or_smiles, name_or_smiles
    raise ValueError(
        f"'{name_or_smiles}' is neither a library name "
        f"({', '.join(LIBRARY)}) nor a valid SMILES string."
    )


def build_molecule(name_or_smiles: str, seed: int = 42,
                   ff: str = "MMFF") -> Molecule:
    """Build a 3D-embedded, force-field-relaxed molecule from a name or SMILES.

    Thin wrapper over :meth:`Molecule.from_smiles`.

    Args:
        name_or_smiles: A library name, alias, or SMILES string.
        seed: RNG seed for the ETKDG embedding.
        ff: Force field for the geometry pre-optimisation ('MMFF' or 'UFF').

    Returns:
        The prepared :class:`Molecule`.

    Raises:
        ValueError: If the SMILES cannot be parsed.
    """
    return Molecule.from_smiles(name_or_smiles, seed=seed, ff=ff)


def enumerate_protonation_sites(name_or_smiles: str) -> list[int]:
    """Heavy-atom indices of candidate protonation sites.

    The neutral O / N lone-pair bearers in the canonical (no-H) structure.
    Indices are stable under AddHs, so they can be passed straight to
    ``build_protonated``.

    Args:
        name_or_smiles: A library name, alias, or SMILES string.

    Returns:
        The candidate O/N atom indices.

    Raises:
        ValueError: If the SMILES cannot be parsed.
    """
    _, smiles = resolve_smiles(name_or_smiles)
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"RDKit could not parse SMILES: {smiles}")
    return [a.GetIdx() for a in mol.GetAtoms()
            if a.GetSymbol() in ("O", "N") and a.GetFormalCharge() == 0]


def build_protonated(name_or_smiles: str, site_idx: int, seed: int = 42,
                     ff: str = "MMFF") -> Molecule:
    """Protonate a neutral O/N site (add H+), returning a +1 cation Molecule.

    The species relevant in acidic media (1 M HCl). Pick ``site_idx`` from
    ``enumerate_protonation_sites``; the DFT driver selects the lowest-energy
    site.

    Args:
        name_or_smiles: A library name, alias, or SMILES string.
        site_idx: The O/N atom index to protonate.
        seed: RNG seed for the ETKDG embedding.
        ff: Force field for the geometry pre-optimisation ('MMFF' or 'UFF').

    Returns:
        The +1 cation :class:`Molecule`.

    Raises:
        ValueError: If the SMILES cannot be parsed or ``site_idx`` is not O/N.
    """
    return Molecule.protonated(name_or_smiles, site_idx, seed=seed, ff=ff)
