"""Verifier for hypergraph Ramsey lower-bound witnesses, R(s,t;k) >= n+1.

A witness is a 2-colouring chi of the k-subsets of [n] with no s-set all of whose
k-subsets are colour 0, and no t-set all of whose k-subsets are colour 1.
Exhibiting one certifies R(s,t;k) >= n+1  (DS1 convention, rev #18 p.5:
R is the LEAST n forcing a monochromatic clique, so a good colouring on n
elements gives R > n).

Design constraints this file is written against:

  §4  No implicit parameters. Every function takes (n, s, t, k) explicitly, so
      the production path can be exercised at a published value (R(4,4;3)=13)
      and at the target (R(5,5;4)), not just at the one it was calibrated on.
  §6  Completeness certificate asserted IN THE RUN: the number of s-subsets
      actually examined must equal comb(n, s), computed, never hard-coded.
  §2  Two independent verifiers over different enumerations, plus a negative
      control that MUST fail. A verifier that only ever sees valid input is
      untested.

The two verifiers share the index convention (lexicographic order of k-subsets,
i.e. the order itertools.combinations emits) but nothing else:

  verify_lex   -- itertools enumeration + dict lookup
  verify_rank  -- integer unranking + closed-form lex rank, no itertools, no dict

Agreement between them is meaningful because the rank arithmetic is an
independent reimplementation of the same index; `selftest_rank_matches_lex`
pins the formula against the enumeration.
"""

from __future__ import annotations

from itertools import combinations
from math import comb
from typing import Iterator, Sequence

__all__ = [
    "lex_rank",
    "lex_unrank",
    "verify_lex",
    "verify_rank",
    "verify_both",
    "selftest_rank_matches_lex",
    "VerificationResult",
]


class VerificationResult:
    """Outcome of one verification pass.

    `ok` is the verdict. `witness` is the first violating s- or t-set found
    (None when ok), so a failure is diagnosable rather than a bare False.
    `examined` is the number of cliques actually inspected. `checked_sizes` is
    the §6 completeness ledger, keyed by (clique size, forbidden colour) --
    keyed by size alone the two passes collide whenever s == t, which silently
    doubled the count until a production-size gate caught it.
    """

    __slots__ = (
        "ok", "witness", "witness_colour", "examined", "checked_sizes",
        "violations",
    )

    def __init__(
        self, ok, witness, witness_colour, examined, checked_sizes, violations=0
    ):
        self.ok = ok
        self.witness = witness
        self.witness_colour = witness_colour
        self.examined = examined
        self.checked_sizes = checked_sizes
        self.violations = violations

    def __repr__(self):
        if self.ok:
            return f"<VerificationResult ok examined={self.examined}>"
        return (
            f"<VerificationResult FAIL colour={self.witness_colour} "
            f"witness={self.witness} violations={self.violations} "
            f"examined={self.examined}>"
        )


# --------------------------------------------------------------------------
# Index arithmetic: lexicographic rank/unrank of k-subsets of [0, n).
# --------------------------------------------------------------------------


def lex_rank(subset: Sequence[int], n: int, k: int) -> int:
    """Lexicographic rank of a strictly increasing k-subset of [0, n).

    Matches the order itertools.combinations(range(n), k) emits.

    rank = C(n,k) - 1 - sum_{i=1..k} C(n-1-c_i, k-i+1)
    """
    if len(subset) != k:
        raise ValueError(f"expected a {k}-subset, got length {len(subset)}")
    total = 0
    for i, c in enumerate(subset, start=1):
        total += comb(n - 1 - c, k - i + 1)
    return comb(n, k) - 1 - total


def lex_unrank(r: int, n: int, k: int) -> tuple[int, ...]:
    """Inverse of lex_rank: the r-th k-subset of [0, n) in lexicographic order."""
    if not 0 <= r < comb(n, k):
        raise ValueError(f"rank {r} out of range for C({n},{k})")
    out = []
    c = 0
    remaining = k
    while remaining:
        # How many subsets start with the current prefix followed by c?
        block = comb(n - c - 1, remaining - 1)
        if r < block:
            out.append(c)
            remaining -= 1
            c += 1
        else:
            r -= block
            c += 1
    return tuple(out)


def selftest_rank_matches_lex(n: int, k: int) -> int:
    """Pin lex_rank/lex_unrank against the actual enumeration order.

    Returns the number of subsets checked. Raises AssertionError on any
    mismatch. This is what makes agreement between the two verifiers evidence
    rather than a shared bug: it tests the arithmetic against the enumeration
    it claims to reproduce.
    """
    count = 0
    for expected_rank, subset in enumerate(combinations(range(n), k)):
        got = lex_rank(subset, n, k)
        assert got == expected_rank, (
            f"lex_rank{subset} = {got}, enumeration says {expected_rank}"
        )
        back = lex_unrank(expected_rank, n, k)
        assert back == subset, f"lex_unrank({expected_rank}) = {back}, want {subset}"
        count += 1
    assert count == comb(n, k), f"enumerated {count}, expected C({n},{k})={comb(n, k)}"
    return count


# --------------------------------------------------------------------------
# Verifier A: itertools enumeration + dict lookup.
# --------------------------------------------------------------------------


