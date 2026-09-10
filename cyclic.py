"""Cyclic (Z_n-invariant) witness search for R(s,t;k).

A colouring is cyclic if the colour of a k-subset depends only on its orbit
under x -> x+1 (mod n). This is the technique behind the neighbouring DS1
7.1(a) entries: Dybizbanski's R(5,5;3) >= 88, R(4,6;3) >= 63 and
R(4,4,4;3) >= 79 are cyclic colourings, and Wesley's block-Cayley colourings
(arXiv:2509.03784) are the same idea with a larger group.

Why it helps: C(35,4) = 52,360 four-subsets collapse to ~1,496 orbits, a 35x
reduction in variables. Why it is not free:

  ** THE RESTRICTION IS INCOMPLETE. **

  A cyclic witness is a witness. But UNSAT here means "no CYCLIC witness on n
  points", NOT "no witness on n points" -- it says nothing about the general
  problem. "0 found" never means "none exists", and under an
  ansatz that is doubly true. Any null from this file must be reported as a
  null of the restricted search, with the restriction named.

Every solution found is expanded to the full C(n,k)-bit colouring and checked
by verify_both on that full object. The orbit representation is a search
device; it is never what gets verified.
"""

from __future__ import annotations

import argparse
import json
import time
from itertools import combinations
from math import comb

from pysat.formula import CNF
from pysat.solvers import Cadical195

from capped import solve_with_deadline, run_capped_out_of_process
from verify import verify_both, verify_lex


def orbit_rep(subset, n):
    """Canonical representative of a subset's orbit under x -> x+1 (mod n)."""
    best = None
    for d in range(n):
        cand = tuple(sorted((x + d) % n for x in subset))
        if best is None or cand < best:
            best = cand
    return best


def build_orbits(n, k):
    """Map every k-subset to an orbit id. Returns (orbit_of, n_orbits)."""
    rep_id, orbit_of = {}, {}
    for sub in combinations(range(n), k):
        r = orbit_rep(sub, n)
        if r not in rep_id:
            rep_id[r] = len(rep_id)
        orbit_of[sub] = rep_id[r]
    # Orbits partition the k-subsets; sizes must sum back.
    assert len(orbit_of) == comb(n, k)
    return orbit_of, len(rep_id)


def build_cyclic_cnf(n, s, t, k):
    orbit_of, n_orb = build_orbits(n, k)
    cnf = CNF()
    seen = set()
    for size, sign in ((s, 1), (t, -1)):
        for clique in combinations(range(n), size):
            lits = sorted({orbit_of[sub] + 1 for sub in combinations(clique, k)})
            key = (sign, tuple(lits))
            if key in seen:
                continue  # same clause under rotation; keep one
            seen.add(key)
            cnf.append([sign * v for v in lits])
    return cnf, orbit_of, n_orb


def expand(model, orbit_of, n, k):
    """Orbit assignment -> full C(n,k)-bit colouring in lex-rank order."""
    val = {}
    for lit in model:
        val[abs(lit)] = 1 if lit > 0 else 0
    chi = [0] * comb(n, k)
    for i, sub in enumerate(combinations(range(n), k)):
        chi[i] = val.get(orbit_of[sub] + 1, 0)
    return chi


