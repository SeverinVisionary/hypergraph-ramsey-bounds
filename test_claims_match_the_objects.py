"""Every witness's class, as claimed in prose, is the class in the object.

A property true of one object is easily asserted of another: the n=79 witness
described as sitting in the same group as n=80/81 (it is `C_39`, they are
`C_13 + m`), or Theorem B's conclusion about `C_41 + 1 fixed` written as though
it were about `C_41`, which is the n=83 witness class. Reading alone does not
catch that reliably -- the sentences are individually plausible -- so the
mapping is pinned here against the shipped objects.
"""

from __future__ import annotations

import glob
import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))

# (file, n, ansatz, certifies). Read off the deposited objects, and asserted
# against them below: if a witness is replaced, this table must be updated,
# which is the point.
WITNESSES = [
    ("witness_444_3_n79.json", 79, "Z_79 : C_39",          "R(4,4,4;3) >= 80"),
    ("witness_444_3_n80.json", 80, "Z_79 : C_13 + 1 fixed", "R(4,4,4;3) >= 81"),
    ("witness_444_3_n81.json", 81, "Z_79 : C_13 + 2 fixed", "R(4,4,4;3) >= 82"),
    ("witness_444_3_n82.json", 82, "Z_73 : C_9 + 9 fixed",  "R(4,4,4;3) >= 83"),
    ("witness_444_3_n83.json", 83, "Z_83 : C_41",           "R(4,4,4;3) >= 84"),
    ("witness_46_3_n63.json",  63,
     "Z_63 : <10,19,37,46,55> order 378",                   "R(4,6;3) >= 64"),
    ("witness_n26.json", 26, None, "R(5,5;4) >= 27"),
    ("witness_n31.json", 31, None, "R(5,5;4) >= 32"),
    ("witness_n32.json", 32, None, "R(5,5;4) >= 33"),
    ("witness_n33.json", 33, None, "R(5,5;4) >= 34"),
    ("witness_n34.json", 34, "Hol(Z_34) | 34pt", "R(5,5;4) >= 35"),
    ("witness_n35.json", 35, "Hol(Z_34)",        "R(5,5;4) >= 36"),
]


@pytest.mark.parametrize("fn,n,ansatz,certifies", WITNESSES)
def test_each_witness_is_the_object_the_table_says(fn, n, ansatz, certifies):
    with open(os.path.join(ROOT, fn)) as fh:
        doc = json.load(fh)
    assert doc["n"] == n
    assert doc.get("ansatz") == ansatz
    assert doc["certifies"] == certifies


def test_the_table_covers_every_shipped_witness():
    """Otherwise a new witness could be added and never checked here."""
    on_disk = {os.path.basename(p)
               for p in glob.glob(os.path.join(ROOT, "witness_*.json"))}
    assert on_disk == {fn for fn, *_ in WITNESSES}


@pytest.mark.parametrize("fn,n,ansatz,certifies", WITNESSES)
def test_certifies_is_one_more_than_the_point_count(fn, n, ansatz, certifies):
    """DS1's convention: a good colouring on n points gives R >= n + 1. A
    witness whose `certifies` field is off by one would overstate a bound."""
    m = re.search(r">= (\d+)$", certifies)
    assert m and int(m.group(1)) == n + 1


def _prose(flat=False):
    """The prose files, raw by default. `flat=True` collapses whitespace, for
    the checks that look for a phrase which may wrap across a newline."""
    out = {}
    # `.zenodo.json` is included deliberately: when both files are present,
    # Zenodo uses it and ignores CITATION.cff, so a claim corrected in the .cff
    # and left wrong there is the version that gets archived. That is exactly
    # what happened to the "pair-regular class is empty" sentence.
    import deposit_paths
    for name, pick in (("CELLS.md", deposit_paths.resolve),
                       ("THEOREMS.md", deposit_paths.resolve),
                       ("SWEET_SPOT.md", deposit_paths.resolve),
                       ("README.md", deposit_paths.resolve_scaffolded),
                       ("CITATION.cff", deposit_paths.resolve_scaffolded),
                       (".zenodo.json", deposit_paths.resolve_scaffolded)):
        p = pick(name)
        if p:
            with open(p) as fh:
                text = fh.read()
            out[name] = re.sub(r"\s+", " ", text) if flat else text
    return out


