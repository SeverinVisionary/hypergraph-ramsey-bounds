"""Negative controls for the cross-check's coverage gate.

`crosscheck_n63.py` re-decides the five deposited n=63 UNSAT classes with two
solvers the pipeline does not use, and `reproduce.sh` labels that step
"Glucose3 and Minisat22 on all five". A gate that checks whatever list it is
handed, and exits 0 whenever every supplied row comes back UNSAT, makes that
label unenforceable: deleting a class leaves four UNSAT results and a passing
gate under a label that says five. `--expect-certified` and `--compare` are
what tie the label to the classes. The tests below drive every branch of the
gate to a refusal, against a baseline that passes.
"""

from __future__ import annotations

import json

import pytest

from crosscheck_n63 import coverage_problems

DEPOSITED = "certs_46_3_n63.json"


def _items():
    """(name, gens_sha, problem) for every deposited class.

    The problem is part of the identity: the group alone is not the decision.
    Without it, a row certifying one question satisfies a claim about another
    while the names and fingerprints match.
    """
    import ansatz
    with open(DEPOSITED) as fh:
        rows = json.load(fh)
    for r in rows:
        assert r.get("gens_sha"), f"{r['name']}: deposited without a fingerprint"
        assert r.get("problem"), f"{r['name']}: deposited without a problem key"
    return [(r["name"], r["gens_sha"], ansatz.row_problem_identity(r))
            for r in rows]


def test_the_baseline_passes():
    """Without this, a gate that refuses everything would pass the suite."""
    assert coverage_problems(_items(), 5, DEPOSITED) == []


def test_a_dropped_class_is_caught():
    assert coverage_problems(_items()[:-1], 5, DEPOSITED)


def test_an_extra_class_is_caught():
    assert coverage_problems(
        _items() + [("Z_63 : <9,9> order 1", "0" * 16, _items()[0][2])],
        5, DEPOSITED)


def test_a_substituted_class_is_caught():
    """Right count, wrong identities -- what a count-only check would miss."""
    swapped = _items()[:-1] + [("Z_63 : <9,9> order 1", "0" * 16,
                               _items()[0][2])]
    assert len(swapped) == 5
    assert coverage_problems(swapped, 5, DEPOSITED)


def test_swapped_generators_under_unchanged_names_are_caught():
    """Every name still matches and the count is still five; one class now
    carries another's generators, so one instance would be checked twice."""
    items = _items()
    swapped = items[:-1] + [(items[-1][0], items[0][1], items[-1][2])]
    assert [n for n, _, _ in swapped] == [n for n, _, _ in items]
    assert coverage_problems(swapped, 5, DEPOSITED)


def test_a_deposited_row_without_a_fingerprint_is_caught(tmp_path):
    dep = tmp_path / "certs.json"
    with open(DEPOSITED) as fh:
        rows = json.load(fh)
    dep.write_text(json.dumps(
        [{k: v for k, v in r.items() if k != "gens_sha"} for r in rows]))
    assert coverage_problems(_items(), 5, str(dep))


@pytest.mark.parametrize("expect", [4, 6])
def test_the_expected_count_is_enforced_both_ways(expect):
    assert coverage_problems(_items(), expect, DEPOSITED)


def test_identity_is_checked_even_with_no_expected_count():
    assert coverage_problems(_items()[:-1], None, DEPOSITED)


def test_a_deposited_row_that_is_not_a_certified_unsat_is_caught(tmp_path):
    """The closing line claims these are the classes the deposit records as
    certified UNSAT. Identity alone does not check that."""
    dep = tmp_path / "certs.json"
    with open(DEPOSITED) as fh:
        rows = json.load(fh)
    rows[0]["status"] = "SAT"
    rows[0]["checked"] = False
    dep.write_text(json.dumps(rows))
    problems = coverage_problems(_items(), 5, str(dep))
    assert any("certified UNSAT" in p for p in problems), problems


def test_an_uncertified_unsat_row_is_caught(tmp_path):
    dep = tmp_path / "certs.json"
    with open(DEPOSITED) as fh:
        rows = json.load(fh)
    rows[2]["checked"] = False
    dep.write_text(json.dumps(rows))
    assert coverage_problems(_items(), 5, str(dep))


def test_a_reference_about_another_problem_does_not_satisfy_this_one(tmp_path):
    """A reference about another problem must not satisfy this gate.

    Binding the group without the problem let the same mismatch through here
    that certify_nulls.gate rejects. The
    discriminator is real: the cyclic group on seven points has no good (3,3)
    assignment and six good (4,4) ones, so a reference certifying one cannot
    stand in for a decision about the other.
    """
    import ansatz
    dep = tmp_path / "certs.json"
    with open(DEPOSITED) as fh:
        rows = json.load(fh)
    for r in rows:                       # same groups, a different question
        r["problem"] = {"n": 7, "s": 4, "t": 4, "k": 2, "sizes": None}
    dep.write_text(json.dumps(rows))
    problems = coverage_problems(_items(), 5, str(dep))
    assert problems, "a reference about another problem satisfied this gate"


def test_the_identity_still_matches_when_the_problem_agrees():
    """Negative control: binding the problem must not reject a genuine match."""
    assert coverage_problems(_items(), 5, DEPOSITED) == []
