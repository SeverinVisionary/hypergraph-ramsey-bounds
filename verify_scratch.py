"""A third verifier that shares NO code and NO library with the producer.

WHY A THIRD ONE.  `verify.py` and `independent_check.py` are two different
algorithms, but both -- like `ansatz.py`, which produced the witness -- build
their face indexing with `itertools.combinations`. That is a common mode: if
the producer and every checker share a wrong understanding of what "the i-th
4-subset in lexicographic order" means, they all agree and all are wrong, and
the certificate is garbage that passes every test.

This file provides a reproducible independent check of that ordering.

So: no itertools, no repo imports, no rank formula. The face ordering is built
by four explicit nested loops incrementing a counter, which is the definition
of lexicographic order rather than a library's implementation of it. The clique
scan is five explicit nested loops. If this agrees with the other two, the
ordering convention is not a shared assumption -- it has been derived twice by
different means.

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