def run(n, s, t, k, cap_s, verbose=True):
    # obstruction.py: Z_n-invariant search is provably empty
    # when 5 | n, so refuse the instance instead of spending a budget proving
    # by machine what two lines of group theory already settle.
    if n % 5 == 0 and s == t == 5 and k == 4:
        step = n // 5
        S = [(i * step) % n for i in range(5)]
        raise ValueError(
            f"n={n} is divisible by 5, so NO Z_{n}-invariant witness exists: "
            f"translation by {step} 5-cycles S={S}, making its five 4-faces one "
            f"orbit and forcing S monochromatic. See obstruction.py. "
            f"This is not a budget problem; widen the group instead."
        )

    t0 = time.time()
    cnf, orbit_of, n_orb = build_cyclic_cnf(n, s, t, k)
    build_s = time.time() - t0
    if verbose:
        print(
            f"  cyclic R({s},{t};{k}) n={n}: {n_orb} orbit vars "
            f"(vs {comb(n, k)} full, {comb(n, k)/n_orb:.1f}x), "
            f"{len(cnf.clauses)} clauses, built {build_s:.1f}s",
            flush=True,
        )
    t1 = time.time()
    with Cadical195(bootstrap_with=cnf) as solver:
        status, model = solve_with_deadline(solver, cap_s)
    solve_s = time.time() - t1
    sat = status == "SAT"

    if status == "TIMEOUT":
        if verbose:
            print(
                f"  n={n}: TIMEOUT after {solve_s:.1f}s (cap {cap_s:.1f}s). "
                f"A null of the restricted search under this budget -- it is "
                f"neither UNSAT nor evidence about any witness.",
                flush=True,
            )
        return {"n": n, "status": "TIMEOUT", "solve_s": solve_s,
                "cap_s": cap_s, "orbit_vars": n_orb, "chi": None}

    if not sat:
        if verbose:
            print(
                f"  n={n}: NO CYCLIC WITNESS in {solve_s:.1f}s. "
                f"This is a null of the RESTRICTED search only -- it does not "
                f"bear on whether a general witness exists.",
                flush=True,
            )
        return {"n": n, "status": "UNSAT_CYCLIC", "solve_s": solve_s,
                "orbit_vars": n_orb, "chi": None}

    chi = expand(model, orbit_of, n, k)
    # The ansatz is a search device. Verify the FULL object.
    if not verify_both(n, s, t, k, chi):
        raise AssertionError(
            f"cyclic model expanded to a NON-witness at n={n}: "
            f"{verify_lex(n, s, t, k, chi)!r}"
        )
    if verbose:
        print(
            f"  n={n}: WITNESS FOUND in {solve_s:.1f}s, "
            f"verified on the full {comb(n, k)}-bit colouring "
            f"=> R({s},{t};{k}) >= {n+1}",
            flush=True,
        )
    return {"n": n, "status": "SAT", "solve_s": solve_s,
            "orbit_vars": n_orb, "chi": chi}


def main():
    ap = argparse.ArgumentParser()
    # 35 is NOT in the default ladder: obstruction.py proves no Z_35-invariant
    # witness exists. 30 is out for the same reason. Both now raise if asked
    # for explicitly, rather than burning a budget on a settled question.
    ap.add_argument("--ns", default="31,32,33,34", help="comma-separated n ladder")
    ap.add_argument("--cap", type=float, default=3600.0)
    ap.add_argument("--out", default="cyclic_results.json")
    a = ap.parse_args()

    s, t, k = 5, 5, 4
    print(f"Cyclic ladder for R({s},{t};{k}). Restriction: Z_n-invariant colourings.")
    print("DS1 rev #18 p.73 records 35 <= R(5,5;4) [Ex24], i.e. a witness on 34")
    print("points is known, so n=34 would tie the incumbent.")
    print()
    print("THE TARGET IS OUT OF REACH FOR THIS FILE. No Z_35-invariant witness")
    print("exists (obstruction.py): translation by 7 forces {0,7,14,21,28}")
    print("monochromatic. n=34 is a bound on this technique, not a step to 35.")
    print()

    results = []
    for n in [int(x) for x in a.ns.split(",")]:
        capped = run_capped_out_of_process(
            run, {"n": n, "s": s, "t": t, "k": k, "verbose": True}, a.cap)
        if capped.status == "TIMEOUT":
            print(f"  n={n}: TIMEOUT after {capped.elapsed_s:.1f}s "
                  f"(cap {a.cap:.1f}s) [outer process cap]. A null of the "
                  f"restricted search under this budget -- it is neither "
                  f"UNSAT nor evidence about any witness.", flush=True)
            rec = {"n": n, "status": "TIMEOUT", "solve_s": capped.elapsed_s,
                   "cap_s": a.cap, "orbit_vars": None, "chi": None}
        elif capped.status == "ERROR":
            raise RuntimeError(f"cyclic.run child failed: {capped.detail}")
        else:
            rec = capped.value
        results.append({kk: vv for kk, vv in rec.items() if kk != "chi"})
        if rec["chi"] is not None:
            fn = f"witness_n{n}.json"
            with open(fn, "w") as f:
                json.dump(
                    {"n": n, "s": s, "t": t, "k": k, "cyclic": True,
                     "certifies": f"R({s},{t};{k}) >= {n+1}",
                     "chi": rec["chi"]}, f,
                )
            print(f"    witness written to {fn}", flush=True)
        with open(a.out, "w") as f:
            json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
