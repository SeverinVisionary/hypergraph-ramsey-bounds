"""Group-invariant search with MORE THAN TWO COLOURS.

`ansatz.py` handles two colours, which covers four of the six DS1 §7.1(a)
cells. The other two are multicolour and much less picked over:

    79  <= R(4,4,4;3)    [Dyb3]     3 colours, 3-uniform  -> needs 78 points
    163 <= R(5,5,5;3)    [BudHR1]   3 colours, 3-uniform  -> needs 162 points

ENCODING. One Boolean per (orbit, colour): x[i][c] says "orbit i takes colour
c". Exactly-one constraints per orbit (one at-least-one clause, and pairwise
at-most-one). For each colour c and each s_c-subset W, forbid W being entirely
colour c: the clause OR_f NOT x[orbit(f)][c] over the faces of W. As in the
two-colour case the clause depends only on the SET of orbits W's faces meet,
so it is deduplicated on that set.

With m = 2 this must reproduce `ansatz.py` exactly; `test_multicolour.py`
requires it on cases where both can run, which is what makes this file
trustworthy rather than merely plausible.

NOT the same as running two colours twice. A three-colouring avoiding K_4 in
every colour is a genuinely harder object, and the exactly-one constraints are
what carry that.
"""

from __future__ import annotations

import argparse
import json

import contracts
import sys
import time
from itertools import combinations
from math import comb

from ansatz import distinct_orbit_sets, face_orbits


def build_cnf(gens, n, sizes, k):
    """CNF for a G-invariant m-colouring avoiding K_{sizes[c]} in colour c.

    Returns (clauses, orbit_of, var, stats) where var(i, c) is the 1-based
    variable for "orbit i has colour c".
    """
    m = len(sizes)
    if m < 2:
        raise ValueError("need at least two colours")
    orbit_of, orbit_sizes = face_orbits(gens, n, k)
    v = len(orbit_sizes)

    def var(i, c):
        return i * m + c + 1

    clauses = []
    for i in range(v):                          # exactly one colour per orbit
        clauses.append([var(i, c) for c in range(m)])
        for c1 in range(m):
            for c2 in range(c1 + 1, m):
                clauses.append([-var(i, c1), -var(i, c2)])
    n_exactly_one = len(clauses)

    # Colours with the SAME clique size walk the same C(n,s) sets and produce
    # the same orbit-sets, so compute each distinct size once. R(4,4,4;3) at
    # n=79 is 1,502,501 four-sets; doing that three times over is 30 wasted
    # seconds per group across a whole sweep.
    # Use the translation shortcut when the group actually has it -- checked,
    # never assumed, since a group with fixed points does not and the shortcut
    # would then silently drop clauses.
    from grouporder import has_all_translations
    fast = has_all_translations(gens, n)

    by_size = {}
    for s in set(sizes):
        by_size[s] = distinct_orbit_sets(orbit_of, n, s, k, translations=fast)

    per_colour = []
    for c, s in enumerate(sizes):
        seen = by_size[s]
        per_colour.append(len(seen))
        for S in seen:
            clauses.append(sorted(-var(i, c) for i in S))

    # A singleton orbit-set is an s-set whose every k-face lies in ONE orbit.
    # It emits the unit clause -x[o,c], and it does so for EVERY colour whose
    # clique size is s. When all m colours share that size -- the diagonal
    # R(4,4,4;3) case -- orbit o is barred from all m colours while the
    # exactly-one clause demands it take one, so the class is empty before the
    # solver starts. Such a class is not a null worth recording: nothing could
    # ever have lived in it.
    #
    # This matters because these instances look like meaningful results. The
    # Z_73 : C_72 + 9 fixed tower at n=82 reports UNSAT at 426 variables in
    # under a tenth of a second, which reads as a searched-and-empty class and
    # is nothing of the kind.
    barred = {}
    for c, s in enumerate(sizes):
        for S in by_size[s]:
            if len(S) == 1:
                barred.setdefault(next(iter(S)), set()).add(c)
    dead = sorted(o for o, cols in barred.items() if len(cols) == m)

    stats = {"empty_by_construction": dead,
             "n": n, "k": k, "sizes": list(sizes), "colours": m,
             "orbits": v, "vars": v * m, "clauses": len(clauses),
             "exactly_one_clauses": n_exactly_one,
             "distinct_per_colour": per_colour,
             "cliques": [comb(n, s) for s in sizes],
             "collapse": [round(comb(n, s) / max(d, 1), 1)
                          for s, d in zip(sizes, per_colour)],
             "translation_fast_path": fast}
    return clauses, orbit_of, var, stats


