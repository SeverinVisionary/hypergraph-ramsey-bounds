"""Enumerate EVERY `Z_83 : C_41`-invariant good 3-colouring at n = 83.

`README.md` states how many there are and how their colour classes split. That
is an exhaustive claim, and a witness search does not establish one: it stops at
the first model. This enumerates all of them by blocking each model and
re-solving until the formula is UNSAT, and verifies every model from scratch
with `multicolour.verify` before counting it — a model the encoding accepts but
the property rejects would be an encoding defect, not a colouring.

    python3 enumerate_n83.py --groups g83_p83.json --class "Z_83 : C_41"

Exits non-zero unless the enumeration terminated in UNSAT (an exhausted search)
and every model verified.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from pysat.solvers import Cadical195

import ansatz
import multicolour


def enumerate_class(gens, n, sizes, k, limit=100000):
    """(models, splits, exhausted). `exhausted` is False if `limit` was hit."""
    cnf, orbit_of, var, stats = multicolour.build_cnf(gens, n, sizes, k)
    nv = stats["vars"]
    solver = Cadical195(bootstrap_with=cnf)
    splits, count = Counter(), 0
    exhausted = True
    try:
        while solver.solve():
            model = solver.get_model()
            chi = multicolour.expand(model, orbit_of, n, len(sizes), k)
            ok, detail = multicolour.verify(chi, n, sizes, k)
            if not ok:
                raise SystemExit(f"model {count} does not verify: {detail}")
            splits[tuple(sorted(Counter(chi).get(c, 0)
                                for c in range(len(sizes))))] += 1
            count += 1
            if count >= limit:
                exhausted = False
                break
            solver.add_clause([-lit for lit in model[:nv]])
    finally:
        solver.delete()
    return count, splits, exhausted


def parse_splits(spec):
    """`12:a/b/c,24:d/e/f` -> {(a,b,c): 12, (d,e,f): 24}.

    The published claim is a distribution, not a total. A count-only gate
    passes on 36 colourings with the wrong splits, which is a different
    mathematical statement about the class.
    """
    want = {}
    for part in spec.split(","):
        howmany, _, sizes = part.partition(":")
        if not sizes or not howmany.strip().isdigit():
            raise SystemExit(f"malformed split spec {part!r}; want N:a/b/c")
        if not all(x.strip().isdigit() for x in sizes.split("/")):
            raise SystemExit(f"malformed split spec {part!r}; want N:a/b/c")
        key = tuple(sorted(int(x) for x in sizes.split("/")))
        if key in want:
            raise SystemExit(f"split {sizes} named twice in {spec!r}")
        want[key] = int(howmany)
    return want


def fmt_splits(d):
    return ", ".join(f"{v}:{'/'.join(str(x) for x in k)}"
                     for k, v in sorted(d.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", default="g83_p83.json")
    ap.add_argument("--class", dest="cls", default="Z_83 : C_41")
    ap.add_argument("--n", type=int, default=83)
    ap.add_argument("--sizes", default="4,4,4")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--expect", type=int, default=None,
                    help="fail unless exactly N colourings are found")
    ap.add_argument("--expect-splits", default=None, metavar="SPEC",
                    help="fail unless the colour-class splits are exactly "
                         "SPEC, written as `12:30627/30627/30627,"
                         "24:27224/30627/34030`. The count alone does not "
                         "check the distribution the write-ups publish.")
    ap.add_argument("--expect-gens-sha", default=None, metavar="SHA256",
                    help="fail unless the selected class's generators hash to "
                         "this. A name is a label; the count asserted here is "
                         "about a group.")
    a = ap.parse_args()

    with open(a.groups) as fh:
        groups = json.load(fh)
    matching = [g for g in groups if g["name"] == a.cls]
    if len(matching) != 1:
        print(f"{a.groups}: {len(matching)} class(es) named {a.cls!r}; "
              f"expected exactly one", file=sys.stderr)
        return 2
    gens = matching[0]["generators"]
    sha = ansatz.gens_fingerprint(gens)
    if a.expect_gens_sha and sha != a.expect_gens_sha:
        print(f"{a.cls}: generators hash to {sha}, expected "
              f"{a.expect_gens_sha}; a uniquely-named row is still only a "
              f"name", file=sys.stderr)
        return 1
    sizes = [int(x) for x in a.sizes.split(",")]

    print(f"enumerating every {a.cls}-invariant good colouring at n={a.n}, "
          f"sizes {sizes}, k={a.k}\n  generators SHA-256 {sha}")
    count, splits, exhausted = enumerate_class(gens, a.n, sizes, a.k)

    if not exhausted:
        print("the search hit its limit; this is NOT an exhaustive count",
              file=sys.stderr)
        return 1

    print(f"\n{count} invariant good colouring(s), search exhausted "
          f"(the formula is UNSAT once all {count} are blocked)")
    for split, howmany in sorted(splits.items()):
        print(f"  colour classes {'/'.join(str(x) for x in split)}: "
              f"{howmany} colouring(s)")

    problems = []
    if a.expect is not None and count != a.expect:
        problems.append(f"expected {a.expect} colouring(s), found {count}")
    if a.expect_splits:
        got = {tuple(k): v for k, v in splits.items()}
        want = parse_splits(a.expect_splits)
        if got != want:
            problems.append(f"splits {fmt_splits(got)} != expected "
                            f"{fmt_splits(want)}")
    if problems:
        print("", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
