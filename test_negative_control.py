"""Controls on the DRAT checker's own discriminating control.

`negative_control.py` is the evidence that the checker refuses something. Its
gate has to be able to fail, and it has to fail for the right reasons -- in
particular, a control that runs on a class certified by unit propagation with
zero proof steps is not evidence about proof replay, which is what the earlier
one did.
"""

from __future__ import annotations

import json
import os

from negative_control import problems_with

ROOT = os.path.dirname(os.path.abspath(__file__))


def _rows(full=None, weakened=None):
    full = full or {"clauses": 54785, "status": "UNSAT", "checked": True,
                    "route": "proof replay", "steps": 30939,
                    "replay_steps": 30939, "replay_sha": "0" * 64,
                    "replay_valid_on_full": True}
    weakened = weakened if weakened is not None else [
        {"clauses": 49292, "status": "UNSAT", "checked": True,
         "route": "proof replay", "steps": 27942,
         "replayed_original_proof": False},
        {"clauses": 38273, "status": "SAT", "checked": False,
         "route": None, "steps": 0, "replayed_original_proof": False},
    ]
    return [full] + weakened


def test_the_baseline_passes():
    assert problems_with(_rows()) == []


def test_no_rows_is_not_a_control():
    assert problems_with([])


def test_a_control_on_the_unit_propagation_class_is_refused():
    """The defect: the shipped control ran on the class whose route is unit
    propagation with zero steps, and was offered as evidence for the replay
    machinery."""
    problems = problems_with(_rows(
        full={"clauses": 14384, "status": "UNSAT", "checked": True,
              "route": "unit propagation", "steps": 0}))
    assert any("never replays a proof" in p for p in problems), problems


def test_a_run_where_nothing_turned_satisfiable_is_refused():
    """If no weakened instance is SAT, the checker was never asked to refuse."""
    problems = problems_with(_rows(weakened=[
        {"clauses": 49292, "status": "UNSAT", "checked": True,
         "route": "proof replay", "steps": 27942,
         "replayed_original_proof": False}]))
    assert any("never offered one it had to refuse" in p for p in problems)


def test_certifying_a_satisfiable_instance_is_the_failure_it_looks_for():
    problems = problems_with(_rows(weakened=[
        {"clauses": 38273, "status": "SAT", "checked": True,
         "route": "proof replay", "steps": 5,
         "replayed_original_proof": False}]))
    assert any("does not discriminate" in p for p in problems), problems


def test_an_uncertified_full_instance_is_refused():
    problems = problems_with(_rows(
        full={"clauses": 54785, "status": "UNSAT", "checked": False,
              "route": None, "steps": 0}))
    assert problems


def test_the_shipped_run_took_the_replay_route():
    """The log is the evidence; read it rather than trusting the prose."""
    with open(os.path.join(ROOT, "logs", "negcontrol.log")) as fh:
        text = fh.read()
    assert "route='proof replay' steps=30939" in text
    assert "GOOD:" in text
    assert "SAT   checked=False" in text


def test_a_run_that_never_put_a_satisfiable_formula_to_the_checker_is_refused():
    """`certify` returns on SAT before the checker runs, so a SAT row records
    that the SOLVER disagreed. The checker has to be asked directly."""
    problems = problems_with(_rows(weakened=[
        {"clauses": 38273, "status": "SAT", "checked": False,
         "route": None, "steps": 0}]))               # no replay recorded
    assert any("put to the proof CHECKER" in p for p in problems), problems


def test_the_checker_accepting_the_proof_of_a_false_statement_is_caught():
    problems = problems_with(_rows(weakened=[
        {"clauses": 38273, "status": "SAT", "checked": False, "route": None,
         "steps": 0, "replayed_original_proof": True}]))
    assert any("proof of a false statement" in p for p in problems), problems


def test_the_shipped_run_replayed_the_original_proof_and_was_refused():
    with open(os.path.join(ROOT, "logs", "negcontrol.log")) as fh:
        text = fh.read()
    assert "original proof replays here: False" in text
    assert "original proof replays here: True" not in text


def test_a_control_that_replayed_a_different_proof_is_refused():
    """`run` emits its own proof inside certify(), so without binding the
    replayed proof to the certified one the control passes with an EMPTY
    proof: every replay fails for a trivial reason and the log looks the
    same."""
    for steps in (0, 5):
        problems = problems_with(_rows(
            full={"clauses": 54785, "status": "UNSAT", "checked": True,
                  "route": "proof replay", "steps": 30939,
                  "replay_steps": steps, "replay_sha": "0" * 64}))
        assert any("not the same proof" in p for p in problems), (steps, problems)


def test_a_control_that_does_not_say_which_proof_it_replayed_is_refused():
    problems = problems_with(_rows(
        full={"clauses": 54785, "status": "UNSAT", "checked": True,
              "route": "proof replay", "steps": 30939}))
    assert any("WHICH proof" in p for p in problems), problems


def test_the_shipped_log_binds_the_replayed_proof_to_the_certified_one():
    with open(os.path.join(ROOT, "logs", "negcontrol.log")) as fh:
        text = fh.read()
    assert "steps=30939" in text
    assert "proof replayed below: 30939 steps" in text
