"""
corrosim.figures
----------------
Publication-grade, template-style figures (cf. the pyrazolo-pyrimidine study
adopted in ADR 0002): 2D structures, frontier-orbital energy diagrams, global
reactivity-descriptor charts, and adsorption poses.

Stage-1 + Stage-2 figures here are pure RDKit/ASE/matplotlib and run anywhere.
The 3D HOMO/LUMO isosurfaces and MEP/ESP maps need PySCF cube files and run in
the QM container (see write_orbital_cube / write_mep_cube). Fukui/MC/MD figures
arrive with milestones M2/M3/M4.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
import numpy as np

# --- consistent publication palette ---------------------------------------
C_HOMO, C_LUMO, C_BAR, C_METAL = "#2b6cb0", "#dd6b20", "#319795", "#c53030"


def _save(fig, out, dpi=150):
    if out:
        fig.savefig(out, dpi=dpi, bbox_inches="tight")
        plt.close(fig)
    return out


# --- Fig 1 analog: 2D molecular structures ---------------------------------
def plot_structures(names, mols_per_row: int = 3, out: str | None = None):
    """RDKit 2D depiction grid for a list of library names / SMILES."""
    from rdkit import Chem
    from rdkit.Chem import Draw, AllChem
    from .molecules import resolve_smiles
    mols, legends = [], []
    for n in names:
        nm, smi = resolve_smiles(n)
        m = Chem.MolFromSmiles(smi)
        AllChem.Compute2DCoords(m)
        mols.append(m)
        legends.append(nm)
    img = Draw.MolsToGridImage(mols, legends=legends,
                               molsPerRow=min(mols_per_row, len(mols)),
                               subImgSize=(330, 270))
    if out:
        img.save(out)
    return img


# --- Frontier molecular-orbital energy diagram -----------------------------
def plot_mo_energy_diagram(rows, metal: str = "Fe(110)", out: str | None = None):
    """HOMO/LUMO levels per molecule with the gap and the metal Fermi level (-Φ).

    rows: list of dicts with at least name, homo_ev, lumo_ev.
    """
    from .descriptors import METAL_WORK_FUNCTION
    phi = METAL_WORK_FUNCTION.get(metal)
    n = len(rows)
    fig, ax = plt.subplots(figsize=(1.7 * n + 1.5, 5.2))
    for i, r in enumerate(rows):
        h, l = float(r["homo_ev"]), float(r["lumo_ev"])
        ax.hlines(h, i - 0.30, i + 0.30, color=C_HOMO, lw=2.5)
        ax.hlines(l, i - 0.30, i + 0.30, color=C_LUMO, lw=2.5)
        ax.annotate("", xy=(i, l), xytext=(i, h),
                    arrowprops=dict(arrowstyle="<->", color="grey", lw=1))
        ax.text(i + 0.02, (h + l) / 2, f"{l - h:.2f} eV", ha="left", va="center",
                fontsize=8, rotation=90, backgroundcolor="white")
        ax.text(i, h - 0.18, f"{h:.2f}", ha="center", va="top", fontsize=8, color=C_HOMO)
        ax.text(i, l + 0.18, f"{l:.2f}", ha="center", va="bottom", fontsize=8, color=C_LUMO)
    if phi is not None:
        ax.axhline(-phi, ls="--", color=C_METAL, lw=1.2)
        ax.text(n - 0.5, -phi + 0.08, f"−Φ({metal}) = −{phi:.2f} eV",
                color=C_METAL, va="bottom", ha="right", fontsize=8)
    ax.set_xticks(range(n))
    ax.set_xticklabels([r["name"] for r in rows], rotation=12, ha="right")
    ax.set_ylabel("Energy vs. vacuum (eV)")
    ax.set_title("Frontier molecular-orbital energies")
    ax.plot([], [], color=C_HOMO, lw=2.5, label="HOMO")
    ax.plot([], [], color=C_LUMO, lw=2.5, label="LUMO")
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    fig.tight_layout()
    return _save(fig, out) or fig


# --- Global reactivity-descriptor comparison -------------------------------
def plot_descriptor_comparison(rows, keys=None, out: str | None = None):
    """Grouped bar charts of the key global descriptors across molecules."""
    from .descriptors import DESCRIPTOR_META
    keys = keys or ["gap_ev", "hardness_ev", "softness_inv_ev",
                    "electrophilicity_ev", "delta_n"]
    names = [r["name"] for r in rows]
    fig, axes = plt.subplots(1, len(keys), figsize=(2.5 * len(keys), 3.6))
    axes = np.atleast_1d(axes)
    for ax, k in zip(axes, keys):
        vals = [float(r.get(k)) if r.get(k) is not None else np.nan for r in rows]
        ax.bar(names, vals, color=C_BAR)
        ax.set_title(DESCRIPTOR_META.get(k, (k,))[0], fontsize=9)
        ax.tick_params(axis="x", rotation=30, labelsize=8)
        ax.axhline(0, color="grey", lw=0.6)
    fig.tight_layout()
    return _save(fig, out) or fig


# --- Adsorption pose (template MC-config analog) ---------------------------
def plot_adsorption_pose(system, out: str | None = None):
    """Top and side views of a slab + adsorbed molecule (an AdsorptionSystem)."""
    from ase.visualize.plot import plot_atoms
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
    plot_atoms(system.combined, axes[0], rotation="0x,0y,0z")
    plot_atoms(system.combined, axes[1], rotation="-90x,0y,0z")
    axes[0].set_title(f"{system.metal}{system.surface} — top")
    axes[1].set_title("side")
    for a in axes:
        a.set_axis_off()
    fig.tight_layout()
    return _save(fig, out) or fig


# --- 3D orbital / ESP cubes (run in the QM container, after the DFT run) ----
def write_orbital_cube(symbols, coords, which: str = "homo",
                       basis: str = "6-311++G(d,p)", xc: str = "b3lyp",
                       charge: int = 0, out: str = "orbital.cube"):
    """Write a HOMO or LUMO .cube for a molecule (PySCF cubegen). Render the cube
    with py3Dmol (notebook) or skimage marching-cubes (static) — see M5."""
    from pyscf import gto, dft
    from pyscf.tools import cubegen
    mol = gto.M(atom=[[s, tuple(c)] for s, c in zip(symbols, coords)],
                basis=basis, charge=charge, verbose=0)
    mf = dft.RKS(mol); mf.xc = xc; mf.kernel()
    occ = mf.mo_occ
    idx = int(np.where(occ > 0)[0].max()) if which.lower() == "homo" \
        else int(np.where(occ == 0)[0].min())
    cubegen.orbital(mol, out, mf.mo_coeff[:, idx])
    return out


def write_mep_cube(symbols, coords, basis: str = "6-311++G(d,p)",
                   xc: str = "b3lyp", charge: int = 0, out: str = "mep.cube"):
    """Write a molecular electrostatic-potential .cube (PySCF cubegen.mep)."""
    from pyscf import gto, dft
    from pyscf.tools import cubegen
    mol = gto.M(atom=[[s, tuple(c)] for s, c in zip(symbols, coords)],
                basis=basis, charge=charge, verbose=0)
    mf = dft.RKS(mol); mf.xc = xc; mf.kernel()
    cubegen.mep(mol, out, mf.make_rdm1())
    return out
