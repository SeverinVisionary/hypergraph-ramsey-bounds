"""SAT search for hypergraph Ramsey witnesses, and the known-answer gate.

Encoding (Wesley, arXiv:2509.03784v1 p.4 Remark 7, for hypergraphs):
one Boolean per k-subset of [n], true = colour 1. For every s-subset a clause
saying "not all colour 0"; for every t-subset a clause saying "not all colour 1".
SAT  => a witness exists on n points => R(s,t;k) >= n+1.
UNSAT => no witness on n points      => R(s,t;k) <= n.

Two rules this file exists to obey:

  1.  Run the known-answer gate BEFORE reading any open case, on the production
      path. `known_answer_gate()` reproduces R(3,3) = 6 and R(3,4) = 9 from
      this same code, both sides of each, and the SAT half of R(4,4;3) = 13.
      The UNSAT half of R(4,4;3) does not decide under any budget tried here
      and is reported as a timeout rather than claimed -- read that function's
      docstring before quoting this gate. A solver that cannot reproduce a
      known value cannot be trusted on an unknown one.
  2.  A SAT model is never trusted. Every model this file produces is handed to
      verify.verify_both(), which re-derives the property from scratch by two
      independent routes. The solver's word is not evidence.
"""

from __future__ import annotations

import time
from itertools import combinations
from math import comb

from pysat.formula import CNF
from pysat.solvers import Cadical195

from capped import solve_with_deadline, run_capped_out_of_process
from verify import verify_both, verify_lex

__all__ = ["build_cnf", "search", "known_answer_gate", "two_sided_verdict",
           "PUBLISHED_TWO_SIDED", "PUBLISHED_R_4_4_3", "SearchOutcome"]


class SearchOutcome:
    __slots__ = ("status", "chi", "seconds", "n", "s", "t", "k", "stats")

    def __init__(self, status, chi, seconds, n, s, t, k, stats=None):
        self.status = status  # "SAT" | "UNSAT" | "TIMEOUT"
        self.chi = chi
        self.seconds = seconds
        self.n, self.s, self.t, self.k = n, s, t, k
        self.stats = stats or {}

    def __repr__(self):
        return (
            f"<{self.status} R({self.s},{self.t};{self.k}) n={self.n} "
            f"{self.seconds:.2f}s>"
        )


def build_cnf(n: int, s: int, t: int, k: int) -> CNF:
    """CNF whose satisfying assignments are exactly the witnesses on [n].

    Variable for the k-subset with lexicographic rank i is (i + 1).
    """
    if not (0 < k < min(s, t) <= n):
        raise ValueError(f"bad parameters: n={n} s={s} t={t} k={k}")
    index = {sub: i + 1 for i, sub in enumerate(combinations(range(n), k))}
    assert len(index) == comb(n, k)

    cnf = CNF()
    added = {"s_clauses": 0, "t_clauses": 0}
    for clique in combinations(range(n), s):
        cnf.append([index[sub] for sub in combinations(clique, k)])
        added["s_clauses"] += 1
    for clique in combinations(range(n), t):
        cnf.append([-index[sub] for sub in combinations(clique, k)])
        added["t_clauses"] += 1

    # §6 completeness: every clique of each size contributed exactly one clause.
    assert added["s_clauses"] == comb(n, s), (
        f"built {added['s_clauses']} s-clauses, expected C({n},{s})={comb(n, s)}"
    )
    assert added["t_clauses"] == comb(n, t), (
        f"built {added['t_clauses']} t-clauses, expected C({n},{t})={comb(n, t)}"
    )
    assert cnf.nv <= comb(n, k)
    return cnf


