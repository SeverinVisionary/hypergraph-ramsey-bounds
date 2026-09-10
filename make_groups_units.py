"""Every class `Z_n : H` for H a subgroup of the multiplier group `Z_n^*`.

`groups63.json` was hand-picked: five classes out of the tower, all under 64
orbit variables, chosen without a committed producer. In fact
`Z_63^*` has 30 subgroups and that 22 of the resulting classes pass the
`--max-vars 200` filter the sweep actually used -- so the cell had been called
"swept" on 5 of 22, and the 17 missing ones were the LARGER classes, which is
exactly where a witness could live.

This enumerates the subgroup lattice properly, so a tower is reproducible
instead of hand-assembled.

    python3 make_groups_units.py --n 63 --k 3 --max-vars 200 --out groups63_all.json
"""

import argparse
import json
from itertools import combinations

import ansatz
import grouporder


def units(n):
    from math import gcd
    return [u for u in range(1, n) if gcd(u, n) == 1]


def subgroups(n):
    """All subgroups of Z_n^*, as frozensets. The group is small (order
    phi(n)), so closing every subset of generators is affordable and avoids a
    structure-theory argument that could quietly miss a non-cyclic subgroup --
    the mistake that once left the decidable end of the n=88 tower unbuilt."""
    U = units(n)
    found = {frozenset([1])}
    frontier = [frozenset([1])]
    while frontier:
        nxt = []
        for H in frontier:
            for u in U:
                if u in H:
                    continue
                K, add = set(H), [u]
                while add:                      # close under multiplication
                    x = add.pop()
                    if x in K:
                        continue
                    K.add(x)
                    for y in list(K):
                        for z in ((x * y) % n, (y * x) % n):
                            if z not in K:
                                add.append(z)
                K = frozenset(K)
                if K not in found:
                    found.add(K)
                    nxt.append(K)
        frontier = nxt
    return sorted(found, key=len, reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--max-vars", type=int, default=200)
    ap.add_argument("--colours", type=int, default=1,
                    help="1 for the two-colour encoding, m for m colours")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    n = a.n
    subs = subgroups(n)
    print(f"Z_{n}^* has {len(subs)} subgroups", flush=True)

    rows, skipped = [], 0
    for H in subs:
        gens = [[(i + 1) % n for i in range(n)]]
        gens += [[(u * i) % n for i in range(n)] for u in sorted(H) if u != 1]
        order = grouporder.group_order(gens, n)
        orbit_of, sizes = ansatz.face_orbits(gens, n, a.k)
        nv = len(sizes) * a.colours
        if nv > a.max_vars:
            skipped += 1
            continue
        name = f"Z_{n} : <{','.join(str(u) for u in sorted(H) if u != 1) or '1'}>"
        rows.append({"name": f"{name} order {order}", "generators": gens,
                     "order": order, "orbit_count": len(sizes), "vars": nv})

    rows.sort(key=lambda r: r["vars"])
    json.dump(rows, open(a.out, "w"), indent=1)
    print(f"{len(rows)} classes at or under {a.max_vars} vars "
          f"({skipped} larger, skipped) -> {a.out}")
    for r in rows:
        print(f"  {r['name']:<34} order {r['order']:<6} {r['vars']} vars")


if __name__ == "__main__":
    main()