# The vocabulary of class names this deposit uses. A sentence about a witness
# that names one of these must name the right one.
CLASS_RE = re.compile(
    r"(Z_\d+ : <[\d,]+>(?: order \d+)?"   # the n=63 class's own spelling
    r"|Z_\d+ : C_\d+(?: \+ \d+ fixed)?"
    r"|Hol\(Z_\d+\)(?: \+ \d+ fixed)?(?: \| \d+pt)?"
    r"|C_\d+ \+ \d+ fixed"
    r"|C_\d+(?!\d)(?! \+ \d+ fixed))")
N_RE = re.compile(r"\bn\s*=\s*(\d+)"          # n=83, n = 83
                  r"|\bat (\d+) points\b"       # at 83 points
                  r"|\b(\d+)-set\b"             # an 83-set
                  r"|\b(\d+)-point\b"           # the 83-point witness
                  r"|\|\s*(\d+)\s*\|")        # a bare table cell

BY_N = {n: ansatz for _fn, n, ansatz, _c in WITNESSES if ansatz}


def _accepted(ansatz):
    """(see below) -- the n=63 class is written with and without its order."""
    """Ways the prose may name this class and still be right.

    The part after the base -- `C_39`, or `C_13 + 1 fixed` -- is how the
    write-ups refer to a class inside a tower whose base is already named. The
    fixed-point count is never dropped: `C_13` does not stand for
    `C_13 + 1 fixed`, since telling those apart is the point of this gate.
    """
    names = {ansatz}
    if " : " in ansatz:
        names.add(ansatz.split(" : ", 1)[1])
    # "Z_63 : <10,19,37,46,55> order 378" is also written without the order.
    stripped = re.sub(r" order \d+$", "", ansatz)
    if stripped != ansatz:
        names.add(stripped)
        names.add(stripped.split(" : ", 1)[1])
    return names


def _units(raw):
    """Split raw markdown into claim-sized units.

    A markdown table row is its own unit: a flattened table is one long run
    with no sentence-ending punctuation, and every row's class name would
    otherwise be available to every other row's claim. Everything else is
    sentence-split.
    """
    units, buf = [], []
    for line in raw.splitlines():
        if line.lstrip().startswith("|"):
            if buf:
                units.extend(re.split(r"(?<=[.!?])\s+",
                                      re.sub(r"\s+", " ", " ".join(buf))))
                buf = []
            units.append(re.sub(r"\s+", " ", line))
        else:
            buf.append(line)
    if buf:
        units.extend(re.split(r"(?<=[.!?])\s+",
                              re.sub(r"\s+", " ", " ".join(buf))))
    return [u for u in units if u.strip()]


# Words that introduce a claim about a deposited object. "witness" alone was
# not enough: "The n=79 construction lies in Z_79 : C_13 + 1 fixed" is the same
# false attribution written with a different noun, and was invisible.
OBJECT_WORDS = re.compile(
    r"\b(witness|witnesses|construction|colouring|coloring|object|"
    r"was found|is found|found under|sits (?:at|in)|lies in)\b", re.I)


def _names_an_object(text):
    return bool(OBJECT_WORDS.search(text))


def witness_sentence_problems(raw):
    """Units that claim a witness at some n and name the wrong class.

    Only units containing 'witness' are read: that is the claim this package
    has twice got wrong, and it is the claim that can be settled against the
    deposited objects. A unit naming several classes is satisfied by naming
    the right one -- what is caught is a witness attributed to a class that is
    not its own, not the mention of neighbours.
    """
    problems = []
    for unit in _units(raw):
        if not _names_an_object(unit):
            continue
        # Per CLAUSE, not per unit. "At n=79, Z_79 : C_39 is UNSAT, while the
        # witness sits in Z_79 : C_13 + 1 fixed" attributes the witness to the
        # wrong class while still mentioning the right one somewhere, and a
        # whole-unit check passes it. The separators are matched with or
        # without a preceding comma: requiring one let the same sentence
        # through unpunctuated.
        for clause in re.split(
                r",?\s+(?:while|but|whereas|though|although|yet|however)\s+"
                r"|;\s+|,\s+and\s+|\s+--\s+|\s+—\s+"
                # "X, not Y" and "X rather than Y": the contrast puts two
                # classes in one clause, and taking the set of both lets the
                # correct one excuse the wrong attribution beside it.
                r"|,?\s+(?:not|rather than|as opposed to|instead of)\s+(?=[A-Z(]|Z_|C_|Hol)",
                unit):
            if not _names_an_object(clause):
                continue
            _check_clause(unit, clause, problems)
    return problems


