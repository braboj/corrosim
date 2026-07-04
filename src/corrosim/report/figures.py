"""corrosim.figures.

Publication-grade, template-style figures: 2D structures, frontier-orbital
energy diagrams, global reactivity-descriptor charts, and adsorption poses.

Stage-1 + Stage-2 figures here are pure RDKit/ASE/matplotlib and run anywhere.
The 3D HOMO/LUMO isosurfaces and MEP/ESP maps need PySCF cube files and run in
the QM container (see write_orbital_cube / write_mep_cube).
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    import numpy.typing as npt
    import pandas as pd

    from ..adsorption.mc import MCResult
    from ..adsorption.md import MDResult

# --- consistent publication palette ---------------------------------------
C_HOMO, C_LUMO, C_BAR, C_METAL = "#2b6cb0", "#dd6b20", "#319795", "#c53030"


def _save(fig, out, dpi=150):
    if out:
        fig.savefig(out, dpi=dpi, bbox_inches="tight")
        plt.close(fig)
    return out


# --- Fig 1 analog: 2D molecular structures ---------------------------------
def plot_structures(names: Sequence[str], mols_per_row: int = 3,
                    out: str | None = None) -> object:
    """RDKit 2D depiction grid for a list of library names / SMILES.

    Args:
        names: Library names or SMILES to depict.
        mols_per_row: Molecules per grid row.
        out: Output image path; if None the image is returned only.

    Returns:
        The rendered grid image (saved to ``out`` when given).
    """
    from rdkit import Chem
    from rdkit.Chem import AllChem, Draw

    from ..molecules import resolve_smiles
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
def plot_mo_energy_diagram(rows: list[dict], metal: str = "Fe(110)",
                           out: str | None = None) -> object:
    """HOMO/LUMO levels per molecule with the gap and the metal Fermi level.

    Args:
        rows: Dicts with at least ``name``, ``homo_ev``, ``lumo_ev``.
        metal: Substrate label selecting the work function Φ (drawn as -Φ).
        out: Output image path; if None the figure is returned only.

    Returns:
        The rendered figure (saved to ``out`` when given).
    """
    from ..qm.descriptors import METAL_WORK_FUNCTION
    phi = METAL_WORK_FUNCTION.get(metal)
    n = len(rows)
    fig, ax = plt.subplots(figsize=(1.7 * n + 1.5, 5.2))
    for i, r in enumerate(rows):
        h, l = float(r["homo_ev"]), float(r["lumo_ev"])
        ax.hlines(h, i - 0.30, i + 0.30, color=C_HOMO, lw=2.5)
        ax.hlines(l, i - 0.30, i + 0.30, color=C_LUMO, lw=2.5)
        ax.annotate("", xy=(i, l), xytext=(i, h),
                    arrowprops=dict(arrowstyle="<->", color="grey", lw=1))
        ax.text(i + 0.02, (h + l) / 2, f"{l - h:.2f} eV", ha="left",
                va="center", fontsize=8, rotation=90, backgroundcolor="white")
        ax.text(i, h - 0.18, f"{h:.2f}", ha="center", va="top", fontsize=8,
                color=C_HOMO)
        ax.text(i, l + 0.18, f"{l:.2f}", ha="center", va="bottom", fontsize=8,
                color=C_LUMO)
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
def plot_descriptor_comparison(rows: list[dict],
                               keys: Sequence[str] | None = None,
                               out: str | None = None) -> object:
    """Grouped bar charts of the key global descriptors across molecules.

    Args:
        rows: Per-molecule descriptor dicts (with ``name``).
        keys: Descriptor keys to chart; a sensible default set if None.
        out: Output image path; if None the figure is returned only.

    Returns:
        The rendered figure (saved to ``out`` when given).
    """
    from ..qm.descriptors import DESCRIPTOR_META
    keys = keys or ["gap_ev", "hardness_ev", "softness_inv_ev",
                    "electrophilicity_ev", "delta_n"]
    names = [r["name"] for r in rows]
    fig, axes = plt.subplots(1, len(keys), figsize=(2.5 * len(keys), 3.6))
    axes = np.atleast_1d(axes)
    for ax, k in zip(axes, keys):
        vals = [float(v) if (v := r.get(k)) is not None else np.nan
                for r in rows]
        ax.bar(names, vals, color=C_BAR)
        ax.set_title(DESCRIPTOR_META.get(k, (k,))[0], fontsize=9)
        ax.tick_params(axis="x", rotation=30, labelsize=8)
        ax.axhline(0, color="grey", lw=0.6)
    fig.tight_layout()
    return _save(fig, out) or fig


# --- Neutral vs protonated descriptor effect --------------------------------
def plot_protonation_effect(df: pd.DataFrame, order: Sequence[str],
                            out: str | None = None,
                            geometry_label: str = "B3LYP/6-311++G(d,p)"
                            ) -> object:
    """Gap and ΔN, neutral vs protonated (aqueous), across molecules.

    Args:
        df: The run_dft results frame (name/form/phase/gap_ev/delta_n).
        order: Molecule display order.
        out: Output image path; if None the figure is returned only.
        geometry_label: Geometry source shown in the title (e.g.
            'DFT-optimised, B3LYP/6-311++G(d,p)').

    Returns:
        The rendered figure (saved to ``out`` when given).
    """
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, key, title in ((axes[0], "gap_ev", "Energy gap ΔE (eV)"),
                           (axes[1], "delta_n", "ΔN (electrons transferred)")):
        def val(name, form, mol):
            sub = df[(df.name == mol) & (df.form == form)
                     & (df.phase == "aqueous")]
            return sub[key].iloc[0] if len(sub) else float("nan")
        neu = [val(m, "neutral", m) for m in order]
        pro = [val(m, "protonated", m + "+H+") for m in order]
        x = np.arange(len(order))
        ax.bar(x - 0.2, neu, 0.4, label="neutral", color=C_BAR)
        ax.bar(x + 0.2, pro, 0.4, label="protonated", color=C_LUMO)
        ax.set_xticks(x)
        ax.set_xticklabels(order, rotation=15)
        ax.set_title(title, fontsize=10)
        ax.axhline(0, color="grey", lw=0.6)
        ax.legend(fontsize=8)
    fig.suptitle(f"Neutral vs protonated (aqueous, {geometry_label})")
    fig.tight_layout()
    return _save(fig, out) or fig


def plot_geometry_comparison(ff_df: pd.DataFrame, opt_df: pd.DataFrame,
                             order: Sequence[str], phase: str = "aqueous",
                             keys: Sequence[str] = ("gap_ev", "hardness_ev",
                                                    "delta_n"),
                             out: str | None = None) -> object:
    """FF-geometry vs DFT-optimised-geometry descriptors (neutral, one phase).

    Per descriptor, grouped bars contrast the two geometry sources to document
    that the M1 refinement shifts magnitudes but preserves the ranking.

    Args:
        ff_df: Force-field-geometry descriptor frame (with form/phase).
        opt_df: DFT-optimised-geometry descriptor frame (with form/phase).
        order: Molecule display order.
        phase: The phase to compare ('gas' or 'aqueous').
        keys: Descriptor keys to contrast.
        out: Output image path; if None the figure is returned only.

    Returns:
        The rendered figure (saved to ``out`` when given).
    """
    from ..qm.descriptors import DESCRIPTOR_META

    def col(df, name, key):
        sub = df[(df.name == name) & (df.form == "neutral")
                 & (df.phase == phase)]
        return float(sub[key].iloc[0]) if len(sub) else float("nan")

    fig, axes = plt.subplots(1, len(keys), figsize=(4.0 * len(keys), 3.6))
    axes = np.atleast_1d(axes)
    x = np.arange(len(order))
    for ax, k in zip(axes, keys):
        ff = [col(ff_df, n, k) for n in order]
        op = [col(opt_df, n, k) for n in order]
        ax.bar(x - 0.2, ff, 0.4, label="FF geom", color=C_BAR)
        ax.bar(x + 0.2, op, 0.4, label="DFT-opt geom", color=C_METAL)
        ax.set_xticks(x)
        ax.set_xticklabels(order, rotation=18, ha="right")
        ax.set_title(DESCRIPTOR_META.get(k, (k, ""))[0], fontsize=10)
        ax.axhline(0, color="grey", lw=0.6)
    axes[0].legend(fontsize=8)
    fig.suptitle(f"Force-field vs DFT-optimised geometry "
                 f"(neutral, {phase}, B3LYP/6-311++G(d,p))")
    fig.tight_layout()
    return _save(fig, out) or fig


# --- Adsorption pose (template MC-config analog) ---------------------------
def plot_adsorption_pose(system: Any, out: str | None = None) -> object:
    """Top and side views of a slab + adsorbed molecule.

    Args:
        system: An object exposing ``combined`` (ASE Atoms), ``metal`` and
            ``surface`` — an AdsorptionSystem, MCResult or MDResult.
        out: Output image path; if None the figure is returned only.

    Returns:
        The rendered figure (saved to ``out`` when given).
    """
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
def plot_mc_energy(result: MCResult, out: str | None = None) -> object:
    """Adsorption-energy trace of the MC simulated annealing.

    Args:
        result: The Monte Carlo result (its ``energies`` trace).
        out: Output image path; if None the figure is returned only.

    Returns:
        The rendered figure (saved to ``out`` when given).
    """
    e = np.asarray(result.energies)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot(e, color=C_BAR, lw=0.7)
    ax.axhline(result.e_ads_ev, color=C_METAL, ls="--", lw=1.2,
               label=f"best = {result.e_ads_ev:.3f} eV "
                     f"({result.e_ads_kjmol:.1f} kJ/mol) "
                     f"@ {result.best_height_A} Å")
    ax.set_xlabel("MC step")
    ax.set_ylabel("Interaction energy (eV)")
    ax.set_title(f"Monte Carlo adsorption annealing — "
                 f"{result.metal}{result.surface}")
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    return _save(fig, out) or fig


# --- MD radial distribution function (adsorption distance) -------------------
def plot_rdf(result: MDResult, out: str | None = None) -> object:
    """metal-X radial distribution from MD; first peak = adsorption distance.

    A first peak < 3.5 Å indicates chemisorption-range contact.

    Args:
        result: The Brownian-MD result (its RDFs + peaks).
        out: Output image path; if None the figure is returned only.

    Returns:
        The rendered figure (saved to ``out`` when given).
    """
    m = result.metal
    r = np.asarray(result.rdf_r)
    fig, ax = plt.subplots(figsize=(7.2, 4))
    ax.axvspan(0, 3.5, color="#f0fff4")
    ax.axvline(3.5, color="grey", ls=":", lw=1)
    ax.text(3.52, 0.95, "3.5 Å (chemisorption cutoff)", fontsize=8,
            color="grey")
    mo = np.asarray(result.rdf_metal_O)
    if mo.any():
        ax.plot(r, mo / mo.max(), color=C_HOMO,
                label=f"{m}–O (peak {result.first_peak_metal_O} Å)")
    mn = np.asarray(result.rdf_metal_N)
    if mn.any():
        ax.plot(r, mn / mn.max(), color=C_LUMO,
                label=f"{m}–N (peak {result.first_peak_metal_N} Å)")
    ax.set_xlabel("r (Å)")
    ax.set_ylabel("g(r) (normalised)")
    ax.set_title(f"{m}–X radial distribution — {result.metal}{result.surface}, "
                 f"{int(result.temperature)} K")
    ax.legend(fontsize=8)
    ax.set_xlim(0, 6)
    fig.tight_layout()
    return _save(fig, out) or fig


# --- Fukui / dual-descriptor map (template local-reactivity figure) ---------
def plot_fukui(fukui: Any, molecule: Any = None, out: str | None = None,
               title: str | None = None) -> object:
    """Condensed Fukui f-/f+ per heavy atom (which atoms donate/accept).

    Args:
        fukui: A FukuiResult (or a dict with symbols/f_plus/f_minus).
        molecule: Optional Molecule; its 2D structure with atom indices is
            drawn beside the bars when available.
        out: Output image path; if None the figure is returned only.
        title: Optional chart title.

    Returns:
        The rendered figure (saved to ``out`` when given).
    """
    def g(k):
        return getattr(fukui, k) if hasattr(fukui, k) else fukui[k]
    syms, fmin, fpl = g("symbols"), g("f_minus"), g("f_plus")
    heavy = [i for i, s in enumerate(syms) if s != "H"]
    labels = [f"{syms[i]}{i}" for i in heavy]
    fm = [fmin[i] for i in heavy]
    fp = [fpl[i] for i in heavy]

    struct = None
    has_mol = getattr(molecule, "rdkit_mol", None) is not None
    if molecule is not None and has_mol:
        try:
            import io

            from PIL import Image
            from rdkit import Chem
            from rdkit.Chem import AllChem
            from rdkit.Chem.Draw import rdMolDraw2D
            mm = Chem.RemoveHs(molecule.rdkit_mol)
            AllChem.Compute2DCoords(mm)
            d = rdMolDraw2D.MolDraw2DCairo(480, 400)
            d.drawOptions().addAtomIndices = True
            rdMolDraw2D.PrepareAndDrawMolecule(d, mm)
            d.FinishDrawing()
            struct = Image.open(io.BytesIO(d.GetDrawingText()))
        except Exception:
            # The atom-index structure panel is optional decoration; RDKit 2D
            # drawing / PIL can fail for many unrelated reasons (no 2D coords,
            # Cairo missing). Degrade to the bar-chart-only layout, never abort.
            struct = None

    if struct is not None:
        fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(11.5, 4.5),
                                       gridspec_kw={"width_ratios": [1, 1.5]})
        ax0.imshow(struct)
        ax0.axis("off")
        ax0.set_title("atom indices", fontsize=10)
    else:
        fig, ax1 = plt.subplots(figsize=(max(6.5, 0.45 * len(heavy)), 4.3))
    x = np.arange(len(heavy))
    ax1.bar(x - 0.2, fm, 0.4, label="f⁻ (donor / binds metal)", color=C_HOMO)
    ax1.bar(x + 0.2, fp, 0.4, label="f⁺ (acceptor)", color=C_LUMO)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=90, fontsize=7)
    ax1.axhline(0, color="grey", lw=0.6)
    ax1.set_ylabel("Condensed Fukui")
    ax1.set_title(title or "Condensed Fukui functions (heavy atoms)",
                  fontsize=11)
    ax1.legend(fontsize=8)
    fig.tight_layout()
    return _save(fig, out) or fig


# --- 3D orbital / ESP cubes (run in the QM container, after the DFT run) ----
def write_orbital_cube(symbols: Sequence[str], coords: npt.ArrayLike,
                       which: str = "homo", basis: str = "6-311++G(d,p)",
                       xc: str = "b3lyp", charge: int = 0,
                       out: str = "orbital.cube") -> str:
    """Write a HOMO or LUMO .cube for a molecule (PySCF cubegen).

    Render the cube with py3Dmol (notebook) or skimage marching-cubes (static).

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        which: 'homo' or 'lumo'.
        basis: The AO basis set.
        xc: The exchange-correlation functional.
        charge: Net molecular charge.
        out: Output .cube path.

    Returns:
        The output .cube path.
    """
    from pyscf import dft, gto
    from pyscf.tools import cubegen
    mol = gto.M(atom=[[s, tuple(c)] for s, c in zip(symbols, coords)],
                basis=basis, charge=charge, verbose=0)
    mf = dft.RKS(mol)
    mf.xc = xc
    mf.kernel()
    occ = mf.mo_occ
    idx = int(np.where(occ > 0)[0].max()) if which.lower() == "homo" \
        else int(np.where(occ == 0)[0].min())
    cubegen.orbital(mol, out, mf.mo_coeff[:, idx])
    return out


def write_mep_cube(symbols: Sequence[str], coords: npt.ArrayLike,
                   basis: str = "6-311++G(d,p)", xc: str = "b3lyp",
                   charge: int = 0, out: str = "mep.cube") -> str:
    """Write a molecular electrostatic-potential .cube (PySCF cubegen.mep).

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        basis: The AO basis set.
        xc: The exchange-correlation functional.
        charge: Net molecular charge.
        out: Output .cube path.

    Returns:
        The output .cube path.
    """
    from pyscf import dft, gto
    from pyscf.tools import cubegen
    mol = gto.M(atom=[[s, tuple(c)] for s, c in zip(symbols, coords)],
                basis=basis, charge=charge, verbose=0)
    mf = dft.RKS(mol)
    mf.xc = xc
    mf.kernel()
    cubegen.mep(mol, out, mf.make_rdm1())
    return out


def write_orbital_cubes(symbols: Sequence[str], coords: npt.ArrayLike,
                        prefix: str = "mol", basis: str = "6-31G(d)",
                        xc: str = "b3lyp", charge: int = 0,
                        nx: int = 70) -> dict:
    """One SCF, then write ``{prefix}_homo.cube`` and ``{prefix}_lumo.cube``.

    A modest basis is enough — orbital *shapes* are basis-insensitive, so this
    stays fast and looks the same as the descriptor-level basis. Run in the QM
    container; render with render_orbital().

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        prefix: Output path prefix.
        basis: The AO basis set.
        xc: The exchange-correlation functional.
        charge: Net molecular charge.
        nx: Grid points per axis.

    Returns:
        The written paths keyed ``'homo'`` / ``'lumo'``.
    """
    from pyscf import dft, gto
    from pyscf.tools import cubegen
    mol = gto.M(atom=[[s, tuple(c)] for s, c in zip(symbols, coords)],
                basis=basis, charge=charge, verbose=0)
    mf = dft.RKS(mol)
    mf.xc = xc
    mf.kernel()
    occ = mf.mo_occ
    homo = int(np.where(occ > 0)[0].max())
    lumo = int(np.where(occ == 0)[0].min())
    paths = {"homo": f"{prefix}_homo.cube", "lumo": f"{prefix}_lumo.cube"}
    cubegen.orbital(mol, paths["homo"], mf.mo_coeff[:, homo],
                    nx=nx, ny=nx, nz=nx)
    cubegen.orbital(mol, paths["lumo"], mf.mo_coeff[:, lumo],
                    nx=nx, ny=nx, nz=nx)
    return paths


def write_density_esp_cubes(symbols: Sequence[str], coords: npt.ArrayLike,
                            prefix: str = "mol", basis: str = "6-31G(d)",
                            xc: str = "b3lyp", charge: int = 0,
                            solvent: str | None = None, nx: int = 80,
                            margin: float = 3.5) -> dict:
    """One SCF, then write the density and ESP cubes on a *shared* grid.

    ``{prefix}_density.cube`` and ``{prefix}_esp.cube``. Pairing the two on the
    same grid lets render_esp() colour the density isosurface by the MEP (the
    classic ESP map). The MEP integral is the slow part — a modest grid
    (nx≈80) and valence basis are plenty for a qualitative map. Run in the QM
    container; render with render_esp().

    Args:
        symbols: Element symbols.
        coords: Geometry in Angstrom.
        prefix: Output path prefix.
        basis: The AO basis set.
        xc: The exchange-correlation functional.
        charge: Net molecular charge.
        solvent: Implicit solvent ('water') or gas phase (None).
        nx: Grid points per axis.
        margin: Padding around the molecule (Å).

    Returns:
        The written paths keyed ``'density'`` / ``'esp'``.
    """
    from pyscf import dft, gto
    from pyscf.tools import cubegen
    mol = gto.M(atom=[[s, tuple(c)] for s, c in zip(symbols, coords)],
                basis=basis, charge=charge, verbose=0)
    mf = dft.RKS(mol)
    mf.xc = xc
    if solvent:
        mf = mf.ddCOSMO()
        mf.with_solvent.eps = 78.3553
    mf.kernel()
    dm = mf.make_rdm1()
    paths = {"density": f"{prefix}_density.cube", "esp": f"{prefix}_esp.cube"}
    # identical (mol, nx, margin) -> identical grid for both cubes
    cubegen.density(mol, paths["density"], dm, nx=nx, ny=nx, nz=nx,
                    margin=margin)
    cubegen.mep(mol, paths["esp"], dm, nx=nx, ny=nx, nz=nx, margin=margin)
    return paths


# --- isosurface renderer (needs scikit-image; runs anywhere) ----------------
_ELEM_COLOR = {"C": "#404040", "H": "#cccccc", "O": "#d00000", "N": "#1060d0",
               "S": "#d4a000", "F": "#30a030", "Cl": "#30a030", "P": "#d08000"}
_ELEM_SIZE = {"C": 45, "H": 16, "O": 65, "N": 58, "S": 80, "P": 80}


def render_orbital(cubefile: str, out: str | None = None, iso: float = 0.03,
                   title: str | None = None, elev: int = 16,
                   azim: int = -64) -> object:
    """Render an orbital .cube as +/- isosurface lobes over the skeleton.

    Args:
        cubefile: Path to the orbital .cube.
        out: Output image path; if None the figure is returned only.
        iso: Isosurface level; iso < 1 is treated as a fraction of the
            orbital's max amplitude (default 3 %).
        title: Optional title.
        elev: 3D view elevation.
        azim: 3D view azimuth.

    Returns:
        The rendered figure (saved to ``out`` when given). Needs scikit-image.
    """
    from ase.io.cube import read_cube
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from skimage import measure
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
        verts, faces, _, _ = measure.marching_cubes(data, level=lvl,
                                                    spacing=tuple(spacing))
        verts = verts + origin
        ax.add_collection3d(Poly3DCollection(verts[faces], alpha=0.45,
                                             facecolor=color, edgecolor="none"))
    P = atoms.get_positions()
    syms = atoms.get_chemical_symbols()
    for s, p in zip(syms, P):
        ax.scatter(*p, color=_ELEM_COLOR.get(s, "#888"),
                   s=_ELEM_SIZE.get(s, 40), depthshade=True, edgecolors="k",
                   linewidths=0.3)
    # simple covalent bonds
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            d = np.linalg.norm(P[i] - P[j])
            if d < 1.75 and not (syms[i] == "H" and syms[j] == "H"):
                ax.plot(*zip(P[i], P[j]), color="#666", lw=1.2)
    lo = P.min(0) - 1.5
    hi = P.max(0) + 1.5
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    try:
        ax.set_box_aspect(hi - lo)
    except (AttributeError, ValueError):
        # set_box_aspect was added in matplotlib 3.3 (AttributeError on older),
        # and a degenerate zero-span axis raises ValueError. Aspect is cosmetic.
        pass
    ax.set_axis_off()
    ax.view_init(elev=elev, azim=azim)
    if title:
        ax.set_title(title, fontsize=11)
    fig.tight_layout()
    return _save(fig, out) or fig


def render_esp(density_cube: str, esp_cube: str, out: str | None = None,
               iso: float = 0.002, title: str | None = None,
               clip_pct: float = 2.0, elev: int = 16,
               azim: int = -64) -> object:
    """Render a molecular electrostatic-potential (ESP/MEP) map.

    The electron-density isosurface (default 0.002 e/bohr³) is coloured by the
    electrostatic potential sampled on it. Red = negative potential
    (electron-rich, nucleophilic O lone pairs — the metal-binding sites);
    blue = positive.

    Args:
        density_cube: Path to the density .cube.
        esp_cube: Path to the ESP .cube (must share ``density_cube``'s grid).
        out: Output image path; if None the figure is returned only.
        iso: Density isosurface level.
        title: Optional title.
        clip_pct: Symmetric colour-scale clip percentile so a few near-nucleus
            outliers don't wash out the map.
        elev: 3D view elevation.
        azim: 3D view azimuth.

    Returns:
        The rendered figure (saved to ``out`` when given). Needs
        scikit-image + scipy.
    """
    import matplotlib as mpl
    from ase.io.cube import read_cube
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from scipy.ndimage import map_coordinates
    from skimage import measure

    with open(density_cube) as fh:
        dens = read_cube(fh)
    with open(esp_cube) as fh:
        esp = read_cube(fh)
    rho = np.asarray(dens["data"], dtype=float)
    pot = np.asarray(esp["data"], dtype=float)
    atoms = dens["atoms"]
    origin = np.asarray(dens.get("origin", [0, 0, 0]), dtype=float)[:3]
    cell = np.asarray(atoms.cell)
    spacing = np.array([cell[i, i] / rho.shape[i] for i in range(3)])

    if not (rho.min() < iso < rho.max()):
        # fall back to a present level
        iso = float(np.quantile(rho[rho > 0], 0.85))
    # marching cubes in *index* space so we can sample the ESP grid directly
    verts_idx, faces, _, _ = measure.marching_cubes(rho, level=iso)
    pot_at_vert = map_coordinates(pot, verts_idx.T, order=1, mode="nearest")
    # physical coords (Å)
    verts = verts_idx * spacing + origin

    face_pot = pot_at_vert[faces].mean(axis=1)
    vmax = (np.percentile(np.abs(pot_at_vert), 100 - clip_pct)
            or np.abs(pot_at_vert).max())
    norm = mpl.colors.Normalize(vmin=-vmax, vmax=vmax)
    # low/negative -> red
    cmap = plt.get_cmap("RdBu")
    facecolors = cmap(norm(face_pot))

    fig = plt.figure(figsize=(6.0, 5.2))
    ax = fig.add_subplot(111, projection="3d")
    surf = Poly3DCollection(verts[faces], facecolors=facecolors,
                            edgecolor="none", alpha=0.97)
    ax.add_collection3d(surf)

    P = atoms.get_positions()
    syms = atoms.get_chemical_symbols()
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            d = np.linalg.norm(P[i] - P[j])
            if d < 1.75 and not (syms[i] == "H" and syms[j] == "H"):
                ax.plot(*zip(P[i], P[j]), color="#444", lw=1.0, alpha=0.6)
    lo, hi = P.min(0) - 1.8, P.max(0) + 1.8
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    try:
        ax.set_box_aspect(hi - lo)
    except (AttributeError, ValueError):
        # set_box_aspect was added in matplotlib 3.3 (AttributeError on older),
        # and a degenerate zero-span axis raises ValueError. Aspect is cosmetic.
        pass
    ax.set_axis_off()
    ax.view_init(elev=elev, azim=azim)
    cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax,
                      shrink=0.6, pad=0.02)
    cb.set_label("electrostatic potential (a.u.)", fontsize=9)
    cb.ax.tick_params(labelsize=7)
    if title:
        ax.set_title(title, fontsize=11)
    fig.tight_layout()
    return _save(fig, out) or fig