def search(
    n: int, s: int, t: int, k: int, timeout: float | None = None, verbose: bool = True
) -> SearchOutcome:
    """Search for a witness on n points. Any model found is independently verified."""
    t0 = time.time()
    cnf = build_cnf(n, s, t, k)
    build_s = time.time() - t0
    nvars, ncls = comb(n, k), len(cnf.clauses)
    if verbose:
        print(
            f"  R({s},{t};{k}) n={n}: {nvars} vars, {ncls} clauses "
            f"(built in {build_s:.2f}s)",
            flush=True,
        )

    t1 = time.time()
    with Cadical195(bootstrap_with=cnf) as solver:
        status, model = solve_with_deadline(solver, timeout)
    solve_s = time.time() - t1

    stats = {"vars": nvars, "clauses": ncls, "build_s": build_s, "solve_s": solve_s}

    if status == "TIMEOUT":
        # A null of the search under this budget. NOT a statement about the
        # existence of a witness, and never to be reported as one.
        if verbose:
            print(f"    n={n} -> TIMEOUT at {timeout:.1f}s (a null, not a verdict)",
                  flush=True)
        return SearchOutcome("TIMEOUT", None, time.time() - t0, n, s, t, k, stats)

    if status == "UNSAT":
        return SearchOutcome("UNSAT", None, time.time() - t0, n, s, t, k, stats)

    chi = [0] * nvars
    for lit in model:
        v = abs(lit)
        if 1 <= v <= nvars:
            chi[v - 1] = 1 if lit > 0 else 0

    # §1: the solver's verdict is not evidence. Re-derive it.
    if not verify_both(n, s, t, k, chi):
        res = verify_lex(n, s, t, k, chi)
        raise AssertionError(
            f"solver returned SAT but the model is NOT a witness at n={n}: {res!r}"
        )
    return SearchOutcome("SAT", chi, time.time() - t0, n, s, t, k, stats)


def two_sided_verdict(lo_status, hi_status, s, t, R):
    """Every reason a two-sided known-answer check has NOT been met.

    Split out and made total on purpose. The obvious way to write this test is
    to collect the n that come back SAT and assert the largest is R-1 -- which
    passes when n=R TIMES OUT, because a timeout simply does not appear in the
    list. The gate then reports success having never observed the UNSAT side,
    which is the half that pins the convention. test_known_answer.py drives
    both branches below to a non-empty result.
    """
    problems = []
    if lo_status != "SAT":
        problems.append(
            f"R({s},{t}) = {R} requires a witness on {R - 1} points; "
            f"this code said {lo_status}")
    if hi_status != "UNSAT":
        problems.append(
            f"R({s},{t}) = {R} requires NO witness on {R} points; this code "
            f"said {hi_status}. A TIMEOUT here is a null of the search, not "
            f"the UNSAT the gate claims to have seen")
    return problems


def _status_under_cap(n, s, t, k, cap_s=None):
    """Child entry point for the OS-enforced cap. Module level so fork can
    pickle it; returns only the status, so nothing large crosses the queue."""
    return search(n, s, t, k, timeout=cap_s, verbose=False).status


def _capped_status(n, s, t, k, budget_s):
    """Decide (n,s,t,k) under a cap that is actually enforced.

    NOT `search(..., timeout=budget_s)`. That path caps by asking the solver to
    interrupt itself, and `Cadical195.interrupt()` raises NotImplementedError
    under python-sat >= 1.9.dev15 -- the timer thread dies silently and the
    solve runs to completion. Measured here while writing this gate: a call
    with `timeout=60.0` was still running after seven minutes. The child
    process cap does not depend on the solver cooperating.
    """
    r = run_capped_out_of_process(_status_under_cap,
                                  {"n": n, "s": s, "t": t, "k": k}, budget_s)
    if r.status == "TIMEOUT":
        return "TIMEOUT", r.elapsed_s
    if r.status == "ERROR":
        raise RuntimeError(f"known-answer gate child failed at n={n}: {r.detail}")
    return r.value, r.elapsed_s


# Published Ramsey values, established outside this repository, used as
# two-sided gates: a witness must exist on R-1 points and must not on R.
# DS1 rev #18 Table I; R(3,3) and R(3,4) are Greenwood-Gleason 1955.
#
# Both sides of both entries decide in under a tenth of a second on the
# production path. That matters: the k=3 gate below has a side that does NOT
# finish (see its docstring), and a gate that cannot be run is not a gate.
PUBLISHED_TWO_SIDED = [
    (3, 3, 2, 6),
    (3, 4, 2, 9),
]

