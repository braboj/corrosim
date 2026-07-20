# User journeys

The actor-level paths through corrosim, from evaluating the tool to screening
your own inhibitors. Each journey names the actor, goal, preconditions, steps,
result, the success signal that confirms it, what happens on failure, and the
next step it leads to. For the exact runnable commands see
[`examples/README.md`](../examples/README.md); for maintainer operations see
[`docs/PLAYBOOK.md`](PLAYBOOK.md).

## Journey 1: See an example result

- **Actor:** Evaluator deciding whether the tool fits.
- **Goal:** Look at a finished screening report without installing a quantum
  engine.
- **Preconditions:** The repo is checked out; Python 3.10+ with `pip` for the
  rebuild path (or just a browser for the tracked bundle).
- **Steps:**
  - Open the tracked bundle `cases/arghel/report/report.html` in a browser, or
  - Rebuild it from the committed result data: `pip install -e ".[viz,report]"`,
    then `python -m corrosim.runs.make_report`.
- **Result:** A self-contained HTML report (rankings, figures, tables) with no
  quantum engine and no server.
- **Success signal:** `make_report` prints `report written to
  cases/arghel/report/report.html (… kB, self-contained)`, plus the `.docx` and
  `tables/` lines; the browser shows figures inline.
- **If it fails:** With the result data absent (a fresh case with no
  `results/`), the report stage exits non-zero reporting that descriptors are
  missing. A stale browser tab shows nothing new until you reopen the file.
- **Next step:** You have seen the shape of a result; the friction is now running
  it on molecules *you* care about, which is journey 2 (fast) or journey 3
  (full).
