"""The witness acceptance in climb.py must be able to reject.

`multicolour.verify` returns `(ok, detail)`. A non-empty tuple is always
truthy, so `if not multicolour.verify(...)` is always False and the rejection
branch is unreachable -- climb.py said exactly that, written while repairing a
different fail-open in the same function, and would have printed
`WITNESS ... (re-verified)` for a witness the verifier rejected.

This is the same shape as `assert rec["n"] + 1 if "n" in rec else 12 + 1`: an
expression whose truthiness is structurally guaranteed, standing where a real
test was meant to be. The controls below fix the shape in place.
"""

from __future__ import annotations

import json

import multicolour



def _PROBLEM(n):
    """The problem a climb row decided. climb binds on this, so a fixture that
    omits it is asserting a result about no question at all."""
    return {"n": n, "sizes": [4, 4, 4], "k": 3}

def _witness():
    with open("witness_444_3_n83.json") as fh:
        return json.load(fh)


def test_verify_returns_a_pair_that_must_be_unpacked():
    doc = _witness()
    r = multicolour.verify(doc["chi"], doc["n"], doc["sizes"], doc["k"])
    assert isinstance(r, tuple) and len(r) == 2
    ok, _ = r
    assert ok is True


def test_a_truthiness_test_on_the_return_value_cannot_reject():
    """The bug itself, pinned so it cannot be reintroduced silently."""
    rejection = (False, "some reason")
    assert bool(rejection) is True
    assert not (not rejection), "a non-empty tuple is always truthy"


def test_the_unpacked_form_does_reject_a_corrupted_witness():
    doc = _witness()
    chi = list(doc["chi"])
    # Force a monochromatic K_4: colour every triple of {0,1,2,3} colour 0.
    from itertools import combinations
    idx = {t: i for i, t in enumerate(combinations(range(doc["n"]), 3))}
    for t in combinations(range(4), 3):
        chi[idx[t]] = 0
    ok, detail = multicolour.verify(chi, doc["n"], doc["sizes"], doc["k"])
    assert ok is False, detail


def test_the_unpacked_form_still_accepts_the_real_witness():
    """Baseline, so the rejection above is not a checker that refuses all."""
    doc = _witness()
    ok, detail = multicolour.verify(doc["chi"], doc["n"], doc["sizes"], doc["k"])
    assert ok is True, detail


# --- climb.try_base itself, not just the checker it calls -----------------
#
# The tests above exercise `multicolour.verify`. `reproduce.sh` labels this
# file "witness acceptance can reject", and that is a claim about `climb.py`:
# reintroducing `if not multicolour.verify(...)` there would leave every test
# above green. These drive the real `try_base` over a witness file it must
# reject and one it must accept.

import climb
import multicolour


def _base(monkeypatch, tmp_path, chi, n=83, gens=None):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir()
    if gens is None:
        gens = [[(i + 1) % n for i in range(n)]]
    groups = [{"name": "g", "generators": gens}]
    monkeypatch.setattr(climb.make_groups_affine, "build",
                        lambda *a, **k: groups)

    def fake_run(argv, **kw):
        out = argv[argv.index("--out") + 1]
        with open(out, "w") as fh:
            json.dump([{"name": "g",
                        "gens_sha": multicolour._gens_fingerprint(gens),
                        "status": "SAT",
                        "problem": _PROBLEM(n)}], fh)
        with open(f"witness_444_3_n{n}.json", "w") as fh:
            json.dump({"n": n, "sizes": [4, 4, 4], "k": 3, "chi": chi}, fh)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(climb.subprocess, "run", fake_run)


def test_try_base_rejects_a_witness_file_that_does_not_verify(
        monkeypatch, tmp_path, capsys):
    """All triples one colour: a monochromatic K_4 in colour 0 everywhere."""
    from math import comb
    n = 20
    _base(monkeypatch, tmp_path, [0] * comb(n, 3), n=n)
    # NOT None: the child recorded SAT, so this base is not a null either.
    assert climb.try_base(n, n, 1200, 60) == "UNDECIDED"
    assert "does NOT verify" in capsys.readouterr().out


def test_try_base_accepts_a_witness_that_does_verify(monkeypatch, tmp_path,
                                                     capsys):
    """Baseline: on 4 points there is no K_4^(3) to be monochromatic in a
    4-set beyond the whole set, and a 3-colouring of the 4 triples with three
    distinct colours has none. Without this the rejection above would be
    indistinguishable from a function that rejects everything.

    The GROUP matters here, and this fixture used to get it wrong. The
    4-cycle is transitive on the four triples, so its only invariant
    colourings are constant -- and a constant colouring makes the whole 4-set
    monochromatic. There is therefore NO good 4-cycle-invariant colouring on
    4 points, and this test was asserting that try_base accept a witness for
    a class that cannot contain one. It passed only because try_base checked
    goodness and never invariance. Under the trivial group every colouring is
    invariant, so the object below is a genuine witness for its class.
    """
    n = 4
    chi = [0, 1, 2, 0]
    ok, detail = multicolour.verify(chi, n, [4, 4, 4], 3)
    assert ok, detail
    _base(monkeypatch, tmp_path, chi, n=n, gens=[list(range(n))])
    assert climb.try_base(n, n, 1200, 60) == n
    assert "WITNESS" in capsys.readouterr().out


def test_try_base_verifies_against_the_problem_being_climbed(
        monkeypatch, tmp_path, capsys):
    """A witness file that declares a DIFFERENT problem must not be accepted.

    Reading `sizes` and `k` back out of the file and handing them to the
    verifier makes the check circular: a colouring that is a valid R(5,5,5;3)
    object verifies against its own declaration while failing R(4,4,4;3),
    which is the bound this climb is about.
    """
    n = 20
    from math import comb
    _base(monkeypatch, tmp_path, [0] * comb(n, 3), n=n)
    w = tmp_path / f"witness_444_3_n{n}.json"

    def fake_run(argv, **kw):
        out = argv[argv.index("--out") + 1]
        gens = [[(i + 1) % n for i in range(n)]]
        with open(out, "w") as fh:
            json.dump([{"name": "g",
                        "gens_sha": multicolour._gens_fingerprint(gens),
                        "status": "SAT",
                        "problem": _PROBLEM(n)}], fh)
        # All triples colour 0: no monochromatic K_5 in three colours is FALSE
        # too, but the point is the declaration -- sizes [5,5,5] is not the
        # problem being climbed and must be refused before verification.
        w.write_text(json.dumps({"n": n, "sizes": [5, 5, 5], "k": 3,
                                 "chi": [0] * comb(n, 3)}))
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(climb.subprocess, "run", fake_run)
    assert climb.try_base(n, n, 1200, 60) == "UNDECIDED"
    out = capsys.readouterr().out
    assert "this climb is solving" in out
    assert "WITNESS" not in out
