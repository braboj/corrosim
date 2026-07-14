# Engineering know-how

Transferable software-engineering patterns: package structure, dependency
isolation, configuration, CLI design, typing contracts, testability, CI/CD,
DevSecOps, and decision hygiene. Organized by engineering category, each entry
states the lesson, shows a minimal mechanism, and explains when it pays off.

The through-line: **make correctness and quality mechanical**. Enforce contracts
with tests a linter cannot express, ratchet complexity against a committed
baseline, keep outputs reproducible and golden-gated, and give every disabled
rule a written reason. Nothing important is left to a reviewer remembering to
check it.

Examples use placeholder names (`mypkg`, `Profile`, `nativelib`, `Result`).
Substitute your own. Snippets are trimmed to the point, with cuts marked `...`.

## Core

Repository, documentation, quality, configuration, testing, and review conventions.

### Repository and commit hygiene

#### Normalize line endings with `.gitattributes`

Add `.gitattributes` on day one of any repo that contributors on different
platforms touch. `* text=auto` stores LF in the repo; explicit `eol=lf` on
sources and scripts forces LF in the working tree too, so a script is never CRLF
on a checkout; `binary` on assets stops the tool transforming or diffing them as
text. Without this, a checkout that auto-converts line endings shows every file
as modified.

```gitattributes
* text=auto            # store LF in the repo
*.py    text eol=lf    # and LF in the working tree, even on Windows
*.sh    text eol=lf
*.png   binary         # never transform or diff as text
```

#### A hosted-Git gotcha worth knowing

Some hosts auto-close an issue when a commit or PR body contains its number as a
bare substring, even inside a negation like "does not close #12". Write it as
"part of #12" to link without closing.

### Documentation and decisions

#### Record decisions, and the alternatives you rejected

Keep short decision records for significant choices, one concern each, and write
down what you rejected and why. The rejected options are what make a decision
teachable rather than arbitrary.

#### Give each fact one home

Keep each rule or fact in exactly one document and cross-reference it, rather
than duplicating it. Structure lives in the project overview; per-run rules in
the contributor guide; decisions in decision records; history in a changelog. A
rule you apply constantly is one line; if it needs a paragraph, it is a decision
record with a one-line pointer.

#### A self-describing examples/ folder

Ship an `examples/` directory whose `README.md` indexes each example as an exact
command paired with the output it produces, so the folder teaches rather than
just holding sample inputs. Where the real output needs an engine or service the
reader may not have, show the reproducible dry-run output instead: it conveys the
shape without computing and runs anywhere. Keep the examples runnable offline
against data the project already bundles, and do not paste fabricated numbers,
point to a committed sample. A sample input that looks incomplete (an optional
column left blank on purpose) gets its intent explained next to the command, not
left for the reader to reverse-engineer.

### Quality and design

#### Curated facade: re-export the public surface, list it in `__all__`

The top package imports its public surface out of private submodules and
re-lists it in `__all__`, so callers import from one stable place and never reach
into internal modules. The internal tree can then be refactored without breaking
import sites, and `__all__` documents the intended surface.

```python
# src/mypkg/__init__.py
from .core import Engine, run
from .config import Profile, load_profile
from .report import render_html, render_pdf

__all__ = ["run", "Engine", "Profile", "load_profile", "render_html", "render_pdf"]
```

#### Exhaustive dispatch over silent fallthrough

When you dispatch on a name or kind, end with a branch that raises, so an unknown
case is loud rather than silently dropped. A dispatch chain with no final `else`
returns `None` for an unhandled value and fails obscurely somewhere later.

```python
if kind == "a":
    return handle_a(x)
if kind == "b":
    return handle_b(x)
raise ValueError(f"unhandled kind {kind!r}")   # never let it fall through
```

#### Derive once, render many

Compute all derived data once into an immutable object via a factory, then let
every renderer consume it. The pure derivation is unit-testable without
rendering, and the outputs cannot diverge because they share one source.

```python
class Prepared(NamedTuple):
    table: "pd.DataFrame"
    ranked: "pd.DataFrame"

    @classmethod
    def derive(cls, rows, order) -> "Prepared":
        ...                          # all the logic lives here, tested in isolation
        return cls(table, ranked)


def render_html(p: Prepared) -> str: ...
def render_pdf(p: Prepared) -> bytes: ...
```

```text
   raw rows --> derive() --> Prepared (immutable) --+--> render_html
               all logic,                            |
               unit-tested                           +--> render_pdf

   one place computes; N renderers consume; they cannot drift apart
```

Scope a shared abstraction to genuine duplication, and delete it when its only
consumer goes away. A seam that no longer serves two callers is just dead code.

#### Rank on one declared basis; gate the claim on robustness

