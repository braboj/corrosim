"""
corrosim.descriptors
---------------------
Global reactivity descriptors used to rank corrosion inhibitors, computed from
the frontier-orbital energies (HOMO, LUMO) the way the literature does.

All energies in eV. Definitions (Koopmans' theorem):

    E_gap = E_LUMO - E_HOMO
    IP    = -E_HOMO
    EA    = -E_LUMO
    chi   = (IP + EA)/2          electronegativity
    eta   = (IP - EA)/2          chemical hardness   (= E_gap/2)
    sigma = 1/eta                chemical softness
    mu    = -chi                 chemical potential
    omega = mu^2 / (2 eta)       electrophilicity index
    dN    = (phi_metal - chi) / [2 (eta_metal + eta)]   fraction of e- transferred
    dE_back = -eta/4             back-donation energy

For dN the metal is described by its work function phi_metal (eV) with hardness
eta_metal ~ 0, following the convention in the recent papers. Surface presets
below; override per study if you use a different convention (some older work
uses chi_Fe = 7.0 eV instead of the work function).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

# Metal work functions (eV) for the common inhibitor substrates.
METAL_WORK_FUNCTION = {
    "Fe(110)": 4.82,
    "Fe": 4.82,
    "Cu(111)": 4.94,
    "Cu": 4.94,
    "Al(111)": 4.26,
    "Al": 4.26,
}
METAL_HARDNESS = 0.0   # eta_metal ~ 0, standard assumption


@dataclass
class Descriptors:
    homo_ev: float
    lumo_ev: float
    gap_ev: float
    ip_ev: float
    ea_ev: float
    electronegativity_ev: float        # chi
    hardness_ev: float                 # eta
    softness_inv_ev: float             # sigma
    chemical_potential_ev: float       # mu
    electrophilicity_ev: float         # omega
    delta_n: float                     # fraction of electrons transferred
    back_donation_ev: float            # dE_back
    metal: str
    phi_metal_ev: float

    def as_dict(self) -> dict:
        return asdict(self)


def total_negative_charge(charges) -> float:
    """TNC = sum of the negative atomic partial charges (Mulliken). A proxy for the
    molecule's electron-rich / nucleophilic character; reported by the methodology
    template (ADR 0002) alongside the global descriptors. Returns None if no
    charges are available."""
    if charges is None:
        return None
    return round(float(sum(q for q in charges if q < 0)), 4)


def compute_descriptors(homo_ev: float, lumo_ev: float,
                        metal: str = "Fe(110)",
                        phi_metal_ev: float | None = None) -> Descriptors:
    if phi_metal_ev is None:
        if metal not in METAL_WORK_FUNCTION:
            raise ValueError(
                f"Unknown metal '{metal}'. Known: {list(METAL_WORK_FUNCTION)}. "
                f"Pass phi_metal_ev explicitly to override."
            )
        phi_metal_ev = METAL_WORK_FUNCTION[metal]

    gap = lumo_ev - homo_ev
    ip = -homo_ev
    ea = -lumo_ev
    chi = (ip + ea) / 2.0
    eta = (ip - ea) / 2.0
    sigma = 1.0 / eta if eta != 0 else float("inf")
    mu = -chi
    omega = (mu * mu) / (2.0 * eta) if eta != 0 else float("inf")
    denom = 2.0 * (METAL_HARDNESS + eta)
    delta_n = (phi_metal_ev - chi) / denom if denom != 0 else float("inf")
    back = -eta / 4.0

    return Descriptors(
        homo_ev=homo_ev, lumo_ev=lumo_ev, gap_ev=gap,
        ip_ev=ip, ea_ev=ea,
        electronegativity_ev=chi, hardness_ev=eta, softness_inv_ev=sigma,
        chemical_potential_ev=mu, electrophilicity_ev=omega,
        delta_n=delta_n, back_donation_ev=back,
        metal=metal, phi_metal_ev=phi_metal_ev,
    )


# Human-readable labels + interpretation direction for reporting.
# 'better' = the direction associated with stronger predicted inhibition.
DESCRIPTOR_META = {
    "homo_ev":              ("E_HOMO (eV)",          "higher"),
    "lumo_ev":              ("E_LUMO (eV)",          "lower"),
    "gap_ev":               ("Energy gap ΔE (eV)",   "lower"),
    "hardness_ev":          ("Hardness η (eV)",      "lower"),
    "softness_inv_ev":      ("Softness σ (1/eV)",    "higher"),
    "electronegativity_ev": ("Electronegativity χ (eV)", "context"),
    "electrophilicity_ev":  ("Electrophilicity ω (eV)",  "context"),
    "delta_n":              ("ΔN (e- transferred)",  "0<ΔN<3.6"),
    "back_donation_ev":     ("Back-donation (eV)",   "context"),
}
