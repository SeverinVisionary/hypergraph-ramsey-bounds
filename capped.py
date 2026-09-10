"""Deadlines that are actually enforced.

Three separate defects motivated this file, all of them "the cap is advertised
but does nothing":

  * `cyclic.run(..., cap_s, ...)` accepted a cap and never consulted it.
  * `search.search(..., timeout=...)` accepted a timeout and explicitly did
    nothing with it.
  * `calibrate.timed_run` capped the child with `p.join(cap_s)` but then read
    the result with an unbounded `q.get()`, so a child that died before writing
    hung the parent forever; the following `p.join()` after `terminate()` was
    also unbounded.

The consequence was operational, not cosmetic: the n=34 run was supervised by an
external watchdog precisely because `--cap` did not work, and that watchdog
matched a build log line and destroyed a 46-minute run.

Two layers, because they fail differently:

  `solve_with_deadline`  in-process: a timer thread calls `solver.interrupt()`,
                         and the solve runs under `solve_limited`.  Cheap, keeps
                         the model, but relies on the solver honouring the
                         interrupt.
  `run_in_child`         out-of-process: a monotonic end-to-end deadline over
                         build + solve + verify, a BOUNDED queue read, an
                         explicit child exit-code check, and an escalating
                         terminate -> kill sequence.  Survives a wedged child.

Statuses are distinguished deliberately.  TIMEOUT is a null; ERROR is a broken
tool.  A broken tool must abort the run and a negative answer must not, which
is impossible if the two are reported the same way.
"""

from __future__ import annotations

import multiprocessing as mp
import queue as queue_mod
import threading
import time

__all__ = ["solve_with_deadline", "run_in_child", "run_capped_out_of_process",
           "CappedResult"]

# How long to wait for a child to die after terminate() before SIGKILL.
_REAP_GRACE_S = 5.0
# How long to wait for a result from a child that has ALREADY exited. The queue
# has a background feeder thread, so a child that put() just before exiting may
# need a moment to flush; a child that never put() will never put(). Two seconds
# covers the flush without making every failure path cost ten.
_QUEUE_GRACE_S = 2.0


class CappedResult:
    """Outcome of a capped call.

    status is one of:
      "OK"      -- `value` holds the child's record
      "TIMEOUT" -- the deadline expired; `value` is None
      "ERROR"   -- the child died or produced nothing; `detail` says how
    """

    __slots__ = ("status", "value", "elapsed_s", "detail")

    def __init__(self, status, value=None, elapsed_s=0.0, detail=""):
        self.status = status
        self.value = value
        self.elapsed_s = elapsed_s
        self.detail = detail

    def __repr__(self):
        return f"<CappedResult {self.status} {self.elapsed_s:.2f}s {self.detail}>"


def solve_with_deadline(solver, cap_s):
    """Run `solver.solve()` under a wall-clock cap, in this process.

    Returns (status, model) with status in {"SAT", "UNSAT", "TIMEOUT"}.

    `cap_s = None` means no cap, in which case this is a plain blocking solve.
    Otherwise a timer thread calls `solver.interrupt()` at the deadline and the
    solve runs under `solve_limited(expect_interrupt=True)`, which is the only
    way pysat exposes a wall-clock stop for Cadical.
    """
    if cap_s is None:
        sat = solver.solve()
        return ("SAT" if sat else "UNSAT"), (solver.get_model() if sat else None)

    if cap_s <= 0:
        raise ValueError(f"cap_s must be positive, got {cap_s!r}")

    # Refuse a cap this route cannot keep. Under python-sat >= 1.9.dev15
    # Cadical195.interrupt() raises NotImplementedError; the timer thread
    # below then dies silently, its exception never reaches the solving
    # thread, and the blocking solve runs to completion -- so the caller gets
    # an unbounded run while believing it set a deadline. Measured: a nominal
    # 1800s cap ran past 38 minutes, and a 60s one past seven.
    #
    # Failing here is not a regression from "it worked before": it never
    # worked, it only looked like it did. Callers that need a real deadline
    # use run_capped_out_of_process, whose SIGTERM/SIGKILL cap does not
    # require the solver's cooperation.
    try:
        solver.interrupt()
    except NotImplementedError as e:
        raise NotImplementedError(
            f"{type(solver).__name__}.interrupt() is unavailable "
            f"({e}), so an in-process cap of {cap_s}s cannot be enforced and "
            f"would silently run unbounded. Use "
            f"capped.run_capped_out_of_process() for a real deadline, or pass "
            f"cap_s=None for an explicitly uncapped solve.") from None
    try:
        solver.clear_interrupt()
    except (AttributeError, NotImplementedError):
        pass

    timer = threading.Timer(cap_s, solver.interrupt)
    timer.daemon = True
    timer.start()
    try:
        sat = solver.solve_limited(expect_interrupt=True)
    finally:
        timer.cancel()
        # clear_interrupt so the solver object is reusable by a caller that
        # wants to continue with a larger budget.
        try:
            solver.clear_interrupt()
        except (AttributeError, NotImplementedError):
            # AttributeError: solver has no clear_interrupt (older pysat).
            # NotImplementedError: pysat 1.9.dev-series raises this for
            # CaDiCaL instead of omitting the method. Either way the
            # already-computed sat/model below is unaffected -- this call
            # only resets internal interrupt state for reuse.
            pass

    if sat is None:
        return "TIMEOUT", None
    return ("SAT" if sat else "UNSAT"), (solver.get_model() if sat else None)