def _check_clause(unit, clause, problems):
        classes = set(CLASS_RE.findall(clause))
        # An n named in the unit but not in this clause still scopes it: a
        # table row puts the n in one cell and the class in another.
        if not classes:
            classes = set(CLASS_RE.findall(unit))
        if not classes:
            return
        # `+N fixed` written apart from the class name still composes with it:
        # a table row reading "`Z_79 : C_13` | ... | `+1 fixed` holds the n=80
        # witness" names Z_79 : C_13 + 1 fixed, in two pieces.
        for m in re.finditer(r"\+\s*(\d+) fixed", unit):
            for c in list(classes):
                if "fixed" not in c and " : " in c:
                    classes.add(f"{c} + {m.group(1)} fixed")
        ns = {int(g) for m in N_RE.finditer(clause) for g in m.groups() if g}
        if not ns:
            ns = {int(g) for m in N_RE.finditer(unit) for g in m.groups() if g}
        for n in sorted(ns & set(BY_N)):
            if not (_accepted(BY_N[n]) & classes):
                problems.append((n, BY_N[n], sorted(classes),
                                 clause.strip()[:160]))


def test_no_prose_attributes_a_witness_to_the_wrong_class():
    for rel, text in _prose().items():
        problems = witness_sentence_problems(text)
        assert not problems, f"{rel}: {problems}"


def test_the_prose_gate_catches_a_wrong_attribution():
    """Without this the gate above could be a function that finds nothing.
    Both mutations are ones this package actually shipped at some point."""
    bad = ("The witness at n=79 was found under Z_79 : C_13 + 1 fixed.")
    assert witness_sentence_problems(bad)
    bad = ("At n=82 the witness sits in Z_79 : C_13 + 2 fixed.")
    assert witness_sentence_problems(bad)
    bad = ("Both R(5,5;4) witnesses came from Hol(Z_34), at n=34 and n=35.")
    assert witness_sentence_problems(bad)
    # The subgroup alone must not stand in for a fixed-point extension.
    bad = ("The witness at n=80 sits at C_13.")
    assert witness_sentence_problems(bad)
    # A clause that attributes the witness to the wrong class while naming the
    # right one elsewhere in the same sentence.
    bad = ("At n=79, Z_79 : C_39 is UNSAT, while the witness sits in "
           "Z_79 : C_13 + 1 fixed.")
    assert witness_sentence_problems(bad)
    # An n written as "79-point", which the earlier pattern did not see.
    bad = ("The 79-point witness was found under Z_79 : C_13 + 1 fixed.")
    assert witness_sentence_problems(bad)
    # A bare table cell for n.
    bad = ("| 79 | Z_79 : C_13 + 1 fixed | holds the witness |")
    assert witness_sentence_problems(bad)
    # The same false attribution with no comma before "but".
    bad = ("At n=79, Z_79 : C_39 is UNSAT but the witness sits in "
           "Z_79 : C_13 + 1 fixed.")
    assert witness_sentence_problems(bad)
    # And with a different noun for the object.
    bad = ("The n=79 construction lies in Z_79 : C_13 + 1 fixed.")
    assert witness_sentence_problems(bad)
    # "yet" as the clause separator, which but/while did not cover.
    bad = ("At n=79, Z_79 : C_39 is UNSAT, yet the construction lies in "
           "Z_79 : C_13 + 1 fixed.")
    assert witness_sentence_problems(bad)
    # The n=63 class has its own spelling, which the pattern did not read at
    # all -- so no claim about that witness could ever have been checked.
    bad = ("The n=63 witness was found under Z_79 : C_39.")
    assert witness_sentence_problems(bad)
    # A contrast inside one clause: the correct class appears, but as the thing
    # being contrasted AGAINST, not as the attribution.
    bad = ("At n=79 the witness lies in Z_79 : C_13 + 1 fixed, "
           "not Z_79 : C_39.")
    assert witness_sentence_problems(bad)
    bad = ("At n=79 the witness sits in Z_79 : C_13 + 1 fixed rather than "
           "Z_79 : C_39.")
    assert witness_sentence_problems(bad)


def test_the_prose_gate_accepts_a_right_attribution():
    ok = ("The witness at n=79 was found under Z_79 : C_39, and the one at "
          "n=80 under Z_79 : C_13 + 1 fixed.")
    assert witness_sentence_problems(ok) == []
    ok = ("The n=34 witness uses Hol(Z_34) | 34pt.")
    assert witness_sentence_problems(ok) == []
    ok = ("The n=63 witness sits in Z_63 : <10,19,37,46,55> order 378.")
    assert witness_sentence_problems(ok) == []
    ok = ("The n=63 witness sits in Z_63 : <10,19,37,46,55>.")
    assert witness_sentence_problems(ok) == []


