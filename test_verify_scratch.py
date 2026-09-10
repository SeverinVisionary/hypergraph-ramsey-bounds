"""The third verifier must agree with the other two, and must not share them.

`verify.py`, `independent_check.py` and the producer `ansatz.py` all build
their face indexing with `itertools.combinations`. `verify_scratch.py` derives
lexicographic order from explicit nested loops instead, so agreement between
them is evidence that the ordering convention is correct rather than merely
shared.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import verify_scratch

HERE = Path(__file__).parent
WITNESSES = ["witness_n33.json", "witness_n34.json", "witness_n35.json"]


def test_verify_scratch_imports_nothing_from_the_repo_or_itertools():
    """The point of this file is the absence of the common mode. Guard it.

    Checked against the parsed import statements, not the raw text -- the
    module's own docstring says the word "itertools" while explaining why it
    does not use it, and a substring guard would flag that.
    """
    import ast
    tree = ast.parse((HERE / "verify_scratch.py").read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    banned = {"itertools", "verify", "ansatz", "obstruction", "capped", "brute",
              "grouporder", "extend", "cyclic", "independent_check"}
    assert not (imported & banned), f"common mode reintroduced: {imported & banned}"
    assert imported <= {"json", "sys"}, f"unexpected dependency: {imported}"


@pytest.mark.parametrize("name", WITNESSES)
def test_each_witness_passes_the_scratch_verifier(name):
    path, ok, msg = verify_scratch.check(str(HERE / name))
    assert ok, msg


@pytest.mark.parametrize("name,expected_bound", [
    ("witness_n33.json", 34), ("witness_n34.json", 35), ("witness_n35.json", 36),
])
def test_the_bound_each_witness_certifies(name, expected_bound):
    _, ok, msg = verify_scratch.check(str(HERE / name))
    assert ok and f">= {expected_bound}" in msg, msg


def test_scratch_face_index_agrees_with_itertools_lex_order():
    """The two derivations of 'lexicographic' must coincide -- checked here
    rather than assumed, since everything rests on it."""
    from itertools import combinations
    for n in (7, 9, 12):
        mine, count = verify_scratch.face_index(n)
        theirs = {f: i for i, f in enumerate(combinations(range(n), 4))}
        assert mine == theirs, n
        assert count == len(theirs)


def test_a_corrupted_witness_is_rejected(tmp_path):
    """Negative control: the verifier must be capable of saying FAIL.

    The scratch file goes in pytest's tmp_path, not beside the sources: an
    earlier version wrote a fixed name into the repository and unlinked it
    afterwards, which destroys anything a reader happened to have at that path.
    """
    import json
    doc = json.loads((HERE / "witness_n35.json").read_text())
    doc["chi"] = [0] * len(doc["chi"])          # all one colour: every K5 mono
    tmp = tmp_path / "corrupt.json"
    tmp.write_text(json.dumps(doc))
    _, ok, msg = verify_scratch.check(str(tmp))
    assert not ok and "monochromatic" in msg
