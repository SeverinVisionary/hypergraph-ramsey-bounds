"""Hash-bound, complete verification of the R(4,4,4;3) >= 84 witness.

The counterpart of verify_witness_n63.py for the three-colour cell, and written
for the same reason: the deposit claimed every headline witness was checked by
a verifier independent of the search, and shipped a hash-bound transcript for
only one of them.

It does not reuse the producer's rank arithmetic: it rebuilds the triple ->
colour map by zipping the stored colour vector against a freshly generated
enumeration and then works with frozensets. That reduces one class of
implementation failure while leaving the stated serialization, witness
specification and runtime assumptions shared.

Four numbers must come out right, and any one wrong is a non-zero exit:

  * the SHA-256 of the colour vector, binding this run to one exact object;
  * C(83,3) = 91,881 colours present, all in {0,1,2};
  * zero 4-sets monochromatic in ANY of the three colours, over all
    C(83,4) = 1,837,620 of them -- the claim;
  * and, as a discriminating control, recolouring a single triple must create
    at least one monochromatic 4-set. A checker that returns zero whatever it
    is handed would pass the third test and fail this one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from itertools import combinations

PUBLISHED_SHA = "a08602b488ec0f899412ce5cc31ec34a69c05995c1432fd74c04cae9467ecce2"


def colour_map(chi, n):
    subsets = [frozenset(c) for c in combinations(range(n), 3)]
    if len(subsets) != len(chi):
        raise AssertionError(f"{len(chi)} colours for {len(subsets)} triples")
    return dict(zip(subsets, chi))


def mono_four_sets(cmap, n, limit=None):
    """Every 4-set whose four triples share a colour. Straight from the
    definition; no ranks, no early algebra."""
    bad = []
    for W in combinations(range(n), 4):
        faces = [cmap[frozenset(f)] for f in combinations(W, 3)]
        if faces[0] == faces[1] == faces[2] == faces[3]:
            bad.append((W, faces[0]))
            if limit and len(bad) >= limit:
                return bad
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--witness", default="witness_444_3_n83.json")
    ap.add_argument("--expect-sha", default=PUBLISHED_SHA)
    a = ap.parse_args()

    with open(a.witness) as fh:
        doc = json.load(fh)
    n, chi = doc["n"], doc["chi"]
    print(f"witness      {a.witness}")
    print(f"declares     n={n} sizes={doc.get('sizes')} k={doc.get('k')}  "
          f"{doc.get('ansatz')}")
    print(f"certifies    {doc.get('certifies')}")

    # The wrapper scans a hard-coded three-colour R(4,4,4;3) reading, so the
    # declaration must agree with the target that is actually checked.
    WANT = {"sizes": [4, 4, 4], "k": 3}
    declared = {"sizes": doc.get("sizes"), "k": doc.get("k")}
    if declared != WANT:
        print(f"MISMATCH: {a.witness} declares {declared}, but this verifier "
              f"checks {WANT}; the declaration and the check are different "
              f"claims", file=sys.stderr)
        return 1

    got = hashlib.sha256(json.dumps(chi).encode()).hexdigest()
    print(f"sha256       {got}")
    if got != a.expect_sha:
        print(f"MISMATCH: expected {a.expect_sha}", file=sys.stderr)
        return 1

    n_faces = n * (n - 1) * (n - 2) // 6
    print(f"faces        {len(chi)} expected C({n},3)={n_faces}")
    if len(chi) != n_faces:
        print("MISMATCH: wrong number of faces", file=sys.stderr)
        return 1
    if any(v not in (0, 1, 2) for v in chi):
        print("MISMATCH: colour outside {0,1,2}", file=sys.stderr)
        return 1
    for c in (0, 1, 2):
        print(f"colour {c}     {chi.count(c)}")

    cmap = colour_map(chi, n)
    total = n * (n - 1) * (n - 2) * (n - 3) // 24
    print(f"scanning all C({n},4) = {total} four-subsets ...", flush=True)
    bad = mono_four_sets(cmap, n)
    print(f"  monochromatic 4-sets: {len(bad)}   (want 0)")
    if bad:
        print(f"FAILED: e.g. {bad[0]}", file=sys.stderr)
        return 1

    print("control: recolour one triple and require the scan to notice ...",
          flush=True)
    victim = next(iter(cmap))
    perturbed = dict(cmap)
    perturbed[victim] = (perturbed[victim] + 1) % 3
    found = mono_four_sets(perturbed, n, limit=1)
    print(f"  monochromatic 4-sets after perturbation: "
          f"{'>=1' if found else '0'}   (want >=1)")
    if not found:
        print("FAILED: the scan is not discriminating -- perturbing a triple "
              "produced no violation", file=sys.stderr)
        return 1

    print(f"\nOK: R(4,4,4;3) >= {n + 1}, complete enumeration, three colours.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
