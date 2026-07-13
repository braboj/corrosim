"""corrosim.runs.run_study.

One command for the full multiscale study: orchestrates the stage drivers in
dependency order so a case goes from its molecule set to a finished report
bundle without hand-running each module or tracking the QM-vs-venv split. It
orchestrates rather than reimplements: each stage calls the existing driver
``main()`` with the case's own output routing, so no paths are threaded through.

::

    QM container (pyscf/tblite)             venv (classical)
    dft -> fukui -> [pka] -> [cubes] -> mc -> md -> figures -> report
     |       |        |        |        |     |       |          |
   _ff.csv  *_fukui  pka.json cubes/  mc.json md.json figures/  report/
   (+_opt)   .json                                              bundle

Bracketed stages are opt-in enrichments (``--with-pka`` / ``--with-cubes``);
``--optimize`` adds the DFT-relaxed matrix to the dft stage. ``--plan`` prints
this order without computing; ``--only`` / ``--skip`` select stages; ``--force``
recomputes a stage whose output already exists (otherwise it is skipped).

The corrosim-qm image carries both the QM and the classical dependencies, so on
Windows the whole study runs in one container invocation::

    docker compose run --rm qm corrosim-run-study --case arghel
"""
from __future__ import annotations

import argparse
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from corrosim.presets import CaseStudy, case_study
from corrosim.runs._cli import add_case_arg, stderr_log

# A stage's presentation (desc / out_display) and behaviour (run / outputs) are
# functions of the resolved case and the parsed flags, so each field is a small
# callable rather than a static string.
_StageFn = Callable[[CaseStudy, argparse.Namespace], object]


@dataclass(frozen=True)
class Stage:
    """One pipeline stage: how to describe it, run it, and detect its output.

    Attributes:
        key: The short stage name used by ``--only`` / ``--skip`` and the plan.
        env: ``"qm"`` (needs pyscf/tblite) or ``"venv"`` (classical) — groups
            the stage in the plan and drives the container reminder.
        default_on: Whether the stage runs without an explicit opt-in flag.
        idempotent: Whether an existing output lets the stage be skipped (the
            terminal render stages always re-run so the report tracks the data).
        desc: ``(case, args) -> str`` describing what the stage computes.
        out_display: ``(case, args) -> str`` naming where it writes, for --plan.
        run: ``(case, args) -> int`` calling the driver ``main()`` (0 on ok).
        outputs: ``(case, args) -> list[str]`` of files whose presence means the
            stage is already done (empty for the always-render stages).
    """

    key: str
    env: str
    default_on: bool
    idempotent: bool
    desc: Callable[[CaseStudy, argparse.Namespace], str]
    out_display: Callable[[CaseStudy, argparse.Namespace], str]
    run: Callable[[CaseStudy, argparse.Namespace], int]
    outputs: Callable[[CaseStudy, argparse.Namespace], list[str]]


# ---- per-stage runners: each lazily imports its driver so --plan (and a venv
# install) never pays the QM/matplotlib import cost of a stage it will not run.


def _run_dft(case: CaseStudy, args: argparse.Namespace) -> int:
    """Run the force-field descriptor matrix, plus the DFT-opt one on request.

    The two matrices land at distinct paths (``_ff`` / ``_opt``), so each
    sub-run is guarded independently: adding ``--optimize`` to a case that
    already has the force-field matrix computes only the missing opt matrix.

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The first non-zero driver exit code, or 0 if all sub-runs succeed.
    """
    from corrosim.runs import run_dft

    rd = case.results_dir
    rc = 0
    if args.force or not os.path.exists(f"{rd}/dft_descriptors_ff.csv"):
        rc = run_dft.main(["--case", args.case])
    need_opt = args.optimize and (
        args.force or not os.path.exists(f"{rd}/dft_descriptors_opt.csv"))
    if rc == 0 and need_opt:
        rc = run_dft.main(["--case", args.case, "--optimize"])
    return rc


def _run_fukui(case: CaseStudy, args: argparse.Namespace) -> int:
    """Run the condensed Fukui / dual-descriptor stage.

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The driver exit code (0 on success).
    """
    from corrosim.runs import run_fukui

    argv = ["--case", args.case]
    # run_fukui defaults to a light Pople set (diffuse sets break the
    # Mulliken-condensed Fukui), but that set has no bromine; a heavier-element
    # case declares a non-diffuse def2 basis, so pass it through for full
    # periodic-table coverage, mirroring the cube stage.
    if case.basis.lower().startswith("def2"):
        argv += ["--basis", case.basis]
    return run_fukui.main(argv)


