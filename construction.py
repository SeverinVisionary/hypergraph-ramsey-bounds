import sys
"""The R(4,4,4;3) >= 84 construction, stated as mathematics rather than output.

A SAT witness is a bitstring: 91,881 entries for the 83-point colouring --
one per triple of the 83-set, C(83,3). That is
not something a reader can check, cite, or build on. What the object actually
is, is far smaller -- 27 numbers -- and this module is the difference between
the two.

THE CONSTRUCTION. Let p = 83 and let a = 9, which generates the subgroup
C_41 of index 2 in Z_83^* (the quadratic residues). Let G be the affine group

    G = { x -> a^i * x + b : 0 <= i < 41, b in Z_83 },   |G| = 3403.

G acts on the C(83,3) = 91,881 triples of Z_83 with exactly 27 orbits, each of
size 3403 = |G| (the action is free). Every triple is equivalent under G to
exactly one of the 27 representatives {0, 1, z} listed in COLOURS below, and
the colouring assigns each triple the colour of its representative.

Nine orbits take each colour, so the three colour classes have exactly
30,627 triples each.

That balance is NOT forced. All orbits having size |G| forces each colour class
to be a multiple of 3403, which allows 8/9/10 just as well as 9/9/9.
Enumerating every invariant good colouring of this class gives 36: twelve
split 9/9/9 and twenty-four split 8/9/10. The table below is one of the
balanced ones. What the balance is NOT is evidence of a character-sum
construction -- the colouring is not a function of (x-y)(y-z)(z-x), which was
checked directly.

THEOREM. No 4-subset of Z_83 has all four of its triples the same colour.
Hence R(4,4,4;3) >= 84.

The theorem is verified by enumeration in `verify()` below: all 1,837,620
four-subsets, zero monochromatic in each colour. `rebuild()` regenerates the
whole colouring from the 27 numbers, so the bitstring in `witness_444_3_n83.json`
is a consequence of this table rather than an independent artifact.
"""

P = 83
MULTIPLIER = 9          # generates C_41 <= Z_83^*, the quadratic residues

# Orbit representative {0, 1, z} -> colour. The whole construction.
COLOURS = {
    2: 2,  3: 2,  4: 0,  5: 2,  6: 1,  7: 0,  8: 1,  9: 0, 10: 2,
    11: 2, 13: 2, 14: 1, 16: 2, 17: 0, 18: 0, 19: 1, 20: 1, 22: 1,
    23: 0, 27: 2, 29: 1, 31: 0, 38: 1, 41: 1, 45: 2, 48: 0, 69: 0,
}


def _subgroup(p=P, a=MULTIPLIER):
    H, x = set(), 1
    while x not in H:
        H.add(x)
        x = x * a % p
    return H


def rebuild(p=P, a=MULTIPLIER, colours=None):
    """Regenerate the full colouring of all C(p,3) triples from the table.

    Returns a dict {(x, y, z): colour}. Uses only the 27 numbers -- no solver,
    no witness file.
    """
    colours = COLOURS if colours is None else colours
    H = _subgroup(p, a)
    # Colour each orbit by flooding from its representative under the group
    # generators, which is cheaper and less error-prone than canonicalising
    # every triple independently.
    chi = {}
    for z, c in colours.items():
        seen = {(0, 1, z)}
        stack = [(0, 1, z)]
        while stack:
            t = stack.pop()
            if t in chi:
                continue
            chi[t] = c
            for u in (1,) if False else H:
                img = tuple(sorted((u * v % p) for v in t))
                if img not in chi and img not in seen:
                    seen.add(img)
                    stack.append(img)
            sh = tuple(sorted(((v + 1) % p) for v in t))
            if sh not in chi and sh not in seen:
                seen.add(sh)
                stack.append(sh)
    return chi


def verify(chi=None, p=P):
    """Enumerate every 4-subset; return the count monochromatic in each colour."""
    chi = rebuild() if chi is None else chi
    bad = {0: 0, 1: 0, 2: 0}
    total = 0
    for a_ in range(p):
        for b in range(a_ + 1, p):
            for c in range(b + 1, p):
                cab = chi[(a_, b, c)]
                for d in range(c + 1, p):
                    total += 1
                    if (chi[(a_, b, d)] == cab and chi[(a_, c, d)] == cab
                            and chi[(b, c, d)] == cab):
                        bad[cab] += 1
    return bad, total


if __name__ == "__main__":
    chi = rebuild()
    print(f"triples coloured: {len(chi)} (expected {P*(P-1)*(P-2)//6})")
    from collections import Counter
    print("colour classes:", dict(sorted(Counter(chi.values()).items())))
    bad, total = verify(chi)
    print(f"four-subsets: {total}")
    print("monochromatic:", bad)
    expected = P * (P - 1) * (P - 2) * (P - 3) // 24
    ok = not any(bad.values()) and total == expected
    print("R(4,4,4;3) >=", P + 1 if ok else "FAILED")
    if not ok:
        # Printing FAILED and exiting 0 lets any caller that reads only the
        # exit status -- reproduce.sh does -- report this step as passing.
        print(f"FAILED: monochromatic={bad}, scanned {total} of {expected}",
              file=sys.stderr)
        sys.exit(1)
