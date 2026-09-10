"""Gates for verify.py. Run with: python3 -m pytest test_verify.py -q

These are the gates for the witness verifier, run on the production path at
production-shaped parameters. In particular:

  §2  Every "accepts a good object" test is paired with a negative control that
      MUST be rejected. Several are boundary pairs: one bit apart, one accepted
      and one rejected, so a verifier that is too lax fails the first half and
      one that is too strict fails the second.
  §4  Two different specialisations of (s,t,k) are pinned, not one -- 3-uniform
      and 4-uniform -- because one specialisation is the value a bug would have
      been calibrated on.
  §6  The completeness count is asserted against comb(), computed each time.
"""

from itertools import combinations
from math import comb

import pytest

from verify import (
    lex_rank,
    lex_unrank,
    selftest_rank_matches_lex,
    verify_both,
    verify_lex,
    verify_rank,
)


# --------------------------------------------------------------------------
# The index arithmetic must reproduce the enumeration it claims to.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("n,k", [(5, 4), (6, 4), (9, 3), (10, 4), (12, 3), (13, 3)])
def test_rank_roundtrips_against_enumeration(n, k):
    assert selftest_rank_matches_lex(n, k) == comb(n, k)


def test_rank_rejects_out_of_range():
    with pytest.raises(ValueError):
        lex_unrank(comb(8, 3), 8, 3)
    with pytest.raises(ValueError):
        lex_unrank(-1, 8, 3)


def test_rank_rejects_wrong_arity():
    with pytest.raises(ValueError):
        lex_rank((0, 1, 2), 8, 4)


# --------------------------------------------------------------------------
# Negative controls: these MUST be rejected.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("n,s,t,k", [(6, 5, 5, 4), (7, 5, 5, 4), (8, 4, 4, 3)])
def test_monochromatic_colouring_is_rejected(n, s, t, k):
    """All-one-colour is the crudest possible violation. If this passes, the
    verifier is not checking anything."""
    for colour in (0, 1):
        chi = [colour] * comb(n, k)
        res_lex = verify_lex(n, s, t, k, chi)
        res_rank = verify_rank(n, s, t, k, chi)
        assert not res_lex.ok, f"all-{colour} accepted at n={n} (lex)"
        assert not res_rank.ok, f"all-{colour} accepted at n={n} (rank)"
        assert res_lex.witness_colour == colour
        assert res_rank.witness_colour == colour


def test_planted_violation_is_caught_and_one_bit_repairs_it():
    """Boundary pair. Same colouring, one bit apart: rejected, then accepted.

    n=6, (5,5;4). Start from a colouring with no mono 5-set, force one 5-set to
    be all-colour-0, confirm rejection, then flip a single one of its 4-subsets
    and confirm acceptance. This is the test that a too-lax verifier fails on
    the first half and a too-strict one on the second.
    """
    n, s, t, k = 6, 5, 5, 4
    # Alternate colours by rank: no 5-set can be monochromatic by construction
    # for this small case (verified below before we break it).
    chi = [i % 2 for i in range(comb(n, k))]
    assert verify_both(n, s, t, k, chi), "baseline should be a valid witness"

    target = tuple(range(s))  # the 5-set {0,1,2,3,4}
    ranks = [lex_rank(sub, n, k) for sub in combinations(target, k)]
    assert len(ranks) == comb(s, k) == 5

    broken = list(chi)
    for r in ranks:
        broken[r] = 0
    res = verify_lex(n, s, t, k, broken)
    assert not res.ok, "planted monochromatic 5-set was not caught"
    assert res.witness == target, f"caught the wrong set: {res.witness}"
    assert res.witness_colour == 0
    assert not verify_rank(n, s, t, k, broken).ok

    repaired = list(broken)
    repaired[ranks[0]] = 1  # a single bit
    assert verify_both(n, s, t, k, repaired), (
        "one-bit repair should restore validity; verifier is over-strict"
    )


def test_violation_in_the_other_colour_is_caught():
    """Asymmetry check: a verifier that only ever checks colour 0 would pass
    every test above. Plant the violation in colour 1."""
    n, s, t, k = 6, 5, 5, 4
    chi = [i % 2 for i in range(comb(n, k))]
    target = (1, 2, 3, 4, 5)
    ranks = [lex_rank(sub, n, k) for sub in combinations(target, k)]
    broken = list(chi)
    for r in ranks:
        broken[r] = 1
    res = verify_lex(n, s, t, k, broken)
    assert not res.ok
    assert res.witness_colour == 1
    assert res.witness == target


def test_off_diagonal_uses_the_right_size_per_colour():
    """s != t. A verifier that used s for both colours would miss a mono
    t-set of size t > s (and vice versa)."""
    n, s, t, k = 7, 4, 5, 3
    # Plant a monochromatic 5-set in colour 1 but keep all 4-sets mixed.
    chi = [i % 2 for i in range(comb(n, k))]
    target = (0, 1, 2, 3, 4)
    for sub in combinations(target, k):
        chi[lex_rank(sub, n, k)] = 1
    res = verify_lex(n, s, t, k, chi)
    assert not res.ok, "mono 5-set in colour 1 missed with s=4,t=5"
    assert res.witness_colour == 1
    assert len(res.witness) == t


