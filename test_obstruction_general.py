"""Gates for Theorem A and the exact emptiness criterion.

A criterion that over-claims is worse than none: it would retire ansaetze that
are perfectly capable of holding a witness. So every test here is paired --
where the theorem fires, something independent must confirm the class really is
empty; where it stays silent, a witness must actually exist.
"""

from __future__ import annotations

from itertools import combinations

import pytest

from obstruction_general import (
    class_is_empty, cyclic, forced_orbits, pair_regular_fixed_point_obstruction,
    theorem_a_applies, _is_prime,
)


def _witness_exists(gens, n, s, t, k, cap=60):
    """Ask the real pipeline whether the class contains a witness."""
    from ansatz import run
    return run("probe", gens, n=n, s=s, t=t, k=k, cap_s=cap,
               verbose=False)["status"]


# --------------------------------------------------------------------------
# Theorem A fires, and is right when it does
# --------------------------------------------------------------------------


@pytest.mark.parametrize("n", [5, 10, 15, 20, 25, 30, 35, 40])
def test_theorem_a_fires_for_r55_4_exactly_when_five_divides_n(n):
    applies, _ = theorem_a_applies(n, s=5, k=4, every_colour_forbids_s=True)
    assert applies == (n % 5 == 0)


@pytest.mark.parametrize("n,expect", [(3, True), (5, False), (6, True), (7, False), (9, True)])
def test_theorem_a_on_the_classical_graph_case_r33(n, expect):
    """s=3, k=2: the ordinary triangle Ramsey problem, where the answer is known."""
    applies, _ = theorem_a_applies(n, s=3, k=2, every_colour_forbids_s=True)
    assert applies == expect


def test_the_pentagon_is_the_positive_control_for_r33():
    """R(3,3) = 6, so a witness exists on 5 points and none on 6.

    At n=5 Theorem A is silent (3 does not divide 5) and the class really does
    contain the classical 5-cycle/pentagram colouring. At n=6 the theorem fires
    and there is genuinely no witness at all, invariant or otherwise. If the
    theorem had fired at n=5 it would have retired a class containing the most
    famous witness in the subject."""
    assert theorem_a_applies(5, s=3, k=2, every_colour_forbids_s=True)[0] is False
    assert _witness_exists(cyclic(5), 5, 3, 3, 2) == "SAT"
    assert theorem_a_applies(6, s=3, k=2, every_colour_forbids_s=True)[0] is True
    assert _witness_exists(cyclic(6), 6, 3, 3, 2) == "UNSAT"


@pytest.mark.parametrize("n", [10, 15, 20])
def test_where_theorem_a_fires_the_pipeline_agrees_it_is_empty(n):
    """Soundness: the theorem must never claim empty for a class that is not."""
    applies, _ = theorem_a_applies(n, s=5, k=4, every_colour_forbids_s=True)
    assert applies
    empty, _ = class_is_empty(cyclic(n), n, 5, 5, 4)
    assert empty, f"Theorem A claimed Z_{n} is empty but the criterion disagrees"


# --------------------------------------------------------------------------
# Sharpness: every hypothesis is load-bearing
# --------------------------------------------------------------------------


def test_k_equals_s_minus_one_is_necessary():
    """s prime and s | |G|, but k < s-1: a witness EXISTS, so the theorem must
    not fire.

    An s-cycle permutes the k-subsets of an s-set transitively only when
    C(s,k) = s, i.e. k = 1 or k = s-1. At k=2, s=5 the ten faces of a 5-set
    split into several orbits and the colouring is free to differ across them.
    Z_10 with 5 | 10 is exactly the configuration Theorem A would exclude if the
    k hypothesis were dropped -- and it holds a witness.
    """
    applies, why = theorem_a_applies(10, s=5, k=2, every_colour_forbids_s=True)
    assert applies is False and "k=2" in why
    assert _witness_exists(cyclic(10), 10, 5, 5, 2) == "SAT"


def test_primality_of_s_is_necessary_for_the_proof():
    """s=4 is not prime, so Cauchy yields no element of order 4 from 4 | |G|,
    and an element of order 4 need not have a 4-cycle anyway (it can be a
    product of 2-cycles). The theorem correctly refuses to fire."""
    applies, why = theorem_a_applies(12, s=4, k=3, every_colour_forbids_s=True)
    assert applies is False and "not prime" in why


