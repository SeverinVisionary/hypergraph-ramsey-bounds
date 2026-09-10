"""No work done must not exit like work done with a negative answer.

Three programs in this package end with a summary line and an exit status, and
in each the "nothing to report" path and the "searched, found nothing" path
were the same path. That difference is the whole content of a null: `climb.py`
printing "all bases ran" after running no solver, `sweep_pdm.py` printing a
table of zero cells, and the n=31 rung printing no median all exited 0, and 0
is what a completed negative search exits with.

Each test below forces the empty case and requires a refusal. The paired
baselines are the point: a program that refuses everything is not a fix.
"""

from __future__ import annotations

import json

import pytest

import climb
import ladder31
import sweep_pdm


# --- the n=31 calibration rung -------------------------------------------


def _PROBLEM(n):
    """The problem a climb row decided. climb binds on this, so a fixture that
    omits it is asserting a result about no question at all."""
    return {"n": n, "sizes": [4, 4, 4], "k": 3}

def _rep(status, solve_s, **kw):
    row = {"status": status, "solve_s": solve_s}
    row.update(kw)
    return row


def test_a_rung_where_every_repeat_was_censored_is_not_a_measurement():
    assert ladder31.problems_with([_rep("TIMEOUT", None)] * 3)


def test_a_rung_that_completed_is_a_measurement():
    """The baseline. Without it, `problems_with` could reject everything."""
    assert ladder31.problems_with([_rep("UNSAT", 12.5)] * 3) == []


def test_the_censored_rung_makes_the_program_exit_non_zero(capsys):
    rc = ladder31.rung(runner=lambda *a, **k: _rep("TIMEOUT", None), out=None)
    assert rc == 1
    assert "measured nothing" in capsys.readouterr().err


def test_a_completed_rung_exits_zero(capsys):
    rc = ladder31.rung(runner=lambda *a, **k: _rep("UNSAT", 3.0), out=None)
    assert rc == 0
    assert "median" in capsys.readouterr().out


@pytest.mark.parametrize("rows", [
    [_rep("SAT", 1.0, verified=True), _rep("UNSAT", 1.0)],       # disagree
    [_rep("ERROR", None), _rep("UNSAT", 1.0)],                   # broken tool
    [_rep("SAT", 1.0)],                                          # unverified SAT
])
def test_the_pre_existing_refusals_still_fire(rows):
    assert ladder31.problems_with(rows)


# --- the climb -----------------------------------------------------------

def test_a_climb_where_no_base_had_a_class_is_not_a_negative_result(
        monkeypatch, capsys):
    """--max-vars 0 leaves every base with no class under the cap. Nothing is
    solved, and before this the climb reported that as 'all bases ran'."""
    monkeypatch.setattr(climb.make_groups_affine, "build",
                        lambda n, p, max_vars, **kw: [])
    monkeypatch.setattr("sys.argv",
                        ["climb.py", "--n", "83", "--bases", "83,79",
                         "--max-vars", "0"])
    assert climb.main() == 1
    assert "NO RESULT" in capsys.readouterr().out


def _climb_with_child(monkeypatch, tmp_path, statuses, drop=0):
    """Drive the REAL try_base with a stubbed child process.

    The child is `multicolour.py`, which records a TIMEOUT row and exits 0 --
    a budget expiring is not an error there. So the stub returns 0 and writes
    one row per generated class, with the statuses given; whether the base
    counts as searched has to come from those rows.

    The rows carry the SAME names and generator fingerprints as the classes
    the builder produced. A fixture whose rows cannot be matched to the classes
    would pass a coverage check that does not exist and fail one that does, so
    it could not tell the two apart. `drop` deletes that many rows, which is
    the case the coverage guard is for.
    """
    import multicolour
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir()
    groups = [{"name": f"c{i}", "generators": [[(j + 1 + i) % 5
                                                for j in range(5)]]}
              for i in range(len(statuses))]
    monkeypatch.setattr(climb.make_groups_affine, "build",
                        lambda n, p, max_vars, **kw: groups)

    def fake_run(argv, **kw):
        out = argv[argv.index("--out") + 1]
        rows = [{"name": g["name"],
                 "gens_sha": multicolour._gens_fingerprint(g["generators"]),
                 "status": st,
                 # climb binds every row to the problem it decided, so a
                 # fixture without one asserts a result about no question.
                 "problem": _PROBLEM(83)}
                for g, st in zip(groups, statuses)]
        with open(out, "w") as fh:
            json.dump(rows[:len(rows) - drop] if drop else rows, fh)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(climb.subprocess, "run", fake_run)


