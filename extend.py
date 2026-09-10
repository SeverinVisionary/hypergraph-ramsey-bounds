"""Extend a cyclic witness by adding fixed points -- the ladder's workhorse.

THE IDEA.  Let B be a witness on a base of `n` points carrying a Z_n symmetry,
and add `e` further points which the group fixes.  The symmetry group of the
extended object is still Z_n, of order n, so as long as 5 does not divide n the
5'-condition of obstruction.py is satisfied and the ansatz is admissible -- even
though the plain cyclic ansatz on n+e points is not (when 5 | n+e).

That is the whole point.  Z_35 is excluded; Z_33 acting on 33 points with 2
further points fixed is NOT, and it reaches 35 points.

WHAT THE NEW VARIABLES ARE.  Adding one point oo means colouring every 4-subset
that contains oo, i.e. choosing a colour for each 3-subset of the base: the
*link* of oo.  The new constraints are one per base 4-set T -- if T is red then
not all four triples of T may be red, and dually -- which is a width-4 clause,
a strictly easier class than the full problem.

With the base pinned to a known witness, only the link variables are free:

    Z_33 + 1  ->  166 free variables   (a 34-point object)
    Z_33 + 2  ->  348
    Z_32 + 3  ->  514
    Z_31 + 4  ->  675

Run `python3 extend.py --help`.  The solve needs substantially more wall time
and memory than the checks in this package are sized for.
"""

from __future__ import annotations

import argparse
import json
import time
from itertools import combinations
from math import comb

from capped import solve_with_deadline, run_capped_out_of_process
from obstruction import admissible
from verify import verify_both, verify_lex

# Base points are ints 0..n-1; added points are n, n+1, ...


def _orbit_rep(face, n):
    """Canonical rep of a face under the base translation, added points fixed."""
    best = None
    for sh in range(n):
        cand = tuple(sorted((v + sh) % n if v < n else v for v in face))
        if best is None or cand < best:
            best = cand
    return best


