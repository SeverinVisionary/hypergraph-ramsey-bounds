"""Hash-bound verification of the R(5,5;4) >= 36 witness, by two checkers.

The counterpart of verify_witness_n63.py and verify_witness_n83.py. It exists
because the R(5,5;4) verification was the one headline claim whose deposited
log named only a FILENAME: both checkers ran and passed, but nothing in the
transcript bound that run to the bytes that ship. A filename is not an object.

Runs both from-scratch checkers on the same object:

  * verify_scratch.py  -- builds the face ordering with explicit nested loops,
    no itertools, no rank formula;
  * independent_check.py -- never computes a rank at all, pairing the colour
    list against a fresh enumeration and working with frozensets thereafter.

They share no code with each other or with the search, so a systematic error in
the index convention cannot be common to them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys

import independent_check
import verify_scratch

PUBLISHED_SHA = "54119af44254165930c290457bad04742218deb9185ce6b2f0f97931c00ac6f3"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--witness", default="witness_n35.json")
    ap.add_argument("--expect-sha", default=PUBLISHED_SHA)
    a = ap.parse_args()

    with open(a.witness) as fh:
        doc = json.load(fh)
    print(f"witness      {a.witness}")
    print(f"declares     n={doc['n']} s={doc['s']} t={doc['t']} k={doc['k']}  "
          f"{doc.get('ansatz')}")
    print(f"certifies    {doc.get('certifies')}")

    got = hashlib.sha256(json.dumps(doc["chi"]).encode()).hexdigest()
    print(f"sha256       {got}")
    if got != a.expect_sha:
        print(f"MISMATCH: expected {a.expect_sha}", file=sys.stderr)
        return 1

    print("\nchecker 1: verify_scratch (explicit nested loops)")
    _, ok1, msg1 = verify_scratch.check(a.witness)
    print(f"  {'PASS' if ok1 else 'FAIL'}: {msg1}")

    print("checker 2: independent_check (no rank arithmetic anywhere)")
    # THREE values, not two. verify_scratch.check and
    # independent_check.check_witness both return (path, ok, msg); unpacking
    # either into a pair raises, and testing the tuple for truthiness -- which
    # is the mistake that made a rejection branch unreachable elsewhere in this
    # package -- would silently always pass.
    _, ok2, msg2 = independent_check.check_witness(a.witness)
    print(f"  {'PASS' if ok2 else 'FAIL'}: {msg2}")

    if not (ok1 and ok2):
        print("\nFAILED: at least one from-scratch checker rejected the "
              "witness", file=sys.stderr)
        return 1

    print(f"\nOK: R(5,5;4) >= {doc['n'] + 1}, two independent checkers, bound "
          f"to sha256 {got[:16]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
