"""Gates for the group-as-data builder.  Every case here is tiny and fast.

The 35-point instances need far more wall time and memory than a test run
should take; what is checked here is that the *encoding* is right, on
parameters where the answer is known independently.
"""

from __future__ import annotations

from itertools import combinations
from math import comb

import pytest

from ansatz import build_cnf, expand, face_orbits, is_invariant, run
from obstruction import _orbit_count_of_subsets
from test_obstruction import _antipodal_witness_n6
from verify import verify_both


def _cyc(n):
    return [[(i + 1) % n for i in range(n)]]


def _trivial(n):
    return [list(range(n))]


@pytest.mark.parametrize("n", [6, 7, 8, 9, 10, 11])
def test_orbit_count_matches_burnside(n):
    """Independent check: BFS orbit count == the Burnside count for Z_n."""
    _, sizes = face_orbits(_cyc(n), n, k=4)
    assert len(sizes) == _orbit_count_of_subsets(n, 4)
    assert sum(sizes) == comb(n, 4)


def test_trivial_group_gives_one_variable_per_face():
    orbit_of, sizes = face_orbits(_trivial(7), 7, k=4)
    assert len(sizes) == comb(7, 4) and set(sizes) == {1}
    assert len(set(orbit_of.values())) == comb(7, 4)


def test_generators_must_be_permutations():
    with pytest.raises(ValueError, match="not a permutation"):
        face_orbits([[0, 1, 2, 3, 3]], 5, k=4)
    with pytest.raises(ValueError, match="not a permutation"):
        face_orbits([[0, 1, 2]], 5, k=4)


def test_z5_class_is_empty_by_construction():
    """obstruction.py's lemma, seen through this encoding: at n=5 the single
    5-set's five faces are ONE orbit, so the CNF holds both x and ~x."""
    clauses, _, stats = build_cnf(_cyc(5), n=5)
    assert stats["vars"] == 1
    assert stats["forced_mono_vars"] == [1]
    assert [1] in clauses and [-1] in clauses


def test_z5_is_unsat_and_reported_as_a_class_null():
    rec = run("Z_5", _cyc(5), n=5, cap_s=30, verbose=False)
    assert rec["status"] == "UNSAT" and rec["chi"] is None


def test_z6_finds_a_verified_witness():
    """Positive control end to end: Z_6 at (6,5,5,4) has a witness, so this
    exercises SAT -> expand -> invariance -> full-colouring verification."""
    rec = run("Z_6", _cyc(6), n=6, cap_s=30, verbose=False)
    assert rec["status"] == "SAT"
    assert rec["vars"] == _orbit_count_of_subsets(6, 4) == 3
    assert len(rec["chi"]) == comb(6, 4)
    assert verify_both(6, 5, 5, 4, rec["chi"]) is True


def test_the_known_witness_is_in_the_class_the_encoding_searches():
    """Guard the guard: if the antipodal witness were NOT Z_6-invariant, the
    test above could pass on a different object and prove nothing about the
    encoding's coverage."""
    chi = _antipodal_witness_n6()
    assert verify_both(6, 5, 5, 4, chi) is True
    assert is_invariant(chi, _cyc(6), 6, k=4)


def test_clause_dedup_is_deterministic_at_n7():
    """NOTE: this is weaker than its old name claimed.

    It was called `test_clause_dedup_is_lossless_at_n7`, but it rebuilds the
    very same frozenset-of-orbits expression that `build_cnf` uses and compares
    the two. That proves the computation is deterministic, not that dedup on S
    preserves the constraint -- if S did NOT determine the constraint, both
    sides would agree and this would still pass.

    The property that actually matters is checked two-sidedly in
    `test_known_answer.py::test_dedup_preserves_the_constraint_two_sidedly`.
    This one is kept only as a cheap determinism check."""
    n, gens = 7, _cyc(7)
    orbit_of, _ = face_orbits(gens, n, k=4)
    naive = set()
    for W in combinations(range(n), 5):
        S = frozenset(orbit_of[f] + 1 for f in combinations(W, 4))
        naive.add(tuple(sorted(S)))
        naive.add(tuple(sorted(-v for v in S)))
    clauses, _, _ = build_cnf(gens, n=n)
    assert {tuple(c) for c in clauses} == naive


def test_collapse_is_real_and_reported():
    """The whole speed argument: a bigger group means fewer distinct clauses."""
    _, _, small = build_cnf(_trivial(9), n=9)
    _, _, big = build_cnf(_cyc(9), n=9)
    assert big["vars"] < small["vars"]
    assert big["distinct_pos"] < small["distinct_pos"]
    assert small["collapse"] == pytest.approx(1.0, abs=0.05)