def build_extension(base_n, extra, chi_base=None, s=5, t=5, k=4):
    """CNF for a Z_base_n-invariant witness on base_n + extra points.

    `chi_base` pins the base colouring to a known witness (its C(base_n,k)-bit
    vector, in lexicographic order on the base).  Pass None to leave the base
    free, which is the "joint" form of the instance.

    Returns (clauses, var_of, n_free, n_fixed).  `var_of` maps an orbit
    representative to a positive variable index; pinned orbits are absent.
    """
    # ONLY for the problem the obstruction is about. `admissible` encodes the
    # 5-divisibility argument of obstruction.py, which is a statement about the
    # DIAGONAL (5,5;4) cell -- not about every (s,t,k) this builder accepts.
    # Applied unconditionally it rejected genuine input: a C_5-invariant good
    # 2-colouring of the edges of K_5 with no monochromatic triangle is a valid
    # base for (3,3;2), and this function refused it. The generic parameters
    # are part of the interface, so the obstruction has to be guarded by the
    # hypotheses that justify it rather than applied to all of them.
    if (s, t, k) == (5, 5, 4) and not admissible(base_n):
        raise ValueError(
            f"base {base_n} is divisible by 5, so for the (5,5;4) problem "
            f"Z_{base_n} already forces a monochromatic clique "
            f"(obstruction.py). Pick a 5'-base."
        )
    total = base_n + extra
    points = list(range(total))

    # Group the faces into orbits, and record which are base-only.
    orbit_of = {}
    reps = []
    for face in combinations(points, k):
        rep = _orbit_rep(face, base_n)
        if rep not in orbit_of:
            orbit_of[rep] = len(reps)
            reps.append(rep)
        orbit_of[face] = orbit_of[rep]

    base_face_index = {f: i for i, f in enumerate(combinations(range(base_n), k))}

    def is_base_only(rep):
        return max(rep) < base_n

    # Assign variables to free orbits only; pinned orbits become constants.
    fixed_value = {}
    var_of = {}
    if chi_base is not None:
        if len(chi_base) != comb(base_n, k):
            raise ValueError(
                f"chi_base has {len(chi_base)} bits, expected C({base_n},{k})="
                f"{comb(base_n, k)}"
            )
        # The pin is applied ONE COLOUR PER ORBIT, taken from the orbit's
        # representative. If the supplied base is not itself Z_base_n-
        # invariant, that silently REPLACES it with a different colouring --
        # the projection of the supplied one onto the invariant colourings --
        # and a subsequent "no witness extends this base" would be about the
        # projection, not about the base that was handed in. So invariance is
        # checked, not assumed.
        disagree = []
        for face, oid in orbit_of.items():
            if max(face) >= base_n or len(face) != k:
                continue
            rep = reps[oid]
            if not is_base_only(rep):
                continue
            if chi_base[base_face_index[face]] != chi_base[base_face_index[rep]]:
                disagree.append((face, rep))
        if disagree:
            face, rep = disagree[0]
            raise ValueError(
                f"chi_base is not Z_{base_n}-invariant: {len(disagree)} base "
                f"face(s) differ from their orbit representative, e.g. {face} "
                f"is colour {chi_base[base_face_index[face]]} while {rep}, in "
                f"the same translation orbit, is "
                f"{chi_base[base_face_index[rep]]}. Pinning would impose the "
                f"representative's colour on the whole orbit and silently "
                f"change the base you supplied.")
        for rep in reps:
            if is_base_only(rep):
                fixed_value[rep] = chi_base[base_face_index[rep]]
    nxt = 1
    for rep in reps:
        if rep not in fixed_value:
            var_of[rep] = nxt
            nxt += 1

    def literal(face, positive):
        rep = reps[orbit_of[face]]
        if rep in fixed_value:
            return ("CONST", fixed_value[rep])
        v = var_of[rep]
        return ("VAR", v if positive else -v)

    clauses = []
    n_s = n_t = 0
    for clique in combinations(points, s):
        lits, satisfied = [], False
        for sub in combinations(clique, k):
            kind, val = literal(sub, True)
            if kind == "CONST":
                if val == 1:          # a face already coloured 1 satisfies
                    satisfied = True  # "not all 0"
                    break
            else:
                lits.append(val)
        n_s += 1
        if satisfied:
            continue
        if not lits:
            raise AssertionError(
                f"pinned base already contains an all-0 clique {clique}: the "
                f"supplied base is not a witness"
            )
        clauses.append(sorted(set(lits)))

    for clique in combinations(points, t):
        lits, satisfied = [], False
        for sub in combinations(clique, k):
            kind, val = literal(sub, False)
            if kind == "CONST":
                if val == 0:
                    satisfied = True
                    break
            else:
                lits.append(val)
        n_t += 1
        if satisfied:
            continue
        if not lits:
            raise AssertionError(
                f"pinned base already contains an all-1 clique {clique}: the "
                f"supplied base is not a witness"
            )
        clauses.append(sorted(set(lits)))

    # §6 completeness: every clique of each size was considered exactly once.
    assert n_s == comb(total, s), (n_s, comb(total, s))
    assert n_t == comb(total, t), (n_t, comb(total, t))

    # Translates of a base clique give literally the same clause, because both
    # the variables and the pinned colours are Z_base_n-invariant. At
    # base_n=33, extra=1 every orbit of base 4-sets has full size 33 (a
    # non-trivial stabiliser would have order dividing both 33 and 4), so the
    # 40920 clauses collapse to 40920/33 = 1240 distinct ones over 166
    # variables -- density 7.5, not the 246 the raw count suggests. Reporting
    # the raw number made these instances look far more constrained than they
    # are, which is part of why four timeouts here read as normal.
    deduped = sorted({tuple(c) for c in clauses})
    return [list(c) for c in deduped], var_of, len(var_of), len(fixed_value)


def expand(model, var_of, base_n, extra, chi_base, k=4):
    """Expand an orbit model to the full C(base_n+extra, k)-bit colouring."""
    total = base_n + extra
    assign = {}
    if model is not None:
        for lit in model:
            assign[abs(lit)] = 1 if lit > 0 else 0
    base_face_index = {f: i for i, f in enumerate(combinations(range(base_n), k))}

    chi = []
    for face in combinations(range(total), k):
        rep = _orbit_rep(face, base_n)
        if rep in var_of:
            chi.append(assign.get(var_of[rep], 0))
        else:
            chi.append(chi_base[base_face_index[rep]])
    return chi