When a scoring or ranking function can be computed on several interchangeable
input *bases* — different methods, parameterizations, or preprocessing choices
for the same items — evaluating each and reporting them side by side lets one
output crown several different "winners", and the headline basis ends up chosen
by whichever code path ran first rather than by a decision. Declare exactly one
*canonical* basis as an explicit, testable property of the run (not the
incidental result of a default path); render every other basis as a labelled
sensitivity panel with no competing "best"; and assert a single top result only
when it survives every basis. When the leaders disagree, the ordering is finer
than the estimator resolves — report a tie, not a rank.

```python
def build_ensemble(bases: dict[str, list[dict]]) -> Ensemble:
    ranked = {name: rank(rows) for name, rows in bases.items()}
    canonical = max(ranked, key=basis_priority)      # declared, not incidental
    leaders = {r[0]["id"] for r in ranked.values()}
    robust = len(leaders) == 1                        # every basis agrees
    return Ensemble(canonical, ranked, robust,
                    lead=next(iter(leaders)) if robust else None)
```

```text
   basis A  basis B  basis C     each --> rank --> a leader
      \________|________/
               v
       leaders all agree?  --yes--> assert the lead
                           --no --> tie within resolution (report, don't rank)
```

Carry the verdict, not just the winner: a rank with no robustness signal reads
as more certain than the inputs support.

#### Inject the one axis you are tempted to hardcode

Thread the parameter that varies through the code and derive labels and lookups
from it, instead of hardcoding the common case. A lookup table keyed by that axis
(with a default) accepts new values without new branches.

```python
# hardcodes the varying axis, so it only works for one case:
def label():           return "latency (ms)"

# threads it, derives from it, and reuses everywhere:
def label(unit: str):  return f"latency ({unit})"

FACTORS = {"ms": 1e-3, "us": 1e-6}          # keyed by the axis
factor = FACTORS.get(unit, 1.0)             # with a sane default
```

#### Verify convergence — escalate, then fail loud

An iterative numerical routine (a fixed-point solver, an optimizer) exposes a
convergence flag but does not force the caller to read it. Kernel it and read the
result without checking, and a run that silently failed to converge feeds a
plausible-looking but wrong answer downstream. Route every such call through one
helper that checks the flag and, on failure, escalates through progressively
stronger (and slower) stabilization strategies — cheapest first — before raising
a descriptive error. The ladder fires ONLY on non-convergence, so the fast path
that already converges is byte-for-byte untouched; it exists to rescue the hard
cases and to refuse to hand back an unconverged result as if it were valid.

```python
def solve(state, label=None):
    state.run()
    for stabilize in (add_damping, second_order):   # cheapest aid first
        if state.converged:
            return state
        state = stabilize(state)                     # runs only on failure
        state.run()
    if state.converged:
        return state
    raise ConvergenceError(f"did not converge for {label}")   # never silent
```

Keep the ladder itself unit-testable without the heavy engine: make each
stabilization step a small function and the driver pure orchestration, then
exercise it with a stub whose convergence is scripted per attempt. A
converged-but-slower answer strictly beats a fast wrong one — and because the
escalation only changes results that were already garbage, the shipped fast-path
numbers cannot regress.

#### An output-changing approximation stays opt-in and off by default

A speed knob that shifts the numbers (a lower-rank approximation, a coarser grid)
must default off, so the canonical output is never silently perturbed by an
optimization someone flipped for throughput. Make it a per-run field the caller
sets deliberately — and carried in the same single source of truth as the rest
of the run's parameters, so a run that needs it is self-reproducing — not a
global default.

#### Size the budget to the box; spill big intermediates to disk or refuse

A memory-heavy step should detect its real budget — an env override, else the
container cgroup limit, else physical RAM, scaled for headroom — instead of
assuming a fixed library default, so it sizes its algorithm to memory the process
can actually use. Estimate a large intermediate's footprint up front: keep it in
RAM only while it fits a fraction of the budget, stream it to a disk scratch path
beyond that, and refuse with a clear error past a hard ceiling. A diagnosable
"too large for this budget" beats an OOM crash mid-run — and the scratch path
must land on real disk, not a RAM-backed tmpfs, or the spill defeats itself.

#### One decode home accepts every persisted shape

When a serialized format evolves — gains a version, wraps its payload in an
envelope, adds a field — route every reader through a single decode function
that accepts all supported shapes, and never let a consumer re-parse the raw
payload itself. A second reader that hard-codes the old shape keeps working
until a new writer changes it, then crashes on data it never learned — and the
break surfaces at the read site, far from the format change. Keep the shape
knowledge in one place (the decode function, the inverse of encode), have it
fall back across the legacy forms, and make every consumer go through it.

```python
@classmethod
def from_json(cls, obj):
    # accept the current {"version", "payload"} envelope AND the legacy bare form
    payload = obj["payload"] if isinstance(obj, dict) else obj
    return cls(...)

rows = Thing.from_json(load(path))   # every reader decodes; none parses raw
```

The bug this prevents: a consumer that loaded the raw payload and assumed the
old shape works until the writer is upgraded, then fails on the new shape — a
format change silently breaking a reader that never went through the one decoder.