def _run_pka(case: CaseStudy, args: argparse.Namespace) -> int:
    """Run the conjugate-acid pKaH stage, persisting to the case ``pka.json``.

    ``run_pka`` does not auto-route its output, so the path make_report reads is
    supplied explicitly here.

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The driver exit code (0 on success).
    """
    from corrosim.runs import run_pka

    return run_pka.main(
        ["--case", args.case, "--out-json", f"{case.results_dir}/pka.json"])


def _run_cubes(case: CaseStudy, args: argparse.Namespace) -> int:
    """Run the HOMO/LUMO + density/ESP cube stage for the case's molecules.

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The driver exit code (0 on success).
    """
    from corrosim.runs import make_cubes

    argv = ["--molecules", ",".join(case.molecule_list()),
            "--what", "orbital,esp"]
    # A heavier-element case declares a def2 basis; the Pople sets lack bromine,
    # so pass the case basis to the cube SCF, not make_cubes' light default.
    if case.basis.lower().startswith("def2"):
        argv += ["--basis", case.basis]
    return make_cubes.main(argv)


def _run_mc(case: CaseStudy, args: argparse.Namespace) -> int:
    """Run the Monte Carlo adsorption pose search.

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The driver exit code (0 on success).
    """
    from corrosim.runs import run_mc

    return run_mc.main(["--case", args.case])


def _run_md(case: CaseStudy, args: argparse.Namespace) -> int:
    """Run the Brownian MD stage (metal-X RDF).

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The driver exit code (0 on success).
    """
    from corrosim.runs import run_md

    return run_md.main(["--case", args.case])


def _run_figures(case: CaseStudy, args: argparse.Namespace) -> int:
    """Render the manuscript figure set into the case report bundle.

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The driver exit code (0 on success).
    """
    from corrosim.runs import make_figures

    return make_figures.main(["--case", args.case])


def _run_report(case: CaseStudy, args: argparse.Namespace) -> int:
    """Assemble the self-contained report bundle (html + docx + tables).

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The driver exit code (0 on success; non-zero if descriptors are absent).
    """
    from corrosim.runs import make_report

    return make_report.main(["--case", args.case])


# ---- per-stage output paths, for the idempotent skip check.


def _out_dft(case: CaseStudy, args: argparse.Namespace) -> list[str]:
    """Descriptor-matrix outputs (adds the opt matrix under ``--optimize``).

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The CSV path(s) whose presence means the dft stage is done.
    """
    rd = case.results_dir
    outs = [f"{rd}/dft_descriptors_ff.csv"]
    if args.optimize:
        outs.append(f"{rd}/dft_descriptors_opt.csv")
    return outs


def _out_fukui(case: CaseStudy, args: argparse.Namespace) -> list[str]:
    """Per-molecule Fukui JSON outputs.

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        One ``<name>_fukui.json`` path per molecule.
    """
    rd = case.results_dir
    return [f"{rd}/{name}_fukui.json" for name in case.molecule_list()]


def _out_pka(case: CaseStudy, args: argparse.Namespace) -> list[str]:
    """The pKaH JSON output.

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The ``pka.json`` path.
    """
    return [f"{case.results_dir}/pka.json"]


def _out_cubes(case: CaseStudy, args: argparse.Namespace) -> list[str]:
    """Representative cube outputs (one orbital + one ESP cube per molecule).

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The cube paths that stand in for a completed cube stage.
    """
    return [f"cubes/{name}_{which}.cube"
            for name in case.molecule_list() for which in ("homo", "esp")]


def _out_mc(case: CaseStudy, args: argparse.Namespace) -> list[str]:
    """The Monte Carlo adsorption JSON output.

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The ``mc_adsorption.json`` path.
    """
    return [f"{case.results_dir}/mc_adsorption.json"]


def _out_md(case: CaseStudy, args: argparse.Namespace) -> list[str]:
    """The MD RDF JSON output.

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The ``md_rdf.json`` path.
    """
    return [f"{case.results_dir}/md_rdf.json"]


def _no_outputs(case: CaseStudy, args: argparse.Namespace) -> list[str]:
    """No skip outputs: the render stages always re-run to track the data.

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        An empty list.
    """
    return []


def _desc_dft(case: CaseStudy, args: argparse.Namespace) -> str:
    """Plan description for the dft stage (names the level, notes --optimize).

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The stage description line.
    """
    level = f"{case.xc.upper()}/{case.basis}"
    desc = f"DFT descriptor matrix {level} + ddCOSMO water"
    return desc + (" (+ DFT-opt geometry)" if args.optimize else "")