def run(base_n, extra, chi_base, cap_s, s=5, t=5, k=4, verbose=True):
    from pysat.formula import CNF
    from pysat.solvers import Cadical195

    total = base_n + extra
    t0 = time.time()
    clauses, var_of, n_free, n_fixed = build_extension(base_n, extra, chi_base, s, t, k)
    build_s = time.time() - t0
    if verbose:
        print(
            f"  Z_{base_n} + {extra} fixed -> {total} points: {n_free} free orbit "
            f"vars ({n_fixed} pinned), {len(clauses)} clauses, built {build_s:.1f}s",
            flush=True,
        )

    cnf = CNF()
    for c in clauses:
        cnf.append(c)

    t1 = time.time()
    with Cadical195(bootstrap_with=cnf) as solver:
        status, model = solve_with_deadline(solver, cap_s)
    solve_s = time.time() - t1

    if status == "TIMEOUT":
        if verbose:
            print(f"  {total} points: TIMEOUT after {solve_s:.1f}s (cap {cap_s:.1f}s)"
                  f" -- a null under this budget, not a verdict.", flush=True)
        return {"n": total, "base": base_n, "extra": extra, "status": "TIMEOUT",
                "solve_s": solve_s, "cap_s": cap_s, "free_vars": n_free, "chi": None}

    if status == "UNSAT":
        if verbose:
            print(
                f"  {total} points: NO witness extending this base under Z_{base_n}. "
                f"({solve_s:.1f}s) This is a null of the RESTRICTED search with the "
                f"base PINNED -- it bears on neither other bases nor the general "
                f"problem.", flush=True)
        return {"n": total, "base": base_n, "extra": extra, "status": "UNSAT_PINNED",
                "solve_s": solve_s, "free_vars": n_free, "chi": None}

    chi = expand(model, var_of, base_n, extra, chi_base, k)
    if not verify_both(total, s, t, k, chi):
        raise AssertionError(
            f"extension model is NOT a witness at n={total}: "
            f"{verify_lex(total, s, t, k, chi)!r}"
        )
    if verbose:
        print(
            f"  {total} points: WITNESS FOUND in {solve_s:.1f}s, verified on the "
            f"full {comb(total, k)}-bit colouring => R({s},{t};{k}) >= {total+1}",
            flush=True,
        )
    return {"n": total, "base": base_n, "extra": extra, "status": "SAT",
            "solve_s": solve_s, "free_vars": n_free, "chi": chi}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", type=int, required=True, help="base size, e.g. 33")
    ap.add_argument("--extra", type=int, required=True, help="points to add")
    ap.add_argument("--witness", help="JSON witness pinning the base; omit to leave free")
    ap.add_argument("--cap", type=float, default=1800.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    chi_base = None
    if a.witness:
        with open(a.witness) as f:
            chi_base = json.load(f)["chi"]

    total = a.base + a.extra
    capped = run_capped_out_of_process(
        run, {"base_n": a.base, "extra": a.extra, "chi_base": chi_base,
              "s": 5, "t": 5, "k": 4, "verbose": True}, a.cap)
    if capped.status == "TIMEOUT":
        print(f"  {total} points: TIMEOUT after {capped.elapsed_s:.1f}s "
              f"(cap {a.cap:.1f}s) [outer process cap] -- a null under this "
              f"budget, not a verdict.", flush=True)
        rec = {"n": total, "base": a.base, "extra": a.extra, "status": "TIMEOUT",
               "solve_s": capped.elapsed_s, "cap_s": a.cap, "chi": None}
    elif capped.status == "ERROR":
        raise RuntimeError(f"extend.run child failed: {capped.detail}")
    else:
        rec = capped.value

    results_fn = "extend_results.json"
    try:
        with open(results_fn) as f:
            results = json.load(f)
    except FileNotFoundError:
        results = []
    results.append({kk: vv for kk, vv in rec.items() if kk != "chi"})
    with open(results_fn, "w") as f:
        json.dump(results, f, indent=2)

    if rec["status"] == "SAT":
        fn = a.out or f"witness_n{rec['n']}.json"
        with open(fn, "w") as f:
            json.dump({"n": rec["n"], "s": 5, "t": 5, "k": 4,
                       "ansatz": f"Z_{a.base} + {a.extra} fixed points",
                       "certifies": f"R(5,5;4) >= {rec['n']+1}",
                       "chi": rec["chi"]}, f)
        print(f"    witness written to {fn}", flush=True)
    print(json.dumps({kk: vv for kk, vv in rec.items() if kk != "chi"}, indent=2))


if __name__ == "__main__":
    main()