Two recurring design criteria worth internalizing:

- **Restraint over speculation.** Abstract only where duplication or a second
  implementation actually exists. A class whose only public method is `.run()` is
  a function in disguise; a strategy interface with one implementation is
  premature.
- **Keep the public wrapper stable while refactoring internals,** so callers
  never break during a reorganization.

### Configuration

#### One frozen config object, a registry, and a lookup

A frozen dataclass bundles every input for a run. `frozen=True` prevents
accidental global mutation, each default carries its rationale in place, derived
properties compute layout from the name, and a copy accessor hands callers a
mutable list so they cannot mutate the shared object.

```python
@dataclass(frozen=True)
class Profile:
    """A named run configuration."""

    name: str
    inputs: tuple[str, ...]
    # default lives next to its reason, so a preset's diff reads as intent
    batch_size: int = 32

    @property
    def out_dir(self) -> str:
        return f"runs/{self.name}"

    def input_list(self) -> list[str]:
        return list(self.inputs)     # fresh copy: callers can't mutate the frozen preset
```

A module-level registry maps names (and aliases) to instances; the lookup is
case-insensitive and raises with the known keys. Callers read fields from the
instance; they never re-declare the data.

```python
PROFILES: dict[str, Profile] = {"default": DEFAULT, "fast": FAST}

def profile(name: str) -> Profile:
    key = name.strip().lower()
    if key not in PROFILES:
        raise KeyError(f"unknown profile {name!r}; known: {sorted(PROFILES)}")
    return PROFILES[key]
```

#### Let the same lookup also load a user config file

Once the config library is data (a registry of built-ins), the *user's* config
should be data too, resolved through the *same* selector, so an installed tool
runs a user's own run without editing source. Add `to_dict`/`from_dict` (keys are
the field names; `from_dict` does structural validation only — required keys,
types, reject unknown keys so a typo fails loud) and grow the resolver one
branch: a value that names a file (an explicit marker — an extension or a path
separator, **not** `exists()`, so a bare registry key never collides with a
same-named file) loads the file; a bare word is the registry, byte-identical.

```python
def config(name: str) -> Profile:
    if name.endswith(".json") or "/" in name or os.sep in name:
        return Profile.from_dict(json.load(open(name)))   # a user file
    return profile(name)                                  # the built-in registry
```

Offer a second front door (ad-hoc flags) as **sugar that materialises a file and
delegates** to the file path: one construction/validation path, and the ad-hoc
run leaves behind a reproducible artifact. And **validate a user config against
the supported envelope at the door** — a message naming the supported set beats a
traceback deep in the run; split the cheap always-on checks (name safety, enum
membership) from the ones needing a heavy import (skip those for a dry run).

#### Unset flag means "use the config"; explicit always wins

Every CLI flag defaults to `None`; after parsing, a shared resolver fills each
unset attribute from the selected config, guarded so an explicit value always
wins. This cleanly separates "the user said nothing" from "the user said this".

```python
def resolve(args) -> Profile:
    p = profile(getattr(args, "profile", "default"))
    if getattr(args, "inputs", None) is None:
        args.inputs = ",".join(p.input_list())
    if getattr(args, "out", None) is None:
        args.out = p.out_dir          # a bare run auto-routes; --out overrides
    return p
```

#### Check the regime before adding a per-item knob

A per-item configuration axis is only worth its weight when the operating point
actually distinguishes the items. Before splitting one shared value into many,
check whether the regime collapses the difference: if every item saturates to the
same response at the operating point, a single shared value is correct and the
extra knob is dead weight and a maintenance liability. Parameterize when the
inputs diverge *and* the output resolves the divergence, not on the mere
possibility that they might differ. (The inverse of "inject the one axis you are
tempted to hardcode": there, one value must vary and is wrongly fixed; here, the
values could vary but the regime makes the distinction moot.)

#### Namespace outputs per run; never hardcode an output root

As soon as a second run configuration exists, a flat output root collides:
identical filenames silently overwrite, and the first one is left unlabelled.
Namespace every output under the run's own directory, split generated data from
the deliverable bundle so the ignore rules stay clean, and derive the location
from the config object. A shared regenerable cache stays outside the namespace on
purpose, because its entries are slow to make and reused across runs.

```text
runs/
  default/
    results/     <- generated data (tracked)
    report/      <- deliverable bundle (tracked)
  fast/
    results/
    report/
cache/           <- shared, regenerable, NOT per-run (documented exception)
```

#### Fallback chains for a schema you do not control

When you read a third-party payload whose field names change, try the new key
then the legacy names in order, with a note on why. It survives a rename without
a hard break, and the fallback documents the migration.

```python
value = (payload.get("value")
         or payload.get("legacyValue")
         or payload.get("old_value"))
if value is None:
    raise LookupError("response carried no value field")
```

#### Regenerate dependent artifacts in the same change

