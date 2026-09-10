import sys
"""The R(5,5;4) >= 36 construction, stated as mathematics rather than output.

Third of the three. The witness file holds 52,360 bits; the object is 107
numbers.

THE CONSTRUCTION. Work on Z_34 together with one extra point, written 34, which
the group fixes. Let

    G = Hol(Z_34) = { x -> u*x + b : u in <3> <= Z_34^*, b in Z_34 },

with 3 a primitive root mod 34, so |<3>| = phi(34) = 16 and |G| = 544. G acts on
the C(35,4) = 52,360 four-subsets of the 35-point set with exactly 107 orbits.

The action is not free: orbit sizes are 544 (87 orbits), 272 (17) and 136 (3),
the short ones being four-sets stabilised by part of the multiplier subgroup.
Compare `construction.py`, where the 83-point action IS free and the colour
classes happen to come out exactly equal -- freeness forces each class to be a
multiple of the orbit size, not to be equal; the enumeration there finds
twenty-four unbalanced good colourings alongside twelve balanced ones.

TABLE below maps each orbit representative to its colour.

THEOREM. No 5-subset of the 35-point set has all five of its four-subsets the
same colour. Hence R(5,5;4) >= 36.

This is the cell whose incumbent is [Ex24] -- G. Exoo, personal communication
(2021) -- which is unobtainable. Its public page still shows a weaker 33-vertex
construction. So unlike the other two cells, the comparison here can never be
made against an object, only against a number DS1 prints.
"""

N = 35
FIXED_POINT = 34          # the point Hol(Z_34) fixes
MODULUS = 34
MULTIPLIER = 3            # primitive root mod 34; <3> = Z_34^*, order 16

TABLE = {
    (0, 1, 2, 3): 0,  (0, 1, 2, 4): 0,
    (0, 1, 2, 5): 0,  (0, 1, 2, 6): 1,
    (0, 1, 2, 7): 1,  (0, 1, 2, 8): 0,
    (0, 1, 2, 9): 0,  (0, 1, 2, 10): 1,
    (0, 1, 2, 11): 0,  (0, 1, 2, 12): 0,
    (0, 1, 2, 13): 0,  (0, 1, 2, 14): 1,
    (0, 1, 2, 15): 1,  (0, 1, 2, 16): 1,
    (0, 1, 2, 17): 1,  (0, 1, 2, 18): 0,
    (0, 1, 2, 34): 0,  (0, 1, 3, 4): 1,
    (0, 1, 3, 5): 1,  (0, 1, 3, 7): 1,
    (0, 1, 3, 8): 1,  (0, 1, 3, 9): 0,
    (0, 1, 3, 10): 0,  (0, 1, 3, 11): 1,
    (0, 1, 3, 12): 1,  (0, 1, 3, 13): 1,
    (0, 1, 3, 14): 0,  (0, 1, 3, 15): 1,
    (0, 1, 3, 16): 1,  (0, 1, 3, 17): 0,
    (0, 1, 3, 18): 0,  (0, 1, 3, 19): 1,
    (0, 1, 3, 20): 0,  (0, 1, 3, 21): 1,
    (0, 1, 3, 22): 0,  (0, 1, 3, 24): 1,
    (0, 1, 3, 25): 0,  (0, 1, 3, 26): 1,
    (0, 1, 3, 27): 1,  (0, 1, 3, 29): 0,
    (0, 1, 3, 30): 0,  (0, 1, 3, 32): 0,
    (0, 1, 3, 34): 1,  (0, 1, 4, 5): 1,
    (0, 1, 4, 6): 0,  (0, 1, 4, 8): 1,
    (0, 1, 4, 9): 0,  (0, 1, 4, 11): 0,
    (0, 1, 4, 14): 1,  (0, 1, 4, 16): 0,
    (0, 1, 4, 17): 1,  (0, 1, 4, 18): 1,
    (0, 1, 4, 20): 0,  (0, 1, 4, 21): 1,
    (0, 1, 4, 22): 0,  (0, 1, 4, 24): 1,
    (0, 1, 4, 25): 0,  (0, 1, 4, 27): 1,
    (0, 1, 4, 28): 1,  (0, 1, 4, 30): 1,
    (0, 1, 4, 31): 0,  (0, 1, 4, 34): 0,
    (0, 1, 5, 6): 1,  (0, 1, 5, 7): 0,
    (0, 1, 5, 8): 0,  (0, 1, 5, 9): 0,
    (0, 1, 5, 14): 0,  (0, 1, 5, 17): 1,
    (0, 1, 5, 22): 1,  (0, 1, 5, 27): 0,
    (0, 1, 5, 30): 1,  (0, 1, 5, 34): 0,
    (0, 1, 6, 8): 0,  (0, 1, 6, 17): 1,
    (0, 1, 6, 18): 0,  (0, 1, 6, 29): 1,
    (0, 1, 6, 34): 0,  (0, 1, 9, 10): 0,
    (0, 1, 9, 13): 1,  (0, 1, 9, 15): 0,
    (0, 1, 9, 17): 0,  (0, 1, 9, 21): 0,
    (0, 1, 9, 26): 0,  (0, 1, 9, 34): 1,
    (0, 1, 10, 18): 1,  (0, 1, 10, 20): 1,
    (0, 1, 10, 25): 0,  (0, 1, 10, 34): 1,
    (0, 1, 13, 14): 0,  (0, 1, 13, 17): 0,
    (0, 1, 13, 34): 1,  (0, 1, 17, 18): 0,
    (0, 1, 17, 34): 1,  (0, 2, 4, 6): 1,
    (0, 2, 4, 8): 0,  (0, 2, 4, 10): 1,
    (0, 2, 4, 12): 1,  (0, 2, 4, 14): 0,
    (0, 2, 4, 16): 0,  (0, 2, 4, 34): 0,
    (0, 2, 6, 8): 0,  (0, 2, 6, 14): 0,
    (0, 2, 6, 22): 1,  (0, 2, 6, 30): 1,
    (0, 2, 6, 34): 0,  (0, 2, 8, 10): 0,
    (0, 2, 8, 34): 1,
}