def test_theorem_a_is_silent_when_s_does_not_divide_the_order():
    for order in (34, 33, 32, 31, 544, 168):
        assert theorem_a_applies(order, s=5, k=4, every_colour_forbids_s=True)[0] is False


# --------------------------------------------------------------------------
# The exact criterion, against the pipeline
# --------------------------------------------------------------------------


@pytest.mark.parametrize("n,s,t,k", [
    (5, 3, 3, 2), (6, 3, 3, 2), (7, 3, 3, 2),
    (6, 4, 4, 3), (7, 4, 4, 3), (8, 4, 4, 3),
    (6, 5, 5, 4), (7, 5, 5, 4),
])
def test_criterion_never_calls_a_nonempty_class_empty(n, s, t, k):
    """One-directional but the important direction: if the criterion says
    EMPTY, the solver must agree. (The converse is false and not claimed -- a
    class can be empty for reasons this criterion does not see.)"""
    empty, why = class_is_empty(cyclic(n), n, s, t, k)
    status = _witness_exists(cyclic(n), n, s, t, k)
    if empty:
        assert status == "UNSAT", f"criterion said empty ({why}) but got {status}"


def test_off_diagonal_needs_a_conflict_not_just_a_forced_orbit():
    """With s != t a single forced orbit is survivable: it just pins that orbit
    to one colour. Only an orbit forced BOTH ways is fatal. Check the criterion
    encodes that rather than copying the diagonal rule."""
    n = 15
    empty, why = class_is_empty(cyclic(n), n, s=5, t=4, k=4)
    s_hits = forced_orbits(cyclic(n), n, 5, 4)
    assert s_hits, "Z_15 should force at least one orbit via a 5-set"
    if not empty:
        assert "no conflict" in why


def test_is_prime_helper():
    assert [m for m in range(2, 20) if _is_prime(m)] == [2, 3, 5, 7, 11, 13, 17, 19]
    assert not _is_prime(1) and not _is_prime(0)


def test_theorem_a_prime_extends_to_composite_s():
    """Theorem A' needs no primality: an element with an s-cycle has order
    divisible by s, so s not dividing |G| makes the obstruction impossible."""
    from obstruction_general import no_s_cycle_possible
    # R(4,4,4;3): s=4, k=s-1, so the 4-cycle argument WOULD apply -- but
    # 4 does not divide |Z_79 : C_78| = 6162, so no element has a 4-cycle.
    assert no_s_cycle_possible(6162, 4)
    assert no_s_cycle_possible(79, 4) and no_s_cycle_possible(237, 4)
    # and it correctly refuses to clear a group that could contain a 4-cycle
    assert not no_s_cycle_possible(12, 4)
    # consistency with Theorem A wherever both speak
    for order in (10, 20, 34, 35, 544):
        if theorem_a_applies(order, s=5, k=4, every_colour_forbids_s=True)[0]:
            assert not no_s_cycle_possible(order, 5)


def test_every_group_in_the_79_point_tower_survives_the_4_cycle_check():
    import json
    from pathlib import Path
    from obstruction_general import no_s_cycle_possible
    path = Path(__file__).with_name("groups79.json")
    if not path.exists():
        pytest.skip("groups79.json not built")
    for g in json.loads(path.read_text()):
        assert no_s_cycle_possible(g["order"], 4), g["name"]


def test_pair_regular_fixed_point_obstruction_matches_the_searches():
    """Theorem B must fire exactly where the solver found emptiness.

    Z_83 : C_41 and Z_79 : C_39 have |G| = C(p,2) exactly, and both were UNSAT
    the moment a fixed point was added. The reduced classes, where the
    witnesses actually live, must NOT be excluded -- an obstruction that
    over-fires would discard the search space that holds the results."""
    from obstruction_general import pair_regular_fixed_point_obstruction as obs

    for p, d in ((83, 41), (79, 39)):
        applies, why = obs(p, d)
        assert applies is True, why

    for p, d in ((79, 13), (73, 9), (83, 1)):
        applies, _ = obs(p, d)
        assert applies is False, (
            f"Z_{p} : C_{d} must not be excluded; witnesses live there"
        )