When an input changes, rerun the downstream generators in the same commit and
verify the diff by spot-checking values, not just file size. The rule applies to
tooling too: a regenerated baseline (see the ratchet below) is committed together
with the change that moved it.

### Testing and testability

#### Keep pure logic out of I/O

Transform and numeric logic should be side-effect-free; commands do the I/O
around it. Pure cores are testable with plain values, no filesystem or network,
which is what keeps a suite fast. Guard the arithmetic that can divide by zero.

```python
def rank(df):
    def zscore(s):
        std = s.std(ddof=0)
        return s * 0 if std == 0 else (s - s.mean()) / std   # guard std == 0
    df["score"] = sum(zscore(df[c]) for c in COLS) / len(COLS)
    return df.sort_values("score", ascending=False)
```

#### Gate refactors on golden output

A behaviour-preserving refactor must produce byte-identical (or
section-identical) output, checked by a golden file. A refactor that changes a
golden is a bug, not a style choice. This is what lets you reorganize freely.

#### Enforce the API contract with a test the linter cannot express

The test parses each module with `ast`, filters the public surface, and asserts
the contract with self-documenting failure messages. This is the most portable
idea here: enforce a documentation or style rule package-wide, in CI, that no
linter has a rule for.

```python
def public_defs(tree):
    """Public top-level functions plus public methods of public classes."""
    out = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            out.append(node)
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            out += [m for m in node.body
                    if isinstance(m, ast.FunctionDef) and not m.name.startswith("_")]
    return out


def test_public_api_is_fully_annotated():
    bad = []
    for path in source_files():
        for fn in public_defs(ast.parse(path.read_text())):
            params = [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs]
            for p in params:
                if p.arg not in ("self", "cls") and p.annotation is None:
                    bad.append(f"{path.name}:{fn.lineno} {fn.name}({p.arg})")
            if fn.returns is None:
                bad.append(f"{path.name}:{fn.lineno} {fn.name} -> ?")
    assert not bad, "untyped public API:\n  " + "\n  ".join(bad)
```

The same technique bans comments that rot (ticket or issue numbers embedded in
code) and comments that trail code on the right, while exempting machine-readable
tool directives.

Rollout lesson: a big-bang sweep of hundreds of violations is unreviewable.
Sweep module-by-module behind an allowlist inside the test; the final change
flips the global gate and retires the allowlist. Every step stays green.

#### A small ASCII diagram in the module docstring

When a module's flow is not obvious from prose (a search loop, a data pipeline, a
state machine), put a small pure-ASCII diagram in its docstring, so orientation
lives with the code.

```python
"""Fetch and validate registry entries.

::

    name --> HTTP API --> validate --> registry.json
             (fetch)      (parse)      (append with source)
"""
```

### Review

**Explicit deviations, never silent ones.** Adopt a standard, then record
precisely what you relaxed and why, so the gap is a documented choice, not a
surprise.

## Language

Per-language structure, dependency isolation, typing, and packaging.

### Package structure and imports

#### Use a `src/` layout so tests exercise the installed build

A flat top-level package lets `import mypkg` resolve to the working tree instead
of the installed distribution, so tests can pass against code that was never
packaged (for example a data file missing from the build). A `src/` layout makes
the working-tree copy un-importable, forcing the test run to exercise what
`pip install` actually produced. Adopt it before you ship package data or
publish.

```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["mypkg*"]
```

Only path-based settings change (build discovery, coverage paths, type-checker
roots, Docker `COPY`). Import-name references (entry points, `-m mypkg.x`) do
not.

#### Group modules along the import graph

When a package grows, regroup flat modules into sub-packages along the boundary
the import graph already reveals: identify the leaves and the clusters, and give
each cluster a sub-package. Verify the graph is a DAG (no cycles) before moving,
and keep the public API stable through the facade above.

```text
   before (flat)                 after (clustered by the import DAG)

   core.py                       core.py
   engine.py                     config.py
   backend_a.py        --->      backends/  (a, b, shared)
   backend_b.py                  report/    (html, pdf, layout)
   shared.py                     __init__.py  re-exports the public names
   html.py
   pdf.py
```

Sequencing lesson: do the **structural move before any line-level refactor**, so
later edits land in each file's final home instead of churning the same lines
twice.

#### Keep `import mypkg` cheap with deferred and type-only imports

Type-only imports hide behind `TYPE_CHECKING` so they cost nothing at runtime.
Genuinely heavy modules are imported inside the function that needs them, so
lightweight paths (help text, a dry run) work in a minimal environment.

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd          # visible to the type checker, never imported at runtime
```

### Isolating optional and native dependencies

Some dependencies are heavy, optional, or have no wheels for every platform
(native extensions that need a compiler, GPU libraries, large SDKs). One seam
handles them, and it drives the packaging, CI, coverage, and test decisions
downstream.

#### The single-backdoor backend module

Do not scatter deferred imports of a heavy dependency across many functions: the
dependency becomes invisible and the "install the extra" error must be repeated
at every call site. Instead, **one private module owns the import**, wraps it in
`try/except`, and re-raises with an actionable message. Every other module is a
consumer that imports the backend lazily.

```python
# src/mypkg/_backend_native.py: the ONLY place nativelib is imported
try:
    import nativelib
    from nativelib.fast import transform
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "the native backend needs the 'accel' extra: pip install mypkg[accel]"
    ) from exc

