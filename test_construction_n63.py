"""Tests for `construction_n63` — the R(4,6;3) >= 64 construction.

Same obligations as `test_construction`: the table must BE the object, not a
summary of a solver artifact we cannot re-derive.
"""

import json

import construction_n63 as c63


def test_table_has_120_orbits():
    assert len(c63.TABLE) == 120


def test_subgroup_is_closed_and_of_order_six():
    H = set(c63.SUBGROUP)
    assert len(H) == 6
    assert all((u * v) % c63.N in H for u in H for v in H), "not a subgroup"


def test_rebuild_covers_every_triple():
    chi = c63.rebuild()
    n = c63.N
    assert len(chi) == n * (n - 1) * (n - 2) // 6


def test_rebuild_reproduces_the_sat_witness_exactly():
    chi = c63.rebuild()
    w = json.load(open("witness_46_3_n63.json"))
    n = w["n"]
    i = 0
    for x in range(n):
        for y in range(x + 1, n):
            for z in range(y + 1, n):
                assert chi[(x, y, z)] == w["chi"][i]
                i += 1


def test_the_theorem_holds():
    bad4, bad6 = c63.verify()
    assert (bad4, bad6) == (0, 0)


def test_perturbing_one_orbit_breaks_it():
    """Changing the selected orbit's colour produces an invalid colouring.

    This is a negative control for the verifier. It does not assert that every
    orbit is indispensable or that sensitivity to every recolouring is required
    for a valid construction.
    """
    broken = dict(c63.TABLE)
    k = next(iter(broken))
    broken[k] = 1 - broken[k]
    chi = c63.rebuild(table=broken)
    assert sum(c63.verify(chi)) > 0


def test_the_K6_branch_is_forced_to_reject_something():
    """The K4 scan and the K6 scan are two separate obligations.

    Every control here summed bad4 and bad6, and the orbit perturbation and
    the reversed-reading control both trip the K4 count -- so deleting the
    entire colour-1 K6 scan and returning bad6 = 0 left all seven tests
    passing and the hash-bound wrapper exiting 0. A branch no control forces
    to reject is a branch nothing checks.

    Six points, every triple colour 1: no colour-0 K4 can exist because no
    triple is colour 0, and the six points are a monochromatic K_6^(3) in
    colour 1. So this input isolates the second scan exactly.
    """
    chi = {}
    for a in range(6):
        for b in range(a + 1, 6):
            for c in range(b + 1, 6):
                chi[(a, b, c)] = 1
    bad4, bad6 = c63.verify(chi, 6)
    assert bad4 == 0, "the discriminator must not depend on the K4 scan"
    assert bad6 == 1, (
        "the colour-1 K6 scan did not reject a planted monochromatic K6; "
        "nothing in this suite forces that branch to say no")


def test_orbits_are_not_all_regular():
    """Check the orbit-size contrast with the 83-point construction.

    Here |G| = 378 and the orbit sizes are 378, 189, 126, 63 and 21.
    Short orbits arise from nontrivial setwise stabilisers in the full
    affine group, not necessarily from pure multipliers. This test checks
    orbit sizes; it does not assert that nonfreeness determines colour
    balance or that freeness forces equal colour-class sizes.
    """
    from collections import Counter
    chi = c63.rebuild()
    orbit_of = {}
    for rep in c63.TABLE:
        stack, seen = [rep], set()
        while stack:
            t = stack.pop()
            if t in seen:
                continue
            seen.add(t)
            for u in c63.SUBGROUP:
                stack.append(tuple(sorted((u * v) % c63.N for v in t)))
            stack.append(tuple(sorted((v + 1) % c63.N for v in t)))
        orbit_of[rep] = len(seen)
    sizes = set(orbit_of.values())
    assert sizes == {378, 189, 126, 63, 21}, sizes
    assert len(sizes) > 1, "action would be free; it is not"