def _subgroup(m=MODULUS, a=MULTIPLIER):
    H, x = set(), 1
    while x not in H:
        H.add(x)
        x = x * a % m
    return H


def _act(t, u, b, m=MODULUS, fixed=FIXED_POINT):
    """Apply x -> u*x + b to a four-set, leaving the fixed point alone."""
    return tuple(sorted(fixed if v == fixed else (u * v + b) % m for v in t))


def rebuild(table=None):
    """Regenerate the colouring of all C(35,4) four-sets from TABLE alone."""
    table = TABLE if table is None else table
    H = _subgroup()
    chi = {}
    for rep, colour in table.items():
        stack = [tuple(rep)]
        while stack:
            t = stack.pop()
            if t in chi:
                continue
            chi[t] = colour
            for u in H:
                img = _act(t, u, 0)
                if img not in chi:
                    stack.append(img)
            sh = _act(t, 1, 1)
            if sh not in chi:
                stack.append(sh)
    return chi


def verify(chi=None, n=N):
    """Count 5-subsets monochromatic in each colour."""
    chi = rebuild() if chi is None else chi
    bad = {0: 0, 1: 0}
    total = 0
    for a in range(n):
        for b in range(a + 1, n):
            for c in range(b + 1, n):
                for d in range(c + 1, n):
                    col = chi[(a, b, c, d)]
                    for e in range(d + 1, n):
                        total += 1
                        if (chi[(a, b, c, e)] == col and chi[(a, b, d, e)] == col
                                and chi[(a, c, d, e)] == col
                                and chi[(b, c, d, e)] == col):
                            bad[col] += 1
    return bad, total


if __name__ == "__main__":
    from collections import Counter
    chi = rebuild()
    print(f"four-sets coloured: {len(chi)} (expected 52360)")
    print("colour classes:", dict(sorted(Counter(chi.values()).items())))
    bad, total = verify(chi)
    print(f"five-subsets: {total}")
    print("monochromatic:", bad)
    expected = N * (N - 1) * (N - 2) * (N - 3) * (N - 4) // 120
    ok = not any(bad.values()) and total == expected
    print("R(5,5;4) >=", N + 1 if ok else "FAILED")
    if not ok:
        print(f"FAILED: monochromatic={bad}, scanned {total} of {expected}",
              file=sys.stderr)
        sys.exit(1)