__all__ = ["nativelib", "transform"]
```

```python
# src/mypkg/engine.py: reached lazily, so `import mypkg` works without the extra
def run_fast(data):
    from . import _backend_native as nb
    return nb.transform(data)
```

```text
        import mypkg                (always succeeds; no heavy dep needed)
             |
   +---------+-----------------------------+
   |                                       |
 pure modules                        engine.py (consumer)
 (no heavy import)                         |  lazy: from . import _backend_native
                                           v
                              _backend_native.py   <- the one guarded import
                                try:    import nativelib
                                except: raise "install mypkg[accel]"
```

Restraint note: keep the *consumers* out of the backend. If drivers import
engine symbols at module top and tests monkeypatch them there, those symbols
must live in a module that does not eager-import the heavy dependency. Respect
test seams when you draw the boundary.

#### Uniform result over swappable backends

Give several interchangeable implementations one result type and one dispatcher
that selects by name and raises on an unknown value. The rest of the code stays
backend-agnostic, so adding a backend is a new branch plus a parser, not a
downstream rewrite.

```python
@dataclass
class Result:
    backend: str
    rows: list[dict]

    @property
    def count(self) -> int:
        return len(self.rows)


def query(backend: str, sql: str) -> Result:
    backend = backend.lower()
    if backend == "sqlite":
        return _query_sqlite(sql)
    if backend == "postgres":
        return _query_postgres(sql)
    raise ValueError(f"unknown backend {backend!r}; use 'sqlite' or 'postgres'")
```

```text
   query("postgres", ...) ---> dispatch ---> _query_postgres ---> Result
   query("sqlite",   ...) --------+                                  ^
   query("mysql",    ...) --------|--> raise ValueError        one shape,
                                  |    (loud, not None)         every backend
```

When a backend shells out to an external tool, use a fixed argument vector with
no shell, and justify the security suppression at the call site rather than
globally.

```python
# fixed argv, no shell, no untrusted input
subprocess.run([tool, input_path], stdout=out, check=True)  # nosec B603
```

### Typing and API contracts

#### Baseline idioms

- `from __future__ import annotations` at the top of every module (cheap forward
  refs, string annotations).
- Types from `collections.abc` (`Sequence`, `Callable`, `Iterator`) in
  signatures, not the deprecated aliases.
- A type alias for a repeated shape improves readability.
- Put the unit in the name, never a bare number: `timeout_s`, `size_bytes`,
  `first_peak`.

#### Split the enforcement: format to the linter, presence to a test

Require every public function to carry complete type hints plus a docstring with
`Args:`/`Returns:`/`Raises:`. A blanket annotation lint would force noise onto
private helpers that take un-stubbed third-party objects, so split the rule: the
linter owns format and complexity, and a test owns the presence of annotations
and docstrings.

The presence half is enforced by an AST-walking test in CI, described under
Core / testing and testability.

### Packaging and reproducibility

#### Extras as capability tiers

Optional-dependency groups separate "always installable pure code" from "needs a
compiler or platform-specific wheels". The heavy group is quarantined so a plain
install never tries to build it; the dev group deliberately excludes it so the
test install stays fast and cross-platform.

```toml
[project.optional-dependencies]
accel  = ["nativelib"]                          # heavy/native; not everyone can build it
report = ["weasyprint"]                          # optional output format
dev    = ["pytest", "pytest-cov", "ruff", "mypy"]  # note: does NOT include accel
```

CI installs `.[dev]`; the container image installs `.[accel,dev]`. That one extra
is the seam every other decision keys off.

#### Content as data, grown by a small tool

Editable content (a library, a registry, a lookup) belongs in a data file, not
baked into a module, and each entry should carry provenance. Ship it as package
data, load it with `importlib.resources` so it resolves the same from a checkout
or an installed wheel, and derive the read-optimized views at import so adding a
field never changes the public API.

```python
# src/mypkg/registry.py
from importlib.resources import files
import json

def _load() -> dict:
    text = (files("mypkg") / "data" / "registry.json").read_text("utf-8")
    return json.loads(text)

