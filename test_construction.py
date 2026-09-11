"""Tests for `construction`.

The construction is the paper's object, so what must be pinned is that the
27-number table really determines the colouring -- not that some code runs.
"""

import json

import construction


def _witness_index(n):
    idx, c = {}, 0
    for x in range(n):
        for y in range(x + 1, n):
            for z in range(y + 1, n):
                idx[(x, y, z)] = c
                c += 1
    return idx


def test_table_has_27_orbits_nine_per_colour():
    from collections import Counter
    assert len(construction.COLOURS) == 27
    assert dict(Counter(construction.COLOURS.values())) == {0: 9, 1: 9, 2: 9}


def test_rebuild_covers_every_triple_exactly_once():
    chi = construction.rebuild()
    p = construction.P
    assert len(chi) == p * (p - 1) * (p - 2) // 6


def test_rebuild_reproduces_the_sat_witness_exactly():
    """The link that makes the table the source of truth rather than a summary
    of it: the object defined by 27 numbers IS the object the solver found."""
    chi = construction.rebuild()
    w = json.load(open("witness_444_3_n83.json"))
    idx = _witness_index(w["n"])
    assert all(chi[t] == w["chi"][i] for t, i in idx.items())


def test_the_theorem_holds():
    bad, total = construction.verify()
    assert total == 1837620
    assert bad == {0: 0, 1: 0, 2: 0}


def test_perturbing_one_orbit_breaks_it():
    """Changing the selected orbit's colour produces an invalid colouring.

    This is a negative control for the verifier. It does not assert that every
    orbit is indispensable or that sensitivity to every recolouring is required
    for a valid construction.
    """
    broken = dict(construction.COLOURS)
    broken[2] = (broken[2] + 1) % 3
    chi = construction.rebuild(colours=broken)
    bad, _ = construction.verify(chi)
    assert sum(bad.values()) > 0


def test_colour_classes_are_exactly_equal():
    """This particular colouring is balanced -- but the balance is NOT forced.

    Each triple orbit has size 3403, so every invariant color class has size
    divisible by 3403; this does not force the color classes to have equal sizes.
    Enumerating the class gives 36 invariant good
    colourings, 12 balanced and 24 not. So this test pins a property of the
    published table, not a theorem about the class."""
    from collections import Counter
    chi = construction.rebuild()
    assert set(Counter(chi.values()).values()) == {30627}
