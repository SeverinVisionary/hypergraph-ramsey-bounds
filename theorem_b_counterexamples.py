"""The `p = 1 (mod 4)` counterexamples to Theorem B without its second
hypothesis, produced rather than asserted.

`THEOREMS.md` and `README.md` say that `Z_p : C_{(p-1)/2} + 1 fixed` is
SATISFIABLE for `R(4,4,4;3)` at `p = 13` (n = 14) and `p = 37` (n = 38), and
that is why omitting the `-1 not in H` condition changes the conclusion.
An existential claim needs an object: this builds each class,
solves it, and re-verifies the model from scratch with `multicolour.verify`
before reporting SAT.

    python3 theorem_b_counterexamples.py

Exits non-zero unless every class listed below is SAT and its colouring
verifies, and unless each really does satisfy Theorem B's FIRST hypothesis
(|G| = C(p,2)) while failing the second (-1 in H; within the index-two family,
equivalently p = 1 mod 4) --
a "counterexample" that fails the hypothesis it is meant to satisfy would show
nothing.
"""

from __future__ import annotations

import argparse
import json

import contracts
import sys
from math import comb

from pysat.solvers import Cadical195

import grouporder
import make_groups_affine
import multicolour

# (p, n, class name). n = p + 1: one fixed point adjoined.
CASES = [(13, 14, "Z_13 : C_6 + 1 fixed"),
         (37, 38, "Z_37 : C_18 + 1 fixed")]


def hypotheses(p, order):
    """(satisfies_first, satisfies_second). Theorem B needs both."""
    return order == comb(p, 2), p % 4 == 3


def run_case(p, n, name, sizes=(4, 4, 4), k=3):
    groups = make_groups_affine.build(n, p, 100000)
    matching = [g for g in groups if g["name"] == name]
    if len(matching) != 1:
        return {"p": p, "n": n, "name": name, "status": "ERROR",
                "error": f"{len(matching)} class(es) named {name!r}"}
    gens = matching[0]["generators"]
    order = grouporder.group_order(gens, n)
    # The group acts on n = p + 1 points; Theorem B's |G| is the order of the
    # action on the p points before the fixed point is adjoined, which is the
    # same permutation group -- the fixed point contributes nothing to it.
    first, second = hypotheses(p, order)

    cnf, orbit_of, _var, stats = multicolour.build_cnf(gens, n, list(sizes), k)
    solver = Cadical195(bootstrap_with=cnf)
    sat = solver.solve()
    model = solver.get_model() if sat else None
    solver.delete()
    row = {"p": p, "n": n, "name": name, "order": order,
           "abs_C_p_2": comb(p, 2), "p_mod_4": p % 4,
           "satisfies_first_hypothesis": first,
           "satisfies_second_hypothesis": second,
           "vars": stats["vars"], "clauses": stats["clauses"],
           "status": "SAT" if sat else "UNSAT"}
    if not sat:
        return row
    chi = multicolour.expand(model, orbit_of, n, len(sizes), k)
    ok, detail = multicolour.verify(chi, n, list(sizes), k)
    row["verified"] = bool(ok)
    if not ok:
        row["status"] = "ERROR"
        row["error"] = f"solver said SAT but the model is not a witness: {detail}"
    return row