RECORDS = _load()                                            # full records + provenance
NAMES = {name: rec["value"] for name, rec in RECORDS.items()}  # derived lookup view
```

```toml
[tool.setuptools.package-data]
mypkg = ["data/*.json"]
```

Grow the data with a small dev-time tool that depends only on the standard
library, so there is no runtime dependency and CI stays offline. Monkeypatch its
one network call in tests to keep the suite deterministic. Adding an entry is a
data edit, never a code edit.

#### Prefer pure-language chains over system binaries

A feature that adds a system binary breaks the "installs anywhere" guarantee and
will not exist in CI. Find a pure-language path, and degrade gracefully when an
optional piece is missing: if the optional renderer is absent, log and skip that
output while still producing the rest.

#### Author with heavy tools at dev time, not in the runtime path

You can use a heavy, paid, or non-deterministic tool to author static content at
dev time, review the diff, and commit the result, without putting that tool in
the runtime path. Never make a reproducible artifact depend on something
non-deterministic, paid, or network-bound at run time. Generate, review, commit;
the artifact then rebuilds byte-for-byte from committed inputs.

## Infrastructure

Build, CI/CD mechanics, and containers.

### CI/CD

#### Run gates as independent parallel jobs

Split CI into jobs that fail separately, so one failure does not mask the others
and the fast jobs finish fast.

```text
         push / PR
            |
   +--------+--------+---------+
   |        |        |         |
  lint     test   security  secrets      (independent; each fails on its own)
  format   matrix   SAST     history scan
  types    3.10-12
  complexity
```

#### Pin any tool that reads or writes a committed state file to the minor

Install tools at a wildcard minor to get patch fixes without surprise breakage.
A tool that persists state on disk (a baseline, a snapshot) must be minor-pinned,
or an upgrade can reject the checked-in file.

```yaml
# the complexity tool writes a version-sensitive baseline, so pin its minor
- run: pip install "ruff==0.15.*" "mypy==1.14.*" "complexity-tool==6.0.*"
```

#### Matrix the version-variant work, cache the installs

Fan out only the jobs whose result depends on the runtime version; pin one
version for the version-invariant lint and security work so no cells are wasted.
`fail-fast: false` reports every cell even when one fails.

```yaml
strategy:
  fail-fast: false                   # one version failing still reports the rest
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
steps:
  - uses: actions/setup-python@v5
    with:
      python-version: ${{ matrix.python-version }}
      cache: pip                      # built-in dependency cache
```

### Containers

#### Split execution: native path in a container, everything else native

When some dependencies have no wheels for your dev platform, isolate exactly
those into a container image and run everything else natively, so the inner loop
stays fast. Run long container jobs detached so a shell or session exit does not
kill them mid-run.

```text
  everyday loop (any OS)              heavy/native path (Linux container)
  ----------------------             -----------------------------------
  tests, lint, docs, CLI             the compiled/native work only
  pip install .[dev]                 pip install .[accel,dev]
  fast feedback                      docker run -d ...   (detached, poll logs)
```

The image picks its base by the wheel availability of the hardest dependency,
and copies dependency manifests before source so the install layer caches across
source-only edits.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
# copy only what resolves deps first, so this layer caches across source edits
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install -e ".[accel,dev]"
```

#### An editable install in a bind-mounted image should import by an explicit path

Installing the project editable inside an image (`pip install -e`) bakes an
absolute finder path at build time. If you then bind-mount the repo over the
workdir at runtime and later move the package (a flat -> `src/` migration), the
baked path points at a directory that no longer exists, so `import pkg` fails
even though the live code is present under the mount, and every run needs a
`PYTHONPATH` override to paper over it. Resolve the package by an explicit source
path so the runtime import tracks the live bind-mounted location instead of the
frozen finder, and fail the build if the import is broken.

```dockerfile
RUN pip install -e ".[accel,dev]"       # deps + console scripts
# resolve by the live location, not the build-time-baked finder path
ENV PYTHONPATH=/app/src
# fail the build (not runtime) if the package or a heavy engine cannot import
RUN python -c "import pkg, heavy_dep"
```

#### Rebuild a hand-built image in CI on any packaging change

An image the main test suite never builds (its heavy deps only exist in the
container) drifts from the layout silently: nothing forces a rebuild when the
package moves. Add a CI job, gated to the files that define the image contract
(the Dockerfile, the dependency manifest, the compose file), that rebuilds and
import-smokes it. Path-gating keeps it off the hot path of every PR while still
catching structural drift before merge.

```yaml
on:
  pull_request:
    paths: [Dockerfile, pyproject.toml, docker-compose.yml, .dockerignore]
jobs:
  build:
    steps:
      - run: docker compose build img      # the build-time import check gates this
      - run: docker compose run --rm img    # import-smoke under the runtime bind mount
```

#### Publish on tag, and smoke the image in the config the user runs

Release-on-tag builds, smoke-runs, and pushes the image, then cuts a release with
the run instructions. The subtle part is the smoke: the dev and CI smoke overlays
the repo with a bind mount, so it never exercises the **standalone** path a
published-image user takes (no mount, the baked source). Run the smoke with no
volume, so a broken standalone image fails before the push, not in a user's hands.
Registry and CI are free for public repos, so this costs the maintainer nothing;
one manual step remains — the token can push but cannot flip package visibility,
so set the package public once after the first release.