def test_a_climb_whose_classes_all_timed_out_is_not_a_negative_result(
        monkeypatch, tmp_path, capsys):
    """multicolour.py exits 0 after a TIMEOUT, so the child's status cannot
    distinguish 'decided nothing' from 'decided, found nothing'."""
    _climb_with_child(monkeypatch, tmp_path, ["TIMEOUT", "TIMEOUT"])
    monkeypatch.setattr("sys.argv",
                        ["climb.py", "--n", "83", "--bases", "83,79"])
    assert climb.main() == 1
    assert "NO RESULT" in capsys.readouterr().out


def test_one_undecided_class_makes_the_base_unexhausted(
        monkeypatch, tmp_path, capsys):
    _climb_with_child(monkeypatch, tmp_path, ["UNSAT", "TIMEOUT"])
    monkeypatch.setattr("sys.argv", ["climb.py", "--n", "83", "--bases", "83"])
    assert climb.main() == 1
    assert "undecided" in capsys.readouterr().out


def test_a_climb_that_searched_and_found_nothing_exits_zero(
        monkeypatch, tmp_path, capsys):
    """The baseline: every class DECIDED, none satisfiable. This must still be
    reportable as a completed negative search, or the guard above is just a
    program that always refuses."""
    _climb_with_child(monkeypatch, tmp_path, ["UNSAT", "EMPTY"])
    monkeypatch.setattr("sys.argv",
                        ["climb.py", "--n", "83", "--bases", "83,79"])
    assert climb.main() == 0
    assert "no witness from 2 base(s) searched" in capsys.readouterr().out


def test_a_base_with_no_class_is_not_counted_as_searched(monkeypatch, capsys):
    monkeypatch.setattr(climb.make_groups_affine, "build",
                        lambda n, p, max_vars, **kw: [] if p == 79 else None)
    monkeypatch.setattr(climb, "try_base",
                        lambda n, p, mv, cap: "EMPTY" if p == 79 else None)
    monkeypatch.setattr("sys.argv",
                        ["climb.py", "--n", "83", "--bases", "83,79"])
    assert climb.main() == 0
    assert "1 base(s) searched" in capsys.readouterr().out


def test_a_broken_base_is_still_no_result(monkeypatch, capsys):
    monkeypatch.setattr(climb, "try_base", lambda n, p, mv, cap: "ERROR")
    monkeypatch.setattr("sys.argv",
                        ["climb.py", "--n", "83", "--bases", "83"])
    assert climb.main() == 1
    assert "failed to run" in capsys.readouterr().out


def test_try_base_reports_an_empty_tower_distinctly(monkeypatch, capsys):
    """`None` means searched-and-nothing; an empty tower must not return it."""
    monkeypatch.setattr(climb.make_groups_affine, "build",
                        lambda n, p, max_vars, **kw: [])
    assert climb.try_base(83, 83, 0, 60) == "EMPTY"
    assert "nothing to search" in capsys.readouterr().out


# --- the (p, d, m) sweep --------------------------------------------------

def test_a_sweep_that_selected_no_cell_is_not_an_exhaustive_sweep(
        monkeypatch, tmp_path, capsys):
    """Every tower filtered out: no row, so no ERROR or TIMEOUT row exists to
    make the run fail, and the summary reads as a completed sweep of nothing."""
    monkeypatch.setattr(sweep_pdm, "build_tower", lambda n, p, mv, **kw: [])
    monkeypatch.setattr("sys.argv",
                        ["sweep_pdm.py", "--pmin", "53", "--pmax", "59",
                         "--mmax", "1", "--max-vars", "1",
                         "--out", str(tmp_path / "s.json")])
    assert sweep_pdm.main() == 1
    assert "Nothing was swept" in capsys.readouterr().err


def test_a_sweep_with_decided_cells_exits_zero(monkeypatch, tmp_path, capsys):
    """The baseline. One UNSAT cell per (p, m) and no undecided cell."""
    monkeypatch.setattr(sweep_pdm, "build_tower",
                        lambda n, p, mv, **kw: [{"name": f"g{p}", "order": 1,
                                           "generators": [[0]]}])
    monkeypatch.setattr(
        sweep_pdm, "run_capped_out_of_process",
        lambda fn, kw, cap: type("R", (), {
            "status": "OK", "elapsed_s": 0.1, "detail": None,
            "value": {"vars": 1, "clauses": 1, "empty": 0,
                      "status": "UNSAT",
                       "problem": _PROBLEM(83)}})())
    out = tmp_path / "s.json"
    monkeypatch.setattr("sys.argv",
                        ["sweep_pdm.py", "--pmin", "53", "--pmax", "59",
                         "--mmax", "1", "--out", str(out)])
    assert sweep_pdm.main() == 0
    assert len(json.loads(out.read_text())) > 0