def test_expand_ignores_unassigned_orbits_safely():
    orbit_of, sizes = face_orbits(_cyc(6), 6, k=4)
    chi = expand([1, -2, 3], orbit_of, 6, k=4)
    assert len(chi) == comb(6, 4) and set(chi) <= {0, 1}
    assert is_invariant(chi, _cyc(6), 6, k=4)


# --------------------------------------------------------------------------
# The n=34 tower, and the cross-checks that make it trustworthy
# --------------------------------------------------------------------------


def _groups34():
    import json
    from pathlib import Path
    with Path(__file__).with_name("groups34.json").open() as f:
        return json.load(f)


def test_groups34_restrict_the_35_point_groups_without_losing_order():
    """Each 34-point group is a 35-point group with one FIXED point deleted, so
    the restriction is injective and the order must be unchanged."""
    from grouporder import group_order
    for g in _groups34():
        assert g["order"] == g["order_in_35"], g["name"]
        assert group_order(g["generators"], 34) == g["order"], g["name"]
        assert g["order"] % 5 != 0, g["name"]


def test_groups34_orbit_counts_agree_with_the_older_ladder_code():
    """Two numbers here were computed long before ansatz.py existed, by
    different code: the plain n=34 cyclic ansatz has 1368 orbit variables, and
    Z_33 with one added point has 1406. If the generic orbit BFS reproduces
    both, it agrees with the hand-checked ladder at two independent points."""
    by_name = {g["from35"]: g for g in _groups34()}
    counts = {n: face_orbits(g["generators"], 34, k=4)[1]
              for n, g in by_name.items() if n in ("C_34", "C_33")}
    assert len(counts["C_34"]) == 1368
    assert len(counts["C_33"]) == 1406

    from obstruction import extension_variables
    assert sum(extension_variables(33, 1).values()) == 1406


# --------------------------------------------------------------------------
# The translation fast path
# --------------------------------------------------------------------------


@pytest.mark.parametrize("n,k,size", [(11, 3, 4), (13, 3, 4), (11, 3, 5),
                                      (9, 2, 4), (13, 2, 5), (12, 3, 4)])
def test_fast_path_gives_identical_clause_sets(n, k, size):
    """The shortcut walks C(n-1,size-1) subsets instead of C(n,size). It is
    sound only because every subset translates to one containing 0, meeting the
    same orbits. If that reasoning were wrong the fast path would drop clauses
    and silently make instances easier -- so require exact equality, not just
    equal counts."""
    from ansatz import distinct_orbit_sets
    from grouporder import has_all_translations
    gens = [[(i + 1) % n for i in range(n)]]
    assert has_all_translations(gens, n)
    orbit_of, _ = face_orbits(gens, n, k)
    slow = distinct_orbit_sets(orbit_of, n, size, k, translations=False)
    fast = distinct_orbit_sets(orbit_of, n, size, k, translations=True)
    assert slow == fast


def test_fast_path_is_refused_for_a_group_without_translations():
    """Hol(Z_34) on 35 points fixes a point, so it does NOT contain x -> x+1 on
    all 35 and must take the slow path. This is the group that produced the
    R(5,5;4) >= 36 witness, so a wrong answer here would corrupt the headline
    result."""
    import json
    from pathlib import Path
    from grouporder import has_all_translations
    with Path(__file__).with_name("groups.json").open() as f:
        g = next(x for x in json.load(f) if x["name"] == "Hol(Z_34)")
    assert not has_all_translations(g["generators"], 35)
    _, _, stats = build_cnf(g["generators"], n=35, s=5, t=5, k=4)
    assert stats["translation_fast_path"] is False
    assert stats["vars"] == 107 and stats["clauses"] == 1230


def test_off_diagonal_unit_clause_is_not_called_a_contradiction():
    """The defect this test exists for: `forced_mono_vars` is positive units
    only. On the diagonal a unit is genuinely forced both ways; off it, the two
    clause families differ and a positive unit proves nothing. Reporting the
    off-diagonal case as "empty by construction" invented an obstruction that
    was not there -- and a whole claim in CELLS.md was built on it.

    Deliberately a tiny instance: the n=63 case that exposed this takes minutes
    to build, which is not something a unit test should cost."""
    gens = [[(i + 1) % 9 for i in range(9)], [(2 * i) % 9 for i in range(9)]]
    _, _, st = build_cnf(gens, 9, 4, 6, 3)
    assert st["forced_mono_vars"], "expected positive units in this class"
    assert st["contradictory_vars"] == [], (
        "off-diagonal (s=4, t=6): a positive unit is not a contradiction"
    )


def test_diagonal_unit_clause_is_a_real_contradiction():
    """On the diagonal the two families coincide, so every unit really is
    forced both ways -- the case the message was originally written for."""
    gens = [[(i + 1) % 9 for i in range(9)], [(2 * i) % 9 for i in range(9)]]
    _, _, st = build_cnf(gens, 9, 4, 4, 3)
    assert st["contradictory_vars"] == st["forced_mono_vars"]
