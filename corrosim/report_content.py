"""corrosim.report_content.

The single home for the report's *narrative*: the standalone explanation under
each figure, the per-stage introductions, and the "Scientific basis & validation"
section woven from ``docs/pipeline.md`` and ``docs/validation.md``. Both report
renderers — HTML (``report``) and Word (``report_docx``) — import this so the two
outputs carry identical prose; only the formatting differs.

Keeping the prose here (not inline in a renderer) is what lets every graphic be
"standalone and explained" without duplicating the text across two formats. The
"Scientific basis" section is expressed as a small list of content items
(``("h3"|"p"|"eq"|"table", payload)``) that each renderer walks with ``inline_runs``
for light ``**bold**`` markup.
"""
from __future__ import annotations

# --- caveats -----------------------------------------------------------------
HEADLINE_CAVEAT = (
    "The flavonoids modelled here (kaempferol, quercetin, isorhamnetin) are "
    "documented major constituents of the Arghel (Solenostemma argel) extract, "
    "simulated as representatives — not a verified profile of a specific sample. "
    "Confirm composition by LC-MS/GC-MS before publication."
)

METHOD_CAVEAT = (
    "Global descriptors come from the frontier-orbital energies via Koopmans' "
    "theorem; ΔN uses the metal work function with η(metal) = 0. The Monte-Carlo "
    "and Brownian-MD stages use a classical van-der-Waals adsorption model — a "
    "physics-based screening surrogate, not a substitute for periodic DFT or for "
    "electrochemical validation. The composite ranking is a heuristic that orders "
    "candidates; it does not prove inhibition."
)

# --- per-stage introductions -------------------------------------------------
STAGE_INTROS = {
    "overview": (
        "corrosim screens a green corrosion inhibitor by zooming in over three "
        "stages, each answering one question about how strongly the molecule "
        "sticks to the metal. Stage 1 studies the isolated molecule with quantum "
        "chemistry (which electrons it will share, and from which atoms). Stage 2 "
        "searches for its best pose on the metal surface. Stage 3 lets that pose "
        "settle at room temperature and reads off the adsorption distance. The "
        "sections below follow that order; every figure is explained on its own, "
        "and the governing equations are collected in the Scientific basis section."
    ),
    "dft": (
        "Density-functional theory solves the molecule's electronic structure and "
        "gives the frontier orbitals — the HOMO (the electrons most willing to be "
        "shared with the metal) and the LUMO (the lowest empty level that can "
        "accept metal back-donation). Their energies yield the global reactivity "
        "descriptors (gap, hardness η, softness σ, electronegativity χ, "
        "electrophilicity ω, and the charge transfer ΔN) used to rank the "
        "candidates. See the Scientific basis section for each definition."
    ),
    "fukui": (
        "Global descriptors say how reactive a molecule is; the condensed Fukui "
        "functions say where. f⁻ locates the electron-donating atoms that "
        "coordinate the metal, f⁺ the electron-accepting (back-donation) atoms. "
        "For these flavonoids the highest-f⁻ sites are the catechol B-ring and "
        "3-OH oxygens."
    ),
    "esp": (
        "The molecular electrostatic-potential (ESP) map colours the electron-"
        "density surface by potential: red (negative) regions are electron-rich "
        "and nucleophilic — the metal-coordinating patches — corroborating the "
        "Fukui donor analysis."
    ),
    "mc": (
        "A Metropolis / simulated-annealing Monte-Carlo search nudges and rotates "
        "the rigid molecule thousands of times over an Fe(110) slab to find the "
        "lowest-energy pose, scored with the UFF van-der-Waals interaction. The "
        "flavonoids settle flat/parallel to the surface; the adsorption energy "
        "E_ads ≈ −16 kJ/mol places them in the physisorption regime."
    ),
    "md": (
        "Starting from the best Monte-Carlo pose, a Brownian rigid-body molecular-"
        "dynamics run lets the molecule jiggle at 298 K. The first peak of the "
        "metal-O radial distribution function g(r) sets the adsorption distance; "
        "a peak near 3.5 Å is physisorption range (a chemisorbed contact would sit "
        "closer)."
    ),
}