def _out_dft_display(case: CaseStudy, args: argparse.Namespace) -> str:
    """Plan output path for the dft stage (adds the opt CSV under --optimize).

    Args:
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        The stage output line.
    """
    base = "results/dft_descriptors_ff.csv"
    return base + (" (+ _opt.csv)" if args.optimize else "")


# Ordered pipeline: the QM stages first (dft, fukui, and the enrichments), then
# the classical stages. --only / --skip select from this order.
STAGES: list[Stage] = [
    Stage("dft", "qm", True, True, _desc_dft, _out_dft_display,
          _run_dft, _out_dft),
    Stage("fukui", "qm", True, True,
          lambda c, a: "condensed Fukui / dual descriptor, B3LYP/6-31G(d)",
          lambda c, a: "results/<name>_fukui.json", _run_fukui, _out_fukui),
    Stage("pka", "qm", False, True,
          lambda c, a: "conjugate-acid pKaH from a DFT cycle",
          lambda c, a: "results/pka.json", _run_pka, _out_pka),
    Stage("cubes", "qm", False, True,
          lambda c, a: "HOMO/LUMO + density/ESP cubes",
          lambda c, a: "cubes/<name>_*.cube", _run_cubes, _out_cubes),
    Stage("mc", "venv", True, True,
          lambda c, a: "Monte Carlo adsorption pose search",
          lambda c, a: "results/mc_adsorption.json", _run_mc, _out_mc),
    Stage("md", "venv", True, True,
          lambda c, a: "Brownian MD -> metal-X RDF",
          lambda c, a: "results/md_rdf.json", _run_md, _out_md),
    Stage("figures", "venv", True, False,
          lambda c, a: "render the manuscript figure set",
          lambda c, a: "report/figures/", _run_figures, _no_outputs),
    Stage("report", "venv", True, False,
          lambda c, a: "assemble the self-contained bundle",
          lambda c, a: f"{c.report_dir}/ (html + docx + tables)",
          _run_report, _no_outputs),
]

# Opt-in enrichment stages and the flag that turns each on.
_ENRICHMENT_FLAG = {"pka": "with_pka", "cubes": "with_cubes"}


def _parse_keys(spec: str | None) -> list[str]:
    """Split a comma-separated ``--only`` / ``--skip`` value into stage keys.

    Args:
        spec: The raw flag value, or None.

    Returns:
        The non-empty, stripped keys, order preserved.
    """
    return [k.strip() for k in spec.split(",") if k.strip()] if spec else []


def _stage_wanted(stage: Stage, args: argparse.Namespace) -> bool:
    """Whether a stage runs from the default/enrichment flags (not --only).

    Args:
        stage: The stage to test.
        args: Parsed CLI arguments.

    Returns:
        True if the stage is default-on or its enrichment flag is set.
    """
    if stage.default_on:
        return True
    flag = _ENRICHMENT_FLAG.get(stage.key)
    return flag is not None and bool(getattr(args, flag))


def select_stages(args: argparse.Namespace) -> list[Stage]:
    """Resolve the ordered stage list to run from the selection flags.

    ``--only`` restricts to a named set; otherwise the default-on stages plus
    any enrichment whose flag is set. ``--skip`` then removes from either.

    Args:
        args: Parsed CLI arguments.

    Returns:
        The stages to run, in pipeline order.

    Raises:
        SystemExit: If ``--only`` or ``--skip`` names an unknown stage.
    """
    only = _parse_keys(args.only)
    skip = _parse_keys(args.skip)
    valid = {s.key for s in STAGES}
    bad = [k for k in only + skip if k not in valid]
    if bad:
        raise SystemExit(
            f"unknown stage(s): {', '.join(bad)}; "
            f"valid stages: {', '.join(s.key for s in STAGES)}")
    chosen = []
    for stage in STAGES:
        wanted = stage.key in only if only else _stage_wanted(stage, args)
        if wanted and stage.key not in skip:
            chosen.append(stage)
    return chosen


def _skipped_enrichments(stages: list[Stage]) -> str:
    """Note which enrichment stages are absent, and the flag that adds each.

    Args:
        stages: The selected stages.

    Returns:
        A comma-joined hint (empty when every enrichment is selected).
    """
    chosen = {s.key for s in stages}
    notes = []
    if "pka" not in chosen:
        notes.append("pka (add --with-pka)")
    if "cubes" not in chosen:
        notes.append("cubes (add --with-cubes)")
    return ", ".join(notes)


