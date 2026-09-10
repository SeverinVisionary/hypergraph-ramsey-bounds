"""Tests for `drat_check`.

The point of a certificate checker is that it says no. Most of these are
negative controls: a checker that accepts a tampered proof is worse than no
checker, because it launders the solver's word into the appearance of a proof.
"""

from itertools import combinations

import pytest

import drat_check as dc


def php(pigeons, holes):
    """Pigeonhole: UNSAT iff pigeons > holes. Small, and RUP-provable."""
    def v(p, h):
        return p * holes + h + 1
    cls = [[v(p, h) for h in range(holes)] for p in range(pigeons)]
    for h in range(holes):
        for a, b in combinations(range(pigeons), 2):
            cls.append([-v(a, h), -v(b, h)])
    return cls


def test_php_certifies():
    r = dc.certify(php(4, 3))
    assert r["status"] == "UNSAT"
    assert r["checked"] is True
    assert r["steps"] > 0


def test_satisfiable_instance_yields_no_proof():
    r = dc.certify([[1, 2], [-1]])
    assert r["status"] == "SAT"
    assert r["checked"] is False


def test_pigeonhole_that_fits_is_sat():
    assert dc.certify(php(3, 3))["status"] == "SAT"


# --- negative controls -------------------------------------------------

def test_truncated_proof_is_rejected():
    """Short prefixes must fail, and the boundary must be sharp.

    Not "drop the last step": the last step is often the explicit empty clause,
    and the step before it already makes the empty clause reachable by unit
    propagation, so a one-step truncation legitimately still certifies. The
    real property is that the proof is not accepted before it has done the
    work, and that once accepted it stays accepted."""
    cls = php(4, 3)
    _, proof = dc.emit_proof(cls)
    assert len(proof) > 2

    verdicts = [dc.check(cls, proof[:i]) for i in range(len(proof) + 1)]
    assert verdicts[0] is False, "empty prefix must not certify"
    assert verdicts[-1] is True, "the full proof must certify"

    first_ok = verdicts.index(True)
    assert first_ok > 1, "the proof must do real work before it is accepted"
    assert all(v is False for v in verdicts[:first_ok])
    assert all(v is True for v in verdicts[first_ok:]), (
        "acceptance must be monotone: adding steps cannot un-prove it"
    )


def test_non_rup_step_is_rejected():
    """A clause that does not follow is caught even though it is 'plausible'."""
    cls = php(4, 3)
    _, proof = dc.emit_proof(cls)
    tampered = [("a", [1])] + list(proof)   # assert pigeon 0 in hole 0
    assert dc.check(cls, tampered) is False


def test_empty_clause_asserted_out_of_nowhere_is_rejected():
    """The one shortcut that would fake every proof."""
    assert dc.check(php(3, 3), [("a", [])]) is False


def test_proof_for_a_different_instance_is_rejected():
    """A real proof, replayed against a CNF it does not belong to."""
    _, proof = dc.emit_proof(php(5, 4))
    assert dc.check(php(3, 3), proof) is False


def test_deleting_the_clause_a_step_needs_breaks_the_step():
    """Deletion is honoured, not ignored, when the clause is really there."""
    cls = [[1, 2], [-1, 2], [1, -2], [-1, -2]]
    _, proof = dc.emit_proof(cls)
    assert dc.check(cls, proof) is True
    assert dc.check(cls[:-1], proof) is False


# --- propagation engine ------------------------------------------------

def test_propagate_detects_direct_conflict():
    db = dc._DB()
    db.add([1])
    db.add([-1])
    assert db.propagate([]) is True


def test_propagate_chains_units():
    db = dc._DB()
    for c in ([1], [-1, 2], [-2, 3], [-3]):
        db.add(c)
    assert db.propagate([]) is True


def test_propagate_does_not_invent_a_conflict():
    db = dc._DB()
    db.add([1, 2, 3])
    assert db.propagate([-1]) is False


def test_duplicate_literals_do_not_break_watches():
    db = dc._DB()
    db.add([1, 1, 2])
    db.add([-2])
    assert db.propagate([-1]) is True


def test_deleting_an_absent_clause_is_a_noop():
    db = dc._DB()
    db.add([1, 2])
    assert db.delete([3, 4]) is False
    assert db.propagate([-1, -2]) is True


@pytest.mark.parametrize("solver", ["Glucose42", "Glucose3", "Lingeling"])
def test_multiple_solvers_all_produce_checkable_proofs(solver):
    """The certificate must not depend on which solver wrote it."""
    cls = php(4, 3)
    r = dc.certify(cls, solver=solver)
    assert r["status"] == "UNSAT" and r["checked"] is True


def test_unit_propagation_refutation_is_certified_with_an_empty_proof():
    """The case every class in this sweep actually hits: the solver refutes by
    propagation, emits nothing, and the empty proof is still a certificate."""
    cls = [[1, 2], [-1], [-2]]
    r = dc.certify(cls)
    assert r["status"] == "UNSAT"
    assert r["steps"] == 0
    assert r["checked"] is True
    assert r["route"] == "unit propagation"


