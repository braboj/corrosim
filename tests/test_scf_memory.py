"""QM-light tests for the SCF convergence ladder and the memory guard.

The escalation ladder (run_scf) and the density-fitting memory guard are pure
orchestration/arithmetic — no PySCF engine needed. The ladder is exercised with
a stub mean field that scripts when it converges, mirroring how test_engines.py
tests the geometry helpers without a QM backend.
"""
import pytest

from corrosim.qm.engines import (
    CDERI_CEILING_GB,
    DEFAULT_MEMORY_MB,
    MEMORY_BUDGET_ENV,
    MEMORY_FLOOR_MB,
    SCF_DAMP_FACTOR,
    SCF_HARD_MAX_CYCLE,
    SCF_LEVEL_SHIFT_HARTREE,
    SCFConvergenceError,
    _cgroup_limit_bytes,
    estimate_cderi_gb,
    plan_scf_memory,
    resolve_memory_budget_mb,
    run_scf,
)


class StubMF:
    """A fake mean field that converges on a scripted kernel attempt.

    ``converge_on`` is the 1-based kernel-call index that first reports
    convergence (None = never converges). newton() returns self so the
    second-order stage keeps counting against the same attempt tally.
    """

    def __init__(self, converge_on):
        self.converge_on = converge_on
        self.attempt = 0
        self.converged = False
        self.kernel_calls = 0
        self.newton_called = False
        self.level_shift = 0.0
        self.damp = 0.0
        self.max_cycle = 50
        self.e_tot = -1.0

    def kernel(self, dm0=None):
        self.attempt += 1
        self.kernel_calls += 1
        self.converged = (self.converge_on is not None
                          and self.attempt >= self.converge_on)
        return self.e_tot

    def make_rdm1(self):
        return "dm"

    def newton(self):
        self.newton_called = True
        return self


# --- run_scf: the escalation ladder ----------------------------------------

def test_run_scf_first_try_does_not_escalate():
    # converges on the default DIIS kernel -> no aids touched (the safety
    # invariant: a normally-converging single point is numerically untouched)
    mf = StubMF(converge_on=1)
    out = run_scf(mf)
    assert out is mf
    assert mf.kernel_calls == 1
    assert not mf.newton_called
    assert mf.level_shift == 0.0


def test_run_scf_second_stage_applies_shift_and_damp():
    # fails once, then the level-shift + damping stage converges it
    mf = StubMF(converge_on=2)
    run_scf(mf)
    assert mf.kernel_calls == 2
    assert not mf.newton_called
    assert mf.level_shift == SCF_LEVEL_SHIFT_HARTREE
    assert mf.damp == SCF_DAMP_FACTOR
    assert mf.max_cycle == SCF_HARD_MAX_CYCLE


def test_run_scf_third_stage_falls_back_to_newton():
    # only the second-order restart converges it
    mf = StubMF(converge_on=3)
    run_scf(mf)
    assert mf.kernel_calls == 3
    assert mf.newton_called


def test_run_scf_raises_when_nothing_converges():
    mf = StubMF(converge_on=None)
    with pytest.raises(SCFConvergenceError, match="phytic"):
        run_scf(mf, label="phytic-acid B3LYP/6-311++G(d,p)")
    # the whole ladder was walked before giving up
    assert mf.kernel_calls == 3
    assert mf.newton_called


def test_run_scf_non_strict_warns_instead_of_raising():
    mf = StubMF(converge_on=None)
    with pytest.warns(UserWarning, match="best-effort"):
        out = run_scf(mf, label="anion", strict=False)
    assert out is mf
    assert not mf.converged


# --- estimate_cderi_gb: the density-fitting tensor size ---------------------

def test_estimate_cderi_gb_matches_the_known_phytic_scale():
    # ~1000 basis functions is the phytic-acid production-basis case that OOM'd
    # the container at ~13 GB; the estimate must land in that ballpark
    gb = estimate_cderi_gb(1000)
    assert 11.0 < gb < 13.0


def test_estimate_cderi_gb_grows_cubically():
    # doubling the basis is ~8x the tensor (naux ~ nao, pairs ~ nao^2)
    assert estimate_cderi_gb(2000) / estimate_cderi_gb(1000) == pytest.approx(
        8.0, rel=0.05)


# --- plan_scf_memory: in-core vs disk-spill vs refuse -----------------------

def test_plan_scf_memory_without_df_carries_the_budget():
    plan = plan_scf_memory(100, 4000, density_fit=False)
    assert not plan.density_fit
    assert plan.incore
    assert plan.max_memory_mb == 4000
    assert not plan.cderi_to_disk


def test_plan_scf_memory_small_tensor_stays_in_core():
    # a tiny tensor fits well under half the budget -> keep it in RAM
    plan = plan_scf_memory(100, 4000, density_fit=True)
    assert plan.density_fit and plan.incore and not plan.cderi_to_disk


def test_plan_scf_memory_large_tensor_spills_to_disk():
    # ~12 GB tensor cannot fit a 4 GB budget -> stream it from disk
    plan = plan_scf_memory(1000, 4000, density_fit=True)
    assert plan.density_fit and not plan.incore and plan.cderi_to_disk


def test_plan_scf_memory_refuses_a_tensor_over_the_ceiling():
    # far past the hard ceiling: a clear error beats an OOM crash mid-run
    huge = int(CDERI_CEILING_GB * 1000)
    with pytest.raises(MemoryError):
        plan_scf_memory(huge, 4000, density_fit=True)


# --- resolve_memory_budget_mb: env override / floor / fallback --------------

def test_resolve_memory_budget_env_override_wins():
    assert resolve_memory_budget_mb({MEMORY_BUDGET_ENV: "8000"}) == 8000


def test_resolve_memory_budget_env_override_clamped_to_floor():
    assert resolve_memory_budget_mb({MEMORY_BUDGET_ENV: "200"}) == MEMORY_FLOOR_MB


def test_resolve_memory_budget_returns_a_sane_default():
    # no override: whatever is detected (or the default), never below the floor
    budget = resolve_memory_budget_mb({})
    assert isinstance(budget, int) and budget >= MEMORY_FLOOR_MB


def test_resolve_memory_budget_default_when_nothing_detected(monkeypatch):
    # neither cgroup nor sysconf available -> the conservative default
    monkeypatch.setattr("corrosim.qm.engines._cgroup_limit_bytes",
                        lambda _reader: None)
    monkeypatch.setattr("corrosim.qm.engines._physical_ram_bytes",
                        lambda: None)
    assert resolve_memory_budget_mb({}) == DEFAULT_MEMORY_MB


# --- _cgroup_limit_bytes: container-limit parsing ---------------------------

def test_cgroup_limit_reads_a_v2_numeric_limit():
    reader = {"/sys/fs/cgroup/memory.max": "2147483648\n"}.get
    assert _cgroup_limit_bytes(reader) == 2147483648


def test_cgroup_limit_treats_v2_max_as_unlimited():
    reader = {"/sys/fs/cgroup/memory.max": "max\n"}.get
    assert _cgroup_limit_bytes(reader) is None


def test_cgroup_limit_treats_the_v1_sentinel_as_unlimited():
    # cgroup v1 reports a near-2**63 sentinel for "no limit"
    reader = {"/sys/fs/cgroup/memory/memory.limit_in_bytes":
              "9223372036854771712\n"}.get
    assert _cgroup_limit_bytes(reader) is None


def test_cgroup_limit_none_when_absent():
    assert _cgroup_limit_bytes(lambda _path: None) is None