def format_study_plan(
    case: CaseStudy,
    stages: list[Stage],
    args: argparse.Namespace,
) -> str:
    """Describe the ordered steps of a study run, for ``--plan`` (a dry run).

    Groups the selected stages by environment (QM container vs venv), numbers
    them in run order, and names each stage's output, mirroring the quick
    screen's ``corrosim --plan``.

    Args:
        case: The resolved case study.
        stages: The selected stages, in order.
        args: Parsed CLI arguments.

    Returns:
        A newline-separated, human-readable plan.
    """
    mols = case.molecule_list()
    lines = [f"Plan - full multiscale study of {len(mols)} molecule(s) on "
             f"{case.metal}, medium {case.medium!r}:"]
    groups = (("qm", "QM container (pyscf/tblite):"),
              ("venv", "venv (classical):"))
    step = 0
    for env, header in groups:
        group = [s for s in stages if s.env == env]
        if not group:
            continue
        lines.append(f"  {header}")
        for stage in group:
            step += 1
            desc = stage.desc(case, args)
            out = stage.out_display(case, args)
            lines.append(f"    {step}. {stage.key:<8} {desc:<52} -> {out}")
    skipped = _skipped_enrichments(stages)
    if skipped:
        lines.append(f"  Skipped enrichments: {skipped}.")
    lines.append("  (xtb/pyscf have no Windows wheels -> run the whole study "
                 "in the corrosim-qm container on Windows.)")
    lines.append("  Nothing computed (--plan).")
    return "\n".join(lines)


def _should_skip(
    stage: Stage,
    case: CaseStudy,
    args: argparse.Namespace,
) -> bool:
    """Whether a stage can be skipped because its output already exists.

    Args:
        stage: The stage to test.
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        True when the stage is idempotent, ``--force`` is off, and every one of
        its declared outputs is present.
    """
    if not stage.idempotent or args.force:
        return False
    outs = stage.outputs(case, args)
    return bool(outs) and all(os.path.exists(o) for o in outs)


def _run_pipeline(
    stages: list[Stage],
    case: CaseStudy,
    args: argparse.Namespace,
) -> int:
    """Run the selected stages in order, skip done ones, stop on failure.

    Args:
        stages: The selected stages, in order.
        case: The resolved case study.
        args: Parsed CLI arguments.

    Returns:
        0 when every run stage succeeds, else the first non-zero exit code.
    """
    for stage in stages:
        if _should_skip(stage, case, args):
            stderr_log(f"skip {stage.key}: output present "
                       f"(--force to recompute)")
            continue
        stderr_log(f"[{stage.key}] running ...")
        rc = stage.run(case, args)
        if rc != 0:
            stderr_log(f"error: stage {stage.key} failed (exit {rc}); stop.")
            return rc
    stderr_log("study complete.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Construct the run_study argument parser.

    Returns:
        The configured argument parser.
    """
    stage_keys = ", ".join(s.key for s in STAGES)
    p = argparse.ArgumentParser(
        prog="corrosim-run-study",
        description="Run the full multiscale study end-to-end (one command).",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    add_case_arg(p)
    p.add_argument("--optimize", action="store_true",
                   help="Also compute the DFT-relaxed-geometry matrix (adds "
                        "the opt-geometry ranking section). Heavy.")
    p.add_argument("--with-pka", action="store_true",
                   help="Add the pKaH stage (conjugate-acid speciation).")
    p.add_argument("--with-cubes", action="store_true",
                   help="Add the HOMO/LUMO + ESP cube stage (isosurface "
                        "figures). Heavy.")
    p.add_argument("--only", default=None,
                   help=f"Run only these stages (comma-separated), in pipeline "
                        f"order. Stages: {stage_keys}.")
    p.add_argument("--skip", default=None,
                   help="Skip these stages (comma-separated).")
    p.add_argument("--force", action="store_true",
                   help="Recompute a stage even if its output already exists "
                        "(default skips a done stage).")
    p.add_argument("--plan", action="store_true",
                   help="Print the ordered steps and their outputs, then exit "
                        "without computing (a dry run).")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: orchestrate the full multiscale study for one case.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv``).

    Returns:
        The process exit code (0 on success; the first failing stage's code
        otherwise).
    """
    args = _build_parser().parse_args(argv)
    case = case_study(args.case)
    stages = select_stages(args)

    # A dry run: describe the steps and stop before importing/running any driver
    # (so it works in a venv without the QM engines installed).
    if args.plan:
        print(format_study_plan(case, stages, args))
        return 0

    qm_keys = [s.key for s in stages if s.env == "qm"]
    if qm_keys:
        stderr_log(f"note: the QM stages ({', '.join(qm_keys)}) need "
                   f"pyscf/tblite; run inside the corrosim-qm container.")
    return _run_pipeline(stages, case, args)


if __name__ == "__main__":
    raise SystemExit(main())