def test_pair_regular_obstruction_needs_a_big_enough_base():
    """The R(4,4;3) = 13 threshold is load-bearing, not decoration."""
    from obstruction_general import pair_regular_fixed_point_obstruction as obs
    from math import comb

    # p = 7 satisfies BOTH regularity conditions -- 7*3 = 21 = C(7,2) and
    # 7 = 3 (mod 4) -- so the only thing that can stop the argument is the
    # base being smaller than R(4,4;3) = 13. Chosen deliberately over p = 5,
    # which is 1 (mod 4) and would exit on the earlier check, leaving this
    # test passing for the wrong reason.
    assert 7 * 3 == comb(7, 2) and 7 % 4 == 3
    applies, why = obs(7, 3)
    assert applies is False and "R(4,4;3)" in why


def test_theorem_b_does_not_apply_when_minus_one_is_a_residue():
    """The counterexample class. |G| = C(p,2) alone is NOT enough.

    For p = 1 (mod 4) the map x -> -x + (a+b) lies in H and stabilises every
    pair, so there are two pair-orbits and the argument collapses. Worse, the
    CONCLUSION fails: at p = 13 and p = 37 the class is satisfiable. An earlier
    version of this function returned True for all of these."""
    from obstruction_general import pair_regular_fixed_point_obstruction as obs
    from math import comb

    for p in (13, 17, 29, 37, 41, 53, 61, 73, 89, 97, 101, 109, 113):
        d = (p - 1) // 2
        assert p * d == comb(p, 2), "precondition: order matches"
        applies, why = obs(p, d)
        assert applies is False, f"Z_{p} : C_{d} must not be excluded: {why}"
        assert "mod 4" in why


def test_pair_orbit_count_matches_the_criterion():
    """Count pair-orbits directly and check the criterion predicts them.

    Walks the two generators (x -> x+1 and x -> a*x) rather than every group
    element; applying all |H|*p maps to every pair made this test take two
    minutes on its own."""
    def pair_orbits(p):
        a = min(g for g in range(2, p)
                if len({pow(g, k, p) for k in range(1, p)}) == p - 1)
        mult = pow(a, 2, p)               # generates the quadratic residues
        seen, orbits = set(), 0
        for x in range(p):
            for y in range(x + 1, p):
                P = frozenset((x, y))
                if P in seen:
                    continue
                orbits += 1
                stack = [P]
                while stack:
                    Q = stack.pop()
                    if Q in seen:
                        continue
                    seen.add(Q)
                    for img in (frozenset(((v + 1) % p) for v in Q),
                                frozenset(((mult * v) % p) for v in Q)):
                        if img not in seen:
                            stack.append(img)
        return orbits

    for p in (13, 17, 29, 37):
        assert p % 4 == 1
        assert pair_orbits(p) == 2, f"p={p} should have two pair-orbits"
    for p in (79, 83):
        assert p % 4 == 3
        assert pair_orbits(p) == 1, f"p={p} should be regular on pairs"


def test_a_false_answer_is_not_a_claim_that_the_class_is_non_empty():
    """The boundary the criterion used to be advertised as not having.

    `class_is_empty` detects emptiness by forced orbits. When no orbit is
    forced it returns False -- and an earlier version of this module called
    that an "exact" test, which would license reading False as "a witness may
    exist here". This is the smallest counterexample: no orbit is forced, and
    the class is empty anyway, by exhaustive enumeration of every assignment.
    """
    from itertools import product

    from ansatz import build_cnf

    gens = cyclic(7)
    empty, why = class_is_empty(gens, 7, 3, 3, 2)
    assert empty is False, "the obstruction is not supposed to fire here"

    clauses, _, stats = build_cnf(gens, 7, 3, 3, 2)
    nv = stats["vars"]
    assert nv <= 12, "keep this exhaustive"
    models = 0
    for bits in product((0, 1), repeat=nv):
        a = {v: bits[v - 1] for v in range(1, nv + 1)}
        if all(any((lit > 0) == bool(a[abs(lit)]) for lit in c) for c in clauses):
            models += 1
    assert models == 0, (
        f"expected an empty class; found {models} invariant colouring(s)")