# --- standalone figure explanations, keyed by role ---------------------------
FIGURE_EXPLANATIONS = {
    "pipeline": (
        "The three-stage pipeline: a molecule (name or SMILES), a substrate metal "
        "and a corrosive medium go in; DFT reactivity descriptors, a Monte-Carlo "
        "adsorption pose, a Brownian-MD adsorption distance, a ranking and this "
        "report come out."
    ),
    "structures": (
        "The 2D structures of the modelled flavonoids. All three share the "
        "flavonol core (a 4-oxo chromone with a 3-OH and a B-ring); they differ in "
        "B-ring substitution — quercetin's catechol (3',4'-diOH), kaempferol's "
        "single 4'-OH, and isorhamnetin's 3'-OMe/4'-OH — which is what shifts their "
        "descriptors."
    ),
    "mo_diagram": (
        "Frontier-orbital energy levels (HOMO below, LUMO above, gap arrowed) for "
        "each molecule, with the Fe(110) Fermi level (−Φ = −4.82 eV) as the dashed "
        "reference. A HOMO lying near −Φ and a small gap favour electron sharing "
        "with the metal."
    ),
    "orbital_homo": (
        "The HOMO isosurface — the spatial shape of the electrons the molecule is "
        "most ready to donate to the metal. Its lobes sit over the electron-rich "
        "oxygen and ring systems that anchor adsorption."
    ),
    "orbital_lumo": (
        "The LUMO isosurface — the lowest empty level that accepts back-donation "
        "from the metal d-electrons, the complementary half of the donor-acceptor "
        "adsorption bond."
    ),
    "descriptors": (
        "The global reactivity descriptors side by side. Read together: a small "
        "gap and low hardness with high softness mark an easily-polarised, "
        "strongly-adsorbing inhibitor; a positive ΔN in the Lukovits window "
        "(0 < ΔN < 3.6) marks net electron donation to the metal."
    ),
    "protonation": (
        "Gap and ΔN for the neutral molecule vs its +1 cation in the acidic "
        "medium. Protonation lowers the gap and drives ΔN negative — the electron-"
        "poor cation stops donating — which is why the headline ranking is stated "
        "on the neutral form (ADR 0003), the species that actually dominates here "
        "(see Speciation)."
    ),
    "geometry": (
        "Descriptors on force-field vs DFT-optimised geometries. Relaxing each "
        "structure at B3LYP/6-31G(d) lowers the gap (~0.4–0.5 eV) and hardness and "
        "raises ΔN, but leaves both the gap and ΔN rankings unchanged — the lead "
        "assignments are geometry-robust."
    ),
    "fukui": (
        "Condensed Fukui functions per heavy atom: f⁻ (donor, binds the metal) "
        "and f⁺ (acceptor). The tallest f⁻ bars are the oxygens that coordinate "
        "the surface; the atom indices match the structure panel."
    ),
    "esp": (
        "The electron-density isosurface coloured by electrostatic potential. Red "
        "over the catechol and carbonyl oxygens is the electron-rich, metal-"
        "binding region; blue is electron-poor — a spatial confirmation of the "
        "Fukui donor sites."
    ),
    "mc_pose": (
        "Top and side views of the lowest-energy Monte-Carlo adsorption pose. The "
        "molecule lies flat/parallel to the Fe(110) slab, maximising oxygen "
        "contact with the surface — the geometry expected for physisorption."
    ),
    "mc_energy": (
        "The simulated-annealing energy trace: interaction energy vs Monte-Carlo "
        "step, converging to the best adsorption energy (dashed). The plateau near "
        "−16 kJ/mol is the reported E_ads."
    ),
    "rdf": (
        "The metal-O radial distribution function from the Brownian-MD trajectory. "
        "The first peak (green physisorption band, ~3.5 Å) is the adsorption "
        "distance; the shaded cutoff marks the chemisorption threshold it stays "
        "above."
    ),
}