def verify_lex(
    n: int, s: int, t: int, k: int, chi: Sequence[int], stop_early: bool = True
) -> VerificationResult:
    """Verify chi has no mono s-set in colour 0 and no mono t-set in colour 1.

    chi is indexed by the lexicographic rank of the k-subset. Enumerates every
    s-subset (and t-subset) with itertools and looks up each of its k-subsets
    in a precomputed dict.

    stop_early=False completes the full sweep even after a violation, so the §6
    completeness certificate can be exercised at production size on a colouring
    that is not a witness. `violations` then counts every offending clique.
    """
    _check_shape(n, s, t, k, chi)
    index = {sub: i for i, sub in enumerate(combinations(range(n), k))}
    assert len(index) == comb(n, k), "index build lost entries"

    examined = 0
    checked_sizes = {}
    first = None
    violations = 0
    for size, colour in _targets(s, t):
        seen = 0
        for clique in combinations(range(n), size):
            seen += 1
            if all(chi[index[sub]] == colour for sub in combinations(clique, k)):
                violations += 1
                if first is None:
                    first = (clique, colour)
                if stop_early:
                    checked_sizes[(size, colour)] = seen
                    return VerificationResult(
                        False, clique, colour, examined + seen, checked_sizes,
                        violations,
                    )
        # §6: completeness certificate, computed not hard-coded.
        assert seen == comb(n, size), (
            f"examined {seen} {size}-subsets, expected C({n},{size})={comb(n, size)}"
        )
        checked_sizes[(size, colour)] = seen
        examined += seen
    if first is not None:
        return VerificationResult(
            False, first[0], first[1], examined, checked_sizes, violations
        )
    return VerificationResult(True, None, None, examined, checked_sizes, 0)


# --------------------------------------------------------------------------
# Verifier B: integer unranking + closed-form rank. No itertools, no dict.
# --------------------------------------------------------------------------


def verify_rank(
    n: int, s: int, t: int, k: int, chi: Sequence[int], stop_early: bool = True
) -> VerificationResult:
    """Same check as verify_lex, by an independent route.

    Walks the s-subsets by unranking integers 0 .. C(n,s)-1, and computes each
    k-subset index with the closed-form lex_rank. Shares no data structure and
    no enumeration call with verify_lex.
    """
    _check_shape(n, s, t, k, chi)

    examined = 0
    checked_sizes = {}
    first = None
    violations = 0
    for size, colour in _targets(s, t):
        total = comb(n, size)
        seen = 0
        for r in range(total):
            clique = lex_unrank(r, n, size)
            seen += 1
            if all(
                chi[lex_rank(sub, n, k)] == colour
                for sub in _subsets_of(clique, k)
            ):
                violations += 1
                if first is None:
                    first = (clique, colour)
                if stop_early:
                    checked_sizes[(size, colour)] = seen
                    return VerificationResult(
                        False, clique, colour, examined + seen, checked_sizes,
                        violations,
                    )
        # §6: completeness certificate.
        assert seen == total, f"examined {seen} {size}-subsets, expected {total}"
        checked_sizes[(size, colour)] = seen
        examined += seen
    if first is not None:
        return VerificationResult(
            False, first[0], first[1], examined, checked_sizes, violations
        )
    return VerificationResult(True, None, None, examined, checked_sizes, 0)


def _subsets_of(clique: Sequence[int], k: int) -> Iterator[tuple[int, ...]]:
    """k-subsets of a sorted tuple, by index unranking rather than itertools."""
    m = len(clique)
    for r in range(comb(m, k)):
        positions = lex_unrank(r, m, k)
        yield tuple(clique[p] for p in positions)


# --------------------------------------------------------------------------


def _targets(s: int, t: int):
    """The (clique size, forbidden colour) pairs to check.

    Deduplicated when s == t and the two colours impose the same size, so the
    completeness assertion counts each size exactly once per colour.
    """
    return ((s, 0), (t, 1))


def _check_shape(n, s, t, k, chi) -> None:
    if not (0 < k < min(s, t) <= n):
        raise ValueError(f"bad parameters: n={n} s={s} t={t} k={k}")
    expected = comb(n, k)
    if len(chi) != expected:
        raise ValueError(
            f"colouring has {len(chi)} entries, expected C({n},{k}) = {expected}"
        )
    bad = {c for c in chi} - {0, 1}
    if bad:
        raise ValueError(f"colouring must be 0/1, saw {sorted(bad)[:5]}")


def verify_both(n: int, s: int, t: int, k: int, chi: Sequence[int]) -> bool:
    """Run both verifiers and require exact agreement.

    Disagreement is a defect in this file, not a property of chi, so it raises
    rather than returning a verdict.
    """
    a = verify_lex(n, s, t, k, chi)
    b = verify_rank(n, s, t, k, chi)
    if a.ok != b.ok:
        raise AssertionError(
            f"verifiers disagree on (n={n},s={s},t={t},k={k}): "
            f"lex={a!r} rank={b!r}"
        )
    if a.checked_sizes != b.checked_sizes:
        raise AssertionError(
            f"verifiers examined different counts: {a.checked_sizes} vs "
            f"{b.checked_sizes}"
        )
    return a.ok
