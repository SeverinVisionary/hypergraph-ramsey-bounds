"""Tests for `construction_n35` — the R(5,5;4) >= 36 construction."""

import json

import construction_n35 as c35


def test_table_has_107_orbits():
    assert len(c35.TABLE) == 107


def test_multiplier_generates_the_full_unit_group():
    """<3> must be all of Z_34^*, order phi(34) = 16 -- the claim in the
    docstring that fixes |G| = 544."""
    H = c35._subgroup()
    assert len(H) == 16
    from math import gcd
    assert H == {u for u in range(1, 34) if gcd(u, 34) == 1}


def test_rebuild_covers_every_four_set():
    assert len(c35.rebuild()) == 52360


def test_rebuild_reproduces_the_sat_witness_exactly():
    chi = c35.rebuild()
    w = json.load(open("witness_n35.json"))
    n = w["n"]
    i = 0
    for a in range(n):
        for b in range(a + 1, n):
            for c in range(b + 1, n):
                for d in range(c + 1, n):
                    assert chi[(a, b, c, d)] == w["chi"][i]
                    i += 1
    assert i == len(w["chi"])


def test_the_theorem_holds():
    bad, total = c35.verify()
    assert total == 324632
    assert bad == {0: 0, 1: 0}


def test_perturbing_one_orbit_breaks_it():
    broken = dict(c35.TABLE)
    k = next(iter(broken))
    broken[k] = 1 - broken[k]
    bad, _ = c35.verify(c35.rebuild(table=broken))
    assert sum(bad.values()) > 0


def test_action_is_not_free():
    """Orbit sizes 544, 272, 136 -- the same non-regularity as the n=63 object,
    and the reason its colour classes are not exactly equal. Only the 83-point
    construction is free."""
    H = c35._subgroup()
    sizes = set()
    for rep in c35.TABLE:
        seen, stack = set(), [tuple(rep)]
        while stack:
            t = stack.pop()
            if t in seen:
                continue
            seen.add(t)
            for u in H:
                stack.append(c35._act(t, u, 0))
            stack.append(c35._act(t, 1, 1))
        sizes.add(len(seen))
    assert sizes == {544, 272, 136}, sizes