def test_the_pair_regular_classes_are_never_called_empty():
    """`Z_83 : C_41` and `Z_79 : C_39` HOLD witnesses. Theorem B is about the
    fixed-point extension, and the two must not be conflated -- the deposit's
    metadata said the base classes were empty."""
    for rel, text in _prose(flat=True).items():
        for cls in ("Z_83 : C_41", "Z_79 : C_39", "C_41", "C_39"):
            for m in re.finditer(re.escape(cls) + r"[^.]{0,40}?is empty", text):
                span = m.group(0)
                assert "fixed" in span, f"{rel}: {span!r}"


def test_that_empty_gate_catches_the_conflation():
    text = "Theorem B explains why Z_83 : C_41 is empty."
    hit = re.search(r"Z_83 : C_41[^.]{0,40}?is empty", text)
    assert hit and "fixed" not in hit.group(0)


def test_n79_and_n80_are_not_described_as_the_same_group():
    """They are `C_39` (order 3081) and `C_13 + 1 fixed` (order 1027)."""
    text = _prose(flat=True)["CELLS.md"]
    assert "All three witnesses use the same affine group" not in text


# --- Theorem B's threshold is a hypothesis, not a detail -------------------
#
# The citable metadata has stated this theorem without its threshold twice.
# The package's own n=79 witness refutes the short form: adjoin a fixed point
# and a fourth colour and the extension has a good invariant colouring, so
# "regular on pairs => the extension is empty" is false as a general claim.

# Matched against text with markup REMOVED. The previous pattern looked for
# `admits no invariant good colouring` and two siblings, and matched ZERO
# sentences in the whole corpus -- the deposit writes the conclusion as
# "no `G`-invariant good colouring exists", with backticks inside the phrase,
# and as "adjoining a fixed point empties them". So a test labelled "no file
# states Theorem B without its threshold" executed its assertion not once.
# The floor below is what makes that failure impossible to repeat silently.
THEOREM_B_CONCLUSION = re.compile(
    r"(?:no [A-Za-z_ -]{0,30}invariant good colouring"
    r"|admits no invariant good colouring"
    r"|no good invariant colouring"
    r"|the extension is empty"
    r"|empties them)[^.]{0,200}", re.I)

# Naming the threshold means naming the RAMSEY NUMBER it is. Accepting the
# bare word "threshold" let a sentence pass by containing it in any sense --
# "no threshold is required" satisfied a check that the threshold be stated.
THRESHOLD_NAMED = re.compile(
    r"R\(4,4;3\)|R\(4,\s*\.\.\.\s*,4;3\)|R\(4,…,4;3\)|R\(4,4,4;3\)"
    r"|\(m-1\)-colour Ramsey number|m-1 colours")


def _demarkup(text):
    """Backticks and emphasis removed: the conclusion is written THROUGH them."""
    return re.sub(r"[`*_]", "", text)


# Theorems A and A' reach the SAME conclusion -- "no G-invariant good colouring
# exists" -- from different hypotheses, and neither needs a Ramsey threshold.
# Broadening the conclusion pattern until it matched the corpus therefore
# started flagging them, and "fixing" that by writing a threshold into A/A'
# would put a false claim in the file to satisfy a test. The threshold
# obligation belongs to Theorem B's argument specifically: the one that adjoins
# a fixed point to a pair-regular action. Only conclusions in that context are
# in scope.
THEOREM_B_CONTEXT = re.compile(
    r"fixed point|fixed-point|\+ 1 fixed|regular on (?:unordered )?pairs"
    r"|pair-regular|C\(p,2\)|adjoin", re.I)


def test_no_file_states_theorem_b_without_its_threshold():
    reached = 0
    for rel, text in _prose(flat=True).items():
        text = _demarkup(text)
        for m in THEOREM_B_CONCLUSION.finditer(text):
            window0 = text[max(0, m.start() - 700):m.end() + 700]
            if not THEOREM_B_CONTEXT.search(window0):
                continue          # Theorem A / A', which carry no threshold
            reached += 1
            window = text[max(0, m.start() - 700):m.end() + 700]
            assert THRESHOLD_NAMED.search(window), (
                f"{rel}: states Theorem B's conclusion without naming the "
                f"threshold it depends on: {m.group(0)[:120]!r}")
    # A universal over an empty match set is vacuously true, and that is
    # exactly how this check shipped: zero matches, corpus-wide, while its
    # name promised every file had been examined.
    assert reached >= 3, (
        f"the Theorem B threshold scan matched {reached} conclusion "
        f"sentence(s) in the whole corpus; it is passing because it found "
        f"nothing to check, not because the prose is right")