# R(4,4;3) = 13, McKay-Radziszowski 1991; DS1 rev #18 p.73 calls it the only
# known value of a nontrivial classical Ramsey number for hypergraphs.
PUBLISHED_R_4_4_3 = 13


def known_answer_gate(budget_s: float = 120.0, verbose: bool = True) -> dict:
    """Reproduce published Ramsey values on the production path.

    The gate is BOTH sides. SAT below the value alone would pass for a solver
    that always says SAT; UNSAT at the value alone would pass for one that
    always says UNSAT. Only the pair pins the encoding and the off-by-one, and
    only a published value makes it a check on this code rather than a check of
    this code against itself.

    WHAT IS AND IS NOT ESTABLISHED HERE
    -----------------------------------
    Two-sided, and reproduced: R(3,3) = 6 and R(3,4) = 9 at k = 2. These fix
    the convention -- a good colouring on n points gives R >= n+1 -- on the
    same build_cnf/search path used for every claim in this package.

    One-sided, and honestly reported as such: R(4,4;3) = 13 at k = 3. The SAT
    half (a witness on 12 points) reproduces in a few seconds. The UNSAT half
    at n = 13 has NOT been reproduced here: it was run for 74 minutes and again
    for 64 minutes without deciding, and `logs/gate.log` is the record of the
    first of those, stopping mid-run. It is attempted under `budget_s` and its
    outcome is returned verbatim. A TIMEOUT is a null of this search under this
    budget. It is NOT evidence about R(4,4;3), whose value is published and not
    in question, and it must never be reported as the gate having passed.
    """
    results = {"two_sided": [], "r443": {}}

    for s, t, k, R in PUBLISHED_TWO_SIDED:
        lo, lo_s = _capped_status(R - 1, s, t, k, budget_s)
        hi, hi_s = _capped_status(R, s, t, k, budget_s)
        if verbose:
            print(f"  R({s},{t})={R}  n={R - 1:<3} -> {lo:<7} want SAT    "
                  f"{lo_s:6.2f}s", flush=True)
            print(f"  R({s},{t})={R}  n={R:<3} -> {hi:<7} want UNSAT  "
                  f"{hi_s:6.2f}s", flush=True)
        problems = two_sided_verdict(lo, hi, s, t, R)
        if problems:
            raise AssertionError("GATE FAILED: " + "; ".join(problems))
        results["two_sided"].append((s, t, k, R - 1, lo))
        results["two_sided"].append((s, t, k, R, hi))

    lo_status, lo_s = _capped_status(12, 4, 4, 3, budget_s)
    if verbose:
        print(f"  R(4,4;3)=13  n=12  -> {lo_status:<7} want SAT    "
              f"{lo_s:6.2f}s", flush=True)
    if lo_status != "SAT":
        raise AssertionError(
            f"GATE FAILED: R(4,4;3) >= 13 requires a witness on 12 points, "
            f"this code said {lo_status}")
    results["r443"]["n12"] = lo_status

    hi_status, hi_s = _capped_status(13, 4, 4, 3, budget_s)
    results["r443"]["n13"] = hi_status
    results["r443"]["n13_reproduced"] = (hi_status == "UNSAT")
    if verbose:
        note = ("reproduced" if hi_status == "UNSAT"
                else f"NOT reproduced within {budget_s:.0f}s -- a null of this "
                     f"search, not a result")
        print(f"  R(4,4;3)=13  n=13  -> {hi_status:<7} want UNSAT  "
              f"{hi_s:6.2f}s  ({note})", flush=True)
    if hi_status == "SAT":
        raise AssertionError(
            "GATE FAILED: a 13-point witness would contradict R(4,4;3) = 13")

    results["passed"] = True
    if verbose:
        print("  GATE PASSED on the two-sided published values; the k=3 UNSAT "
              "half is reported above, not assumed.\n")
    return results


if __name__ == "__main__":
    known_answer_gate()
