"""Hash-bound, complete, two-way verification of the R(4,6;3) >= 64 witness.

Run:  python3 verify_witness_n63.py

This wrapper binds the declared convention and witness vector to a complete
two-way check. It is shipped so that the reader can rerun the stated checks
against the exact witness bytes.

Three numbers have to come out right, and any one of them wrong is a non-zero
exit:

  * the SHA-256 of the witness's colour vector, so this record is bound to one
    exact object and not merely to a filename;
  * zero monochromatic K_4 in colour 0 and zero monochromatic K_6 in colour 1,
    which is the claim;
  * 102,627 monochromatic K_4 in colour 1 under the REVERSED reading of the
    convention. Under the intended convention, this count is allowed and
    provides a discriminating control against certain implementation failures;
    it does not establish the convention or validate the K_6 branch. A separate
    six-vertex control assigns colour 1 to all twenty triples and requires the
    K_6 detector to report one violation. The first verification script written
    for this witness had the convention backwards and reported those 102,627 as
    a failure of the witness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from itertools import combinations

import construction_n63 as c63

PUBLISHED_SHA = "998c2217a9c3e3cc1d2b082be2a5b9b8d9c30e1d2b62b1dfc1cc896bdbd754cd"
PUBLISHED_REVERSED_K4 = 102627


def load(path):
    with open(path) as fh:
        doc = json.load(fh)
    return doc


def colour_vector_sha(chi):
    """The convention used when the witness was first recorded."""
    return hashlib.sha256(json.dumps(chi).encode()).hexdigest()


def as_dict(chi, n):
    """Flat lex-ordered vector -> dict keyed by triple, which is what the
    construction module's verifier consumes."""
    out = {}
    for i, t in enumerate(combinations(range(n), 3)):
        out[t] = chi[i]
    if len(out) != len(chi):
        raise AssertionError(f"{len(chi)} colours for {len(out)} triples")
    return out


def reversed_reading_k4_in_colour_1(d, n):
    """Count K_4 monochromatic in colour 1 -- the clique the OTHER colour is
    supposed to avoid. The discriminating control."""
    bad = 0
    for a in range(n):
        for b in range(a + 1, n):
            for c in range(b + 1, n):
                if not d[(a, b, c)]:
                    continue
                for e in range(c + 1, n):
                    if d[(a, b, e)] and d[(a, c, e)] and d[(b, c, e)]:
                        bad += 1
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--witness", default="witness_46_3_n63.json")
    ap.add_argument("--expect-sha", default=PUBLISHED_SHA)
    a = ap.parse_args()

    doc = load(a.witness)
    n, chi = doc["n"], doc["chi"]
    print(f"witness      {a.witness}")
    print(f"declares     n={n} s={doc['s']} t={doc['t']} k={doc['k']}  "
          f"{doc.get('ansatz')}")
    print(f"certifies    {doc.get('certifies')}")

    # The wrapper scans a hard-coded (4,6;3) reading, so the declaration must
    # agree with the target that is actually checked.
    WANT = {"s": 4, "t": 6, "k": 3}
    declared = {f: doc.get(f) for f in WANT}
    if declared != WANT:
        print(f"MISMATCH: {a.witness} declares {declared}, but this verifier "
              f"checks {WANT}; the declaration and the check are different "
              f"claims", file=sys.stderr)
        return 1

    got = colour_vector_sha(chi)
    print(f"sha256       {got}")
    if got != a.expect_sha:
        print(f"MISMATCH: expected {a.expect_sha}", file=sys.stderr)
        return 1

    n_faces = n * (n - 1) * (n - 2) // 6
    print(f"faces        {len(chi)} expected C({n},3)={n_faces}")
    if len(chi) != n_faces:
        print("MISMATCH: wrong number of faces", file=sys.stderr)
        return 1
    if any(v not in (0, 1) for v in chi):
        print("MISMATCH: non-binary colour present", file=sys.stderr)
        return 1
    print(f"colour 0     {chi.count(0)}")
    print(f"colour 1     {chi.count(1)}")

    d = as_dict(chi, n)

    print("scanning intended reading (K_4 in colour 0, K_6 in colour 1) ...",
          flush=True)
    bad4, bad6 = c63.verify(d, n)
    print(f"  mono K_4 in colour 0: {bad4}   (want 0)")
    print(f"  mono K_6 in colour 1: {bad6}   (want 0)")

    print("scanning reversed reading (K_4 in colour 1) ...", flush=True)
    rev = reversed_reading_k4_in_colour_1(d, n)
    print(f"  mono K_4 in colour 1: {rev}   (want {PUBLISHED_REVERSED_K4})")

    problems = []
    if bad4 or bad6:
        problems.append(f"witness is NOT good: bad4={bad4} bad6={bad6}")
    if rev != PUBLISHED_REVERSED_K4:
        problems.append(f"reversed-reading count {rev} != "
                        f"{PUBLISHED_REVERSED_K4}; the checker is not "
                        f"discriminating as recorded")
    if problems:
        print("\nFAILED:", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1

    print(f"\nOK: R(4,6;3) >= {n + 1}, complete enumeration, both readings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
