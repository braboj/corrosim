"""corrosim.app.

The unified ``corrosim`` command-line front door: one tool, three subcommands,
each backed by an existing module entry point.

::

    corrosim screen ...         -> corrosim.cli.main            (quick screen)
    corrosim run-study ...      -> corrosim.runs.run_study.main  (full study)
    corrosim add-inhibitor ...  -> corrosim.fetch.main           (library tool)

Each subcommand module is imported lazily, only when its command is chosen, so a
``screen`` run never pays the study's import cost and ``add-inhibitor`` stays
dependency-light. Two compatibility affordances: a leading option
(``corrosim --inhibitors ...``) routes to ``screen``, the tool's original
bare-command behaviour; and the standalone ``corrosim-run-study`` /
``corrosim-add-inhibitor`` console scripts remain as aliases of the subcommands.
"""
from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from typing import TextIO


def _screen(rest: Sequence[str]) -> int:
    """Run the quick screen with the remaining args."""
    from .cli import main as screen_main

    return screen_main(rest)


def _run_study(rest: Sequence[str]) -> int:
    """Run the full multiscale study with the remaining args."""
    from .runs.run_study import main as study_main

    return study_main(rest)


def _add_inhibitor(rest: Sequence[str]) -> int:
    """Run the PubChem library-add tool with the remaining args."""
    from .fetch import main as add_main

    return add_main(rest)


# The subcommands, in help order: name -> (handler, one-line help). Both the
# dispatcher and the usage text derive from this single mapping, and each
# handler imports its module lazily so an unused command's imports never load.
_COMMANDS: dict[str, tuple[Callable[[Sequence[str]], int], str]] = {
    "screen": (_screen,
               "quick reactivity screen + ranking of a molecule set"),
    "run-study": (_run_study,
                  "full multiscale study (DFT -> MC -> MD -> report) "
                  "for a case"),
    "add-inhibitor": (_add_inhibitor,
                      "fetch a compound from PubChem into the inhibitor "
                      "library"),
}


def _usage_text() -> str:
    """The top-level help, with the command list rendered from _COMMANDS."""
    lines = [
        "corrosim - automated corrosion-inhibitor screening (free/open-source)",
        "",
        "usage: corrosim <command> [options]",
        "",
        "commands:",
        *(f"  {name:<15} {help_text}"
          for name, (_handler, help_text) in _COMMANDS.items()),
        "",
        "Run 'corrosim <command> --help' for a command's own options. A "
        "leading",
        "option ('corrosim --inhibitors ...') is shorthand for the screen.",
    ]
    return "\n".join(lines) + "\n"


def _print_usage(stream: TextIO | None = None) -> None:
    """Write the top-level command list to ``stream`` (stdout by default).

    ``stream`` is resolved at call time, not bound as a default, so a
    redirected ``sys.stdout`` (a test's capture, a pipe) is honoured.
    """
    (stream or sys.stdout).write(_usage_text())


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch ``corrosim <command> ...`` to the matching subcommand.

    Args:
        argv: Argument vector (defaults to ``sys.argv[1:]``).

    Returns:
        The chosen subcommand's exit code; 0 for a top-level help request; 2 for
        an unknown command.
    """
    argv = list(sys.argv[1:] if argv is None else argv)

    # No command, or an explicit top-level help request: show the command list.
    if not argv or argv[0] in ("-h", "--help"):
        _print_usage()
        return 0

    first = argv[0]

    # Back-compat: a leading option is the original bare-`corrosim` screen, so
    # `corrosim --inhibitors ...` keeps working as `corrosim screen ...`.
    if first.startswith("-"):
        return _screen(argv)

    # Otherwise the first token selects a subcommand; the rest are its own args.
    command = _COMMANDS.get(first)
    if command is not None:
        handler, _help = command
        return handler(argv[1:])

    # Unknown command: name it, then show the valid ones.
    sys.stderr.write(f"corrosim: unknown command {first!r}\n\n")
    _print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
