"""Negative controls for the resume cache.

`ansatz.py` and `multicolour.py` append to a results file and skip work already
recorded there. That skip was originally keyed on the group's NAME alone, so a
file written at one (n, s, t, k) would satisfy a run at another, and the stored
status would be printed as this run's result. Stamping the parameters fixed
half of it and left the other half: a name is a label a human chose, and the
same label can be attached to a different generator list.

Every branch of the guard is driven to a refusal below, against a baseline that
must reuse -- otherwise a guard that rejects everything would pass the suite.
"""

from __future__ import annotations

import pytest

import ansatz

PROBLEM = {"k": 3, "n": 88, "s": 5, "t": 5}
GENS_A = [[1, 2, 0]]
GENS_B = [[2, 0, 1]]


def _group(name, gens):
    return {"name": name, "generators": gens}


def _row(name, gens, status="UNSAT", problem=None):
    return {"name": name, "status": status,
            "problem": PROBLEM if problem is None else problem,
            "gens_sha": ansatz._gens_fingerprint(gens)}


def _key(name, gens):
    return (name, ansatz._gens_fingerprint(gens))


def test_the_baseline_is_reused():
    rows = [_row("G", GENS_A)]
    done = ansatz._resume(rows, PROBLEM, [_group("G", GENS_A)], "f.json")
    assert done == {_key("G", GENS_A)}
    assert len(rows) == 1


def test_the_same_name_with_different_generators_is_not_reused():
    """The half the parameter stamp did not cover."""
    rows = [_row("G", GENS_A)]
    done = ansatz._resume(rows, PROBLEM, [_group("G", GENS_B)], "f.json")
    assert done == set()
    assert rows == [], "the stale row must not survive into the summary"


def test_a_row_for_a_different_problem_refuses_the_whole_file():
    rows = [_row("G", GENS_A, problem={"k": 3, "n": 63, "s": 4, "t": 6})]
    with pytest.raises(SystemExit):
        ansatz._resume(rows, PROBLEM, [_group("G", GENS_A)], "f.json")


def test_an_unstamped_legacy_row_is_dropped_not_trusted():
    rows = [{"name": "G", "status": "UNSAT"}]
    done = ansatz._resume(rows, PROBLEM, [_group("G", GENS_A)], "f.json")
    assert done == set()
    assert rows == []


def test_a_legacy_sat_cannot_be_reported_as_this_run_s_witness():
    """The concrete fail-open: an unstamped SAT left in the results list is
    picked up by the end-of-run summary and printed as a witness."""
    rows = [{"name": "G", "status": "SAT"}, _row("H", GENS_A, status="UNSAT")]
    ansatz._resume(rows, PROBLEM, [_group("G", GENS_A), _group("H", GENS_A)],
                   "f.json")
    assert [r["name"] for r in rows] == ["H"]
    assert not [r for r in rows if r.get("status") == "SAT"]


def test_the_fingerprint_distinguishes_generator_lists():
    assert ansatz._gens_fingerprint(GENS_A) != ansatz._gens_fingerprint(GENS_B)
    assert ansatz._gens_fingerprint(GENS_A) == ansatz._gens_fingerprint(
        [list(g) for g in GENS_A])


def test_two_groups_with_the_same_name_are_refused():
    """A cached row for the SECOND of two same-named groups used to mark the
    FIRST -- never run -- as already decided, because completion was keyed on
    the name alone."""
    groups = [_group("G", GENS_A), _group("G", GENS_B)]
    with pytest.raises(SystemExit):
        ansatz._resume([], PROBLEM, groups, "f.json")


def test_completion_is_keyed_by_name_and_generators():
    rows = [_row("G", GENS_A)]
    done = ansatz._resume(rows, PROBLEM, [_group("G", GENS_A)], "f.json")
    assert done == {("G", ansatz._gens_fingerprint(GENS_A))}
    assert "G" not in done, "a bare name must never be a completion key"