def expand(model, orbit_of, n, m, k):
    """Model -> a colour in 0..m-1 for every k-subset, lex order."""
    true = {lit for lit in (model or []) if lit > 0}
    colour_of = {}
    for lit in true:
        i, c = divmod(lit - 1, m)
        colour_of[i] = c
    return [colour_of.get(orbit_of[f], 0) for f in combinations(range(n), k)]


def verify(chi, n, sizes, k):
    """Independent check: no s_c-set is entirely colour c. Returns (ok, detail)."""
    idx = {f: i for i, f in enumerate(combinations(range(n), k))}
    if len(chi) != len(idx):
        return False, f"chi has {len(chi)} entries, expected {len(idx)}"
    if not set(chi) <= set(range(len(sizes))):
        return False, f"colours out of range: {sorted(set(chi))}"
    for c, s in enumerate(sizes):
        for W in combinations(range(n), s):
            if all(chi[idx[f]] == c for f in combinations(W, k)):
                return False, f"{W} is entirely colour {c}"
    return True, (f"n={n}: no K_{sizes} monochromatic in its own colour "
                  f"=> R({','.join(map(str, sizes))};{k}) >= {n + 1}")


def run(name, gens, n, sizes, k, cap_s=600.0, verbose=True):
    # A finite cap has to be enforced by something that does not need the
    # solver's cooperation. solve_with_deadline() now REFUSES a cap it cannot
    # keep rather than silently running unbounded, so route the request to the
    # child-process deadline instead of handing the caller an error. The child
    # is invoked with cap_s=None by run_capped_out_of_process, so this does not
    # recurse.
    if cap_s is not None:
        from capped import run_capped_out_of_process
        _kw = dict({"name": name, "gens": gens, "n": n, "sizes": sizes, "k": k, "verbose": verbose})
        capped = run_capped_out_of_process(run, _kw, cap_s)
        if capped.status == "TIMEOUT":
            return {"name": name, "status": "TIMEOUT",
                    "solve_s": round(capped.elapsed_s, 2), "cap_s": cap_s,
                    "chi": None, "vars": None, "clauses": None}
        if capped.status == "ERROR":
            raise RuntimeError(f"{name}: capped child failed: {capped.detail}")
        return capped.value

    from pysat.formula import CNF
    from pysat.solvers import Cadical195
    from capped import solve_with_deadline

    t0 = time.time()
    clauses, orbit_of, _, stats = build_cnf(gens, n, sizes, k)
    build_s = time.time() - t0
    if verbose:
        print(f"  {name}: {stats['orbits']} orbits x {stats['colours']} colours "
              f"= {stats['vars']} vars, {stats['clauses']} clauses, "
              f"built {build_s:.1f}s", flush=True)

    cnf = CNF()
    for c in clauses:
        cnf.append(c)
    t1 = time.time()
    with Cadical195(bootstrap_with=cnf) as solver:
        status, model = solve_with_deadline(solver, cap_s)
    solve_s = time.time() - t1

    rec = {"name": name, "status": status, "solve_s": round(solve_s, 2),
           "build_s": round(build_s, 2), "chi": None, **stats}
    if status == "SAT":
        chi = expand(model, orbit_of, n, len(sizes), k)
        ok, detail = verify(chi, n, sizes, k)
        if not ok:
            raise AssertionError(f"{name}: model is NOT a witness -- {detail}")
        rec["chi"] = chi
        if verbose:
            print(f"    WITNESS: {detail} ({solve_s:.1f}s)", flush=True)
    elif verbose:
        word = ("no witness in this symmetry class (a null for THIS class only)"
                if status == "UNSAT" else "TIMEOUT -- a null under this budget")
        print(f"    {word} ({solve_s:.1f}s)", flush=True)
    return rec



from capped import run_capped_out_of_process


