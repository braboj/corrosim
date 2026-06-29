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


# --- Monte Carlo annealing energy trace -------------------------------------
def plot_mc_energy(result, out: str | None = None):
    """Adsorption-energy trace of the MC simulated annealing (an MCResult)."""
    e = np.asarray(result.energies)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot(e, color=C_BAR, lw=0.7)
    ax.axhline(result.e_ads_ev, color=C_METAL, ls="--", lw=1.2,
               label=f"best = {result.e_ads_ev:.3f} eV "
                     f"({result.e_ads_kjmol:.1f} kJ/mol) @ {result.best_height_A} Å")
    ax.set_xlabel("MC step"); ax.set_ylabel("Interaction energy (eV)")
    ax.set_title(f"Monte Carlo adsorption annealing — {result.metal}{result.surface}")
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    return _save(fig, out) or fig


# --- Fukui / dual-descriptor map (template local-reactivity figure) ---------
def plot_fukui(fukui, molecule=None, out: str | None = None, title: str | None = None):
    """Condensed Fukui f-/f+ per heavy atom (which atoms donate/accept electrons),
    optionally beside the 2D structure with atom indices. `fukui` is a FukuiResult
    or a dict with symbols/f_plus/f_minus."""
    def g(k):
        return getattr(fukui, k) if hasattr(fukui, k) else fukui[k]
    syms, fmin, fpl = g("symbols"), g("f_minus"), g("f_plus")
    heavy = [i for i, s in enumerate(syms) if s != "H"]
    labels = [f"{syms[i]}{i}" for i in heavy]
    fm = [fmin[i] for i in heavy]
    fp = [fpl[i] for i in heavy]

    struct = None
    if molecule is not None and getattr(molecule, "rdkit_mol", None) is not None:
        try:
            import io
            from rdkit import Chem
            from rdkit.Chem import AllChem
            from rdkit.Chem.Draw import rdMolDraw2D
            from PIL import Image
            mm = Chem.RemoveHs(molecule.rdkit_mol)
            AllChem.Compute2DCoords(mm)
            d = rdMolDraw2D.MolDraw2DCairo(480, 400)
            d.drawOptions().addAtomIndices = True
            rdMolDraw2D.PrepareAndDrawMolecule(d, mm)
            d.FinishDrawing()
            struct = Image.open(io.BytesIO(d.GetDrawingText()))
        except Exception:
            struct = None

    if struct is not None:
        fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(11.5, 4.5),
                                       gridspec_kw={"width_ratios": [1, 1.5]})
        ax0.imshow(struct); ax0.axis("off"); ax0.set_title("atom indices", fontsize=10)
    else:
        fig, ax1 = plt.subplots(figsize=(max(6.5, 0.45 * len(heavy)), 4.3))
    x = np.arange(len(heavy))
    ax1.bar(x - 0.2, fm, 0.4, label="f⁻ (donor / binds metal)", color=C_HOMO)
    ax1.bar(x + 0.2, fp, 0.4, label="f⁺ (acceptor)", color=C_LUMO)
    ax1.set_xticks(x); ax1.set_xticklabels(labels, rotation=90, fontsize=7)
    ax1.axhline(0, color="grey", lw=0.6)
    ax1.set_ylabel("Condensed Fukui")
    ax1.set_title(title or "Condensed Fukui functions (heavy atoms)", fontsize=11)
    ax1.legend(fontsize=8)
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


def write_orbital_cubes(symbols, coords, prefix: str = "mol",
                        basis: str = "6-31G(d)", xc: str = "b3lyp",
                        charge: int = 0, nx: int = 70) -> dict:
    """One SCF, then write {prefix}_homo.cube and {prefix}_lumo.cube. A modest
    basis is enough — orbital *shapes* are basis-insensitive, so this stays fast
    and looks the same as the descriptor-level basis. Returns {'homo','lumo'} paths.
    Run in the QM container; render with render_orbital()."""
    from pyscf import gto, dft
    from pyscf.tools import cubegen
    mol = gto.M(atom=[[s, tuple(c)] for s, c in zip(symbols, coords)],
                basis=basis, charge=charge, verbose=0)
    mf = dft.RKS(mol); mf.xc = xc; mf.kernel()
    occ = mf.mo_occ
    homo = int(np.where(occ > 0)[0].max())
    lumo = int(np.where(occ == 0)[0].min())
    paths = {"homo": f"{prefix}_homo.cube", "lumo": f"{prefix}_lumo.cube"}
    cubegen.orbital(mol, paths["homo"], mf.mo_coeff[:, homo], nx=nx, ny=nx, nz=nx)
    cubegen.orbital(mol, paths["lumo"], mf.mo_coeff[:, lumo], nx=nx, ny=nx, nz=nx)
    return paths


# --- isosurface renderer (needs scikit-image; runs anywhere) ----------------
_ELEM_COLOR = {"C": "#404040", "H": "#cccccc", "O": "#d00000", "N": "#1060d0",
               "S": "#d4a000", "F": "#30a030", "Cl": "#30a030", "P": "#d08000"}
_ELEM_SIZE = {"C": 45, "H": 16, "O": 65, "N": 58, "S": 80, "P": 80}


def render_orbital(cubefile, out: str | None = None, iso: float = 0.03,
                   title: str | None = None, elev: int = 16, azim: int = -64):
    """Render an orbital .cube as +/- isosurface lobes over the molecular skeleton.

    iso < 1 is treated as a fraction of the orbital's max amplitude (default 3 %).
    Needs scikit-image (marching cubes).
    """
    from ase.io.cube import read_cube
    from skimage import measure
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    with open(cubefile) as fh:
        cube = read_cube(fh)
    data = np.asarray(cube["data"], dtype=float)
    atoms = cube["atoms"]
    origin = np.asarray(cube.get("origin", [0, 0, 0]), dtype=float)[:3]
    cell = np.asarray(atoms.cell)
    spacing = np.array([cell[i, i] / data.shape[i] for i in range(3)])

    fig = plt.figure(figsize=(5.2, 5.2))
    ax = fig.add_subplot(111, projection="3d")
    level = iso * float(np.abs(data).max()) if abs(iso) < 1 else iso
    for lvl, color in ((level, C_HOMO), (-level, C_LUMO)):
        if not (data.min() < lvl < data.max()):
            continue
        verts, faces, _, _ = measure.marching_cubes(data, level=lvl, spacing=tuple(spacing))
        verts = verts + origin
        ax.add_collection3d(Poly3DCollection(verts[faces], alpha=0.45,
                                             facecolor=color, edgecolor="none"))
    P = atoms.get_positions()
    syms = atoms.get_chemical_symbols()
    for s, p in zip(syms, P):
        ax.scatter(*p, color=_ELEM_COLOR.get(s, "#888"),
                   s=_ELEM_SIZE.get(s, 40), depthshade=True, edgecolors="k", linewidths=0.3)
    # simple covalent bonds
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            d = np.linalg.norm(P[i] - P[j])
            if d < 1.75 and not (syms[i] == "H" and syms[j] == "H"):
                ax.plot(*zip(P[i], P[j]), color="#666", lw=1.2)
    lo = P.min(0) - 1.5
    hi = P.max(0) + 1.5
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
    try:
        ax.set_box_aspect(hi - lo)
    except Exception:
        pass
    ax.set_axis_off()
    ax.view_init(elev=elev, azim=azim)
    if title:
        ax.set_title(title, fontsize=11)
    fig.tight_layout()
    return _save(fig, out) or fig
