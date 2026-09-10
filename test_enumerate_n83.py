"""Controls on the exhaustive enumeration behind the "36 colourings" claim.

An exhaustive count is a different kind of claim from a witness, and the search
that produces a witness cannot support one. `enumerate_n83.py` blocks each model
and re-solves until the formula is UNSAT; the tests below check that it counts
what it says it counts, on instances small enough to settle independently.
"""

from __future__ import annotations

import pytest

from obstruction_general import cyclic
from enumerate_n83 import enumerate_class


def test_it_counts_every_model_and_no_others():
    """A tiny diagonal instance, counted independently by brute force."""
    import multicolour
    from itertools import product

    gens, n, sizes, k = cyclic(5), 5, [3, 3], 2
    cnf, orbit_of, _, stats = multicolour.build_cnf(gens, n, sizes, k)
    nv = stats["vars"]
    assert nv <= 12, "keep this exhaustive"
    by_hand = 0
    for bits in product([False, True], repeat=nv):
        assign = {i + 1: bits[i] for i in range(nv)}
        if all(any(assign[abs(l)] == (l > 0) for l in c) for c in cnf):
            by_hand += 1
    count, splits, exhausted = enumerate_class(gens, n, sizes, k)
    assert exhausted
    assert by_hand > 0, "a baseline of zero models would prove nothing"
    assert count == by_hand
    assert sum(splits.values()) == count


def test_an_unreached_limit_is_reported_as_not_exhaustive():
    """The distinction the claim rests on: a count that stopped is not a count."""
    count, _splits, exhausted = enumerate_class(cyclic(5), 5, [3, 3], 2, limit=1)
    assert count == 1
    assert exhausted is False


def test_an_empty_class_enumerates_to_zero_and_is_still_exhaustive():
    """`R(3,3) = 6`, so a Z_7-invariant good 2-colouring of a 7-set cannot
    exist; zero models with the search exhausted is the right answer, and is
    not the same as a search that produced nothing because it stopped."""
    count, splits, exhausted = enumerate_class(cyclic(7), 7, [3, 3], 2)
    assert exhausted
    assert count == 0 and splits == {}


# --- the published claim is a distribution, not a total -------------------

def test_the_split_spec_round_trips():
    from enumerate_n83 import fmt_splits, parse_splits
    want = parse_splits("12:30627/30627/30627,24:27224/30627/34030")
    assert want == {(30627, 30627, 30627): 12, (27224, 30627, 34030): 24}
    assert parse_splits(fmt_splits(want)) == want


def test_a_split_spec_that_totals_correctly_but_distributes_wrongly_differs():
    """36 colourings with the wrong split is a different statement about the
    class, and a count-only gate passes on it."""
    from enumerate_n83 import parse_splits
    right = parse_splits("12:30627/30627/30627,24:27224/30627/34030")
    wrong = parse_splits("13:30627/30627/30627,23:27224/30627/34030")
    assert sum(right.values()) == sum(wrong.values()) == 36
    assert right != wrong


@pytest.mark.parametrize("spec", ["12", "12:", ":1/2/3",
                                  "1:1/2/3,2:3/2/1"])
def test_a_malformed_or_repeated_split_spec_is_refused(spec):
    from enumerate_n83 import parse_splits
    with pytest.raises(SystemExit):
        parse_splits(spec)


def test_the_deposited_class_hashes_to_what_reproduce_sh_pins():
    """`reproduce.sh` passes --expect-gens-sha; if the pinned value drifts from
    the shipped group the gate silently stops binding anything."""
    import json
    import os

    import ansatz

    with open("g83_p83.json") as fh:
        rows = [g for g in json.load(fh) if g["name"] == "Z_83 : C_41"]
    assert len(rows) == 1
    sha = ansatz.gens_fingerprint(rows[0]["generators"])
    assert len(sha) == 64, "a truncated digest is not the SHA-256 it claims"
    # The harness may sit at the top level or in a staging subdirectory;
    # both are the same file and this test must run against either.
    import deposit_paths
    path = deposit_paths.resolve("reproduce.sh")
    assert path, "reproduce.sh was not found"
    with open(path) as fh:
        assert sha in fh.read(), f"{path} does not pin {sha}"
