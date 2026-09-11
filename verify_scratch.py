"""A direct-loop verifier for binary (5,5;4) witnesses.

This checker constructs the stipulated lexicographic ordering of four-subsets
with explicit nested loops and scans every five-subset. It imports no
repository modules and uses neither itertools nor the producer's rank
formula.

Agreement with the other checkers cross-checks implementations of the face
ordering and clique predicate. The checks still share the witness
serialization and mathematical specification, and rely on the Python
runtime and standard-library parsing. Agreement does not rule out a shared
specification or runtime error.

    python3 verify_scratch.py witness_n35.json [...]
"""

import json
import sys


def face_index(n):
    """{(a,b,c,d): rank} in lexicographic order, by explicit enumeration."""
    idx = {}
    r = 0
    for a in range(n):
        for b in range(a + 1, n):
            for c in range(b + 1, n):
                for d in range(c + 1, n):
                    idx[(a, b, c, d)] = r
                    r += 1
    return idx, r


def check(path):
    with open(path) as fh:
        doc = json.load(fh)
    n = doc["n"]
    chi = doc["chi"]

    if doc.get("k", 4) != 4 or doc.get("s", 5) != 5 or doc.get("t", 5) != 5:
        return path, False, f"not a (5,5;4) witness: {doc.get('s')},{doc.get('t')};{doc.get('k')}"

    idx, n_faces = face_index(n)
    if len(chi) != n_faces:
        return path, False, f"chi has {len(chi)} entries, expected {n_faces}"
    for v in chi:
        if v not in (0, 1):
            return path, False, f"non-binary colour {v!r}"

    bad0 = bad1 = 0
    n_cliques = 0
    for a in range(n):
        for b in range(a + 1, n):
            for c in range(b + 1, n):
                for d in range(c + 1, n):
                    for e in range(d + 1, n):
                        n_cliques += 1
                        # the five 4-subsets of {a,b,c,d,e}, written out
                        s = (chi[idx[(b, c, d, e)]] + chi[idx[(a, c, d, e)]]
                             + chi[idx[(a, b, d, e)]] + chi[idx[(a, b, c, e)]]
                             + chi[idx[(a, b, c, d)]])
                        if s == 0:
                            bad0 += 1
                        elif s == 5:
                            bad1 += 1

    if bad0 or bad1:
        return path, False, (f"{bad0} monochromatic-0 and {bad1} "
                             f"monochromatic-1 K5 among {n_cliques} five-sets")
    return path, True, (f"n={n}: {n_faces} faces, {n_cliques} five-sets, "
                        f"0 monochromatic  =>  R(5,5;4) >= {n + 1}")


def main(paths):
    ok = True
    for p in paths:
        path, good, msg = check(p)
        print(f"[{'PASS' if good else 'FAIL'}] {path}: {msg}")
        ok = ok and good
    print("\nALL WITNESSES PASS" if ok else "\nVERIFICATION FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["witness_n33.json"]))
