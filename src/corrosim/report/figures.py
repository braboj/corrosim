"""corrosim.figures.

Publication-grade, template-style figures: 2D structures, frontier-orbital
energy diagrams, global reactivity-descriptor charts, adsorption poses, and the
3D orbital / ESP isosurface renderers.

Everything here is pure RDKit/ASE/matplotlib/scikit-image and runs anywhere: the
3D HOMO/LUMO and MEP/ESP maps render the .cube files written by
corrosim.qm.cubes (which needs PySCF and runs in the QM container).
"""
from __future__ import annotations

import io
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from ase.io.cube import read_cube

if TYPE_CHECKING:
    import pandas as pd

    from ..adsorption.mc import MCResult
    from ..adsorption.md import MDResult

# --- consistent publication palette ---------------------------------------
C_HOMO, C_LUMO, C_BAR, C_METAL = "#2b6cb0", "#dd6b20", "#319795", "#c53030"

# Covalent-bond cutoff for the ball-and-stick skeleton in the 3D renderers: a
# pair closer than this (H-H excepted) is drawn as a bond.
BOND_CUTOFF_ANG = 1.75


def _save(fig, out, dpi=150):
    if out:
        fig.savefig(out, dpi=dpi, bbox_inches="tight")
        plt.close(fig)
    return out


def _read_cube_grid(path):
    """Read a .cube; return (data, atoms, origin_ang, spacing_ang)."""
    with open(path) as fh:
        cube = read_cube(fh)
    data = np.asarray(cube["data"], dtype=float)
    atoms = cube["atoms"]
    origin = np.asarray(cube.get("origin", [0, 0, 0]), dtype=float)[:3]
    cell = np.asarray(atoms.cell)
    spacing = np.array([cell[i, i] / data.shape[i] for i in range(3)])
    return data, atoms, origin, spacing


def _draw_bonds(ax, positions, symbols, **line_kw):
    """Draw covalent bonds — atom pairs within BOND_CUTOFF_ANG, minus H-H."""
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            dist = float(np.linalg.norm(positions[i] - positions[j]))
            if dist < BOND_CUTOFF_ANG and not (
                    symbols[i] == "H" and symbols[j] == "H"):
                ax.plot(*zip(positions[i], positions[j]), **line_kw)


