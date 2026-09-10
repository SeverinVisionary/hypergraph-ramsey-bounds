"""Gates for the Schreier-Sims order computation.

The point of grouporder.py is to replace 45 asserted group orders with 45
computed ones, so it has to be right about groups whose orders are known
independently before it is trusted about the ones that are not.
"""

from __future__ import annotations

import json
from math import factorial
from pathlib import Path

import pytest

from grouporder import audit, group_order, stabiliser_chain


def _sym(n):
    """S_n from a transposition and an n-cycle."""
    return [[1, 0] + list(range(2, n)), [(i + 1) % n for i in range(n)]]


@pytest.mark.parametrize("n", [3, 4, 5, 6, 7, 8, 9])
def test_symmetric_group(n):
    assert group_order(_sym(n), n) == factorial(n)


@pytest.mark.parametrize("n", [5, 6, 7])
def test_alternating_group(n):
    """A_n from the 3-cycles (0 1 2), (0 1 3), ..., (0 1 n-1)."""
    gens = []
    for k in range(2, n):
        p = list(range(n))
        p[0], p[1], p[k] = 1, k, 0
        gens.append(p)
    assert group_order(gens, n) == factorial(n) // 2


@pytest.mark.parametrize("n", [7, 31, 33, 35])
def test_cyclic_group(n):
    assert group_order([[(i + 1) % n for i in range(n)]], n) == n


def test_trivial_group_has_order_one_and_an_empty_chain():
    assert group_order([list(range(35))], 35) == 1
    base, trans = stabiliser_chain([list(range(35))], 35)
    assert base == [] and trans == []


def test_a_group_that_is_not_the_obvious_one():
    """<(0 1 2), (1 2 3)> is A_4, not A_5 -- a case an eyeball gets wrong."""
    assert group_order([[1, 2, 0, 3, 4], [0, 2, 3, 1, 4]], 5) == 12


@pytest.mark.parametrize("mult,expected", [(2, 21), (3, 42), (6, 14)])
def test_affine_groups_mod_7(mult, expected):
    """<x -> x+1, x -> m*x> mod 7 has order 7 * ord(m) in Z_7^*."""
    gens = [[(i + 1) % 7 for i in range(7)], [(mult * i) % 7 for i in range(7)]]
    assert group_order(gens, 7) == expected


def test_rejects_a_non_permutation():
    with pytest.raises(ValueError, match="not a permutation"):
        group_order([[0, 1, 2, 2, 4]], 5)


def test_every_claimed_order_in_groups_json_is_correct():
    """The reason this file exists: the 45 orders were asserted from abstract
    structure, not measured from the stored permutations, and two of them are
    around 10^15 and cannot be checked by enumeration.

    The 5'-check is the load-bearing one. obstruction.py shows that if 5
    divides |G| then no G-invariant colouring can be a witness, so a search
    over that class is doomed and its UNSAT carries no information.
    """
    path = Path(__file__).with_name("groups.json")
    with path.open() as f:
        groups = json.load(f)
    rows = audit(groups, n=35)
    assert len(rows) == 45
    mismatched = [(r["name"], r["claimed_order"], r["computed_order"])
                  for r in rows if not r["order_matches"]]
    assert mismatched == [], mismatched
    doomed = [r["name"] for r in rows if not r["is_5prime"]]
    assert doomed == [], doomed