def _gens_fingerprint(gens):
    """SHA-256 of the generator list, canonically encoded.

    The problem key below records n, s, t, k -- the QUESTION. This records the
    GROUP. Both are needed. Matching a cached row by group name alone lets a
    run at different Ramsey parameters reuse it, and matching by parameters
    alone is no better: a group's name is a label a human chose, and the same
    label can be attached to a different generator list.

    The FULL 64-character digest, not a prefix. The docstring says SHA-256 and
    a truncation would make that false; the rows that carry this value are the
    binding between a claim and the group it is about.
    """
    import hashlib
    canon = json.dumps([list(map(int, g)) for g in gens], separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def _problem_key(**kw):
    """Canonical identity of the instance a cached row belongs to."""
    return {k: (list(v) if isinstance(v, (list, tuple)) else v)
            for k, v in sorted(kw.items())}


def _resume(results, problem, groups, path):
    """Delegates to contracts.resume -- see there. Both engines share one body
    so that their resume semantics cannot differ."""
    return contracts.resume(results, problem, groups, path, _gens_fingerprint)

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--groups", required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--sizes", required=True,
                    help="comma-separated clique size per colour, e.g. 4,4,4")
    ap.add_argument("--k", type=int, required=True)
    ap.add_argument("--cap", type=float, default=600.0)
    ap.add_argument("--out", default="multicolour_results.json")
    a = ap.parse_args()

    sizes = [int(x) for x in a.sizes.split(",")]
    with open(a.groups) as f:
        groups = json.load(f)
    print(f"R({','.join(map(str,sizes))};{a.k}) at n={a.n}: "
          f"{len(groups)} group(s), cap {a.cap:.0f}s each", flush=True)

    try:
        with open(a.out) as f:
            results = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        results = []
    problem = _problem_key(n=a.n, sizes=sizes, k=a.k)
    done = _resume(results, problem, groups, a.out)

    for g in groups:
        if (g["name"], _gens_fingerprint(g["generators"])) in done:
            continue
        # The cap is enforced by the OS, not by the solver. run()'s own cap_s
        # goes to solve_with_deadline, which asks Cadical195 to interrupt
        # itself -- and that raises NotImplementedError under python-sat
        # >= 1.9.dev15, so the timer thread dies silently and the solve runs
        # to completion regardless. --cap was advertised and unenforced on
        # this path; the child-process deadline does not need the solver to
        # cooperate. (see capped.run_capped_out_of_process)
        capped = run_capped_out_of_process(
            run, {"name": g["name"], "gens": g["generators"], "n": a.n,
                  "sizes": sizes, "k": a.k, "verbose": True}, a.cap)
        if capped.status == "TIMEOUT":
            print(f"  {g['name']}: TIMEOUT after {capped.elapsed_s:.1f}s "
                  f"(cap {a.cap:.0f}s) [outer process cap] -- a null under "
                  f"this budget, not a verdict.", flush=True)
            rec = {"name": g["name"], "status": "TIMEOUT",
                   "solve_s": round(capped.elapsed_s, 2), "cap_s": a.cap,
                   "vars": None, "clauses": None, "chi": None}
        elif capped.status == "ERROR":
            raise RuntimeError(f"multicolour.run child failed on "
                               f"{g['name']}: {capped.detail}")
        else:
            rec = capped.value
        rec["order"] = g.get("order")
        row = {kk: vv for kk, vv in rec.items() if kk != "chi"}
        row["problem"] = problem
        row["gens_sha"] = _gens_fingerprint(g["generators"])
        results.append(row)
        with open(a.out, "w") as f:
            json.dump(results, f, indent=1)
        if rec["status"] == "SAT":
            fn = f"witness_{''.join(map(str,sizes))}_{a.k}_n{a.n}.json"
            with open(fn, "w") as f:
                json.dump({"n": a.n, "sizes": sizes, "k": a.k,
                           "ansatz": g["name"], "order": g.get("order"),
                           "certifies": f"R({','.join(map(str,sizes))};{a.k}) >= {a.n+1}",
                           "chi": rec["chi"]}, f)
            print(f"    written to {fn}", flush=True)
            break


if __name__ == "__main__":
    main()
