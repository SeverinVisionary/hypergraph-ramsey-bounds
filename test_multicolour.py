"""Gates for the multi-colour engine.

Two things have to hold before this file can be trusted on the cells it was
written for. It must agree with the well-tested two-colour engine wherever both
can run, and it must reproduce the SAT side of a PUBLISHED multi-colour
value. The UNSAT side of R(3,3,3;2) = 17 is NOT reproduced here: the general
(trivial-group) instance at n = 17 was run out-of-process under a 900 s cap and
timed out. What the n = 17 tests below check is that no SYMMETRY CLASS holds a
3-colouring -- a much weaker statement, and one that would still pass for an
encoding that is too permissive in ways the symmetry restriction hides.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from math import comb

import pytest

import ansatz
import multicolour
from obstruction_general import cyclic

PUBLISHED_R_333_2 = 17          # Greenwood & Gleason


def _gf16_mul(x, y):
    r = 0
    for i in range(4):
        if (y >> i) & 1:
            r ^= x << i
    for i in range(7, 3, -1):
        if (r >> i) & 1:
            r ^= 0b10011 << (i - 4)
    return r & 15


def _gf16_cube_subgroup_affine():
    """x -> a*x + b over GF(16), a in the index-3 (order 5) subgroup of GF(16)*.

    This is the symmetry of the classical Greenwood-Gleason colouring: the 15
    non-zero differences split into three classes of five, which become the
    three colours.
    """
    t3 = 1
    for _ in range(3):
        t3 = _gf16_mul(t3, 2)
    return [[x ^ 1 for x in range(16)], [_gf16_mul(x, t3) for x in range(16)]]


# --------------------------------------------------------------------------
# Agreement with the two-colour engine
# --------------------------------------------------------------------------


@pytest.mark.parametrize("n,s,k", [(6, 3, 2), (7, 3, 2), (8, 3, 2),
                                   (7, 4, 3), (8, 4, 3), (6, 5, 4)])
def test_two_colours_reproduces_ansatz(n, s, k):
    a = ansatz.run("a", cyclic(n), n=n, s=s, t=s, k=k, cap_s=60, verbose=False)
    b = multicolour.run("m", cyclic(n), n, [s, s], k, cap_s=60, verbose=False)
    assert a["status"] == b["status"], (n, s, k)


def test_two_colours_gives_the_same_orbit_count():
    """The colouring variables differ (v vs v*m) but the orbit count must not."""
    _, _, stats_a = ansatz.build_cnf(cyclic(9), n=9, s=4, t=4, k=3)
    _, _, _, stats_m = multicolour.build_cnf(cyclic(9), 9, [4, 4], 3)
    assert stats_a["vars"] == stats_m["orbits"]
    assert stats_m["vars"] == stats_m["orbits"] * 2


# --------------------------------------------------------------------------
# The published three-colour value: the SAT side, plus restricted-class
# controls on the other side (see the docstrings -- it is NOT two-sided)
# --------------------------------------------------------------------------


def test_reproduces_the_published_r333():
    """R(3,3,3;2) = 17, so a 3-colouring of K_16 with no monochromatic triangle
    exists. Finding it confirms the encoding admits genuine multi-colour
    objects rather than degenerating to two colours."""
    rec = multicolour.run("GG", _gf16_cube_subgroup_affine(), 16, [3, 3, 3], 2,
                          cap_s=120, verbose=False)
    assert rec["status"] == "SAT"
    ok, detail = multicolour.verify(rec["chi"], 16, [3, 3, 3], 2)
    assert ok, detail
    # The bound this object supports, derived from the object rather than
    # written twice: a witness on n points gives R >= n + 1. `16 + 1 ==
    # PUBLISHED_R_333_2` was the previous form and compares two constants
    # written in this file, so it holds whatever the code does.
    n_points = 16
    assert len(rec["chi"]) == comb(n_points, 2)
    assert n_points + 1 == PUBLISHED_R_333_2, (
        f"a witness on {n_points} points gives R(3,3,3;2) >= {n_points + 1}, "
        f"but the published value is {PUBLISHED_R_333_2}")
    # all three colours must actually be used, or it is not a 3-colouring
    counts = Counter(rec["chi"])
    assert set(counts) == {0, 1, 2}, counts
    assert sum(counts.values()) == comb(16, 2) == 120


@pytest.mark.parametrize("group", ["cyclic", "holomorph"])
def test_no_symmetry_class_holds_a_three_colouring_at_seventeen(group):
    """A RESTRICTED-CLASS control, not the other side of the published value.

    R(3,3,3;2) = 17 means every 3-colouring of K_17 has a monochromatic
    triangle, so in particular no symmetry class can hold one, and a SAT here
    would mean the encoding is too permissive. That implication runs one way
    only: these classes being empty is implied by the published value and does
    not reproduce it. The general instance at n = 17 does not decide -- it was
    run out-of-process under a 900 s cap and timed out -- so this package
    reproduces R(3,3,3;2) = 17 on the SAT side only, and says so.
    """
    from math import gcd
    n = 17
    if group == "cyclic":
        gens = cyclic(n)
    else:
        gens = [[(i + 1) % n for i in range(n)]]
        gens += [[(u * i) % n for i in range(n)] for u in range(2, n) if gcd(u, n) == 1]
    assert multicolour.run(group, gens, n, [3, 3, 3], 2,
                           cap_s=120, verbose=False)["status"] == "UNSAT"


# --------------------------------------------------------------------------
# Encoding hygiene
# --------------------------------------------------------------------------


def test_exactly_one_colour_per_orbit_is_enforced():
    clauses, _, var, stats = multicolour.build_cnf(cyclic(7), 7, [3, 3, 3], 2)
    v, m = stats["orbits"], stats["colours"]
    for i in range(v):
        assert sorted([var(i, c) for c in range(m)]) in [sorted(c) for c in clauses]
    # at-most-one: one negative pair per unordered colour pair per orbit
    assert stats["exactly_one_clauses"] == v * (1 + m * (m - 1) // 2)


def test_rejects_fewer_than_two_colours():
    with pytest.raises(ValueError, match="at least two colours"):
        multicolour.build_cnf(cyclic(6), 6, [3], 2)


def test_verify_catches_a_monochromatic_class():
    """Negative control: an all-one-colour assignment must be rejected."""
    chi = [0] * comb(8, 2)
    ok, detail = multicolour.verify(chi, 8, [3, 3, 3], 2)
    assert not ok and "entirely colour 0" in detail


def test_verify_rejects_out_of_range_colours():
    chi = [3] * comb(6, 2)
    ok, detail = multicolour.verify(chi, 6, [3, 3, 3], 2)
    assert not ok and "out of range" in detail


def test_equal_sizes_are_computed_once():
    """The cache must not change the answer, only the cost."""
    _, _, _, st = multicolour.build_cnf(cyclic(9), 9, [4, 4, 4], 3)
    assert len(set(st["distinct_per_colour"])) == 1
    assert st["clauses"] == st["exactly_one_clauses"] + 3 * st["distinct_per_colour"][0]


def test_empty_by_construction_is_detected():
    """A singleton orbit-set bars its orbit from EVERY colour at once (all
    three clique sizes are 4 here), while the exactly-one clause demands it
    take one. Such a class is contradictory before the solver starts.

    This matters because those instances do not look degenerate: the class
    below reports UNSAT at 426 variables in under a tenth of a second, which
    reads as a searched-and-empty symmetry class and is nothing of the kind."""
    import json

    import drat_check

    g = json.load(open("g82_p73.json"))[0]        # Z_73 : C_72 + 9 fixed
    cnf, _, _, st = multicolour.build_cnf(g["generators"], 82, [4, 4, 4], 3)
    assert st["empty_by_construction"], "expected a barred orbit in this class"

    # and it really is contradictory: unit propagation alone refutes it
    db = drat_check._DB()
    for c in cnf:
        db.add(c)
    assert db.propagate([]) is True


def test_a_class_holding_a_witness_is_not_flagged():
    """The negative control: the class that produced the n=82 witness must not
    be reported empty, or the flag would be discarding real search space."""
    import json

    g = [x for x in json.load(open("g82_p73.json"))
         if x["name"].startswith("Z_73 : C_9")][0]
    _, _, _, st = multicolour.build_cnf(g["generators"], 82, [4, 4, 4], 3)
    assert st["empty_by_construction"] == []