def test_theorem_a_says_nothing_off_the_diagonal():
    """The hypothesis the theorem used to omit, with its counterexample.

    R(3,4) on three vertices under C_3. Every hypothesis the old version
    checked holds -- s = 3 is prime, k = s - 1 = 2, and 3 divides |G| = 3 --
    and it returned "the class is empty". It is not: colour all three edges
    with the colour that forbids K_4. That colouring is C_3-invariant, has no
    monochromatic K_3 in the colour that forbids K_3, and cannot have a
    monochromatic K_4 because there are only three vertices.
    """
    from itertools import combinations

    n, s, t, k = 3, 3, 4, 2

    # Off the diagonal the theorem must decline.
    applies, why = theorem_a_applies(3, s=s, k=k, every_colour_forbids_s=False)
    assert applies is False, why

    # ... and here is the good colouring whose existence it would have denied.
    chi = {e: 1 for e in combinations(range(n), k)}      # 1 forbids K_t only
    mono_s_in_0 = [W for W in combinations(range(n), s)
                   if all(chi[f] == 0 for f in combinations(W, k))]
    assert not mono_s_in_0
    assert n < t, "no K_t can exist on n < t vertices"

    # On the diagonal the same group and parameters DO give an empty class,
    # so the guard is not simply refusing everything.
    assert theorem_a_applies(3, s=3, k=2, every_colour_forbids_s=True)[0] is True


def test_theorem_b_needs_its_threshold_hypothesis():
    """The condition `p >= R(4,...,4;3)` on `m-1` colours is load-bearing.

    The write-up once said the fixed-point extension is excluded "for any base
    colouring and any number of colours". This package's own n=79 witness
    refutes that: adjoin the fixed point and give every triple through it a
    FOURTH colour. The result is invariant under the same group and has no
    monochromatic K_4^(3) in any colour, so a good invariant colouring of the
    extension exists at m = 4 -- where the threshold fails, since 79 is below
    this package's own R(4,4,4;3) >= 84.
    """
    import json
    from itertools import combinations

    with open("witness_444_3_n79.json") as fh:
        doc = json.load(fh)
    n, chi = doc["n"], doc["chi"]
    idx = {t: i for i, t in enumerate(combinations(range(n), 3))}
    inf = n

    def colour(T):
        T = tuple(sorted(T))
        return 3 if inf in T else chi[idx[T]]

    mono = {c: 0 for c in range(4)}
    for W in combinations(range(n + 1), 4):
        cs = {colour(f) for f in combinations(W, 3)}
        if len(cs) == 1:
            mono[cs.pop()] += 1
    assert mono == {0: 0, 1: 0, 2: 0, 3: 0}, (
        f"expected a good 4-colouring on {n + 1} points; found {mono}")


# --- the threshold is R(4,4;3), so s = 4 is not a free parameter -----------

def test_theorem_b_refuses_a_clique_size_its_threshold_does_not_cover():
    """`s` was exposed as a parameter while the threshold stayed R(4,4;3) = 13.

    At (p, d) = (19, 9) every other condition holds -- |G| = C(19,2) = 171 and
    19 = 3 (mod 4) -- so the unguarded function returned True for s = 5. It is
    false there: `Z_19 : C_9 + 1 fixed` is satisfiable for R(5,5,5;3) on 20
    points, which the next test exhibits.
    """
    applies, why = pair_regular_fixed_point_obstruction(19, 9, colours=3, s=5)
    assert applies is False
    assert "R(5,5;3)" in why and "wrong number" in why


def test_the_class_theorem_b_would_have_excluded_is_satisfiable():
    """The object that makes the guard necessary, built and verified here."""
    from pysat.solvers import Cadical195

    import make_groups_affine
    import multicolour

    groups = make_groups_affine.build(20, 19, 10 ** 9)
    g = [x for x in groups if x["name"] == "Z_19 : C_9 + 1 fixed"]
    assert len(g) == 1
    cnf, orbit_of, _var, stats = multicolour.build_cnf(
        g[0]["generators"], 20, [5, 5, 5], 3)
    solver = Cadical195(bootstrap_with=cnf)
    sat = solver.solve()
    model = solver.get_model() if sat else None
    solver.delete()
    assert sat, "the class is satisfiable; that is the point"
    chi = multicolour.expand(model, orbit_of, 20, 3, 3)
    ok, detail = multicolour.verify(chi, 20, [5, 5, 5], 3)
    assert ok, detail


def test_theorem_b_still_fires_where_it_is_proved():
    """Baseline: the guard must not turn the theorem off where it holds."""
    for p, d in ((83, 41), (79, 39)):
        applies, _ = pair_regular_fixed_point_obstruction(p, d, colours=3, s=4)
        assert applies is True, (p, d)


@pytest.mark.parametrize("colours", [2, 4, 5])
def test_theorem_b_refuses_a_colour_count_its_threshold_does_not_cover(colours):
    applies, why = pair_regular_fixed_point_obstruction(
        83, 41, colours=colours, s=4)
    assert applies is False
    assert "3 colours" in why