```yaml
on:
  push:
    tags: ["v*"]
permissions: { contents: write, packages: write }   # release + registry push
steps:
  - run: docker build -t "$IMG:${TAG#v}" -t "$IMG:latest" .   # build-time import check gates
  - run: docker run --rm "$IMG:${TAG#v}" app --dry-run        # STANDALONE: no bind mount
  - run: docker push "$IMG:${TAG#v}" && docker push "$IMG:latest"
```

Mount only the output directory to retrieve results; never mount over the workdir
that holds the baked source, or the mount shadows it and the import breaks.

## Security

SAST, secrets, and supply chain.

### DevSecOps

Layer complementary scanners; each catches what the others miss.

**Fast SAST on every commit.** A static analyzer over the source tree gives quick
per-commit signal. Justify any suppression at the call site (as in the subprocess
example above), and anchor exclude globs so they do not accidentally exempt real
source.

```yaml
- run: bandit -c pyproject.toml -r src/mypkg
```

**Deep semantic analysis on a schedule.** A heavier code-scanning engine runs on
push, on PRs, and on a weekly cron (off-peak, and off the top of the hour to
avoid the stampede), under least-privilege permissions.

```yaml
on:
  schedule:
    - cron: "27 3 * * 1"          # weekly, Monday 03:27 UTC
permissions:                      # least privilege
  security-events: write
  contents: read
```

**Secret scanning over full history.** A secret that was committed and later
deleted still lives in old commits, so the scanner must see the whole history,
not just the tip. Run it in CI and as a pre-commit hook.

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0                # ALL history: a deleted secret still lives in old commits
- uses: gitleaks/gitleaks-action@v2
```

Pin third-party CI actions to a tag, pin tool minors, and keep auxiliary tooling
offline so CI never needs the network.

## Workflow

Quality gates and process discipline.

### Quality gates

#### Scope coverage to what CI can actually run

A global coverage threshold is a trap when part of the code cannot run in CI
(native, GPU, or container-only paths). Do not lower the gate to a meaningless
number and do not drop it. Omit the un-runnable modules from the denominator,
validate them by a separate suite, and gate the remainder honestly. The omit list
is the contract: a new pure module is in scope by default and must be tested.

```toml
[tool.coverage.run]
source = ["mypkg"]
omit = ["src/mypkg/_backend_native.py", "src/mypkg/gpu.py"]   # can't run in CI

[tool.coverage.report]
fail_under = 80    # meaningful, because the un-runnable code is out of the denominator
```

```text
              coverage denominator
   +----------------------------------------+
   |  pure, CI-runnable code   <- 80% gate  |
   +----------------------------------------+
        omitted: native / GPU / container-only
        (validated out-of-band, not counted)

   lowering ONE global gate to fit the bottom band makes the top band meaningless
```

#### Ratchet complexity against a committed baseline

To pay down complexity debt without a big up-front refactor, ratchet. Commit a
snapshot of the current over-threshold functions; a run fails only when a
function is newly over-threshold or worse than recorded, so existing offenders
are frozen rather than exempted. A successful run rewrites the snapshot, so the
watermark only tightens.

```text
   committed snapshot            new run
   funcA: 22   --------------->  22   ok    (frozen, not worse)
   funcB: 18   --------------->  20   FAIL  (increased)
   funcC:  -   --------------->  17   FAIL  (new offender)
   funcA: 22   --------------->  14   ok    (better -> snapshot rewritten to 14)
```

Measure cognitive complexity (nesting and control-flow interruptions, which
tracks how hard code is to read) alongside cyclomatic complexity (branch count).
They disagree: a flat function with many branches can read easily, while a deeply
nested one with few branches does not.

#### Adopt strict typing gradually; quarantine untyped deps

Run the type checker non-strict at first, with a written path to tighten.
Isolate untyped third-party libraries with per-module overrides and a stated
reason, rather than weakening the whole check.

```toml
[[tool.mypy.overrides]]
# quarantine untyped third-party libs here, not by weakening the global config
module = ["nativelib.*", "someuntyped.*"]
follow_imports = "skip"
```

#### Pre-commit: exempt generated files, pin every rev

A global exclude keeps tracked-but-generated files out of the whitespace fixers,
or they churn on every commit. Adopting a linter without its auto-formatter is a
valid, documented intermediate state. Pin every hook to an exact rev: the config
is the lockfile.

```yaml
exclude: |                       # generated/tracked files skip the whitespace hooks
  (?x)^(results/.*|report/.*|.*\.(csv|json))$
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.20                # pin the rev exactly
    hooks:
      - id: ruff-check
        args: [--fix]