def test_rows_that_do_not_cover_every_generated_class_are_not_a_search(
        monkeypatch, tmp_path, capsys):
    """Two classes generated, one row written. Counting decided rows says
    "one decided, none undecided"; the base was not searched."""
    _climb_with_child(monkeypatch, tmp_path, ["UNSAT", "UNSAT"], drop=1)
    monkeypatch.setattr("sys.argv", ["climb.py", "--n", "83", "--bases", "83"])
    assert climb.main() == 1
    out = capsys.readouterr().out
    assert "covers 1 of the 2" in out and "NO RESULT" in out


def test_a_row_without_a_generator_fingerprint_is_not_a_decided_class(
        monkeypatch, tmp_path, capsys):
    import multicolour
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir()
    groups = [{"name": "c0", "generators": [[1, 2, 3, 4, 0]]}]
    monkeypatch.setattr(climb.make_groups_affine, "build",
                        lambda *a, **k: groups)

    def fake_run(argv, **kw):
        out = argv[argv.index("--out") + 1]
        with open(out, "w") as fh:                       # no gens_sha
            json.dump([{"name": "c0", "status": "UNSAT",
                        "problem": _PROBLEM(83)}], fh)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(climb.subprocess, "run", fake_run)
    monkeypatch.setattr("sys.argv", ["climb.py", "--n", "83", "--bases", "83"])
    assert climb.main() == 1
    assert "does not identify one" in capsys.readouterr().out


def test_a_cached_sat_is_not_turned_into_a_negative_result(
        monkeypatch, tmp_path, capsys):
    """multicolour.py skips a class already decided in --out, so a cached SAT
    row plus the witness that run produced leaves the witness file untouched.
    That is a base WITH a witness; reporting "no witness" would invert it."""
    import multicolour
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir()
    groups = [{"name": "c0", "generators": [[1, 2, 3, 4, 0]]}]
    monkeypatch.setattr(climb.make_groups_affine, "build",
                        lambda *a, **k: groups)
    w = tmp_path / "witness_444_3_n83.json"
    w.write_text(json.dumps({"n": 83, "sizes": [4, 4, 4], "k": 3, "chi": []}))

    def fake_run(argv, **kw):
        out = argv[argv.index("--out") + 1]
        with open(out, "w") as fh:          # cached SAT; witness untouched
            json.dump([{"name": "c0",
                        "gens_sha": multicolour._gens_fingerprint(
                            groups[0]["generators"]),
                        "status": "SAT",
                        "problem": _PROBLEM(83)}], fh)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(climb.subprocess, "run", fake_run)
    assert climb.try_base(83, 83, 1200, 60) == "UNDECIDED"
    assert "has a witness" in capsys.readouterr().out


def test_a_search_stopped_at_a_sat_is_not_called_incomplete(
        monkeypatch, tmp_path, capsys):
    """The other side: multicolour.py breaks at the first SAT, so the later
    classes have no rows. Demanding full coverage there would reject a find."""
    import multicolour
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir()
    n = 4
    # The identity, deliberately. The 4-cycle [1,2,3,0] is transitive on the
    # four triples of a 4-set, so its only invariant colourings are constant
    # and every one of them is monochromatic on the whole set: that class
    # cannot hold the witness this fixture hands it. Under the trivial group
    # the colouring below really is invariant, so the SAT row and the witness
    # agree with each other.
    gens = [[0, 1, 2, 3]]
    groups = [{"name": "c0", "generators": gens},
              {"name": "c1", "generators": [[2, 3, 0, 1]]}]
    monkeypatch.setattr(climb.make_groups_affine, "build",
                        lambda *a, **k: groups)

    def fake_run(argv, **kw):
        out = argv[argv.index("--out") + 1]
        with open(out, "w") as fh:                 # only the first class ran
            json.dump([{"name": "c0",
                        "gens_sha": multicolour._gens_fingerprint(gens),
                        "status": "SAT",
                        "problem": _PROBLEM(n)}], fh)
        with open(f"witness_444_3_n{n}.json", "w") as fh:
            json.dump({"n": n, "sizes": [4, 4, 4], "k": 3,
                       "chi": [0, 1, 2, 0]}, fh)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(climb.subprocess, "run", fake_run)
    assert climb.try_base(n, n, 1200, 60) == n
    assert "WITNESS" in capsys.readouterr().out