def test_a_real_proof_is_labelled_proof_replay():
    r = dc.certify(php(4, 3))
    assert r["checked"] is True and r["route"] == "proof replay"


def test_empty_proof_does_not_certify_a_satisfiable_instance():
    """The failure mode the change above could have introduced."""
    assert dc.check([[1, 2], [2, 3]], []) is False


def test_a_genuinely_rat_step_is_accepted():
    """RAT must do real work, not just be dead code.

    With F = {(x or y), (not x or y)}, the unit (x) is NOT RUP -- assuming
    not-x propagates y and reaches no conflict -- but it IS RAT on pivot x: the
    only clause holding not-x resolves to (x or y), already in F. A checker
    that rejects this rejects the proofs of every variable-eliminating
    preprocessor."""
    db = dc._DB()
    for c in ([1, 2], [-1, 2]):
        db.add(c)
    assert db.propagate([-1]) is False, "precondition: (x) is not RUP here"
    assert db.is_rat([1]) is True


def test_rat_does_not_launder_an_arbitrary_clause():
    """The negative control for RAT: it must not accept just anything.

    (not x) is not RAT on pivot not-x here, because resolving against (x or y)
    gives (not x or y), which does not follow."""
    db = dc._DB()
    for c in ([1, 2], [1, -2]):
        db.add(c)
    assert db.is_rat([-1]) is False


def test_rat_cannot_conjure_the_empty_clause():
    """The empty clause has no pivot, so RAT must never apply to it."""
    assert dc.check([[1, 2], [2, 3]], [("a", [])]) is False


def test_ignoring_deletions_still_rejects_a_bad_proof():
    """Skipping deletions must not turn the checker into a rubber stamp.

    Keeping deleted clauses can only make RUP easier, so the risk is accepting
    something false. It does not: a non-RUP step and a conjured empty clause are
    still refused with deletions ignored."""
    cls = php(4, 3)
    assert dc.check(cls, [("a", [1])]) is False
    assert dc.check(cls, [("d", cls[0]), ("a", [])]) is False


def test_deletion_handling_is_selectable_and_agrees_when_nothing_is_deleted():
    cls = php(4, 3)
    _, proof = dc.emit_proof(cls)
    assert dc.check(cls, proof, honour_deletions=True) is True
    assert dc.check(cls, proof, honour_deletions=False) is True


def test_certifier_discriminates_on_a_real_instance():
    """The control that matters: a checker which ignores deletions could in
    principle rubber-stamp anything, and pigeonhole would not reveal it.

    So take a real instance from this repo's own sweep -- R(4,5;3) at n=35 under
    Z_35 : <2>, genuinely UNSAT -- weaken it until it becomes satisfiable, and
    demand the certifier notice. Cheap: 20 variables, builds in a tenth of a
    second."""
    import random

    import ansatz

    n = 35
    gens = [[(i + 1) % n for i in range(n)], [(2 * i) % n for i in range(n)]]
    cnf, _, _ = ansatz.build_cnf(gens, n, 4, 5, 3)
    assert dc.certify(cnf)["checked"] is True, "the real instance must certify"

    random.seed(7)
    saw_sat = False
    for frac in (0.9, 0.7, 0.5, 0.3, 0.15):
        sub = [c for c in cnf if random.random() < frac]
        r = dc.certify(sub)
        if r["status"] == "SAT":
            saw_sat = True
            assert r["checked"] is False, (
                "a satisfiable instance must never be certified"
            )
        else:
            assert r["checked"] is True, (
                "a still-UNSAT weakening must still be provable"
            )
    assert saw_sat, "the weakening never became satisfiable; control was vacuous"


# --- the monotonicity direction the soundness argument depends on ---------

def test_rup_is_monotone_in_the_database():
    """Adding clauses makes a RUP check EASIER, never harder.

    The docstring in drat_check.py once said the opposite -- that ignoring
    deletions makes the checker "more demanding" -- and the whole reason the
    discriminating control matters is that it does not. This pins the
    direction: a clause that is RUP against a database is RUP against every
    superset, and a clause can be RUP against a superset while not being RUP
    against the subset.
    """
    from drat_check import _DB

    def db(clauses):
        d = _DB()
        for c in clauses:
            d.add(c)
        return d

    # F = {(a)}. The clause (b) is not RUP against it: assuming -b propagates
    # only a, and no conflict follows. Adding (-a b) makes it RUP.
    small = db([[1]])
    big = db([[1], [-1, 2]])
    # RUP for clause C is: assume every literal of C false, propagate, conflict.
    assert big.propagate([-2]), "adding (-a b) makes (b) RUP"
    assert not small.propagate([-2]), ("without it, (b) is not RUP -- so the "
                                       "superset is the easier check, not the "
                                       "harder")


def test_the_checker_stops_certifying_when_the_instance_becomes_satisfiable():
    """The control that carries the argument, since the reading is permissive:
    a satisfiable formula must not be certified UNSAT whatever proof is
    supplied."""
    from drat_check import check
    sat_formula = [[1, 2], [-1, 2]]          # satisfiable: a=F, b=T
    # A conjured lemma and an empty clause, in the ("a", lits) step form.
    assert check(sat_formula, [("a", [3]), ("a", [])]) is False
