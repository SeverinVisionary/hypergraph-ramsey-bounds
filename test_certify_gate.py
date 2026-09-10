"""Negative controls for the certificate gate.

The deposit's central claim is that its UNSAT classes are machine-checked. The
program that establishes this is certify_nulls.py, and for a long time it
computed a pass count, printed it, and exited zero either way -- so a run in
which nothing certified was indistinguishable, to a caller, from one in which
everything did.

The lesson is not "add an exit status". It is that a check nobody has watched
fail is not known to be a check. Every branch of certify_nulls.gate is driven
to a non-empty result below, against a baseline that must come back empty.
"""

from __future__ import annotations

import json

import pytest

from certify_nulls import gate

# A well-formed run: four proof-replay certificates and one class decided by
# unit propagation, which is a real UNSAT proof with zero added lemmas.
# The problem every row below decides. A row that does not say WHICH question
# it settled cannot certify a null about any particular question, so the gate
# now requires it and a well-formed fixture has to carry it.
PROBLEM = {"k": 3, "n": 63, "s": 4, "sizes": None, "t": 6}

GOOD = [
    {"name": "Z_63 : <2,5> order 2268", "gens_sha": "aaaa000000000001",
     "status": "UNSAT", "checked": True,
     "steps": 0, "route": "unit propagation", "problem": PROBLEM},
    {"name": "Z_63 : <4,5> order 1134", "gens_sha": "aaaa000000000002",
     "status": "UNSAT", "checked": True,
     "steps": 13975, "route": "proof replay", "problem": PROBLEM},
    {"name": "Z_63 : <2,11> order 1134", "gens_sha": "aaaa000000000003",
     "status": "UNSAT", "checked": True,
     "steps": 30939, "route": "proof replay", "problem": PROBLEM},
]


def _rows(**overrides):
    rows = [dict(r) for r in GOOD]
    if overrides:
        rows[1].update(overrides)
    return rows


def test_the_baseline_passes():
    """Without this the suite below would pass on a gate that rejects everything."""
    assert gate(_rows()) == []


def test_an_unsat_class_that_did_not_certify_is_caught():
    assert gate(_rows(checked=False))


def test_a_timeout_masquerading_as_a_null_is_caught():
    assert gate(_rows(status="TIMEOUT", checked=False))


def test_a_missing_checked_field_is_caught():
    rows = _rows()
    del rows[1]["checked"]
    assert gate(rows)


def test_a_sat_class_is_not_required_to_certify():
    """SAT classes carry a witness object; they are not nulls."""
    assert gate(_rows(status="SAT", checked=False)) == []


def test_the_expected_count_is_enforced_both_ways():
    assert gate(_rows(), expect_certified=3) == []
    assert gate(_rows(), expect_certified=4)
    assert gate(_rows(), expect_certified=2)


@pytest.mark.parametrize("field,bad", [
    ("status", "SAT"),
    ("checked", False),
    ("route", "proof replay"),
])
def test_comparison_against_the_deposited_file_catches_each_field(
        tmp_path, field, bad):
    dep = tmp_path / "certs.json"
    dep.write_text(json.dumps(GOOD))
    rows = [dict(r) for r in GOOD]
    rows[0][field] = bad
    assert gate(rows, compare_path=str(dep))


def test_comparison_passes_on_an_unchanged_file(tmp_path):
    dep = tmp_path / "certs.json"
    dep.write_text(json.dumps(GOOD))
    assert gate([dict(r) for r in GOOD], compare_path=str(dep)) == []


def test_step_counts_are_deliberately_not_compared(tmp_path):
    """Proof length depends on the solver build; requiring it to match would
    fail for a reason that says nothing about the mathematics."""
    dep = tmp_path / "certs.json"
    dep.write_text(json.dumps(GOOD))
    rows = [dict(r) for r in GOOD]
    rows[1]["steps"] = 999999
    assert gate(rows, compare_path=str(dep)) == []


def test_a_class_dropped_from_the_run_is_caught(tmp_path):
    """The failure that motivated --compare: certifying fewer classes than the
    deposit claims, and reporting success because each one that ran passed."""
    dep = tmp_path / "certs.json"
    dep.write_text(json.dumps(GOOD))
    assert gate([dict(GOOD[0])], compare_path=str(dep))


def test_an_extra_class_not_in_the_deposit_is_caught(tmp_path):
    dep = tmp_path / "certs.json"
    dep.write_text(json.dumps(GOOD[:2]))
    assert gate([dict(r) for r in GOOD], compare_path=str(dep))


# --- the rows must name an instance, not just a label ----------------------
#
# `<4,5> order 1134` and `<2,11> order 1134` are two different groups of the
# same order at n=63. Nothing in a name stops one from being certified twice
# while the other is never touched, so the gate keys on (name, gens_sha).


def test_a_row_without_a_generator_fingerprint_is_caught():
    rows = _rows()
    del rows[1]["gens_sha"]
    assert gate(rows)


def test_a_deposited_row_without_a_fingerprint_is_caught(tmp_path):
    dep = tmp_path / "certs.json"
    stripped = [{k: v for k, v in r.items() if k != "gens_sha"} for r in GOOD]
    dep.write_text(json.dumps(stripped))
    assert gate([dict(r) for r in GOOD], compare_path=str(dep))


def test_swapped_generators_under_unchanged_names_are_caught(tmp_path):
    """The concrete trigger: keep all five names, give one class another's
    generators. Every name still matches and every status is still UNSAT."""
    dep = tmp_path / "certs.json"
    dep.write_text(json.dumps(GOOD))
    rows = [dict(r) for r in GOOD]
    rows[2]["gens_sha"] = rows[1]["gens_sha"]      # <2,11> now carries <4,5>'s
    problems = gate(rows, expect_certified=3, compare_path=str(dep))
    assert problems, "one instance certified twice, another never -- and the " \
                     "count and every name still line up"


def test_the_same_instance_certified_twice_is_caught(tmp_path):
    dep = tmp_path / "certs.json"
    dep.write_text(json.dumps(GOOD))
    rows = [dict(GOOD[0]), dict(GOOD[1]), dict(GOOD[1])]
    assert gate(rows, expect_certified=3, compare_path=str(dep))