# --- a cap that drops classes must not be invisible ------------------------

def test_the_tower_builder_reports_what_the_cap_dropped():
    """`build` returns only the classes under the cap. A caller summarising
    "every class" needs the rest, and before this it could not have them."""
    import make_groups_affine
    under = make_groups_affine.build(53, 53, 800)
    everything = make_groups_affine.build(53, 53, 10 ** 9)
    dropped = []
    again = make_groups_affine.build(53, 53, 800, skipped=dropped)
    assert [g["name"] for g in again] == [g["name"] for g in under]
    assert len(under) + len(dropped) == len(everything)
    assert [d["name"] for d in dropped] == ["Z_53 : C_1"]
    assert dropped[0]["vars"] > 800


def test_an_uncapped_build_drops_nothing():
    """Baseline: `skipped` must not collect classes that were built."""
    import make_groups_affine
    dropped = []
    make_groups_affine.build(53, 53, 10 ** 9, skipped=dropped)
    assert dropped == []


def test_the_sweep_records_the_classes_it_never_built(monkeypatch, tmp_path,
                                                      capsys):
    """A class over the cap appears as a row, so a table built from the output
    cannot read as though the tower had no such class."""
    import json as _json

    import sweep_pdm
    monkeypatch.setattr("sys.argv",
                        ["sweep_pdm.py", "--pmin", "53", "--pmax", "53",
                         "--mmax", "0", "--max-vars", "800", "--cap", "60",
                         "--out", str(tmp_path / "s.json")])
    rc = sweep_pdm.main()
    rows = _json.loads((tmp_path / "s.json").read_text())
    over = [r for r in rows if r["status"] == "OVER_CAP"]
    assert [r["name"] for r in over] == ["Z_53 : C_1"]
    out = capsys.readouterr().out
    assert "never built" in out
    assert "says nothing about" in out
    assert rc in (0, 1)


def test_contradictory_cached_rows_are_not_a_negative_result(
        monkeypatch, tmp_path, capsys):
    """A cache holding the same instance twice, SAT then UNSAT.

    Collapsing rows into a dict lets the later one win, so the SAT is lost and
    the base reports "searched, found nothing" -- a witness turned into a null
    by a stale file."""
    import multicolour
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir()
    gens = [[1, 2, 3, 4, 0]]
    groups = [{"name": "c0", "generators": gens}]
    monkeypatch.setattr(climb.make_groups_affine, "build",
                        lambda *a, **k: groups)
    sha = multicolour._gens_fingerprint(gens)

    def fake_run(argv, **kw):
        out = argv[argv.index("--out") + 1]
        with open(out, "w") as fh:
            json.dump([{"name": "c0", "gens_sha": sha, "status": "SAT",
                        "problem": _PROBLEM(83)},
                       {"name": "c0", "gens_sha": sha, "status": "UNSAT",
                        "problem": _PROBLEM(83)}], fh)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(climb.subprocess, "run", fake_run)
    assert climb.try_base(83, 83, 1200, 60) == "UNDECIDED"
    # The wording is the shared reducer's now: climb no longer has a private
    # contradiction check with its own message.
    assert "holds both SAT and UNSAT" in capsys.readouterr().out


def test_duplicate_rows_that_agree_are_not_refused(monkeypatch, tmp_path):
    """Baseline: a repeated row saying the same thing is not a contradiction,
    or the guard would refuse ordinary resumed runs."""
    import multicolour
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir()
    gens = [[1, 2, 3, 4, 0]]
    groups = [{"name": "c0", "generators": gens}]
    monkeypatch.setattr(climb.make_groups_affine, "build",
                        lambda *a, **k: groups)
    sha = multicolour._gens_fingerprint(gens)

    def fake_run(argv, **kw):
        out = argv[argv.index("--out") + 1]
        with open(out, "w") as fh:
            json.dump([{"name": "c0", "gens_sha": sha, "status": "UNSAT",
                        "problem": _PROBLEM(83)},
                       {"name": "c0", "gens_sha": sha, "status": "UNSAT",
                        "problem": _PROBLEM(83)}], fh)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(climb.subprocess, "run", fake_run)
    assert climb.try_base(83, 83, 1200, 60) is None