def _style_3d_axes(ax, positions, margin, elev, azim):
    """Equal-aspect cubic limits (± margin Å), axes hidden, fixed 3D view."""
    lo = positions.min(0) - margin
    hi = positions.max(0) + margin
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
        homo, lumo = float(r["homo_ev"]), float(r["lumo_ev"])
        ax.hlines(homo, i - 0.30, i + 0.30, color=C_HOMO, lw=2.5)
        ax.hlines(lumo, i - 0.30, i + 0.30, color=C_LUMO, lw=2.5)
        ax.annotate("", xy=(i, lumo), xytext=(i, homo),
                    arrowprops=dict(arrowstyle="<->", color="grey", lw=1))
        ax.text(i + 0.02, (homo + lumo) / 2, f"{lumo - homo:.2f} eV", ha="left",
                va="center", fontsize=8, rotation=90, backgroundcolor="white")
        ax.text(i, homo - 0.18, f"{homo:.2f}", ha="center", va="top",
                fontsize=8, color=C_HOMO)
        ax.text(i, lumo + 0.18, f"{lumo:.2f}", ha="center", va="bottom",
                fontsize=8, color=C_LUMO)
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
        def val(form, mol):
            sub = df[(df.name == mol) & (df.form == form)
                     & (df.phase == "aqueous")]
            return sub[key].iloc[0] if len(sub) else float("nan")
        neu = [val("neutral", m) for m in order]
        pro = [val("protonated", m + "+H+") for m in order]
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
def _atom_index_structure(molecule):
    """Optional RDKit 2D depiction with atom indices, or None if unavailable."""
    if molecule is None or getattr(molecule, "rdkit_mol", None) is None:
        return None
    try:
        from PIL import Image
        from rdkit import Chem
        from rdkit.Chem import AllChem
        from rdkit.Chem.Draw import rdMolDraw2D
        mol2d = Chem.RemoveHs(molecule.rdkit_mol)
        AllChem.Compute2DCoords(mol2d)
        drawer = rdMolDraw2D.MolDraw2DCairo(480, 400)
        drawer.drawOptions().addAtomIndices = True
        rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol2d)
        drawer.FinishDrawing()
        return Image.open(io.BytesIO(drawer.GetDrawingText()))
    except Exception:
        # The atom-index structure panel is optional decoration; RDKit 2D
        # drawing / PIL can fail for many unrelated reasons (no 2D coords,
        # Cairo missing). Degrade to the bar-chart-only layout, never abort.
        return None


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
    def field(k):
        return getattr(fukui, k) if hasattr(fukui, k) else fukui[k]
    syms, fmin, fpl = field("symbols"), field("f_minus"), field("f_plus")
    heavy = [i for i, s in enumerate(syms) if s != "H"]
    labels = [f"{syms[i]}{i}" for i in heavy]
    fmin_heavy = [fmin[i] for i in heavy]
    fplus_heavy = [fpl[i] for i in heavy]

    struct = _atom_index_structure(molecule)
    if struct is not None:
        fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(11.5, 4.5),
                                       gridspec_kw={"width_ratios": [1, 1.5]})
        ax0.imshow(struct)
        ax0.axis("off")
        ax0.set_title("atom indices", fontsize=10)
    else:
        fig, ax1 = plt.subplots(figsize=(max(6.5, 0.45 * len(heavy)), 4.3))
    x = np.arange(len(heavy))
    ax1.bar(x - 0.2, fmin_heavy, 0.4, label="f⁻ (donor / binds metal)",
            color=C_HOMO)
    ax1.bar(x + 0.2, fplus_heavy, 0.4, label="f⁺ (acceptor)", color=C_LUMO)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=90, fontsize=7)
    ax1.axhline(0, color="grey", lw=0.6)
    ax1.set_ylabel("Condensed Fukui")
    ax1.set_title(title or "Condensed Fukui functions (heavy atoms)",
                  fontsize=11)
    ax1.legend(fontsize=8)
    fig.tight_layout()
    return _save(fig, out) or fig


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
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from skimage import measure
    data, atoms, origin, spacing = _read_cube_grid(cubefile)

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
    positions = atoms.get_positions()
    syms = atoms.get_chemical_symbols()
    for s, p in zip(syms, positions):
        ax.scatter(*p, color=_ELEM_COLOR.get(s, "#888"),
                   s=_ELEM_SIZE.get(s, 40), depthshade=True, edgecolors="k",
                   linewidths=0.3)
    _draw_bonds(ax, positions, syms, color="#666", lw=1.2)
    _style_3d_axes(ax, positions, margin=1.5, elev=elev, azim=azim)
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
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from scipy.ndimage import map_coordinates
    from skimage import measure

    rho, atoms, origin, spacing = _read_cube_grid(density_cube)
    # The ESP cube shares the density grid by construction; only its data used
    pot, _, _, _ = _read_cube_grid(esp_cube)

    if not (rho.min() < iso < rho.max()):
        # Fall back to a present level
        iso = float(np.quantile(rho[rho > 0], 0.85))
    # Marching cubes in *index* space so we can sample the ESP grid directly
    verts_idx, faces, _, _ = measure.marching_cubes(rho, level=iso)
    pot_at_vert = map_coordinates(pot, verts_idx.T, order=1, mode="nearest")
    # Physical coords (Å)
    verts = verts_idx * spacing + origin

    face_pot = pot_at_vert[faces].mean(axis=1)
    vmax = (np.percentile(np.abs(pot_at_vert), 100 - clip_pct)
            or np.abs(pot_at_vert).max())
    norm = mpl.colors.Normalize(vmin=-vmax, vmax=vmax)
    # Low/negative -> red
    cmap = plt.get_cmap("RdBu")
    facecolors = cmap(norm(face_pot))

    fig = plt.figure(figsize=(6.0, 5.2))
    ax = fig.add_subplot(111, projection="3d")
    surf = Poly3DCollection(verts[faces], facecolors=facecolors,
                            edgecolor="none", alpha=0.97)
    ax.add_collection3d(surf)

    positions = atoms.get_positions()
    syms = atoms.get_chemical_symbols()
    _draw_bonds(ax, positions, syms, color="#444", lw=1.0, alpha=0.6)
    _style_3d_axes(ax, positions, margin=1.8, elev=elev, azim=azim)
    cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax,
                      shrink=0.6, pad=0.02)
    cb.set_label("electrostatic potential (a.u.)", fontsize=9)
    cb.ax.tick_params(labelsize=7)
    if title:
        ax.set_title(title, fontsize=11)
    fig.tight_layout()
    return _save(fig, out) or fig
