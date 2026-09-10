"""Gates for the 5'-group obstruction and for the deadline machinery.

Every test here is sub-second and needs no SAT solver, so the whole file runs
on any host. The solver-bearing gates live in the cloud job spec.
"""

from __future__ import annotations

import os
import random
import time
from itertools import combinations
from math import comb

import pytest

from capped import CappedResult, run_in_child
from verify import verify_both
from extend import build_extension, expand
from obstruction import (
    _orbit_count_of_subsets,
    admissible,
    blocks_c7,
    close_group,
    cyclic_obstruction,
    cyclic_plus_fixed,
    extension_variables,
    forced_monochromatic,
    full_cyclic,
    has_five_cycle,
    link_orbit_count,
    orbits_of_faces,
)

# --------------------------------------------------------------------------
# The lemma
# --------------------------------------------------------------------------


@pytest.mark.parametrize("n", [5, 10, 15, 20, 25, 30, 35, 40])
def test_five_divides_n_forces_a_monochromatic_clique(n):
    """Corollary 1, at every multiple of 5 including the target n=35."""
    S, faces, n_orbits = cyclic_obstruction(n)
    assert len(faces) == 5
    assert n_orbits == 1, f"n={n}: faces of {S} fell into {n_orbits} orbits"
    assert S == [(i * (n // 5)) % n for i in range(5)]


@pytest.mark.parametrize("n", [31, 32, 33, 34, 36, 37])
def test_lemma_is_silent_when_five_does_not_divide_n(n):
    """A negative control on the lemma itself: it must NOT over-claim.

    n=34 is the case that matters. The unresolved 46-minute run there has no
    structural explanation, and a version of this lemma that "explained" it
    would be wrong.
    """
    assert cyclic_obstruction(n) is None


def test_every_invariant_colouring_has_a_mono_five_set_exhaustively_at_n5():
    """Exhaustive where exhaustive is cheap: n=5 has one orbit variable."""
    n = 5
    points, gens = full_cyclic(n)
    group = close_group(gens, points)
    rep_of, _ = orbits_of_faces(group, points, k=4)
    orbit_keys = sorted(set(rep_of.values()))
    assert len(orbit_keys) == _orbit_count_of_subsets(n, 4) == 1
    for mask in range(1 << len(orbit_keys)):
        colour = {key: (mask >> i) & 1 for i, key in enumerate(orbit_keys)}
        assert any(
            len({colour[rep_of[f]] for f in combinations(W, 4)}) == 1
            for W in combinations(range(n), 5)
        ), f"mask {mask} would be a Z_5-invariant witness, contradicting the lemma"


@pytest.mark.parametrize("n,seed_count", [(10, 200), (15, 200), (20, 100)])
def test_forced_sets_are_monochromatic_under_sampled_invariant_colourings(n, seed_count):
    """Randomised control at sizes where 2^orbits is out of reach.

    Exhaustion at n=10 would be 2^22 masks x C(10,5) checks -- about a billion
    operations, and an earlier draft of this test did exactly that. The lemma
    is structural, so sampling is the right shape of check: whatever colours a
    run picks, the forced sets must come out monochromatic.
    """
    rng = random.Random(20260905 + n)
    points, gens = full_cyclic(n)
    group = close_group(gens, points)
    rep_of, _ = orbits_of_faces(group, points, k=4)
    orbit_keys = sorted(set(rep_of.values()))
    assert len(orbit_keys) == _orbit_count_of_subsets(n, 4)

    forced = forced_monochromatic(group, points)
    assert forced, f"Z_{n} should force at least one 5-set"

    for _ in range(seed_count):
        colour = {key: rng.randint(0, 1) for key in orbit_keys}
        for W in forced:
            seen = {colour[rep_of[f]] for f in combinations(W, 4)}
            assert len(seen) == 1, (n, W, seen)


def test_order_test_agrees_with_cycle_structure_test():
    """`5 | |G|` and `some element has a 5-cycle` must coincide, as claimed."""
    cases = [full_cyclic(10), full_cyclic(20), full_cyclic(35), blocks_c7(),
             cyclic_plus_fixed(33, 2), cyclic_plus_fixed(31, 4)]
    for points, gens in cases:
        group = close_group(gens, points)
        by_order = not admissible(len(group))
        by_cycles = any(has_five_cycle(g) for g in group)
        assert by_order == by_cycles, (len(points), len(group))


@pytest.mark.parametrize("n", [20, 30, 35])
def test_negative_control_forbidden_groups_force_cliques(n):
    points, gens = full_cyclic(n)
    group = close_group(gens, points)
    assert not admissible(len(group))
    assert forced_monochromatic(group, points), f"Z_{n} forced nothing"


@pytest.mark.parametrize("factory,label", [
    (blocks_c7, "block-C7"),
    (lambda: cyclic_plus_fixed(33, 2), "Z33+2"),
    (lambda: cyclic_plus_fixed(32, 3), "Z32+3"),
    (lambda: cyclic_plus_fixed(31, 4), "Z31+4"),
])
def test_positive_control_admissible_groups_force_nothing(factory, label):
    """The other side of the gate: admissible ansaetze are not vacuous.

    A lemma that excluded everything would pass the negative controls above
    and still be useless. These four must survive.
    """
    points, gens = factory()
    group = close_group(gens, points)
    assert admissible(len(group)), label
    assert not any(has_five_cycle(g) for g in group), label
    assert forced_monochromatic(group, points) == [], label


def test_no_vertex_transitive_witness_on_35_points():
    """Corollary 2, by the counting argument rather than by enumeration."""
    for order in range(35, 35 * 40 + 1, 35):   # any transitive group order
        assert not admissible(order), order


# --------------------------------------------------------------------------
# Variable counts the search ladder is budgeted from
# --------------------------------------------------------------------------


def test_block_c7_orbit_count_is_exact():
    points, gens = blocks_c7()
    group = close_group(gens, points)
    _, sizes = orbits_of_faces(group, points, k=4)
    assert len(sizes) == comb(35, 4) // 7 == 7480
    assert set(sizes.values()) == {7}, "some orbit was short, so 52360/7 is wrong"


@pytest.mark.parametrize("base,expected", [(33, 166), (32, 155), (31, 145)])
def test_link_orbit_count(base, expected):
    """Adding one point contributes the link: 3-subsets of the base, up to Z_base."""
    assert link_orbit_count(base) == expected
    # and it really is C(base,3) split into orbits
    total = comb(base, 3)
    if base % 3:
        assert total == expected * base
    else:
        assert total == (expected - 1) * base + base // 3


@pytest.mark.parametrize("base,extra,total", [
    (33, 1, 1406), (33, 2, 1588), (32, 3, 1642), (31, 4, 1690), (34, 1, 1544),
])
def test_extension_variable_totals(base, extra, total):
    strata = extension_variables(base, extra)
    assert sum(strata.values()) == total
    # the core must match the plain cyclic count at the base
    points, gens = full_cyclic(base)
    group = close_group(gens, points)
    _, sizes = orbits_of_faces(group, points, k=4)
    assert strata[0] == len(sizes)


# --------------------------------------------------------------------------
# The deadline machinery -- the defect that cost a 46-minute run
# --------------------------------------------------------------------------


def _sleep_forever():
    while True:
        time.sleep(3600)


def _die_hard():
    os._exit(17)


def _ok():
    return {"fine": True}


def test_run_in_child_returns_a_result():
    res = run_in_child(_ok, {}, cap_s=30)
    assert isinstance(res, CappedResult)
    assert res.status == "OK" and res.value == {"fine": True}


def test_run_in_child_enforces_the_cap():
    """The advertised cap must actually stop a wedged child."""
    t0 = time.monotonic()
    res = run_in_child(_sleep_forever, {}, cap_s=1.0)
    elapsed = time.monotonic() - t0
    assert res.status == "TIMEOUT"
    assert elapsed < 20, f"cap of 1s took {elapsed:.1f}s to enforce"


def test_run_in_child_survives_a_child_that_dies_without_answering():
    """The exact hang: child exits before writing, parent used to block forever."""
    t0 = time.monotonic()
    res = run_in_child(_die_hard, {}, cap_s=30)
    elapsed = time.monotonic() - t0
    assert res.status == "ERROR"
    assert elapsed < 20, f"a dead child blocked the parent for {elapsed:.1f}s"
    assert "17" in res.detail or "exit" in res.detail.lower()


def test_timeout_and_error_are_distinguishable():
    """Abort on a broken tool, never on a negative answer."""
    assert run_in_child(_sleep_forever, {}, cap_s=1.0).status == "TIMEOUT"
    assert run_in_child(_die_hard, {}, cap_s=30).status == "ERROR"


# --------------------------------------------------------------------------
# The extension builder (extend.py) -- small parameters only, no solver
# --------------------------------------------------------------------------


def test_extension_refuses_a_base_divisible_by_five():
    """A Z_35 base is already dead; the builder must say so, not build it."""
    with pytest.raises(ValueError, match="divisible by 5"):
        build_extension(35, 0)


def test_extension_rejects_a_base_that_is_not_a_witness():
    """Pinning a base containing a monochromatic clique must fail loudly."""
    n, s, t, k = 7, 4, 4, 3
    all_red = [0] * comb(n, k)          # every face colour 0 -> all-0 cliques
    with pytest.raises(AssertionError, match="all-0 clique"):
        build_extension(n, 1, all_red, s=s, t=t, k=k)


def _antipodal_witness_n6():
    """A real Z_6-invariant witness at (6,5,5,4): blue iff the complementary
    pair is antipodal. Every 5-set then has exactly one blue face and four red,
    so neither colour completes a K5. Verified by verify_both below."""
    chi = []
    for f in combinations(range(6), 4):
        comp = [x for x in range(6) if x not in f]
        chi.append(1 if (comp[1] - comp[0]) % 6 == 3 else 0)
    return chi


def test_the_small_base_really_is_a_witness():
    """Guard the guard: if this base stops being a witness, the tests below
    would silently stop testing extension of a valid object."""
    assert verify_both(6, 5, 5, 4, _antipodal_witness_n6()) is True


def test_extension_free_variables_are_exactly_the_link():
    """With the base pinned, the free variables are exactly the link orbits.

    Z_6 is admissible (5 does not divide 6) and reaches 7 points, so this is a
    working miniature of the Z_33 + 2 -> 35 rung.
    """
    chi = _antipodal_witness_n6()
    _, var_of, free, fixed = build_extension(6, 1, chi, s=5, t=5, k=4)
    assert fixed == _orbit_count_of_subsets(6, 4) == 3
    assert free == _orbit_count_of_subsets(6, 3) == 4
    assert len(var_of) == free


def test_extension_expand_round_trips_the_pinned_base():
    """Whatever the solver says about the link, the base must come back intact."""
    chi = _antipodal_witness_n6()
    _, var_of, free, _ = build_extension(6, 1, chi, s=5, t=5, k=4)
    full = expand([i + 1 for i in range(free)], var_of, 6, 1, chi)
    assert len(full) == comb(7, 4)
    base_faces = list(combinations(range(6), 4))
    full_index = {f: i for i, f in enumerate(combinations(range(7), 4))}
    for i, f in enumerate(base_faces):
        assert full[full_index[f]] == chi[i], f


def test_extension_refuses_a_base_that_is_not_translation_invariant():
    """The guard the round-trip above cannot supply.

    `build_extension` pins one colour per translation orbit, read off the
    orbit's representative. Handed a base that is a valid witness but NOT
    Z_base_n-invariant, it would silently pin the projection instead -- and a
    later "no witness extends this base" would be about an object the caller
    never supplied. The fixture above is invariant by construction, so it
    cannot expose that.
    """
    chi = _antipodal_witness_n6()
    faces = list(combinations(range(6), 4))
    index = {f: i for i, f in enumerate(faces)}

    # Flip one face away from its orbit-mates. Z_6 acts by translation, so
    # {0,1,2,3} and {1,2,3,4} share an orbit; recolouring only the first makes
    # the vector non-invariant while leaving it a colouring of the same shape.
    broken = list(chi)
    broken[index[(0, 1, 2, 3)]] ^= 1
    orbit_mate = tuple(sorted((x + 1) % 6 for x in (0, 1, 2, 3)))
    assert broken[index[(0, 1, 2, 3)]] != broken[index[orbit_mate]]

    with pytest.raises(ValueError, match="not Z_6-invariant"):
        build_extension(6, 1, broken, s=5, t=5, k=4)


def test_the_invariant_base_is_still_accepted():
    """Baseline: the guard must not refuse every base."""
    chi = _antipodal_witness_n6()
    _, var_of, free, fixed = build_extension(6, 1, chi, s=5, t=5, k=4)
    assert free > 0 and fixed > 0
