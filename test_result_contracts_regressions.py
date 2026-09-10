"""Result-handling invariants, each pinned by a concrete input.

Every test below supplies a specific input rather than a paraphrase of one: a
gate is only known to hold when the input it must refuse is actually offered
to it.
"""
import json
import os
import subprocess
import sys

import pytest

import certify_nulls
import negative_control

ROOT = os.path.dirname(os.path.abspath(__file__))
PROB = {"k": 3, "n": 63, "s": 4, "t": 6, "sizes": None}
OTHER = {"k": 2, "n": 7, "s": 4, "t": 4, "sizes": None}


def _row(problem, **kw):
    r = {"name": "C", "gens_sha": "a" * 64, "status": "UNSAT",
         "checked": True, "route": "proof replay", "problem": problem}
    r.update(kw)
    return r


# --- 1: comparisons must bind the problem ----------------------
def test_a_result_for_one_problem_cannot_certify_a_claim_about_another(tmp_path):
    """The same group is UNSAT for one problem and SAT for
    another, so a deposited row recording the WRONG problem must not be
    satisfied by a genuine result for the right one."""
    dep = tmp_path / "dep.json"
    dep.write_text(json.dumps([_row(OTHER)]))
    problems = certify_nulls.gate([_row(PROB)], compare_path=str(dep))
    assert problems, "a row decided on one problem certified another"
    assert any("problem" in p for p in problems), problems


def test_the_same_problem_still_matches(tmp_path):
    """Negative control: the binding must not reject a genuine match."""
    dep = tmp_path / "dep.json"
    dep.write_text(json.dumps([_row(PROB)]))
    assert certify_nulls.gate([_row(PROB)], compare_path=str(dep)) == []


def test_a_deposited_row_without_a_problem_key_is_refused(tmp_path):
    dep = tmp_path / "dep.json"
    d = _row(PROB)
    del d["problem"]
    dep.write_text(json.dumps([d]))
    assert certify_nulls.gate([_row(PROB)], compare_path=str(dep))


# --- 2: --out must not be able to overwrite --compare ----------
@pytest.mark.parametrize("alias", ["same", "symlink"])
def test_out_cannot_alias_compare(tmp_path, alias):
    """Pointing both at one path makes the run compare its
    own output against itself and print the matching claim."""
    ref = tmp_path / "ref.json"
    ref.write_text(json.dumps([_row(PROB)]))
    out = ref if alias == "same" else tmp_path / "link.json"
    if alias == "symlink":
        os.symlink(ref, out)
    before = ref.read_text()
    p = subprocess.run(
        [sys.executable, os.path.join(ROOT, "certify_nulls.py"),
         "--groups", os.path.join(ROOT, "groups63.json"),
         "--n", "63", "--s", "4", "--t", "6", "--k", "3",
         "--out", str(out), "--compare", str(ref)],
        capture_output=True, text=True, cwd=ROOT)
    assert p.returncode == 2, p.stdout + p.stderr
    assert "same file" in p.stderr, p.stderr
    assert ref.read_text() == before, "the reference was written before the refusal"


# --- 3: the replayed proof must be the real one ----------------
def test_an_equal_length_proof_that_fails_on_the_full_instance_is_refused():
    """A same-length substitute has the right step count,
    fails against the full CNF, and so fails against every weakening for a
    reason that says nothing about the checker."""
    rows = [{"status": "UNSAT", "checked": True, "route": "proof replay",
             "steps": 30939, "replay_steps": 30939, "clauses": 100,
             "replay_valid_on_full": False},
            {"status": "SAT", "checked": False, "clauses": 50,
             "replayed_original_proof": False}]
    problems = negative_control.problems_with(rows)
    assert any("does not itself verify" in p for p in problems), problems


def test_a_proof_that_does_verify_is_accepted():
    """Negative control: the new requirement must not reject a real run."""
    rows = [{"status": "UNSAT", "checked": True, "route": "proof replay",
             "steps": 30939, "replay_steps": 30939, "clauses": 100,
             "replay_valid_on_full": True},
            {"status": "SAT", "checked": False, "clauses": 50,
             "replayed_original_proof": False}]
    assert negative_control.problems_with(rows) == []


# --- 4: over-cap bookkeeping is not a decided sweep ----------------
def test_an_all_over_cap_sweep_is_not_a_successful_sweep(tmp_path):
    """Every class over the cap, no solver call,
    exit 0 and no output file."""
    out = tmp_path / "result.json"
    p = subprocess.run(
        [sys.executable, os.path.join(ROOT, "sweep_pdm.py"),
         "--pmin", "53", "--pmax", "53", "--mmax", "0",
         "--max-vars", "1", "--out", str(out)],
        capture_output=True, text=True, cwd=ROOT)
    assert p.returncode != 0, "a sweep that decided nothing exited 0"
    assert "DECIDED" in p.stderr, p.stderr
    assert out.exists(), "the requested --out file was never written"
    rows = json.loads(out.read_text())
    assert rows and all(r["status"] == "OVER_CAP" for r in rows)


# --- the harness must actually invoke every test file ------------------
def test_every_test_file_is_on_the_reproduction_path():
    """Shipping a test is not running it.

    This file was written to pin four defects, shipped in the
    package, and invoked by no harness mode -- the checks existed and never
    ran. Listing it fixes that one file; this test fixes the class, by making
    the harness's coverage of test_*.py an explicit release obligation.
    """
    import deposit_paths
    path = deposit_paths.resolve("reproduce.sh")
    assert path, "reproduce.sh was not found"
    cand = os.path.basename(path)
    with open(path) as fh:
        harness = fh.read()
    # The obligation is about the DEPOSIT, whose set of test files is final.
    # Before packaging, the directory also holds tooling and its tests, which
    # are not deposited and so cannot be on the reproduction path; the file
    # set is not yet the one being promised about. The harness sitting beside
    # the tests is what says the set is final.
    if os.path.dirname(path) != os.path.normpath(ROOT):
        pytest.skip("not the assembled deposit; the file set is not final")
    on_disk = {f for f in os.listdir(ROOT)
               if f.startswith("test_") and f.endswith(".py")}
    missing = sorted(f for f in on_disk if f not in harness)
    assert not missing, (
        f"{cand} never invokes {missing}; those checks ship with the package "
        f"but are not on the reproduction path")
