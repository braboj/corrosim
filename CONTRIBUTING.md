# Contributing to corrosim

corrosim is a free, open-source tool for screening green corrosion inhibitors.
Bug reports, fixes, new validation cases, documentation, and features are all
welcome.

This file is the entry point. The detailed conventions live in the documents it
links to, each of which is the single home for its topic, so nothing is
restated here and the copies cannot drift apart.

## Ways to contribute

- **Report a bug or request a feature.** Open an issue on the
  [tracker](https://github.com/braboj/corrosim/issues). Include the command you
  ran, what you expected, and the actual output (with any error text).
- **Add an inhibitor or a validation case.** The inhibitor library is data, not
  code; see "Growing the inhibitor library" in
  [docs/PLAYBOOK.md](docs/PLAYBOOK.md).
- **Change the code or docs.** Fork, branch, and open a pull request as below.

## Getting set up

[docs/ONBOARDING.md](docs/ONBOARDING.md) walks through a first-time local setup:
clone with the template submodule, create a virtual environment, install the
`dev` extras, and build the QM image if you need the DFT/xTB stages. Day-to-day
operations are in [docs/PLAYBOOK.md](docs/PLAYBOOK.md).

## Making a change

1. Branch off `main`; never commit to `main` directly.
2. Keep the change focused, and add a test for any new behaviour. The suite is
   deliberately QM-light and runs in the venv without Docker (`pytest -q`).
3. Run the quality gates before you push: `ruff check .`, `mypy`, `pytest -q`,
   and `complexipy`. CI runs the same set; see the README's Development setup
   for what each one covers.
4. Write a conventional commit and open a pull request.

The commit, branch, and pull-request conventions (commit types, the
`Co-Authored-By` trailer, PR titles, the "closes #N" auto-close caveat, and
which artifacts are tracked) have a single home in [CLAUDE.md](CLAUDE.md) §2.1.
Please follow them there.

## Code style

Code follows [CLAUDE.md](CLAUDE.md) §2.2 and the quality templates under
`docs/solid-ai-templates/`: 80-column lines, Google docstrings with full type
hints on public functions, units carried in names or docstrings (eV, Å,
kJ/mol), and substrate-agnostic code that threads the `metal` through rather
than hardcoding one element. `ruff` and the docstring test enforce most of it.

## License

By contributing you agree that your work is licensed under the project's
[MIT License](LICENSE). The published QM image also redistributes third-party
packages under their own licenses; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
