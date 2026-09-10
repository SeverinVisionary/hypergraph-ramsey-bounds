"""The gates whose expected numbers come from OUTSIDE this repository.

Every other test here checks this code against this code. These run the whole
pipeline -- build_cnf, solve, expand, verify -- at parameters where the answer
is published, and check that the bound the convention reports equals it.

The convention is the thing under test. `R` is the LEAST n forcing a
monochromatic clique (DS1 rev #18 p.5), so a good colouring on n points gives
`R >= n+1`. The whole `R(5,5;4) >= 36` claim rests on that direction and on
nothing else, which is why it is checked against published values rather than
against this package's own restatement of the definition.

An earlier version of this file asserted `12 + 1 == PUBLISHED_R_4_4_3` and
called that the off-by-one gate. Both sides of that comparison are constants
written here, so it holds whatever the code does; it was standing in for a
computation that does not terminate (see `search.known_answer_gate`). The tests
below derive the largest witness-bearing n FROM THE SOLVER and compare that.
"""

from __future__ import annotations

from itertools import combinations

import pytest

from ansatz import build_cnf, expand, run
from search import (PUBLISHED_R_4_4_3, PUBLISHED_TWO_SIDED,
                    _capped_status, two_sided_verdict)


def _trivial_group(n):
    return [list(range(n))]


def _has_mono_clique(chi, n, s, k):
    """Independent of verify.py: rebuild the index and scan."""
    idx = {f: i for i, f in enumerate(combinations(range(n), k))}
    for W in combinations(range(n), s):
        cols = {chi[idx[f]] for f in combinations(W, k)}
        if len(cols) == 1:
            return True
    return False


@pytest.mark.parametrize("s,t,k,R", PUBLISHED_TWO_SIDED)
def test_both_sides_of_the_published_value(s, t, k, R):
    """A witness must exist on R-1 points and must NOT exist on R.

    Stated as two explicit statuses, not as "the largest n that came back SAT".
    That formulation passes when the upper side times out, because a timeout is
    simply absent from the list -- the gate then never observes UNSAT, which is
    the half that pins the convention the R(5,5;4) >= 36 claim rests on.
    """
    lo, _ = _capped_status(R - 1, s, t, k, 120.0)
    hi, _ = _capped_status(R, s, t, k, 120.0)
    assert two_sided_verdict(lo, hi, s, t, R) == [], (lo, hi)


@pytest.mark.parametrize("lo,hi", [
    ("SAT", "TIMEOUT"),      # the failure the old formulation could not see
    ("SAT", "SAT"),          # a witness at R would contradict the value
    ("TIMEOUT", "UNSAT"),
    ("UNSAT", "UNSAT"),      # no witness at R-1 contradicts it the other way
    ("TIMEOUT", "TIMEOUT"),
])
def test_the_two_sided_verdict_rejects_every_incomplete_outcome(lo, hi):
    """Negative controls. Without these the assertion above is a gate nobody
    has watched fail."""
    assert two_sided_verdict(lo, hi, 3, 3, 6)


def test_the_two_sided_verdict_accepts_the_correct_pair():
    """Baseline, so the controls above cannot pass by rejecting everything."""
    assert two_sided_verdict("SAT", "UNSAT", 3, 3, 6) == []


def test_the_published_hypergraph_value_reproduces_on_the_sat_side():
    """R(4,4;3) = 13: a good 2-colouring of the triples of a 12-set exists.

    The UNSAT half at n=13 is NOT asserted here. It does not decide under any
    budget this package has been able to spend on it, and claiming it from a
    constant is what the previous version of this file did.
    """
    rec = run("R(4,4;3) gate", _trivial_group(12), n=12, s=4, t=4, k=3,
              cap_s=600, verbose=False)
    assert rec["status"] == "SAT", "a 12-point (4,4;3) witness must exist"
    chi = rec["chi"]
    assert len(chi) == len(list(combinations(range(12), 3))) == 220
    # Re-derived here, sharing no code with verify.py or the solver.
    assert not _has_mono_clique(chi, 12, 4, 3)


def test_a_thirteen_point_witness_would_contradict_the_published_value():
    """The direction the R(5,5;4) claim depends on, stated as a live check.

    Not an assertion that n=13 is UNSAT -- that is the half that does not
    decide. An assertion that IF the search ever returns SAT at n=13, the gate
    must fail rather than report a new bound.

    The cap here has to be the out-of-process one. `search(timeout=...)` asks
    the solver to interrupt itself, and CaDiCaL under python-sat >= 1.9.dev15
    raises NotImplementedError from `interrupt()`, so that cap is a silent
    no-op and this test would never return.
    """
    status, secs = _capped_status(13, 4, 4, 3, 20.0)
    assert status in ("UNSAT", "TIMEOUT"), (
        f"search returned {status} at n=13 for R(4,4;3) in {secs:.1f}s; a "
        f"witness there would contradict the published value "
        f"{PUBLISHED_R_4_4_3}")


@pytest.mark.parametrize("m", [12, 13])
def test_symmetric_classes_at_the_gate_behave(m):
    """Z_m-invariant classes at the gate parameters are all UNSAT.

    At m=13 they MUST be: a 13-point witness would contradict the published
    value. At m=12 it merely says the cyclic class is too rigid -- a null of
    the restricted search, not of the general problem."""
    gens = [[(i + 1) % m for i in range(m)]]
    rec = run(f"Z_{m} gate", gens, n=m, s=4, t=4, k=3, cap_s=120, verbose=False)
    assert rec["status"] == "UNSAT"


def test_dedup_preserves_the_constraint_two_sidedly():
    """The dedup property, checked two-sidedly.

    A previous version rebuilt the very same
    frozenset-of-orbits expression that `build_cnf` uses and compares the two,
    so it proves determinism and nothing else: if S did NOT determine the
    constraint, both sides would agree and it would still pass.

    The real property is that an orbit assignment satisfies the deduplicated
    CNF exactly when its expansion has no monochromatic s-set. Check that
    directly, on random groups and random assignments, and require BOTH
    outcomes to occur so the test cannot pass vacuously.
    """
    import random
    rng = random.Random(20260906)
    agree = witness_positive = 0
    for _ in range(40):
        n = rng.randint(6, 8)
        k, s = 3, 4
        gens = [rng.sample(range(n), n) for _ in range(rng.randint(1, 2))]
        clauses, orbit_of, stats = build_cnf(gens, n=n, s=s, t=s, k=k)
        if stats["vars"] == 0:
            continue
        for _ in range(25):
            assign = {v: rng.randint(0, 1) for v in range(1, stats["vars"] + 1)}
            model = [v if assign[v] else -v for v in assign]
            sat_cnf = all(any((lit > 0) == bool(assign[abs(lit)]) for lit in c)
                          for c in clauses)
            chi = expand(model, orbit_of, n, k)
            no_mono = not _has_mono_clique(chi, n, s, k)
            assert sat_cnf == no_mono, (n, gens, model)
            agree += 1
            witness_positive += int(no_mono)
    assert agree > 500, agree
    assert 0 < witness_positive < agree, (
        f"{witness_positive}/{agree} -- need both outcomes or the test is vacuous")