# --------------------------------------------------------------------------
# The two verifiers must agree, on good and bad inputs alike.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("n,s,t,k", [(6, 5, 5, 4), (7, 5, 5, 4), (6, 4, 4, 3)])
def test_verifiers_agree_on_random_colourings(n, s, t, k):
    import random

    rng = random.Random(20260905)
    agreements = 0
    saw_ok = saw_fail = False
    for _ in range(40):
        chi = [rng.randint(0, 1) for _ in range(comb(n, k))]
        a = verify_lex(n, s, t, k, chi)
        b = verify_rank(n, s, t, k, chi)
        assert a.ok == b.ok, f"disagreement on {chi}"
        saw_ok |= a.ok
        saw_fail |= not a.ok
        agreements += 1
    assert agreements == 40
    # A test where every input lands on one side proves nothing about the other.
    assert saw_ok and saw_fail, (
        f"random sample was one-sided at n={n} (ok={saw_ok}, fail={saw_fail}); "
        "this test is not exercising both branches"
    )


@pytest.mark.parametrize("n,s,t,k", [(9, 4, 4, 3), (10, 5, 5, 4)])
def test_verifiers_agree_on_dense_instances(n, s, t, k):
    """Agreement at sizes where random colourings essentially always fail.

    Deliberately NOT asserting two-sidedness here: at these n the expected
    violation count is C(n,s)/2^(C(s,k)-1) >> 1, so the accept branch is
    unreachable by sampling and demanding it would be a test that cannot pass.
    Two-sidedness is covered by the test above, at n where it is achievable.
    What this adds is agreement of the two routes at larger n, including the
    full violation count with stop_early off.
    """
    import random

    rng = random.Random(7)
    for _ in range(5):
        chi = [rng.randint(0, 1) for _ in range(comb(n, k))]
        a = verify_lex(n, s, t, k, chi, stop_early=False)
        b = verify_rank(n, s, t, k, chi, stop_early=False)
        assert a.ok == b.ok
        assert a.violations == b.violations, (
            f"violation counts differ: {a.violations} vs {b.violations}"
        )
        assert a.witness == b.witness, "verifiers found different first witness"
        # Full sweep ran to completion in both colours.
        assert a.examined == comb(n, s) + comb(n, t)
        assert b.examined == comb(n, s) + comb(n, t)


# --------------------------------------------------------------------------
# §6 completeness certificate.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("n,s,t,k", [(9, 4, 4, 3), (12, 4, 4, 3), (10, 5, 5, 4)])
def test_completeness_count_is_asserted_at_size(n, s, t, k):
    """§6 completeness certificate on a FULL sweep, regardless of verdict.

    stop_early=False means this exercises the certificate even where no witness
    is available, which is the case at most n. The earlier version of this test
    skipped whenever the baseline colouring was not a witness -- i.e. it was
    silently not running at exactly the sizes worth checking.
    """
    chi = [i % 2 for i in range(comb(n, k))]
    for fn in (verify_lex, verify_rank):
        res = fn(n, s, t, k, chi, stop_early=False)
        assert res.checked_sizes[(s, 0)] == comb(n, s)
        assert res.checked_sizes[(t, 1)] == comb(n, t)
        assert res.examined == comb(n, s) + comb(n, t)


def test_completeness_certificate_at_production_size():
    """The §6 assertion at the real target shape: n=35, (5,5;4).

    This is the run the README commits to -- C(35,4) variables and C(35,5)
    cliques per colour. Uses a colouring that is not a witness (all-zero would
    early-exit), with stop_early off, so the full sweep and its completeness
    assertion actually execute at production parameters. A gate that only ever
    runs at n=6 is not a gate for a run at n=35.
    """
    n, s, t, k = 35, 5, 5, 4
    chi = [i % 2 for i in range(comb(n, k))]
    assert len(chi) == 52360
    res = verify_lex(n, s, t, k, chi, stop_early=False)
    assert res.checked_sizes[(s, 0)] == comb(n, s) == 324632
    assert res.checked_sizes[(t, 1)] == comb(n, t) == 324632
    assert res.examined == 2 * comb(n, s) == 649264


def test_shape_errors_are_rejected():
    with pytest.raises(ValueError):
        verify_lex(6, 5, 5, 4, [0] * 3)  # wrong length
    with pytest.raises(ValueError):
        verify_lex(6, 5, 5, 4, [2] * comb(6, 4))  # not 0/1
    with pytest.raises(ValueError):
        verify_lex(6, 5, 5, 6, [0] * comb(6, 6))  # k not < s


def test_target_shape_is_what_the_readme_claims():
    """The numbers the target README commits to, recomputed here."""
    assert comb(35, 4) == 52360
    assert comb(35, 5) == 324632
    assert 2 * comb(35, 5) == 649264
