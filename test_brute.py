"""Gates for the solver-free decider, and for the claim that motivated it.

The decider exists to answer one question about the four ladder timeouts: is
CDCL struggling because the problem is hard, or because it is being handed the
wrong problem? It can only answer that if it is itself trustworthy, so it is
checked here against CaDiCaL on random instances, and against hand-computed
cases where the answer is obvious.
"""

from __future__ import annotations

import random
from math import comb

import pytest

import brute
from obstruction import _orbit_count_of_subsets


def _solve_with_cadical(clauses):
    from pysat.formula import CNF
    from pysat.solvers import Cadical195
    cnf = CNF()
    for c in clauses:
        cnf.append(c)
    with Cadical195(bootstrap_with=cnf) as s:
        return "SAT" if s.solve() else "UNSAT"


def test_hand_cases():
    assert brute.decide([[1], [-1]], 1) == ("UNSAT", None)
    assert brute.decide([[1], [2], [-1, -2]], 2) == ("UNSAT", None)
    status, model = brute.decide([[1, 2], [-1, 2]], 2)
    assert status == "SAT" and brute.satisfies([[1, 2], [-1, 2]], model)


def test_the_empty_clause_is_unsatisfiable():
    assert brute.decide([[]], 3) == ("UNSAT", None)
    assert brute.count_models([[]], 3) == 0


def test_no_clauses_means_everything_survives():
    assert brute.count_models([], 5) == 32
    assert brute.decide([], 4)[0] == "SAT"


def test_variable_masks_have_the_right_shape():
    """Bit i of the assignment index IS variable i+1, so each mask must have
    exactly half the bits set, and masks must be pairwise independent."""
    for v in range(1, 8):
        masks, full = brute._var_masks(v)
        assert len(masks) == v
        for i, m in enumerate(masks):
            assert bin(m).count("1") == (1 << v) // 2, (v, i)
            for m2 in masks[i + 1:]:
                assert bin(m & m2).count("1") == (1 << v) // 4


def test_count_models_matches_a_direct_count():
    clauses = [[1, 2], [-2, 3], [-1, -3]]
    direct = 0
    for m in range(8):
        val = {1: (m >> 0) & 1, 2: (m >> 1) & 1, 3: (m >> 2) & 1}
        if all(any((val[abs(l)] == 1) == (l > 0) for l in c) for c in clauses):
            direct += 1
    assert brute.count_models(clauses, 3) == direct


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_agrees_with_cadical_on_random_instances(seed):
    """100 random CNFs per seed, spanning both answers."""
    rng = random.Random(seed)
    seen = set()
    for _ in range(100):
        v = rng.randint(1, 9)
        clauses = [sorted({rng.choice([1, -1]) * rng.randint(1, v)
                           for _ in range(rng.randint(1, 3))})
                   for _ in range(rng.randint(1, 40))]
        status, model = brute.decide(clauses, v)
        assert status == _solve_with_cadical(clauses), clauses
        seen.add(status)
        if status == "SAT":
            assert brute.satisfies(clauses, model), clauses
    assert seen == {"SAT", "UNSAT"}, f"only saw {seen}; not a two-sided test"


def test_refuses_instances_that_are_too_large():
    with pytest.raises(ValueError, match="beyond brute force"):
        brute.decide([[1]], brute.MAX_VARS + 1)


def test_rejects_a_literal_outside_the_declared_range():
    with pytest.raises(ValueError, match="exceeds n_vars"):
        brute.decide([[5]], 3)


# --------------------------------------------------------------------------
# The arithmetic that made the ladder timeouts look wrong
# --------------------------------------------------------------------------


def test_rung_one_collapses_to_1240_distinct_clauses():
    """Rung 1 has 166 variables and 40920 raw clauses, one per 4-subset of the
    33-point base. Translates give the SAME clause: both the variables and the
    pinned colours are Z_33-invariant. Every orbit has full size 33, since a
    non-trivial stabiliser would have order dividing both 33 and 4.

    So the real instance is 1240 width-4 clauses over 166 variables -- density
    7.5, below the random 4-SAT threshold of about 9.93, not the density 246
    the raw count implies. That is why a 30-minute timeout there is a fact
    needing explanation rather than a normal outcome.
    """
    assert comb(33, 4) == 40920
    assert 40920 % 33 == 0 and 40920 // 33 == 1240
    assert _orbit_count_of_subsets(33, 4) == 1240
    assert _orbit_count_of_subsets(33, 3) == 166      # the free variables
    assert round(1240 / 166, 1) == 7.5


# --------------------------------------------------------------------------
# Malformed input: a clause list is not trusted to be well-formed
# --------------------------------------------------------------------------


@pytest.mark.parametrize("clauses", [[[0]], [[1, 0]], [[-1, 0, 2]]])
def test_literal_zero_is_rejected_not_silently_accepted(clauses):
    """0 terminates a DIMACS clause; it is not a literal.

    `abs(0) - 1` is -1, which indexes the LAST variable's mask instead of
    raising, so `decide([[0]], 1)` used to return a confident SAT. A decider
    whose whole job is to be a second opinion must not quietly accept
    malformed input.
    """
    with pytest.raises(ValueError, match="not a literal"):
        brute.decide(clauses, 3)
    with pytest.raises(ValueError, match="not a literal"):
        brute.count_models(clauses, 3)


def test_count_models_validates_range_like_decide_does():
    """The two entry points must reject the same things; count_models used to
    raise a bare IndexError where decide raised a clear ValueError."""
    with pytest.raises(ValueError, match="exceeds n_vars"):
        brute.count_models([[5]], 3)
