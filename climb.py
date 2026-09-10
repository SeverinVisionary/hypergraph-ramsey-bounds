"""Climb the R(4,4,4;3) ladder across several affine bases at once.

One base is not enough. The `Z_79 + fixed points` tower carried 79, 80 and 81
and then stalled: at n=82 its C_13 class is UNSAT and its C_6 class ran an hour
without deciding. Rebasing on p=73 with 9 fixed points found a witness at n=82
in 185 s. So the useful unit of work is "try every base at this n", not "descend
one tower".

    python3 climb.py --n 83 --bases 83,79,73,71 --max-vars 1200

Stops at the first witness for each n and reports which base produced it.
"""

import argparse
import json
import os
import subprocess
import sys

import make_groups_affine
import ansatz
import contracts
import multicolour


def try_base(n, p, max_vars, cap):
    over_cap = []
    groups = make_groups_affine.build(n, p, max_vars, skipped=over_cap)
    if over_cap:
        print(f"  p={p}: {len(over_cap)} class(es) are over the {max_vars}-"
              f"variable cap and were not built; nothing below is a statement "
              f"about them", flush=True)
    if not groups:
        # NOT None. None means "searched, found nothing", and the caller
        # reports that as a completed negative search. Nothing was searched
        # here: with --max-vars small enough every base takes this branch and
        # the climb would print "all bases ran" having run no solver at all.
        print(f"  p={p}: no class under {max_vars} variables -- nothing to "
              f"search, not a result about n={n}", flush=True)
        return "EMPTY"
    gf = f"g{n}_p{p}.json"
    json.dump(groups, open(gf, "w"), indent=1)
    out = f"cell_444_3_n{n}_p{p}.json"
    log = f"logs/n{n}_p{p}.log"
    print(f"  p={p}: {len(groups)} classes -> {gf}", flush=True)
    w = f"witness_444_3_n{n}.json"

    # Three things stand between a crashed child and a reported witness, and
    # for a while none of them did: the search reported WITNESS whenever the
    # target path existed, so a stale file from an earlier base plus a
    # multicolour.py that died on startup produced a clean success line.
    before = os.path.getmtime(w) if os.path.exists(w) else None

    with open(log, "w") as fh:
        rc = subprocess.run([sys.executable, "-u", "multicolour.py",
                             "--groups", gf, "--n", str(n), "--sizes", "4,4,4",
                             "--k", "3", "--cap", str(cap), "--out", out],
                            stdout=fh, stderr=subprocess.STDOUT).returncode
    if rc != 0:
        print(f"  p={p}: multicolour.py exited {rc}; see {log}", flush=True)
        return "ERROR"

    # Did the child DECIDE anything? multicolour.py records a TIMEOUT row and
    # exits 0 -- a budget expiring is not an error there -- so a base every one
    # of whose classes timed out reaches this point looking exactly like a base
    # that searched and found nothing. Only the output file tells them apart,
    # and the difference is the whole content of the negative result this
    # function feeds. sweep_pdm.py refuses an undecided cell for the same
    # reason; this refuses an undecided base.
    if not os.path.exists(out):
        print(f"  p={p}: {out} was never written; nothing was decided",
              flush=True)
        return "UNDECIDED"
    with open(out) as fh:
        rows = json.load(fh)

    # The rows have to BE the classes that were generated, not merely some
    # rows. Counting decided rows is not coverage: a child that wrote one UNSAT
    # row for a two-class tower leaves this function reporting a searched base.
    # Bound by (name, gens_sha), because a name is a label -- the same binding
    # ansatz._resume and certify_nulls.gate use.
    want = {(g["name"], multicolour._gens_fingerprint(g["generators"]))
            for g in groups}
    # The problem, on the NEGATIVE path too. This bound rows by
    # (name, gens_sha) alone, so correctly fingerprinted UNSAT rows for a
    # DIFFERENT question -- R(2,2;1) on the same points -- made try_base
    # return None, i.e. "searched this base and found nothing", while the
    # class in fact holds a good invariant colouring. The witness checks below
    # never run on that path.
    here = contracts.problem_identity({"n": n, "sizes": [4, 4, 4], "k": 3})
    for r in rows:
        rid = contracts.row_problem_identity(r)
        if rid != here:
            print(f"  p={p}: a row in {out} records {rid} but this climb is "
                  f"solving {here}; nothing here is a result about n={n}",
                  flush=True)
            return "UNDECIDED"

    # The shared reducer first: climb kept a private one keyed by
    # (name, gens_sha), so contradictory rows under different aliases were
    # accepted here while contracts.reduce_history rejected the same history.
    try:
        contracts.reduce_history(rows, want_problem={"n": n, "sizes": [4, 4, 4],
                                                     "k": 3})
    except contracts.Contradiction as exc:
        print(f"  p={p}: {out}: {exc}", flush=True)
        return "UNDECIDED"

    got = {}
    for r in rows:
        key = (r.get("name"), r.get("gens_sha"))
        if key[1] is None:
            print(f"  p={p}: a row in {out} carries no gens_sha; it names a "
                  f"class but does not identify one", flush=True)
            return "UNDECIDED"
        # Collapsing rows into a dict lets a later row overwrite an earlier
        # one. If the two disagree, the overwrite silently picks a verdict --
        # a cached SAT followed by an UNSAT for the SAME instance would be
        # read as "searched and found nothing", turning a witness into a null.
        # A TIMEOUT is not a verdict. Treating any difference as a
        # contradiction meant a class that timed out and was later DECIDED
        # read as a corrupt cache and forced a fresh run -- the opposite
        # error to the one this check exists for. Only two genuine verdicts
        # that disagree are a contradiction.
        VERDICTS = ("SAT", "UNSAT", "EMPTY")
        st = r.get("status")
        if key in got and got[key] != st:
            if got[key] in VERDICTS and st in VERDICTS:
                print(f"  p={p}: {out} holds contradictory rows for "
                      f"{key[0]}: {got[key]} and {st}. Nothing here "
                      f"is a result about n={n}; point --out at a fresh file",
                      flush=True)
                return "UNDECIDED"
            # One of them is TIMEOUT/ERROR: the decision supersedes it.
            if st not in VERDICTS:
                continue
        got[key] = st
    sat = sorted(name for (name, _), st in got.items() if st == "SAT")
    # Keep the IDENTITY of the SAT class, not just its label: the witness is
    # attributed to that class, so the check below needs its generators.
    sat_keys = sorted(key for key, st in got.items() if st == "SAT")
    extra = set(got) - want
    if extra:
        print(f"  p={p}: {out} holds {len(extra)} row(s) for class(es) this "
              f"run did not generate -- not a result about n={n}", flush=True)
        return "UNDECIDED"

    # A SAT row means this base HAS a witness, and multicolour.py stops at the
    # first one -- so the later classes legitimately have no rows, and full
    # coverage must not be demanded here. Everything below this point is about
    # the witness object, and none of it may return None: "no witness" is a
    # claim this base has already contradicted.
    if sat:
        if not os.path.exists(w):
            print(f"  p={p}: {out} records {sat[0]} SAT but {w} does not "
                  f"exist; the witness object is missing", flush=True)
            return "UNDECIDED"
        if before is not None and os.path.getmtime(w) == before:
            # The child skips a class already decided in --out, so a cached SAT
            # row plus the witness it produced earlier looks exactly like this.
            # It is still not a null: reporting "no witness" here would turn a
            # find into a negative result.
            print(f"  p={p}: {out} records {sat[0]} SAT and {w} is unchanged "
                  f"from before this run -- this base has a witness, but not "
                  f"one this run produced; re-run against a fresh --out",
                  flush=True)
            return "UNDECIDED"
    else:
        missing = want - set(got)
        if missing:
            print(f"  p={p}: {out} covers {len(got)} of the {len(want)} "
                  f"generated class(es) and none is SAT -- an incomplete "
                  f"search, not a result about n={n}", flush=True)
            return "UNDECIDED"
        undecided = sorted(name for (name, _), st in got.items()
                           if st not in ("UNSAT", "EMPTY"))
        if undecided:
            print(f"  p={p}: {len(undecided)} of {len(want)} class(es) "
                  f"undecided ({', '.join(undecided[:3])}); this base is not "
                  f"exhausted", flush=True)
            return "UNDECIDED"
        if os.path.exists(w) and before is not None and \
                os.path.getmtime(w) == before:
            # No SAT row and an untouched witness file from an earlier base:
            # this base decided everything and found nothing, which is a real
            # null. The stale file says nothing about it either way.
            pass
        return None

    # The child already verifies before writing. Verify again here anyway: this
    # function's return value is what the climb reports, so it should not rest
    # on another process's word about a file on disk.
    with open(w) as fh:
        doc = json.load(fh)
    # Neither branch below returns None. The child recorded SAT for this base,
    # so "searched, found nothing" is already contradicted; what these catch is
    # a witness object that does not match the claim, and that is a broken
    # result, not a null.
    # The witness is verified against the problem THIS CLIMB IS SOLVING, not
    # against the one the file declares. Reading `sizes` and `k` back out of
    # the document and passing them to the verifier makes the check circular:
    # a file claiming sizes [5,5,5] verifies vacuously as an R(5,5,5;3)
    # colouring while failing R(4,4,4;3), and this function would report it as
    # a re-verified witness for the bound being climbed.
    want = {"n": n, "sizes": [4, 4, 4], "k": 3}
    for field, expected in want.items():
        if doc.get(field) != expected:
            print(f"  p={p}: {w} records {field}={doc.get(field)!r}, but this "
                  f"climb is solving {field}={expected!r}", flush=True)
            return "UNDECIDED"
    # UNPACKED, deliberately. multicolour.verify returns (ok, detail), and a
    # non-empty tuple is always truthy, so `if not multicolour.verify(...)`
    # is always False and the rejection below would be unreachable.
    # test_climb_accepts_only_verified.py drives this branch to a rejection.
    ok, detail = multicolour.verify(doc["chi"], n, [4, 4, 4], 3)
    if not ok:
        print(f"  p={p}: {w} does NOT verify: {detail}", flush=True)
        return "UNDECIDED"

    # GOOD is not INVARIANT. multicolour.verify establishes only that the
    # colouring has no monochromatic K_4^(3) -- an ordinary Ramsey fact about
    # the object. This function then reports it as a witness FOR THE NAMED
    # SYMMETRY CLASS, and that is a strictly stronger claim: a good but
    # non-invariant colouring, paired with a SAT row carrying the class's
    # correct generator fingerprint, was accepted and printed as re-verified.
    # The colouring must be constant on the orbits of the very generators the
    # row is bound to.
    by_key = {(g["name"], multicolour._gens_fingerprint(g["generators"])): g
              for g in groups}
    for key in sat_keys:
        g = by_key.get(key)
        if g is None:
            print(f"  p={p}: {out} records {key[0]} SAT but no generated "
                  f"class matches its fingerprint", flush=True)
            return "UNDECIDED"
        if not ansatz.is_invariant(doc["chi"], g["generators"], n, 3):
            print(f"  p={p}: {w} is a good colouring but is NOT invariant "
                  f"under {key[0]}; it is not a witness for that class",
                  flush=True)
            return "UNDECIDED"

    print(f"  p={p}: WITNESS at n={n} -> {w} "
          f"(re-verified: good AND invariant under {sat[0]})", flush=True)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--bases", default="83,79,73,71,67")
    ap.add_argument("--max-vars", type=int, default=1200)
    ap.add_argument("--cap", type=int, default=1800)
    a = ap.parse_args()

    print(f"n={a.n}, bases {a.bases}, max {a.max_vars} vars, cap {a.cap}s",
          flush=True)
    broken, searched, skipped, undecided = [], 0, [], []
    for p in [int(x) for x in a.bases.split(",")]:
        if p > a.n:
            skipped.append(p)
            continue
        out = try_base(a.n, p, a.max_vars, a.cap)
        if out == "ERROR":
            broken.append(p)
        elif out == "EMPTY":
            skipped.append(p)
        elif out == "UNDECIDED":
            undecided.append(p)
        else:
            searched += 1
            if out:
                return 0

    # "No witness found" and "the search did not run" must not share an exit
    # status: a climb whose children died reports the same thing as a completed
    # negative search, and the negative is what gets written down.
    if broken:
        print(f"n={a.n}: NO RESULT -- base(s) {broken} failed to run; this is "
              f"not a statement about n={a.n}", flush=True)
        return 1
    if undecided:
        print(f"n={a.n}: NO RESULT -- base(s) {undecided} left classes "
              f"undecided under the {a.cap}s cap; a budget expiring is not a "
              f"null", flush=True)
        return 1
    if not searched:
        print(f"n={a.n}: NO RESULT -- no base ran a search (skipped {skipped}); "
              f"an empty climb is not a negative result", flush=True)
        return 1
    print(f"n={a.n}: no witness from {searched} base(s) searched, over the "
          f"classes at or under {a.max_vars} variables"
          + (f"; {skipped} had no class under that cap" if skipped else ""),
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