def _child(fn, kwargs, q):
    try:
        q.put(("OK", fn(**kwargs)))
    except BaseException as exc:  # noqa: BLE001 - report, never swallow
        q.put(("ERROR", f"{type(exc).__name__}: {exc}"))


_POLL_S = 0.1


def run_in_child(fn, kwargs, cap_s):
    """Run `fn(**kwargs)` in a child process under a monotonic end-to-end cap.

    The cap covers everything the child does -- construction, solving and
    verification -- not just the solve.  A timeout is therefore reported as a
    bound on the whole call, and never attributed to the solver alone.

    Context choice: "fork" where the platform has it, "spawn" otherwise.  This
    is not a performance preference.  A spawn child re-imports `__main__`, and
    under pytest `__main__` is the pytest console script -- so spawning from a
    test re-runs the entire test session inside every child.  Measured here:
    the suite went from 25s to 429s.  Fork children inherit the interpreter and
    import nothing.

    Polls the queue instead of `p.join(cap_s)` first: a `multiprocessing.Queue`
    write is buffered through a pipe by a background feeder thread, and a
    payload larger than the pipe's buffer (a witness `chi` list is tens of
    thousands of ints) blocks that thread until the reader drains it. A parent
    stuck in a blocking `p.join()` never reads meanwhile, so the child never
    fully exits and `p.join()` waits out the entire cap regardless of the
    answer already sitting in the pipe -- reproduced live: a completed SAT
    result sat unread while the child idled on a futex for the full 900s cap.
    Draining the queue on every poll tick, cap or no cap, avoids this.
    """
    ctx = mp.get_context("fork" if "fork" in mp.get_all_start_methods() else "spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_child, args=(fn, kwargs, q))
    start = time.monotonic()
    p.start()
    deadline = start + cap_s

    got = False
    tag = payload = None
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            tag, payload = q.get(timeout=min(_POLL_S, remaining))
            got = True
            break
        except queue_mod.Empty:
            pass
        if not p.is_alive():
            # Dead and silent so far. Give the feeder thread one short grace
            # window to flush anything already queued before giving up --
            # it will never produce more than that once the child is gone.
            try:
                tag, payload = q.get(timeout=min(_QUEUE_GRACE_S, max(0.0, remaining)))
                got = True
            except queue_mod.Empty:
                pass
            break
    elapsed = time.monotonic() - start

    if not got:
        if p.is_alive():
            p.terminate()
            p.join(_REAP_GRACE_S)
            if p.is_alive():
                p.kill()
                p.join(_REAP_GRACE_S)
            _drain(q)
            return CappedResult("TIMEOUT", None, elapsed,
                                f"cap {cap_s:.1f}s expired; child reaped")
        return CappedResult(
            "ERROR", None, elapsed,
            f"child exited with code {p.exitcode!r} without producing a result",
        )

    # A result arrived. Reap the child -- it should already be exiting.
    p.join(_REAP_GRACE_S)
    if p.is_alive():
        p.terminate()
        p.join(_REAP_GRACE_S)
        if p.is_alive():
            p.kill()
            p.join(_REAP_GRACE_S)

    if tag == "ERROR":
        return CappedResult("ERROR", None, elapsed, payload)
    if p.exitcode not in (0, None):
        return CappedResult(
            "ERROR", payload, elapsed,
            f"child produced a result but exited with code {p.exitcode!r}",
        )
    return CappedResult("OK", payload, elapsed, "")


def run_capped_out_of_process(run_fn, kwargs, cap_s):
    """Run `run_fn(**kwargs, cap_s=None)` under a hard, OS-enforced wall-clock
    cap, by delegating to `run_in_child`.

    Exists because `solve_with_deadline`'s in-process cap is a silent no-op
    for CaDiCaL under python-sat >= 1.9.dev15: `Cadical195.interrupt()`
    unconditionally raises `NotImplementedError`, so the timer thread that is
    supposed to call it dies silently (the exception never reaches the
    solving thread) and the blocking `solve_limited()` call runs to actual
    completion regardless of `cap_s`. Confirmed live: a 1800s-capped rung
    ran unbounded past 38 minutes with no interrupt. `run_in_child`'s
    SIGTERM/SIGKILL cap does not depend on the solver library cooperating,
    so it works regardless.

    `run_fn` must accept a `cap_s` keyword, which this forces to `None` (a
    plain blocking `solver.solve()`, see `solve_with_deadline`) since the
    outer process-level deadline is what enforces the cap here.
    """
    call_kwargs = dict(kwargs)
    call_kwargs["cap_s"] = None
    return run_in_child(run_fn, call_kwargs, cap_s)


def _drain(q):
    """Discard anything a reaped child left behind, without blocking."""
    try:
        while True:
            q.get_nowait()
    except Exception:  # noqa: BLE001 - Empty, or a closed queue
        pass