```

### Process and scope

**Sequence structural change before line-level change,** so you do not churn the
same lines twice.

#### Judge reuse at decision time

Decide whether a convention is reusable at the moment you make it, not later.
Strip the project-specific nouns out of the rule and re-ask whether it still
holds: if it does, it belongs in the shared conventions; if it does not, keep it
local. Record that verdict while the decision is fresh, so you are not
rediscovering the boundary every time the pattern recurs.

## Free-form (not yet in the taxonomy)

Patterns with no category home yet. Each is a candidate to generalize into the shared conventions.

### CLI and driver architecture

#### One shared plumbing module

Have every command import one helper module that single-sources argument
registration, config resolution, file I/O with closed handles, and output
formatting, so each command stays close to one unit of real work.

A sentinel distinguishes "no default given, so a missing file is an error" from
"an explicit default of `None`":

```python
_REQUIRED = object()

def read_json(path: str, default=_REQUIRED):
    if default is not _REQUIRED and not os.path.exists(path):
        return default            # caller opted into a fallback
    with open(path) as fh:        # otherwise a missing file is a real error
        return json.load(fh)
```

Send progress to stderr so stdout stays machine-parseable:

```python
def log(msg: str) -> None:
    print(msg, file=sys.stderr)
```

#### Thin `main()`, extracted steps, and the argv seam

Keep `main(argv=None) -> int` small: parse, resolve config, call a pure core,
write outputs. The `argv` parameter is the testability seam (tests pass a list
instead of touching `sys.argv`), and the `int` return is a checkable exit code.

```python
def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)   # tests call main(["--fast", ...])
    cfg = resolve(args)
    rows = analyse(cfg)                        # pure core: no I/O
    write_outputs(rows, args)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

#### A `--plan` dry run that imports nothing heavy

A dry-run flag prints the steps a run would take and returns before any heavy
import, so the shape can be inspected or smoke-tested in any environment.

```python
if args.plan:
    print(format_plan(args))     # describe the steps, touch nothing
    return 0

import mypkg                     # the heavy import happens only past here
```

This pattern has no core-convention home yet, so it is a candidate to propose
upstream into the shared conventions.

#### A step with a durable output persists it by default, or fails loud

A command that runs an expensive computation and prints its result must also
write it, by default, to a path resolved from the run's own config. A driver
that persists only when an explicit `--out` flag is passed will, the first time
the flag is forgotten, run the whole computation and silently discard it: the
operator sees the printed table, assumes it was saved, and finds an empty output
dir only when the next step reads nothing. Default the output path from the same
config the input came from, so a plain `run --case X` writes to `X`'s results
dir like every sibling command; let `--out` override *where*, not *whether*.

```python
# footgun: computes, prints, persists nothing unless a flag is remembered
if args.out_csv:
    df.to_csv(args.out_csv)        # forget the flag -> the expensive run is lost

# safer: default the path from config, so a bare run always persists
default_output(args, "out_csv", f"{cfg.results_dir}/descriptors.csv")
df.to_csv(args.out_csv)           # always written; the flag only redirects it
```

Silent non-persistence of a completed computation is indistinguishable from
success until something downstream reads the gap. Make the durable artifact the
default; reserve print-only for an explicit dry run. (Also an upstream candidate
for the shared CLI conventions.)

#### A thin orchestrator over the stage commands

When a multi-stage pipeline is already exposed as N independent stage commands,
add one orchestrator command that invokes each stage's existing entry point in
dependency order rather than reimplementing the flow. It owns order and
selection; the stage commands stay the single source of each stage's behaviour.
Build the plan, the skip logic, and stage selection on top of one ordered table
of stage records.

```python
STAGES = [Stage("build", run=_run_build, outputs=_out_build), ...]

for st in select(args):                       # --only / --skip filter this list
    outs = st.outputs(cfg)
    if outs and all(exists(o) for o in outs) and not args.force:
        log(f"skip {st.key}: output present"); continue    # idempotent resume
    if st.run(cfg) != 0:                      # each runner calls the stage main()
        return fail                           # stop at the first failure
```

Reuse the `--plan` dry run (above) to print the ordered steps without computing,
and each stage's own output routing so the orchestrator threads no paths. Each
runner imports its stage lazily, so the plan pays no heavy import for a stage it
will not run. (Upstream candidate for the shared CLI conventions.)

## The shortlist

If you take five things:

1. **One backend module owns each heavy or optional dependency**, imported
   lazily, so the package imports cleanly everywhere and the dependency is
   declared in one greppable place. (Language / isolating dependencies)
2. **An AST-walking test enforces the API and comment contract package-wide,**
   where no linter has a rule. (Core / testing)
3. **A frozen config object plus a registry plus unset-means-default resolution**
   gives one source of truth that commands consume, with no output root ever
   hardcoded. (Core / configuration and CLI)
4. **Derive once, render many:** one immutable model, many renderers that cannot
   drift. (Core / quality and design)
5. **Scope coverage and ratchet complexity** so quality gates stay honest on a
   codebase where part of the surface cannot run in CI. (Infrastructure and
   Workflow)
