"""The aggregate counts in SWEET_SPOT.md, recomputed from the shipped files.

A number like "110 measured classes" is unfalsifiable once the record it
summarises has moved, and this one had: the shipped records hold 200 rows. The
count is now derived here rather than remembered, so the prose and the deposit
cannot drift apart silently.
"""

from __future__ import annotations

import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))


def measured():
    """(rows, distinct (name, n) pairs, sorted n values) over the records."""
    rows, pairs, ns = 0, set(), set()
    files = (sorted(glob.glob(os.path.join(ROOT, "ansatz*_results.json")))
             + sorted(glob.glob(os.path.join(ROOT, "cell_*.json"))))
    for f in files:
        with open(f) as fh:
            d = json.load(fh)
        if not isinstance(d, list):
            continue
        for r in d:
            n = r.get("n")
            if n is None:
                m = re.search(r"n(\d+)", os.path.basename(f))
                n = int(m.group(1)) if m else None
            rows += 1
            pairs.add((r.get("name"), n))
            if n:
                ns.add(n)
    return rows, len(pairs), sorted(ns)


def test_the_quoted_counts_are_the_computed_ones():
    rows, pairs, ns = measured()
    with open(os.path.join(ROOT, "SWEET_SPOT.md")) as fh:
        text = re.sub(r"\s+", " ", fh.read())
    assert f"**{rows} rows**" in text, f"prose does not quote {rows} rows"
    assert f"**{pairs} distinct (class, n) pairs**" in text, \
        f"prose does not quote {pairs} distinct pairs"
    quoted = re.search(r"pairs\*\* at n = ([\d, and]+?)(?: \(|\.)", text)
    assert quoted, "prose does not list the n values"
    listed = [int(x) for x in re.findall(r"\d+", quoted.group(1))]
    assert listed == ns, f"prose lists {listed}, records hold {ns}"


def test_there_is_something_to_count():
    """A baseline: the check above would pass on an empty record set only if
    the prose also said zero, but an empty glob would be a silent failure."""
    rows, pairs, ns = measured()
    assert rows > 100 and pairs > 100 and len(ns) > 5
