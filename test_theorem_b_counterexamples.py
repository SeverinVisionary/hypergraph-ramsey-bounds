"""Controls on the gate behind Theorem B's second hypothesis.

The claim is existential -- two satisfiable classes exist -- so the gate has
the shape that has repeatedly failed open in this package: nothing to check
means nothing fails. Every branch below is driven to a refusal against a
baseline that passes.
"""

from __future__ import annotations

import json
import os

import pytest

from theorem_b_counterexamples import CASES, hypotheses, problems_with

ROOT = os.path.dirname(os.path.abspath(__file__))


def _row(**over):
    r = {"p": 13, "n": 14, "name": "Z_13 : C_6 + 1 fixed", "order": 78,
         "abs_C_p_2": 78, "p_mod_4": 1, "satisfies_first_hypothesis": True,
         "satisfies_second_hypothesis": False, "vars": 24, "clauses": 1,
         "status": "SAT", "verified": True}
    r.update(over)
    return r


def _row37(**over):
    """A CONSISTENT p = 37 row.

    The baseline used to be `_row(p=37)`, which kept p = 13's n, name, order
    and C(p,2) -- a row describing no class at all. It was the suite's proof
    that the gate ACCEPTS a valid counterexample, and it was proving the gate
    accepts an internally contradictory one.
    """
    r = {"p": 37, "n": 38, "name": "Z_37 : C_18 + 1 fixed", "order": 666,
         "abs_C_p_2": 666, "p_mod_4": 1, "satisfies_first_hypothesis": True,
         "satisfies_second_hypothesis": False, "vars": 24, "clauses": 1,
         "status": "SAT", "verified": True}
    r.update(over)
    return r


def test_the_baseline_passes():
    assert problems_with([_row(), _row37()], expect=2) == []


def test_a_row_whose_arithmetic_does_not_describe_one_class_is_caught():
    """The old baseline, now as a negative control."""
    assert problems_with([_row(), _row(p=37)], expect=2)


def test_one_prime_counted_twice_is_not_two_counterexamples():
    assert problems_with([_row(), _row()], expect=2)


def test_no_rows_at_all_is_not_a_set_of_counterexamples():
    """The fail-open: every per-row check is vacuous on an empty list."""
    assert problems_with([])
    assert problems_with([], expect=2)


def test_a_dropped_case_is_caught():
    assert problems_with([_row()], expect=2)


def test_an_extra_case_is_caught():
    assert problems_with([_row(), _row(p=37), _row(p=41)], expect=2)


def test_an_unsat_class_is_not_a_counterexample():
    assert problems_with([_row(status="UNSAT")], expect=1)


def test_an_unverified_sat_is_not_a_counterexample():
    assert problems_with([_row(verified=False)], expect=1)


def test_a_class_missing_the_first_hypothesis_shows_nothing():
    """|G| != C(p,2): the class is outside the theorem's scope, so its being
    satisfiable says nothing about the hypothesis under test."""
    assert problems_with([_row(satisfies_first_hypothesis=False)], expect=1)


def test_a_class_satisfying_BOTH_hypotheses_would_refute_the_theorem():
    """p = 3 mod 4 and SAT is not a counterexample to the weakened form -- it
    would contradict the theorem itself, and must never be reported as
    supporting evidence."""
    problems = problems_with(
        [_row(p=79, p_mod_4=3, satisfies_second_hypothesis=True)], expect=1)
    assert any("REFUTE" in p for p in problems), problems


@pytest.mark.parametrize("p,first,second", [
    (13, True, False), (37, True, False), (79, True, True), (83, True, True),
])
def test_the_hypothesis_test_is_the_arithmetic_it_claims(p, first, second):
    from math import comb
    assert hypotheses(p, comb(p, 2)) == (first, second)
    assert hypotheses(p, comb(p, 2) + 1)[0] is False


def test_the_deposited_result_is_sound_on_its_own_terms():
    with open(os.path.join(ROOT, "theorem_b_counterexamples.json")) as fh:
        rows = json.load(fh)
    assert problems_with(rows, expect=len(CASES)) == []
    assert {r["p"] for r in rows} == {13, 37}
    assert all(r["status"] == "SAT" and r["verified"] for r in rows)


def test_the_write_ups_cite_the_primes_that_were_actually_run():
    """The previous version of this test was named for the write-ups and never
    opened one. Every prime the prose offers as a counterexample must be a
    prime the deposited run covers, and vice versa."""
    import re

    with open(os.path.join(ROOT, "theorem_b_counterexamples.json")) as fh:
        deposited = {r["p"] for r in json.load(fh)}

    # The README may sit at the top level or in a staging subdirectory. Both
    # layouts must work, and a write-up that is in NEITHER is a failure, not a
    # skip: an absent file would silently satisfy every check below. The
    # staging path is tried first so that the deposit's own README wins
    # wherever both exist.
    import deposit_paths
    for name, pick in (("THEOREMS.md", deposit_paths.resolve),
                       ("README.md", deposit_paths.resolve_scaffolded)):
        path = pick(name)
        assert path, f"{name} is not present; nothing was checked"
        rel = os.path.relpath(path, ROOT)
        seen = set()
        with open(path) as fh:
            text = re.sub(r"\s+", " ", fh.read())
        # Sentences that offer primes as the counterexample to the second
        # hypothesis. Both write-ups phrase it as "at `p = 13` and `p = 37`".
        for m in re.finditer(
                r"(?:satisfiable|counterexample|fails)[^.]{0,200}", text):
            span = m.group(0)
            cited = {int(x) for x in re.findall(r"`?p = (\d+)`?", span)}
            cited -= {p for p in cited if p % 4 == 3}   # towers, not examples
            if not cited:
                continue
            assert cited <= deposited, (
                f"{rel} offers p in {sorted(cited)} as a counterexample, but "
                f"the deposited run covers {sorted(deposited)}")
            seen |= cited

        # PER FILE, not on the union of both: accumulating across the write-ups
        # lets one of them drop the examples entirely while the other carries
        # the set. Each write-up that makes the claim must make it completely.
        assert seen == deposited, (
            f"{rel} cites {sorted(seen)} as Theorem B's counterexamples but "
            f"the deposited run covers {sorted(deposited)}")


def test_that_write_up_check_would_notice_an_uncited_prime():
    """Baseline: the scan above must be able to fail."""
    import re
    text = "the conclusion fails, with satisfiable classes at `p = 41`."
    span = re.search(r"(?:satisfiable|counterexample|fails)[^.]{0,200}",
                     text).group(0)
    cited = {int(x) for x in re.findall(r"`?p = (\d+)`?", span)}
    assert cited == {41}
    assert not cited <= {13, 37}
