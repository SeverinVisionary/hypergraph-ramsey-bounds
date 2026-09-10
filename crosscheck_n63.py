"""Re-decide the five n=63 UNSAT classes with solvers the pipeline never uses.

The sweep decides with Cadical195 and the certifier replays with Glucose42. A
null that only one engine has ever produced is a claim about that engine as
much as about the instance, and the write-up asserts these five are
solver-independent. This produces the evidence for that assertion.

    python3 crosscheck_n63.py --groups groups63.json

Exits non-zero unless every class comes back UNSAT from every solver tried.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import ansatz
import grouporder

OTHER_SOLVERS = ["Glucose3", "Minisat22"]      # neither used by the pipeline


def coverage_problems(items, expect, compare_path):
    """Every way the set of classes about to be checked fails to be the set the
    deposit claims. `items` is a list of (name, gens_sha, problem_identity) triples. Checked BEFORE
    the solving, so a mis-specified run fails in a second rather than an hour,
    and so it can be driven to failure in a test.

    A gate labelled "all five" has to know what five means, and it has to mean
    five INSTANCES. Matching on the name alone leaves two holes at once:
    deleting a group leaves four UNSAT rows and a successful exit, and swapping
    one class's generators for another's leaves every name matching while one
    instance is checked twice and another never.
    """
    problems = []
    items = [tuple(x) for x in items]
    # ONE population for both checks, and that population is the MATHEMATICAL
    # identity: (gens_sha, problem). Counting with `len` while comparing with
    # `set` lets five identical tuples satisfy expect=5 against a reference
    # holding one class -- the two checks would be about different things.
    # Carrying the display name in the identity is the same error one level
    # up: five copies of one instance under five aliases are one class.
    instances = [i[1:] for i in items]
    if len(set(instances)) != len(instances):
        dupes = sorted({str(i) for i in instances if instances.count(i) > 1})
        problems.append(f"the same instance appears more than once among the "
                        f"classes to check ({', '.join(dupes)}); repeated "
                        f"copies are one class, not several")
    if expect is not None and len(set(instances)) != expect:
        problems.append(f"{len(set(instances))} distinct class(es) to check, "
                        f"expected {expect}")
    if compare_path:
        with open(compare_path) as fh:
            dep_rows = json.load(fh)
        deposited = set()
        for d in dep_rows:
            if not d.get("gens_sha"):
                problems.append(f"{d.get('name')}: deposited row in "
                                f"{compare_path} carries no gens_sha; it cannot "
                                f"be matched to an instance")
                continue
            # The identity is not the whole claim. This program's closing line
            # says these are the classes the deposit RECORDED UNSAT, and a row
            # that records something else would make that sentence false while
            # the identities still matched. certify_nulls.gate compares these
            # same fields for the same reason.
            if d.get("status") != "UNSAT" or not d.get("checked"):
                problems.append(
                    f"{d['name']}: deposited in {compare_path} as "
                    f"status={d.get('status')!r} checked={d.get('checked')!r}; "
                    f"this program cross-checks classes the deposit records as "
                    f"certified UNSAT")
            # The PROBLEM, not only the group. Without it a reference
            # certifying one question satisfies a decision about another.
            # This and certify_nulls.gate both key on
            # ansatz.problem_identity so the two cannot disagree.
            if ansatz.row_problem_identity(d) is None:
                problems.append(f"{d['name']}: deposited row in "
                                f"{compare_path} carries no usable problem "
                                f"key; it records a group, not a decision")
                continue
            deposited.add((d["name"], d["gens_sha"],
                           ansatz.row_problem_identity(d)))
        for name, sha, prob in sorted(deposited - set(items)):
            problems.append(f"{name} [{sha}] on {prob}: recorded in "
                            f"{compare_path} but not among the classes to "
                            f"check")
        for name, sha, prob in sorted(set(items) - deposited):
            problems.append(f"{name} [{sha}] on {prob}: to be checked but no "
                            f"class with this name AND these generators AND "
                            f"this problem is in {compare_path}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", default="groups63.json")
    ap.add_argument("--n", type=int, default=63)
    ap.add_argument("--s", type=int, default=4)
    ap.add_argument("--t", type=int, default=6)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--out", default="crosscheck_46_3_n63.json")
    ap.add_argument("--expect", type=int, metavar="N", default=5,
                    help="fail unless exactly N classes were cross-checked")
    ap.add_argument("--compare", metavar="CERTS.json",
                    default="certs_46_3_n63.json",
                    help="fail unless the classes cross-checked are exactly "
                         "the classes this deposited file records")
    a = ap.parse_args()

    from pysat.formula import CNF
    from pysat.solvers import Solver

    with open(a.groups) as fh:
        groups = json.load(fh)
    print(f"cross-checking {len(groups)} class(es) at n={a.n}, "
          f"R({a.s},{a.t};{a.k}) with {', '.join(OTHER_SOLVERS)}\n"
          f"(the pipeline uses Cadical195 and Glucose42; neither appears here)")

    ansatz.refuse_ambiguous_names(groups, a.groups)
    # The problem THIS RUN is deciding, in the canonical form the deposited
    # rows are normalised into. Passing only (name, sha) is what let a
    # reference about another question satisfy this gate.
    here = ansatz.problem_identity({"n": a.n, "s": a.s, "t": a.t, "k": a.k})
    cover = coverage_problems(
        [(g["name"], ansatz.gens_fingerprint(g["generators"]), here)
         for g in groups],
        a.expect, a.compare)
    if cover:
        print("\nCOVERAGE GATE FAILED (checked before solving):",
              file=sys.stderr)
        for c in cover:
            print(f"  {c}", file=sys.stderr)
        return 1

    rows, problems = [], []
    for g in groups:
        name, gens = g["name"], g["generators"]
        t0 = time.time()
        clauses, _, stats = ansatz.build_cnf(gens, a.n, a.s, a.t, a.k)
        build = time.time() - t0
        row = {"name": name, "gens_sha": ansatz.gens_fingerprint(gens),
               "order": grouporder.group_order(gens, a.n),
               "vars": stats["vars"], "clauses": stats["clauses"],
               "build_s": round(build, 1)}
        cnf = CNF()
        for c in clauses:
            cnf.append(c)
        for eng in OTHER_SOLVERS:
            t1 = time.time()
            with Solver(name=eng, bootstrap_with=cnf) as sv:
                sat = sv.solve()
            row[eng] = {"status": "SAT" if sat else "UNSAT",
                        "s": round(time.time() - t1, 2)}
            if sat:
                problems.append(f"{name}: {eng} says SAT where the pipeline "
                                f"recorded UNSAT")
        rows.append(row)
        print(f"  {name:<28} {row['vars']:>3} vars {row['clauses']:>7} clauses "
              f"build {row['build_s']:>6}s  "
              + "  ".join(f"{e}={row[e]['status']} ({row[e]['s']}s)"
                          for e in OTHER_SOLVERS), flush=True)
        with open(a.out, "w") as fh:
            json.dump(rows, fh, indent=1)

    print(f"\nwritten to {a.out}")

    if problems:
        print("\nCROSS-CHECK FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print(f"all {len(rows)} class(es) UNSAT under every solver tried, and "
          f"they are exactly the classes {a.compare} records -- matched by "
          f"name AND generator fingerprint")
    return 0


if __name__ == "__main__":
    sys.exit(main())
