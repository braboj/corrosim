"""
corrosim.molecules
-------------------
Turn an inhibitor (a built-in name or any SMILES string) into a 3D geometry
ready for a quantum-chemistry engine. No network required: structures are
generated from SMILES by RDKit.

The built-in library focuses on the major documented constituents of Arghel
(Solenostemma argel) plus a couple of reference inhibitors for comparison.
"""
from __future__ import annotations
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

# Friendly aliases
ALIASES = {"argel": "kaempferol", "arghel": "kaempferol"}


@dataclass
class Molecule:
    """A prepared inhibitor: identity + 3D geometry."""
    name: str
    smiles: str
    symbols: list[str]
    coords: list[tuple[float, float, float]]   # Angstrom
    rdkit_mol: Chem.Mol = field(repr=False, default=None)

    @property
    def n_atoms(self) -> int:
        return len(self.symbols)

    @property
    def formula(self) -> str:
        from rdkit.Chem import rdMolDescriptors
        return rdMolDescriptors.CalcMolFormula(self.rdkit_mol)

    def atoms_for_pyscf(self):
        return [[s, c] for s, c in zip(self.symbols, self.coords)]

    def to_xyz(self) -> str:
        lines = [str(self.n_atoms), self.name]
        for s, (x, y, z) in zip(self.symbols, self.coords):
            lines.append(f"{s:2s} {x:14.8f} {y:14.8f} {z:14.8f}")
        return "\n".join(lines)


def resolve_smiles(name_or_smiles: str) -> tuple[str, str]:
    """Return (display_name, smiles) for a library name, alias, or raw SMILES."""
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
    """
    Build a 3D-embedded, force-field-relaxed molecule from a name or SMILES.

    ff: 'MMFF' or 'UFF' (geometry pre-optimisation before any QM step).
    """
    name, smiles = resolve_smiles(name_or_smiles)
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"RDKit could not parse SMILES: {smiles}")
    mol = Chem.AddHs(mol)
    if AllChem.EmbedMolecule(mol, randomSeed=seed) != 0:
        # retry with random coords if ETKDG fails
        AllChem.EmbedMolecule(mol, randomSeed=seed, useRandomCoords=True)
    if ff.upper() == "MMFF" and AllChem.MMFFHasAllMoleculeParams(mol):
        AllChem.MMFFOptimizeMolecule(mol)
    else:
        AllChem.UFFOptimizeMolecule(mol)

    conf = mol.GetConformer()
    symbols = [a.GetSymbol() for a in mol.GetAtoms()]
    coords = [(conf.GetAtomPosition(i).x,
               conf.GetAtomPosition(i).y,
               conf.GetAtomPosition(i).z) for i in range(mol.GetNumAtoms())]
    # canonical SMILES without explicit Hs for display
    disp_smiles = Chem.MolToSmiles(Chem.RemoveHs(mol))
    return Molecule(name=name, smiles=disp_smiles, symbols=symbols,
                    coords=coords, rdkit_mol=mol)
