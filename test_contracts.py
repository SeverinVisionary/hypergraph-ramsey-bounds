"""Negative controls for the shared contracts.

Each test below is an input that a narrower rule would accept.  They live
here, next to the contract, rather than beside any one consumer: the rule is
tested where it is defined, and the consumers are tested for USING it.
"""
import itertools

import pytest

import ansatz
import certify_nulls
import contracts
import crosscheck_n63
import multicolour
from theorem_b_counterexamples import problems_with as tb_problems

P = {"n": 63, "s": 4, "t": 6, "k": 3}
SHA = "a" * 64


def _row(status="UNSAT", name="g", sha=SHA, problem=None):
    return {"name": name, "gens_sha": sha, "status": status,
            "problem": P if problem is None else problem}


# --- problem identity ---------------------------------------------------
def test_every_legacy_shape_means_the_same_question():
    shapes = [{"n": 63, "s": 4, "t": 6, "k": 3},
              {"n": 63, "s": 4, "t": 6, "k": 3, "sizes": None},
              {"n": 63, "sizes": [4, 6], "k": 3}]
    ids = {contracts.problem_identity(x) for x in shapes}
    assert len(ids) == 1 and None not in ids


def test_an_unusable_problem_is_not_an_identity():
    """Two DIFFERENT incomplete problems both normalised to None, and a gate
    that lets None match None treats them as the same question."""
    assert contracts.problem_identity({"n": 3, "k": 2}) is None
    assert contracts.problem_identity({"n": 9, "k": 4}) is None


def test_identity_ignores_the_display_name():
    a = contracts.instance_identity(_row(name="one"))
    b = contracts.instance_identity(_row(name="two"))
    assert a == b and a is not None


# --- history reduction --------------------------------------------------
@pytest.mark.parametrize("seq", [
    ("SAT", "UNSAT"),
    ("SAT", "TIMEOUT", "UNSAT"),      # the intervening non-decision
    ("UNSAT", "TIMEOUT", "SAT"),
    ("SAT", "ERROR", "TIMEOUT", "UNSAT"),
])
def test_two_verdicts_for_one_instance_are_refused_in_any_order(seq):
    for perm in set(itertools.permutations(seq)):
        with pytest.raises(contracts.Contradiction):
            contracts.reduce_history([_row(s) for s in perm])


def test_a_timeout_alone_is_not_a_verdict():
    assert contracts.reduce_history([_row("TIMEOUT")]) == {}


def test_agreeing_rows_are_not_a_contradiction():
    assert contracts.reduce_history([_row("UNSAT"), _row("UNSAT")])


# --- both engines share one resume --------------------------------------
@pytest.mark.parametrize("engine", [ansatz, multicolour])
def test_a_run_over_one_class_does_not_delete_another(engine):
    sha_b = engine._gens_fingerprint([[0]])
    rows = [_row("SAT", name="A", sha="x" * 64),
            _row("UNSAT", name="B", sha=sha_b)]
    engine._resume(rows, P, [{"name": "B", "generators": [[0]]}], "f.json")
    assert [r["name"] for r in rows] == ["A", "B"]


@pytest.mark.parametrize("engine", [ansatz, multicolour])
def test_contradictory_rows_are_refused_by_both_engines(engine):
    sha_b = engine._gens_fingerprint([[0]])
    rows = [_row("SAT", name="B", sha=sha_b), _row("UNSAT", name="B", sha=sha_b)]
    with pytest.raises(SystemExit):
        engine._resume(rows, P, [{"name": "B", "generators": [[0]]}], "f.json")


@pytest.mark.parametrize("engine", [ansatz, multicolour])
def test_the_same_question_in_another_shape_is_not_foreign(engine):
    sha_b = engine._gens_fingerprint([[0]])
    rows = [_row("UNSAT", name="B", sha=sha_b,
                 problem={"n": 63, "sizes": [4, 6], "k": 3})]
    assert engine._resume(rows, P, [{"name": "B", "generators": [[0]]}],
                          "f.json")


# --- certified instances are not labels ---------------------------------
def test_renaming_does_not_create_distinct_certified_classes():
    rows = [{**_row(), "name": f"n{i}", "checked": True,
             "route": "unit propagation"} for i in range(5)]
    assert certify_nulls.gate(rows, expect_certified=5)


def test_certification_rejects_an_unusable_identity():
    rows = [{**_row(problem={"n": 3, "k": 2}), "checked": True,
             "route": "unit propagation"}]
    assert certify_nulls.gate(rows, expect_certified=1)


def test_crosscheck_counts_the_same_population_it_compares(tmp_path):
    import json
    here = contracts.problem_identity(P)
    dep = tmp_path / "d.json"
    dep.write_text(json.dumps([{"name": "g", "gens_sha": SHA,
                                "status": "UNSAT", "checked": True,
                                "problem": P}]))
    assert crosscheck_n63.coverage_problems([("g", SHA, here)] * 5, 5,
                                            str(dep))


# --- Theorem B hypotheses are derived -----------------------------------
def _tb(p, order, first=True, second=False):
    return {"p": p, "n": p + 1, "name": f"Z_{p}", "order": order,
            "abs_C_p_2": p * (p - 1) // 2, "p_mod_4": p % 4,
            "satisfies_first_hypothesis": first,
            "satisfies_second_hypothesis": second,
            "vars": 1, "clauses": 1, "status": "SAT", "verified": True}


@pytest.mark.parametrize("rows", [
    [_tb(13, 1), _tb(37, 1)],            # |G| != C(p,2), flag says otherwise
    [_tb(7, 21), _tb(11, 55)],           # p = 3 mod 4, flag says otherwise
    [_tb(9, 36), _tb(25, 300)],          # not prime
])
def test_declared_hypotheses_must_match_the_derived_ones(rows):
    assert tb_problems(rows, expect=2)


def test_the_genuine_counterexamples_still_pass():
    assert tb_problems([_tb(13, 78), _tb(37, 666)], expect=2) == []


# --- further probes -----------------------------------------------------
@pytest.mark.parametrize("order", [("SAT", "UNSAT"), ("UNSAT", "SAT")])
def test_certification_reduces_history_in_either_order(order):
    """Filtering to certified rows first removed the contradiction."""
    rows = [{**_row(s), "checked": s == "UNSAT", "route": "unit propagation"}
            for s in order]
    assert certify_nulls.gate(rows, expect_certified=1)


def test_crosscheck_population_ignores_aliases(tmp_path):
    """Five copies of ONE instance under five names are one class."""
    import json
    here = contracts.problem_identity(P)
    dep = tmp_path / "d.json"
    dep.write_text(json.dumps([{"name": "g", "gens_sha": SHA,
                                "status": "UNSAT", "checked": True,
                                "problem": P}]))
    items = [(f"alias{i}", SHA, here) for i in range(5)]
    assert crosscheck_n63.coverage_problems(items, 5, str(dep))


@pytest.mark.parametrize("bad", [
    {"n": 63.9, "k": 3.9, "sizes": [4.9, 6.9]},   # truncated into a real one
    {"n": 63, "k": 3, "sizes": "46"},             # string iterated per char
    {"n": 63, "k": 3, "sizes": [4, 6], "s": 5, "t": 5},   # two declarations
    {"n": 63, "k": True, "sizes": [4, 6]},        # bool is an int in Python
])
def test_malformed_input_is_rejected_not_reinterpreted(bad):
    assert contracts.problem_identity(bad) is None


def test_theorem_b_predicate_rejects_non_integers():
    with pytest.raises(ValueError):
        contracts.theorem_b_hypotheses(13.9, 78.9)