# --- Scientific basis & validation (from pipeline.md + validation.md) ---------
# Each item is (kind, payload): "h3"/"p" -> str, "eq" -> equation key,
# "table" -> {"columns", "rows", "caption"}.
SCIENTIFIC_BASIS: list[tuple[str, object]] = [
    ("p",
     "This section consolidates the scientific basis (docs/pipeline.md) and the "
     "validation record (docs/validation.md) so the report is self-explanatory. "
     "The pipeline **screens and explains**; it does not prove inhibition — a "
     "candidate should still be confirmed electrochemically."),

    ("h3", "Governing equations"),
    ("p",
     "Stage 1 turns the two frontier-orbital energies into the standard reactivity "
     "descriptors via Koopmans' theorem; Stage 1b localises reactivity with the "
     "condensed Fukui functions; the speciation layer fixes the protonation state; "
     "and Stages 2–3 quantify adsorption. The full set is collected below."),
    ("eqgroups", None),   # renderer injects equations.EQUATION_GROUPS here

    ("h3", "Descriptor results (B3LYP/6-311++G(d,p), neutral, aqueous)"),
    ("p",
     "All three flavonoids show a positive ΔN inside the Lukovits window "
     "(0 < ΔN < 3.6): they donate electron density to the steel. **Quercetin** has "
     "the smallest gap and highest softness (the composite lead); **isorhamnetin** "
     "has the highest ΔN and total negative charge (electron-richest, via its "
     "methoxy group); kaempferol is third."),
    ("table", {
        "columns": ["Molecule", "HOMO (eV)", "LUMO (eV)", "Gap (eV)", "η (eV)",
                    "ΔN", "TNC"],
        "rows": [
            ["quercetin", "−6.134", "−2.052", "4.082", "2.041", "+0.178", "−4.71"],
            ["isorhamnetin", "−6.009", "−1.910", "4.099", "2.049", "+0.210", "−5.52"],
            ["kaempferol", "−6.193", "−2.047", "4.146", "2.073", "+0.169", "−4.42"],
        ],
        "caption": "Stage-1 DFT descriptors. Smallest gap = quercetin; highest "
                   "ΔN/TNC = isorhamnetin.",
    }),

    ("h3", "Protonation resolved by a computed pKaH"),
    ("p",
     "The most basic site is the 4-oxo carbonyl, a very weak base. A "
     "frequency-corrected DFT deprotonation cycle (B3LYP/6-311++G(d,p) + ddCOSMO "
     "on gas opt+freq geometries) gives pKaH ≈ **−13.3** (quercetin), −12.9 "
     "(kaempferol) and −5.1 (isorhamnetin) — all far below the 5–7% crossover — so "
     "every flavonoid is under 0.1% protonated in 1 M HCl. The neutral form is "
     "physically dominant, so the neutral-basis ranking is robust, not merely "
     "conventional; the ZPE/thermal/entropy correction moved every value more "
     "negative (more neutral) than the uncorrected cycle."),
    ("p",
     "*Caveat:* quercetin and kaempferol are clean minima (no imaginary "
     "frequencies); the isorhamnetin cation retained one small imaginary mode (a "
     "methoxy/hydroxyl torsion), so its value is less tightly determined — but it "
     "stays neutral and is not the lead. The lead (quercetin) rests on a clean, "
     "imaginary-frequency-free calculation."),

    ("h3", "Cross-check against published Fe(110) studies"),
    ("p",
     "corrosim's Stage-2 adsorption energies (−16.0 / −16.6 / −16.7 kJ/mol for "
     "quercetin / kaempferol / isorhamnetin) and Stage-3 Fe-O RDF first peaks "
     "(3.65 / 3.35 / 3.75 Å) agree with an independent black-tea-extract DFT study "
     "on Fe(110) (ΔGads ≈ −20 kJ/mol, quercetin strongest) and a lady's-mantle "
     "study (kaempferol reference) — same regime, same order."),

    ("h3", "Experimental anchor — Mohammed 2014 (Arghel on mild steel, 1 M HCl)"),
    ("p",
     "A direct experiment on the *same* system (Arghel methanolic extract on mild "
     "steel in 1 M HCl, 27 °C; PDP + EIS) reports inhibition efficiency rising to "
     "**99.62%** at 150 ppm, with a Langmuir adsorption free energy ΔG°ads ≈ −32.5 "
     "to −34.5 kJ/mol and a small (+26 mV) E_corr shift — a mixed-type inhibitor "
     "adsorbing physically. This validates the medium, the substrate, the overall "
     "efficacy and the physisorption mechanism."),
    ("table", {
        "columns": ["C_inh (ppm)", "I_corr (µA/cm²)", "−E_corr (mV)", "IE% (PDP)",
                    "R_ct (Ω·cm²)", "IE% (EIS)"],
        "rows": [
            ["blank", "447.0", "496", "—", "11.78", "—"],
            ["25", "14.7", "484", "96.71", "126.4", "90.68"],
            ["50", "10.67", "480", "97.60", "135.6", "91.31"],
            ["75", "1.99", "472", "99.55", "142.7", "91.74"],
            ["125", "1.90", "470", "99.57", "198.1", "94.05"],
            ["150", "1.66", "470", "99.62", "258.3", "95.43"],
        ],
        "caption": "Mohammed (2014), MSc, Alexandria University — the approved "
                   "experimental-validation source.",
    }),

    ("h3", "What this does and does not settle"),
    ("p",
     "**Confirmed:** the medium/substrate match, the physisorption mechanism "
     "(Langmuir, |ΔG°ads| ≳ 32 kJ/mol) consistent with the Stage-2 E_ads and the "
     "Stage-3 ~3.5 Å contact, and strong extract-level inhibition. **Not settled:** "
     "the extract study has no LC-MS/GC-MS, so it validates the extract, not the "
     "individual flavonoids — the quercetin > isorhamnetin > kaempferol ranking "
     "remains a computational prediction pending LC-MS plus isolated-compound "
     "electrochemistry. Note E_ads (single-molecule vdW) and ΔG°ads (whole-extract "
     "isotherm free energy) are different observables: they agree on regime and "
     "order of magnitude, not on the number."),
]


def inline_runs(text: str) -> list[tuple[str, bool]]:
    """Split ``**bold**`` markup into (text, is_bold) runs for either renderer."""
    runs: list[tuple[str, bool]] = []
    for i, chunk in enumerate(text.split("**")):
        if chunk:
            runs.append((chunk, i % 2 == 1))
    return runs
