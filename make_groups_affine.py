"""Affine towers `Z_p : C_d + m fixed` on n = p + m points, for any prime p.

Generalises `make_groups_79fixed.py`. The R(4,4,4;3) ladder is built from the
affine group `x -> a*x + b` on p points with `a` in the order-d subgroup of
`Z_p^*`, extended by m points the group fixes pointwise.

Two knobs matter and they pull against each other: a smaller d gives more
triple-orbits (more solver freedom, bigger instance), and a smaller p with more
fixed points does the same. When one base stalls, another may not -- at n=82 the
p=79 tower's C_13 class is UNSAT where its n=81 counterpart held a witness, so
the useful move is to try p=73 and p=71 rather than only descend the p=79 tower.

    python3 make_groups_affine.py --n 82 --p 73 --max-vars 400 --out g82_p73.json
"""

import argparse
import json

import grouporder


def is_prime(x):
    if x < 2:
        return False
    for d in range(2, int(x ** 0.5) + 1):
        if x % d == 0:
            return False
    return True


def primitive_root(p):
    fac = {q for q in range(2, p) if (p - 1) % q == 0 and is_prime(q)}
    for g in range(2, p):
        if all(pow(g, (p - 1) // q, p) != 1 for q in fac):
            return g
    raise ValueError(p)


def build(n, p, max_vars=None, k=3, colours=3, skipped=None):
    """The affine tower at base `p` on `n` points.

    `max_vars` drops classes whose encoding is larger than the cap. That drop
    is SILENT to the return value, which is what a caller summarising "every
    class" needs to know about: pass a list as `skipped` and each dropped class
    is appended to it as {"name", "order", "orbit_count", "vars"}. A caller
    that does not pass one is asking only for the classes under the cap.
    """
    assert is_prime(p) and p <= n
    m, g = n - p, primitive_root(p)
    fixed = list(range(p, n))
    out = []
    for d in sorted({d for d in range(1, p) if (p - 1) % d == 0}, reverse=True):
        a = pow(g, (p - 1) // d, p)
        gens = [[(i + 1) % p for i in range(p)] + fixed,
                [(a * i) % p for i in range(p)] + fixed]
        order = grouporder.group_order(gens, n)
        assert order == p * d, (order, p * d)
        row = {"name": f"Z_{p} : C_{d}" + (f" + {m} fixed" if m else ""),
               "generators": gens, "order": order}
        if max_vars is not None:
            import ansatz
            orbit_of, sizes = ansatz.face_orbits(gens, n, k)
            if len(sizes) * colours > max_vars:
                if skipped is not None:
                    skipped.append({"name": row["name"], "order": order,
                                    "orbit_count": len(sizes),
                                    "vars": len(sizes) * colours})
                continue
            row["orbit_count"] = len(sizes)
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--p", type=int, required=True)
    ap.add_argument("--max-vars", type=int)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    over_cap = []
    groups = build(a.n, a.p, a.max_vars, skipped=over_cap)
    json.dump(groups, open(a.out, "w"), indent=1)
    print(f"n={a.n}, base p={a.p}: {len(groups)} classes -> {a.out}")
    for g in groups:
        oc = g.get("orbit_count")
        print(f"  {g['name']:<26} order {g['order']:<7}"
              + (f" {oc} orbits, {oc * 3} vars" if oc else ""))

    # The cap drops classes, and a count of the survivors reads as the size of
    # the tower unless the drop is printed. climb.py and sweep_pdm.py collect
    # this; so must the producer they are all built on.
    for sk in over_cap:
        print(f"  {sk['name']:<26} order {sk['order']:<7} "
              f"{sk['orbit_count']} orbits, {sk['vars']} vars "
              f"-- OVER the {a.max_vars}-variable cap, not built")
    if over_cap:
        print(f"  ({len(over_cap)} class(es) over the cap; this file is the "
              f"tower at or under {a.max_vars} variables, not the whole tower)")


if __name__ == "__main__":
    main()
