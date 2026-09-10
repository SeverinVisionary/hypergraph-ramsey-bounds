"""Build Hol(Z_m) ansaetze on n points, for pushing the bound past 35.

Hol(Z_m) = Z_m : Aut(Z_m), the translations together with the multiplications
by units, acting on Z_m and fixing the remaining n - m points. It is the group
that produced the 34- and 35-point witnesses: Hol(Z_34) has order 34*phi(34) =
34*16 = 544 = 2^5 * 17, which is prime to 5, so the obstruction of
obstruction.py does not apply to it.

The 35-point witness came from Hol(Z_34) on 34 points with ONE point fixed, so
the natural next rungs are more fixed points and larger m. Only m with
5 not dividing m*phi(m) are usable; the rest are excluded outright.
"""

from __future__ import annotations

import argparse
import json
from math import gcd


def units(m):
    return [u for u in range(1, m) if gcd(u, m) == 1]


def hol(m, n):
    """Generators of Hol(Z_m) acting on 0..m-1, fixing m..n-1."""
    if m > n:
        raise ValueError(f"m={m} exceeds n={n}")
    fixed = list(range(m, n))
    gens = [[(i + 1) % m for i in range(m)] + fixed]
    gens += [[(u * i) % m for i in range(m)] + fixed for u in units(m) if u != 1]
    return gens


def order(m):
    return m * len(units(m))


def build(n, ms=None):
    """Every usable Hol(Z_m) on n points, largest group first."""
    out = []
    for m in (ms or range(6, n + 1)):
        o = order(m)
        if o % 5 == 0:
            continue                      # 5 | |G|: the class cannot contain a witness
        out.append({
            "name": f"Hol(Z_{m}) + {n - m} fixed",
            "generators": hol(m, n),
            "order": o,
            "m": m,
            "fixed": n - m,
            "orbit_count_4subsets": None,
        })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    from ansatz import face_orbits
    from grouporder import group_order

    rows = build(a.n)
    for r in rows:
        computed = group_order(r["generators"], a.n)
        if computed != r["order"]:
            raise AssertionError(
                f"{r['name']}: claimed order {r['order']}, Schreier-Sims says "
                f"{computed}")
        r["orbit_count_4subsets"] = len(face_orbits(r["generators"], a.n, k=4)[1])
    rows.sort(key=lambda r: r["orbit_count_4subsets"])
    for r in rows:
        print(f"{r['orbit_count_4subsets']:>6} vars  |G|={r['order']:<8} {r['name']}")
    out = a.out or f"groups_hol_n{a.n}.json"
    with open(out, "w") as f:
        json.dump(rows, f, indent=1)
    print(f"\n{len(rows)} usable groups -> {out}")


if __name__ == "__main__":
    main()
