"""Times the bitmask build against the committed one, so the number is auditable.

`CELLS.md` records that replacing the per-subset `frozenset` in
`ansatz.distinct_orbit_sets` with an integer bitmask makes the n=63 build 281 s
instead of 19.9 s. This file holds both variants, runnable side by side, so
that comparison can be re-measured rather than taken on trust.

    python3 bitmask_experiment.py            # small, seconds
    python3 bitmask_experiment.py --full     # the n=63 case, minutes

The mechanism: `orbit_of[f]` returns a reference to an
integer already living in the dict, so the frozenset path allocates no integers
per face. `1 << orbit_of[f]` and `m |= ...` each construct a new integer object
per face. The frozenset path builds one container per subset; the bitmask path
builds two integers per face, twenty faces per subset.
"""

import argparse
import time
from itertools import combinations
from math import comb

from ansatz import distinct_orbit_sets, face_orbits


def bitmask_orbit_sets(orbit_of, n, size, k, translations=False):
    """The reverted variant: accumulate a bitmask, decode once per distinct mask."""
    masks = set()
    walked = 0
    if translations:
        for rest in combinations(range(1, n), size - 1):
            walked += 1
            m = 0
            for f in combinations((0,) + rest, k):
                m |= 1 << orbit_of[f]
            masks.add(m)
        assert walked == comb(n - 1, size - 1)
    else:
        for W in combinations(range(n), size):
            walked += 1
            m = 0
            for f in combinations(W, k):
                m |= 1 << orbit_of[f]
            masks.add(m)
        assert walked == comb(n, size)

    out = set()
    for m in masks:
        S, i = [], 0
        while m:
            if m & 1:
                S.append(i)
            m >>= 1
            i += 1
        out.add(frozenset(S))
    return out


def race(gens, n, size, k, translations=True):
    orbit_of, sizes = face_orbits(gens, n, k)

    t = time.time()
    a = distinct_orbit_sets(orbit_of, n, size, k, translations=translations)
    ta = time.time() - t

    t = time.time()
    b = bitmask_orbit_sets(orbit_of, n, size, k, translations=translations)
    tb = time.time() - t

    assert a == b, "the two builds must agree -- otherwise the race is meaningless"
    return len(sizes), len(a), ta, tb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true",
                    help="run the n=63, t=6 case from CELLS.md (minutes)")
    a = ap.parse_args()

    n = 63
    gens = [[(i + 1) % n for i in range(n)],
            [(2 * i) % n for i in range(n)],
            [(5 * i) % n for i in range(n)]]
    size = 6 if a.full else 4

    orbits, distinct, ta, tb = race(gens, n, size, 3)
    print(f"n={n}, size={size}, k=3, {orbits} orbits, {distinct} distinct sets")
    print(f"  frozenset (committed) : {ta:7.1f}s")
    print(f"  bitmask   (reverted)  : {tb:7.1f}s   {tb / ta:.1f}x slower"
          if tb > ta else
          f"  bitmask   (reverted)  : {tb:7.1f}s   {ta / tb:.1f}x FASTER")


if __name__ == "__main__":
    main()