def problems_with(rows, expect=None):
    """Every reason these rows fail to be Theorem B counterexamples.

    `expect` is the number of counterexamples the deposit claims. An empty
    list of rows has no reason to fail every per-row check below and would
    otherwise pass -- the no-work-is-success shape that certify_nulls,
    crosscheck_n63 and enumerate_n83 each carry a guard against.
    """
    out = []
    if not rows:
        out.append("no classes were run; an empty set of counterexamples "
                   "establishes nothing")
    if expect is not None and len(rows) != expect:
        out.append(f"{len(rows)} class(es) run, expected {expect}")
    for r in rows:
        if r["status"] != "SAT":
            out.append(f"{r['name']}: {r['status']}"
                       + (f" -- {r['error']}" if r.get("error") else "")
                       + "; a counterexample has to be satisfiable")
            continue
        if not r.get("verified"):
            out.append(f"{r['name']}: SAT but the colouring was not verified")
        if not r["satisfies_first_hypothesis"]:
            out.append(f"{r['name']}: |G| = {r['order']} != C({r['p']},2) = "
                       f"{r['abs_C_p_2']}; this class does not satisfy the "
                       f"hypothesis the counterexample is about")
        if r["satisfies_second_hypothesis"]:
            out.append(f"{r['name']}: p = {r['p']} is 3 mod 4, so Theorem B "
                       f"applies with both hypotheses and this SAT class would "
                       f"REFUTE the theorem, not its weakened form")
        # The row's own arithmetic has to hold together. The gate trusted the
        # hypothesis FLAGS and never recomputed the quantities behind them, so
        # a row carrying one prime's p with another prime's n, order and
        # C(p,2) was accepted -- and the suite's own passing baseline was
        # exactly such a row.
        pr = r["p"]
        # DERIVED, not declared. Recomputing the three fields that had been
        # added and then trusting the two booleans that carry the actual claim
        # left the gate accepting rows with order = 1, with p = 3 mod 4, and
        # with composite "primes". One predicate, in contracts.py, is the only
        # thing entitled to say whether the hypotheses hold.
        is_prime, first, second, c_p_2 = contracts.theorem_b_hypotheses(
            pr, r.get("order"))
        if not is_prime:
            out.append(f"{r['name']}: p = {pr} is not prime; Theorem B is "
                       f"about affine groups over a prime field")
        if r.get("satisfies_first_hypothesis") != first:
            out.append(f"{r['name']}: declares "
                       f"satisfies_first_hypothesis="
                       f"{r.get('satisfies_first_hypothesis')!r}, but "
                       f"|G| = {r.get('order')!r} and C({pr},2) = {c_p_2}, "
                       f"so it is {first}")
        if r.get("satisfies_second_hypothesis") != second:
            out.append(f"{r['name']}: declares "
                       f"satisfies_second_hypothesis="
                       f"{r.get('satisfies_second_hypothesis')!r}, but "
                       f"p = {pr} is {pr % 4} mod 4, so it is {second}")
        for field, want in (("n", pr + 1),
                            ("abs_C_p_2", c_p_2),
                            ("p_mod_4", pr % 4)):
            if r.get(field) != want:
                out.append(f"{r['name']}: p = {pr} but {field} = "
                           f"{r.get(field)!r}, not {want}; this row does not "
                           f"describe a single class")
    # Two DISTINCT primes, not one counted twice: the claim is that the
    # conclusion fails across p = 1 mod 4, and one example repeated is one
    # example.
    primes = [r["p"] for r in rows]
    if expect is not None and len(set(primes)) != expect:
        out.append(f"{len(set(primes))} distinct prime(s) among {primes}; "
                   f"the deposit claims {expect} counterexamples")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="theorem_b_counterexamples.json")
    ap.add_argument("--expect", type=int, default=len(CASES), metavar="N",
                    help="fail unless exactly N counterexamples were run")
    a = ap.parse_args()

    rows = []
    for p, n, name in CASES:
        row = run_case(p, n, name)
        rows.append(row)
        print(f"  p={p:<3} n={n:<3} {name:<24} |G|={row.get('order')} "
              f"C(p,2)={row['abs_C_p_2']} p%4={row['p_mod_4']}  "
              f"{row['vars'] if 'vars' in row else '?'} vars  "
              f"{row['status']}"
              + ("  [VERIFIED]" if row.get("verified") else ""), flush=True)

    with open(a.out, "w") as fh:
        json.dump(rows, fh, indent=1)
    print(f"\nwritten to {a.out}")

    problems = problems_with(rows, expect=a.expect)
    if problems:
        print("\nNOT COUNTEREXAMPLES:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"all {len(rows)} of {len(rows)} class(es) satisfy |G| = C(p,2), "
          f"fail -1 not in H, and are SAT with a verified colouring")
    return 0


if __name__ == "__main__":
    sys.exit(main())