- **Notes:** The report inlines its figures, CSS, and equations, so it opens
  offline (see ADR 0006/0008, report bundle layout). The rebuild reads only the
  tracked `cases/arghel/results/`, so it runs no DFT. A hosted gallery of the
  shipped cases is live at [corrosim.org](https://corrosim.org), built in CI
  from the tracked reports.

## Journey 2: Rank a shortlist fast

- **Actor:** Corrosion researcher triaging candidates.
- **Goal:** Rank a handful of molecules by reactivity in seconds, before
  committing to the heavy pipeline.
- **Preconditions:** The xTB engine is available (Linux/macOS `pip install -e
  ".[qm]"`, or the container). Molecules are library names or SMILES.
- **Steps:**
  - Run `corrosim screen --inhibitors "kaempferol,quercetin,isorhamnetin"
    --engine xtb --out report.html --csv results.csv`.
  - Batch a list with `--input molecules.csv`; add `--adsorption` for a UFF
    physisorption estimate; set `--metal` / `--medium` for a different system.
- **Result:** A best-first ranking (CSV) plus a self-contained HTML report.
- **Success signal:** The run prints `Ranking (best first):` with the scored
  table, then `HTML report: <path>` (and `Results CSV: <path>`); the top row is
  the predicted best inhibitor.
- **If it fails:** A name that is neither in the library nor a valid SMILES
  raises `'<x>' is neither a known inhibitor name nor a valid SMILES` (currently
  an uncaught traceback, not a one-line error). With no engine installed, the
  descriptor step fails importing `tblite`; `--plan` first confirms the steps
  without an engine.
- **Next step:** The ranking is a cheap single-point proxy; the natural friction
  is trusting it, which leads to the full pipeline (journey 3) or reproducing a
  validation case (journey 4).
- **Notes:** This is the fast screening tier, one single-point per molecule; the
  full multiscale pipeline is journey 3. Preview any run with `--plan`, which
  needs no engine (see examples/README.md, quick screen).

## Journey 3: Screen your own inhibitors end-to-end

- **Actor:** Corrosion researcher.
- **Goal:** Run the full multiscale study on your own molecules, metal, and
  medium.
- **Preconditions:** The QM engines are available (the container, or the `qm`
  extra on Linux/macOS). The metal is Fe, Cu, or Al; every atom has a UFF
  parameter (H, C, N, O, S, F, Cl, Br, P).
- **Steps:**
  - From flags: `corrosim run-study --name my-study --molecules
    "quercetin,benzotriazole,CCO" --metal Fe(110) --medium "1 M HCl"`, or
  - From a file: copy `examples/study.template.json`, edit it, and run
    `corrosim run-study --case ./my-study.json`.
- **Result:** A full report bundle (DFT descriptors, Fukui, ESP, Monte Carlo
  adsorption, MD RDF) under `cases/<name>/report/`, plus the study definition at
  `cases/<name>/study.json`.
- **Success signal:** Each stage logs `[<stage>] running ...` and the run ends
  with `study complete.`; the report stage prints `report written to
  cases/<name>/report/report.html`.
- **If it fails:** An out-of-envelope study exits `2` before any compute with a
  named-set message, for example `error: metal 'Zn' is not supported; the slab
  builder knows Al, Cu, Fe` or `error: molecule 'CI' carries element(s) I with no
  UFF parameters`. `--molecules` without `--name` exits with `--molecules needs
  --name`. A stage that errors mid-run stops the pipeline with `error: stage
  <stage> failed (exit N); stop.`, and a re-run resumes at that stage.
- **Next step:** Your first full run raises two frictions: is the ranking
  trustworthy (reproduce a paper, journey 4) and is DFT too slow (run detached
  and tune the basis, see PLAYBOOK). A compound missing from the library is
  journey 6.
- **Notes:** A study is declarable as data, so this needs no source edit and no
  rebuild (see ADR 0026, study as data). The flags form materializes the same
  `study.json` and delegates, so the two forms are interchangeable. The supported
  envelope is validated up front (see PLAYBOOK, run your own study). Molecules are
  names (resolved against the bundled library) or SMILES, so a novel compound
  needs no library edit; for a bromine set declare `basis: def2-SVP`.

## Journey 4: Reproduce a published validation case

- **Actor:** Researcher or reviewer assessing whether to trust the method.
- **Goal:** Reproduce a published system and compare corrosim against the paper.
- **Preconditions:** The QM engines are available (container or `qm` extra).
- **Steps:**
  - Run `corrosim run-study --case arghel` (or `phytic-acid`, `tetrazoles`,
    `tmp-smx`, `pyrazolylnucleosides`, `pyrazolo-pyrimidine`).
- **Result:** The same report bundle as a user study, for a system whose reported
  values are on record.
- **Success signal:** `study complete.` and the written report; the ah-ha is
  reading the report's ranking against the paper's, and finding the lead and the
  descriptor picture match the scorecard in `docs/validation.md`.
- **If it fails:** The shipped cases are inside the envelope, so validation
  passes; a failure here is environmental (a QM stage erroring because the engines
  are absent, i.e. run outside the container). The numbers reproducing only
  *qualitatively* is expected for some cases and is documented, not a failure.
- **Next step:** Once the method earns trust, the friction is applying it to your
  own set, which is journey 3.
- **Notes:** Each shipped case reproduces one paper's molecule set, substrate,
  and medium, spanning Fe / Cu / Al (see docs/validation.md, per-case scorecards;
  and ADR 0020, status vocabulary). The runner orchestrates the stage drivers in
  dependency order rather than reimplementing them (see ADR 0022, full-study
  orchestrator).

## Journey 5: Run the pipeline with only Docker

- **Actor:** Windows user, or anyone avoiding a Python/toolchain setup.
- **Goal:** Run the whole pipeline with only Docker installed.
- **Preconditions:** Docker is installed and running. A host `cases/` directory
  for the outputs.
- **Steps:**
  - Pull-and-run the published image: `docker run --rm -v "$PWD/cases:/work/cases"
    ghcr.io/braboj/corrosim corrosim run-study --case arghel`, or
  - Build locally: `docker compose run --rm qm corrosim run-study --case arghel`.
- **Result:** The full study runs inside the container; outputs land in the host
  `cases/`.
- **Success signal:** The same `[<stage>] running ...` / `study complete.` log as
  a native run, and the new `cases/<name>/` tree appearing on the host afterward.
- **If it fails:** If the Docker daemon is down the client errors before any
  run. The published `ghcr.io/braboj/corrosim:latest` is public, so a `denied` /
  `unauthorized` on `docker pull` points at a mistyped tag or an offline host;
  build locally with `docker compose` meanwhile. Mounting a volume over `/work`
  (instead of `/work/cases`) shadows the baked source and breaks
  `import corrosim`.
- **Next step:** Once a shipped case runs, the same command runs your own study
  (journey 3) with `--name ... --molecules ...` or a mounted `--case study.json`.
- **Notes:** The DFT/xTB engines have no Windows wheels, so the container is the
  cross-platform way to run them (see ADR 0027, tool-only distribution). Mount
  only `cases/` for outputs. The image is published per release (see
  `.github/workflows/release.yml`).

## Journey 6: Add an inhibitor to the library

- **Actor:** Researcher extending the compound set.
- **Goal:** Make a compound resolve by name across the CLI and the presets.
- **Preconditions:** Network access to PubChem (for a name/CAS lookup), or a
  known SMILES for an offline / air-gapped add.
- **Steps:**
  - Run `corrosim add-inhibitor <name-or-CAS>` to fetch and append the entry, or
  - Add it by hand to `src/corrosim/data/inhibitors.json`.
- **Result:** The compound resolves by name in `--inhibitors` / `--molecules` and
  in a study.
- **Success signal:** Prints `added '<name>': <smiles> (source: pubchem, cas:
  <cas>)` and exits `0`; the SMILES lets you eyeball that the right molecule was
  fetched.
- **If it fails:** PubChem returning nothing gives `error: PubChem returned no
  SMILES for '<query>'` (exit 1); a network outage gives `error: <url error>`; an
  ambiguous query gives `error: could not derive a library name; pass --name`. In
  an air-gapped plant with no PubChem, add the SMILES by hand instead.
- **Next step:** The compound now resolves by name, so it feeds straight into a
  screen (journey 2) or a study (journey 3).
- **Notes:** The inhibitor library is data, not code, so an add is a data edit and
  not a source change (see ADR 0017, data-driven inhibitor library). You can skip
  the library entirely by passing a SMILES directly wherever a molecule is
  accepted.

## Journey 7: Call corrosim from a script

- **Actor:** Developer integrating corrosim.
- **Goal:** Run a screen programmatically and get structured results.
- **Preconditions:** The package installed from a checkout (`pip install -e "."`),
  plus the engine extra for the chosen engine.
- **Steps:**
  - `import corrosim`, then `df, html = corrosim.screen([...], metal="Fe(110)",
    engine="xtb", out_html="report.html")`, then `corrosim.rank_inhibitors(df)`.
- **Result:** A pandas DataFrame of descriptors plus the rendered HTML.
- **Success signal:** `screen` returns a non-empty DataFrame and a written HTML
  path; `rank_inhibitors(df).iloc[0]["name"]` is the predicted best inhibitor.
- **If it fails:** A bad SMILES raises `ValueError: RDKit could not parse SMILES:
  <x>` and an unknown name raises `'<x>' is neither a known inhibitor name nor a
  valid SMILES`. Both are Python exceptions you catch in your own code, unlike
  the CLI.
- **Next step:** From a DataFrame you script your own ranking or filtering; the
  next friction is driving the *full* pipeline from Python, which means building a
  `CaseStudy` and calling the stages directly.
- **Notes:** corrosim is a library as well as a CLI; the same functions back
  both. For a fileless in-memory study, build a `CaseStudy` and drive the stages
  directly (see README.md, usage).
