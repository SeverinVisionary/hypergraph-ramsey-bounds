"""Third, independent check of a witness file. Shares NO code with verify.py.

verify.py's two routes agree by construction on the index convention: both map
a 4-subset to its lexicographic rank. A systematic error in that convention --
an off-by-one, a transposed pair, a wrong ordering -- would be invisible to
both, because both would make it identically.

This file removes that common mode. It:

  * imports nothing from verify.py or cyclic.py;
  * never computes a rank -- it rebuilds the subset->colour map by zipping the
    colour list against a freshly generated enumeration, and works with frozen
    sets thereafter, so subset identity is set identity and not an integer;
  * checks the defining property directly from the definition quoted in DS1
    rev #18 p.5, re-stated here in full so the reader can compare:

      "R (G_1, ..., G_m ; s) ... the least integer n such that, in any coloring
       with m colors of the s-subsets of a set of n elements, for some i the
       s-subsets of color i contain a sub-(hyper)graph isomorphic to G_i"

    so a colouring of the 4-subsets of [n] with NO 5-set whose five 4-subsets
    are all one colour witnesses R(5,5;4) > n, i.e. R(5,5;4) >= n+1.

Run:  python3 independent_check.py witness_n33.json [...]
"""

import itertools
import json
import sys


def check_witness(path):
    with open(path) as f:
        w = json.load(f)
    n, s, t, k = w["n"], w["s"], w["t"], w["k"]
    chi = w["chi"]

    # Rebuild the map without any rank arithmetic: pair the colour list with a
    # freshly generated enumeration, then discard ordering entirely.
    subsets = [frozenset(c) for c in itertools.combinations(range(n), k)]
    if len(subsets) != len(chi):
        return path, False, f"length mismatch: {len(chi)} colours, {len(subsets)} {k}-subsets"
    colour = dict(zip(subsets, chi))
    if len(colour) != len(subsets):
        return path, False, "duplicate subsets in enumeration"
    if set(chi) - {0, 1}:
        return path, False, f"non-binary colours present: {sorted(set(chi))[:5]}"

    # Count independently, from the definition. No comb(), no early exit.
    n_cliques = 0
    bad = []

    for size, want in ((s, 0), (t, 1)):
        seen = 0
        for clique in itertools.combinations(range(n), size):
            seen += 1
            faces = [frozenset(f) for f in itertools.combinations(clique, k)]
            if all(colour[f] == want for f in faces):
                bad.append((tuple(sorted(clique)), want))
        n_cliques += seen
        # Independent completeness count: multiplicative formula, not comb().
        expect = 1
        for i in range(size):
            expect = expect * (n - i) // (i + 1)
        if seen != expect:
            return path, False, f"examined {seen} {size}-subsets, expected {expect}"

    if bad:
        return path, False, f"{len(bad)} monochromatic clique(s), first: {bad[0]}"

    claimed = w.get("certifies", "")
    derived = f"R({s},{t};{k}) >= {n+1}"
    if claimed and claimed.replace(" ", "") != derived.replace(" ", ""):
        return path, False, f"file claims {claimed!r} but the object gives {derived}"

    return path, True, (
        f"n={n} k={k}: {len(chi)} colours, {n_cliques} cliques checked, "
        f"0 monochromatic  =>  {derived}"
    )


def main(paths):
    allok = True
    for p in paths:
        path, ok, msg = check_witness(p)
        print(f"[{'PASS' if ok else 'FAIL'}] {path}: {msg}")
        allok &= ok
    print("\nALL WITNESSES PASS" if allok else "\nSOME WITNESSES FAILED")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["witness_n33.json"]))
