"""The cap has to be enforced by something that does not need the solver's help.

Three CLIs in this package accept a `--cap` and print it. For a long time none
of them enforced it: they passed it to `capped.solve_with_deadline`, which asks
the solver to interrupt itself on a timer, and `Cadical195.interrupt()` raises
NotImplementedError under python-sat >= 1.9.dev15 -- so the timer thread died
silently and the blocking solve ran to completion. A 1800 s cap was measured
running past 38 minutes, and a `search(..., timeout=60)` call written while
fixing this ran for seven.

A cap the caller can set and the code ignores is worse than no cap, because the
number gets quoted. These tests pin both halves: that the in-process route is
the unreliable one on this build, and that the out-of-process route works.
"""

from __future__ import annotations

import time

import pytest

from capped import run_capped_out_of_process, run_in_child


def _hang(cap_s=None):
    while True:
        time.sleep(0.05)


def _quick(cap_s=None):
    return {"status": "OK"}


def test_the_process_cap_actually_stops_a_wedged_child():
    t0 = time.time()
    r = run_capped_out_of_process(_hang, {}, 1.0)
    elapsed = time.time() - t0
    assert r.status == "TIMEOUT", r
    assert elapsed < 30, f"cap of 1.0s took {elapsed:.1f}s to bite"


def test_the_process_cap_does_not_break_a_fast_child():
    """Baseline: without this the test above would pass on a cap that kills
    everything."""
    r = run_capped_out_of_process(_quick, {}, 30.0)
    assert r.status == "OK", r
    assert r.value == {"status": "OK"}


def test_run_in_child_reports_an_error_distinctly_from_a_timeout():
    """A broken tool must not be recorded as a slow one."""
    def _boom(cap_s=None):
        raise RuntimeError("deliberate")
    r = run_in_child(_boom, {}, cap_s=30)
    assert r.status == "ERROR", r


def test_the_in_process_solver_interrupt_is_the_unreliable_route():
    """Why the caps go through a child process at all.

    If this ever starts passing -- i.e. CaDiCaL grows a working interrupt --
    the in-process route becomes usable again. Until then, code that relies on
    it has no cap, and this test says so out loud rather than leaving it as a
    comment.
    """
    from pysat.formula import CNF
    from pysat.solvers import Cadical195

    cnf = CNF()
    cnf.append([1, 2])
    with Cadical195(bootstrap_with=cnf) as solver:
        try:
            solver.interrupt()
        except NotImplementedError:
            pytest.skip("Cadical195.interrupt() raises NotImplementedError on "
                        "this python-sat build -- the documented reason every "
                        "cap in this package is enforced out of process")
        except Exception as e:                       # pragma: no cover
            pytest.skip(f"Cadical195.interrupt() unusable: {e!r}")
    pytest.fail("Cadical195.interrupt() now works; the in-process cap in "
                "capped.solve_with_deadline may be usable again -- re-measure "
                "before relying on it")
