"""Build `Z_79 : C_d + m fixed` towers on n = 79 + m points.

The R(4,4,4;3) ladder climbs by adding fixed points: the group acts on the first
79 points as the affine group `x -> a*x + b` with `a` in the order-d subgroup of
`Z_79^*`, and fixes the rest pointwise. Each extra fixed point multiplies the
number of triple-orbits, which buys the solver freedom -- which is why 79, 80
and 81 were all reachable while a rigid group on the same points was not.

    python3 make_groups_79fixed.py --n 82 --out groups82.json
"""

import argparse
import json

import grouporder

P = 79
G = 3   # primitive root mod 79, verified by order


def divisors(x):
    return [d for d in range(1, x + 1) if x % d == 0]


def build(n):
    m = n - P
    assert m >= 0, "n must be at least 79"
    fixed = list(range(P, n))
    out = []
    for d in sorted(divisors(78), reverse=True):
        a = pow(G, 78 // d, P)               # generator of the order-d subgroup
        gens = [[(i + 1) % P for i in range(P)] + fixed,
                [(a * i) % P for i in range(P)] + fixed]
        order = grouporder.group_order(gens, n)
        assert order == P * d, (order, P * d)
        out.append({"name": f"Z_79 : C_{d}" + (f" + {m} fixed" if m else ""),
                    "generators": gens, "order": order})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    groups = build(a.n)
    json.dump(groups, open(a.out, "w"), indent=1)
    print(f"n={a.n}: {len(groups)} classes -> {a.out}")
    for g in groups:
        print(f"  {g['name']:<26} order {g['order']}")


if __name__ == "__main__":
    main()