def test_the_metadata_records_that_m_equals_4_fails():
    """The counterexample is the reason the threshold is a hypothesis, and the
    two citable files are where the short form kept coming back."""
    prose = _prose(flat=True)
    # Both layouts, and the file must BE THERE. `if rel not in prose: continue`
    # `if rel not in prose: continue` checked nothing at all wherever the
    # first candidate path is absent -- a green run over an empty loop. Each
    # role is resolved across its candidate paths and its absence is a
    # failure, not a skip.
    for role in ("citation", "zenodo"):
        found = [rel for rel in PROSE_ROLES[role] if rel in prose]
        assert found, (
            f"no file resolved for the {role!r} metadata role (tried "
            f"{PROSE_ROLES[role]}); the caveat gate checked nothing. "
            f"Loaded: {sorted(prose)}")
        for rel in found:
            text = prose[rel]
            assert "m = 4" in text or "m=4" in text, f"{rel}: no m = 4 caveat"
            assert "R(4,4;3)" in text, f"{rel}: no threshold named"


def test_that_gate_would_catch_the_short_form():
    """Baseline: the scan must be able to fail on the wording that shipped."""
    bad = ("an affine group whose order equals C(p,2) and whose multiplier "
           "subgroup omits -1 acts regularly on unordered pairs and therefore "
           "admits no invariant good colouring once a fixed point is adjoined. "
           "The pair-regular class of each tower is the index-two subgroup.")
    hits = list(THEOREM_B_CONCLUSION.finditer(bad))
    assert hits
    window = bad[max(0, hits[0].start() - 700):hits[0].end() + 700]
    assert "R(4,4;3)" not in window and "threshold" not in window


# --- the gate must have something to read ------------------------------
# `_prose()` skips a file that is not there, and `witness_sentence_problems`
# returns clean when no unit names an object. Composed, those two silences
# make a green run that read nothing indistinguishable from a green run that
# read everything and found nothing -- the fail-open shape this package has
# now shipped several times. This test measures the scan instead of trusting
# it: every documentary ROLE must resolve to a file, and the scan must reach
# a floor of class-bearing clauses. The floors sit below the counts measured
# when this was written (20 clauses in total, 13 of them in
# CELLS.md) so that ordinary editing does not trip them, and far enough above
# zero to catch a corpus that failed to load or a CLASS_RE that stopped
# matching.
PROSE_ROLES = {
    "cells": ("CELLS.md",),
    "theorems": ("THEOREMS.md",),
    "sweet_spot": ("SWEET_SPOT.md",),
    "readme": ("README.md",),
    "citation": ("CITATION.cff",),
    "zenodo": (".zenodo.json",),
}


def _class_bearing_clauses(text):
    """Clauses the attribution gate actually reaches a verdict on."""
    n = 0
    for unit in _units(text):
        if not _names_an_object(unit):
            continue
        for clause in re.split(
                r",?\s+(?:while|but|whereas|though|although|yet|however)\s+"
                r"|;\s+|,\s+and\s+|\s+--\s+|\s+—\s+"
                r"|,?\s+(?:not|rather than|as opposed to|instead of)\s+"
                r"(?=[A-Z(]|Z_|C_|Hol)",
                unit):
            if not _names_an_object(clause):
                continue
            if CLASS_RE.findall(clause) or CLASS_RE.findall(unit):
                n += 1
    return n


def test_the_prose_corpus_is_actually_present():
    loaded = _prose()
    missing = [role for role, cands in PROSE_ROLES.items()
               if not any(c in loaded for c in cands)]
    assert not missing, (
        f"the attribution gate scanned no file for: {missing}. A role that "
        f"resolves to nothing makes the gate pass vacuously. Loaded: "
        f"{sorted(loaded)}")


def test_the_attribution_gate_reaches_a_verdict_on_real_clauses():
    per_file = {rel: _class_bearing_clauses(text)
                for rel, text in _prose().items()}
    total = sum(per_file.values())
    assert total >= 15, (
        f"the attribution gate reached a verdict on only {total} clauses; it "
        f"is passing because it read nothing, not because the prose is right. "
        f"Per file: {per_file}")
    cells = max(v for rel, v in per_file.items() if rel.endswith("CELLS.md"))
    assert cells >= 10, (
        f"CELLS.md contributed only {cells} class-bearing clauses to the "
        f"attribution gate; it is the per-cell record and carries most of the "
        f"witness attributions. Per file: {per_file}")
