"""When is a symmetry class EMPTY before you search it?

`obstruction.py` proves one case: for R(5,5;4), a Z_n-invariant colouring can
never be a witness when 5 | n. That was found the expensive way, after a long
campaign aimed at an object the ansatz excluded. This file states the general
fact it is an instance of, and -- as importantly -- the boundary where the fact
stops being true.

THE GENERAL CRITERION (SUFFICIENT, NOT NECESSARY -- see the boundary below).

ALSO: every statement here about "a monochromatic K_s^(k) exists, so the
colouring is not good" needs the colour it lands in to be one that FORBIDS
K_s^(k). That holds on the diagonal (s == t, or m colours each forbidding
K_s) and can fail off it. See theorem_a_applies.

    A G-invariant colouring exists for (s,t;k) on n points ONLY IF no s-set has
    all its k-faces in one G-orbit AND no t-set does, *conflicting*.

    Precisely: if some s-set W has all C(s,k) of its faces inside a single orbit
    O, then W is monochromatic in whatever colour O receives, so O must take
    colour 1 (or the K_s in colour 0 appears). Dually a t-set whose faces all
    lie in O forces O to colour 0. If one orbit is forced both ways the class is
    EMPTY -- the CNF contains x and ~x -- and searching it is wasted budget.

    In the diagonal case s = t this collapses to: ONE s-set with all its faces
    in a single orbit is already fatal. That is `forced_monochromatic`.

THEOREM A -- the clean group-theoretic case, of which our lemma is s = 5.

    Let s be PRIME and k = s - 1. If s divides |G|, then no G-invariant
    colouring of the k-subsets of [n] avoids a monochromatic K_s^(k).

    Proof. By Cauchy's theorem G has an element g of order s. Since s is prime,
    every non-trivial cycle of g has length exactly s, and g is not the
    identity, so g has at least one s-cycle -- say on W = {w_0, ..., w_{s-1}}
    with g(w_i) = w_{i+1 mod s}. The k-subsets of W with k = s-1 are exactly the
    s complements W \\ {w_i}, and g sends W \\ {w_i} to W \\ {w_{i+1}}. So g
    permutes those s faces in a single cycle: they form ONE orbit. A G-invariant
    colouring is constant on orbits, so all s faces of W share a colour and W is
    a monochromatic K_s^(k). []

    Corollary. The automorphism group of any witness is an s'-group, and there
    is no vertex-transitive witness on n points when s | n (orbit-stabiliser
    forces n, hence s, to divide |G|).

WHY k = s-1 IS NOT DECORATION -- the sharpness that makes Theorem A a theorem
rather than a guess. An s-cycle acts on the k-subsets of an s-set transitively
only when C(s,k) = s, i.e. k = 1 or k = s-1. For every other k the s faces fall
into several orbits, the colouring is free to differ across them, and the
argument collapses. `test_obstruction_general.py` exhibits an explicit witness
with s | |G| at k < s-1, so the hypothesis cannot be dropped.

So: the criterion below is what to compute; Theorem A is when you can skip the
computation and know the answer.
"""

from __future__ import annotations

from itertools import combinations
from math import comb


def face_orbit_map(gens, n, k):
    """orbit id of every k-subset, by BFS under the generators."""
    orbit_of, sizes = {}, []
    for f in combinations(range(n), k):
        if f in orbit_of:
            continue
        oid = len(sizes)
        orbit_of[f] = oid
        stack, count = [f], 0
        while stack:
            cur = stack.pop()
            count += 1
            for g in gens:
                img = tuple(sorted(g[v] for v in cur))
                if img not in orbit_of:
                    orbit_of[img] = oid
                    stack.append(img)
        sizes.append(count)
    return orbit_of, sizes


def forced_orbits(gens, n, s, k):
    """Orbits O such that some s-set has ALL its k-faces inside O.

    Returns {orbit_id: [one witnessing s-set, ...]}. An entry means "this orbit
    cannot take the colour that would make that s-set monochromatic".
    """
    orbit_of, _ = face_orbit_map(gens, n, k)
    hits = {}
    for W in combinations(range(n), s):
        ids = {orbit_of[f] for f in combinations(W, k)}
        if len(ids) == 1:
            hits.setdefault(ids.pop(), []).append(W)
    return hits


def class_is_empty(gens, n, s, t, k):
    """Detect emptiness by FORCED ORBITS. Returns (empty, reason).

    `True` is a proof: the CNF contains a literal and its negation, so no
    invariant colouring exists.

    **`False` is not.** It means only that this particular obstruction does not
    fire. A class can be empty for reasons no orbit-forcing argument sees, and
    the smallest example is inside the range this file is tested on:

        class_is_empty(cyclic(7), 7, 3, 3, 2) -> (False, "no s-set has ...")

    but that class has 3 orbit variables and 8 clauses, and enumerating all
    2**3 assignments gives ZERO satisfying ones. The class is empty; this test
    says nothing of the kind. An earlier version of this file called the
    criterion "exact" and this function an "exact emptiness test", which is
    wrong in exactly that direction and would license reading a `False` as
    "the class has a witness". It does not. Only a solver decides that.

    Diagonal (s == t): any forced orbit is fatal on its own.
    Off-diagonal: fatal only when one orbit is forced by BOTH an s-set and a
    t-set, since then it must be colour 1 and colour 0 at once.
    """
    s_hits = forced_orbits(gens, n, s, k)
    if s == t:
        if s_hits:
            o, ws = next(iter(s_hits.items()))
            return True, (f"s-set {ws[0]} has all {comb(s, k)} of its {k}-faces "
                          f"in orbit {o}; s == t so that alone is fatal")
        return False, "no s-set has all its faces in one orbit"   # NOT "non-empty"

    t_hits = forced_orbits(gens, n, t, k)
    both = set(s_hits) & set(t_hits)
    if both:
        o = sorted(both)[0]
        return True, (f"orbit {o} is forced to colour 1 by s-set {s_hits[o][0]} "
                      f"and to colour 0 by t-set {t_hits[o][0]}")
    return False, (f"{len(s_hits)} orbit(s) forced one way, {len(t_hits)} the "
                   f"other, no conflict")


def theorem_a_applies(order, s, k, every_colour_forbids_s):
    """Theorem A: s prime, k = s-1, s | |G|, AND every colour forbids K_s^(k)
    => the class is empty.

    Returns (applies, explanation). Deliberately returns False rather than
    guessing whenever a hypothesis fails -- a criterion that over-claims is
    worse than no criterion, since it would retire ansaetze that are fine.

    `every_colour_forbids_s` is REQUIRED and has no default, because omitting
    it is precisely how this function came to over-claim. The proof produces an
    s-set whose faces lie in one orbit, hence one colour -- and then needs that
    colour to be one in which K_s^(k) is forbidden. On the diagonal (s == t, or
    m colours all forbidding K_s) every colour is; off the diagonal the s-set
    can simply land in the colour that forbids K_t, and nothing is
    contradicted.

    The smallest counterexample is checked in the test suite: R(3,4) on three
    vertices under C_3, every edge coloured with the colour that forbids K_4.
    |G| = 3, s = 3 is prime, k = s - 1 = 2, and 3 | 3 -- every hypothesis this
    function used to check -- yet the colouring is invariant and good.
    """
    if not every_colour_forbids_s:
        return False, ("not every colour forbids K_s: the monochromatic s-set "
                       "the proof produces may lie in a colour where K_s is "
                       "allowed, so Theorem A says nothing here")
    if k != s - 1:
        return False, (f"k={k} != s-1={s-1}: an s-cycle does not act "
                       f"transitively on the {comb(s, k)} faces of an s-set, "
                       f"so Theorem A says nothing")
    if not _is_prime(s):
        return False, (f"s={s} is not prime, so Cauchy gives no element of "
                       f"order s and the proof does not start")
    if order % s:
        return False, f"s={s} does not divide |G|={order}"
    return True, (f"s={s} is prime, k=s-1, and {s} | {order}: some element has "
                  f"an s-cycle, whose s faces form one orbit")


def no_s_cycle_possible(order, s):
    """True when NO element of G can have an s-cycle, from |G| alone.

    Theorem A needs s prime only so that Cauchy supplies an element of order s.
    The underlying statement is weaker and needs no primality:

        THEOREM A'. If k = s-1 and SOME element of G has an s-cycle, then no
        G-invariant colouring avoids a monochromatic K_s^(k).

    (Same proof: the s-cycle permutes the s = C(s,s-1) faces of its support
    cyclically, so they form one orbit and share a colour.)

    An element with an s-cycle has order divisible by s, so s | |G| is
    NECESSARY for Theorem A' to fire. This function reports the contrapositive:
    when s does not divide |G|, no element has an s-cycle and the class is safe
    from this obstruction whether or not s is prime.

    That is the check to run for composite s -- R(4,4,4;3) has s = 4, k = 3, so
    the 4-cycle argument would apply, but 4 does not divide 79*78 = 6162 and the
    ansatz survives.
    """
    return order % s != 0


def _is_prime(m):
    if m < 2:
        return False
    d = 2
    while d * d <= m:
        if m % d == 0:
            return False
        d += 1
    return True


def cyclic(n, m=None):
    """Z_m on m points, fixing the rest of [n]. Defaults to the full cycle."""
    m = m or n
    return [[(i + 1) % m for i in range(m)] + list(range(m, n))]


def report(cells, verbose=True):
    """Apply Theorem A across a table of (name, n, s, t, k, order) rows."""
    out = []
    for name, n, s, t, k, order in cells:
        # s == t is what makes "the colour the s-set lands in forbids K_s"
        # true; the table carries t precisely so this is not assumed.
        applies, why = theorem_a_applies(order, s, k,
                                         every_colour_forbids_s=(s == t))
        out.append({"name": name, "n": n, "s": s, "t": t, "k": k,
                    "order": order, "theorem_a": applies, "why": why})
        if verbose:
            print(f"  {name:<28} R({s},{t};{k}) |G|={order:<8} "
                  f"{'EMPTY by Theorem A' if applies else 'not excluded'}")
            print(f"      {why}")
    return out


if __name__ == "__main__":
    print("Theorem A across the DS1 §7.1(a) cells, for a cyclic ansatz Z_n:\n")
    report([
        ("R(5,5;4) at n=35",   35, 5, 5, 4, 35),
        ("R(5,5;4) at n=34",   34, 5, 5, 4, 34),
        ("R(4,5;3) at n=35",   35, 4, 5, 3, 35),
        ("R(5,5;3) at n=88",   88, 5, 5, 3, 88),
        ("R(4,6;3) at n=63",   63, 4, 6, 3, 63),
        ("R(3,3;2) at n=6",     6, 3, 3, 2, 6),
    ])


def pair_regular_fixed_point_obstruction(p, d, colours=3, s=4):
    """Theorem B. If `Z_p : H` acts **regularly** on unordered pairs, then no
    good `m`-colouring on p + 1 points is invariant under it -- with no SAT call.

    Only `s = 4` and `colours = 3`: the proof below ends at a threshold, and
    `R(4,4;3) = 13` is the only one known here. Both parameters are checked
    rather than assumed -- with `s = 5` the threshold would be `R(5,5;3)`, and
    at `(p, d) = (19, 9)` the conclusion is simply false.

    Regularity needs TWO conditions, and only the first is about the order:

    1. `|G| = p*d = C(p,2)`, i.e. `d = (p-1)/2`, so `H` is the quadratic
       residues and the orbit count could be one; and
    2. **`-1 not in H`**, equivalently **`p = 3 (mod 4)`**.

    Condition 2 is not decoration. The map `x -> -x + (a+b)` swaps `a` and `b`,
    so it stabilises the pair `{a,b}`; it lies in `G` exactly when `-1 in H`.
    For `p = 1 (mod 4)`, `-1` IS a quadratic residue, every pair has a
    stabiliser of order 2, and there are **two** pair-orbits rather than one.
    Counted directly: p = 13, 17, 29, 37 all give |G| = C(p,2) and 2 orbits.

    And the conclusion genuinely fails there, not just the proof: at p = 13
    (n = 14) and p = 37 (n = 38) the class `Z_p : C_{(p-1)/2} + 1 fixed` is
    **satisfiable** for R(4,4,4;3), so an invariant good colouring exists.
    The triples through the fixed point split across the two orbits and may
    take different colours, which is exactly what the argument below forbids
    when there is only one.

    Proof (under both conditions). One pair-orbit means every triple `{inf,x,y}`
    lies in a single `G`-orbit, so an invariant colouring gives them all one
    colour `c`. No triple inside the base may take `c`: with `inf` it would
    close a monochromatic `K_s^(k)` for s = 4. The base must therefore be
    coloured with the other `m - 1` colours avoiding a monochromatic
    `K_4^(3)`, which for m = 3 needs a 2-colouring and is impossible once the
    base has at least `R(4,4;3) = 13` points. []

    Both towers used in this repo satisfy condition 2 -- 79 and 83 are each
    3 (mod 4) -- so the explanation of their behaviour stands.

    Returns (applies, reason).
    """
    from math import comb

    order = p * d
    pairs = comb(p, 2)
    if order != pairs:
        return False, (f"|G| = {order} != C({p},2) = {pairs}; the pair action "
                       f"cannot be regular, so this argument says nothing")
    if p % 4 != 3:
        return False, (f"p = {p} is {p % 4} (mod 4), so -1 is a quadratic "
                       f"residue and lies in H; the map x -> -x + (a+b) then "
                       f"stabilises every pair and the action has two "
                       f"pair-orbits, not one. The argument does not apply, "
                       f"and for p = 13 and p = 37 the class is in fact "
                       f"satisfiable")
    if s != 4:
        # `s` is a parameter and the threshold below is not. The base is left
        # needing a (colours-1)-colouring of its triples with no monochromatic
        # K_s^(3), so the threshold is R(s,s;3) -- and only R(4,4;3) = 13 is
        # known here. Without this guard the function returns True on inputs
        # where an invariant good colouring exists: (p, d, colours, s) =
        # (19, 9, 3, 5) satisfies every other condition, and the class
        # Z_19 : C_9 + 1 fixed is SAT for R(5,5,5;3) on 20 points.
        return False, (f"only implemented for s = 4; with s = {s} the base "
                       f"needs a colouring of its triples with no mono "
                       f"K_{s}^(3), and the threshold is R({s},{s};3), which "
                       f"is not known here -- R(4,4;3) = {R_4_4_3} is the "
                       f"wrong number for it")
    if colours != 3:
        # The base is left needing a (colours-1)-colouring with no mono
        # K_4^(3), so the threshold is the (colours-1)-COLOUR Ramsey number.
        # Only the 2-colour one is known here: R(4,4;3) = 13. For 4 colours
        # the relevant value is R(4,4,4;3) itself, which is what this whole
        # package is bounding -- so the argument cannot be closed. An earlier
        # version applied the 2-colour threshold regardless of `colours` and
        # returned True for cases where an invariant good colouring exists.
        return False, (f"only implemented for 3 colours; with {colours} the "
                       f"base needs a {colours - 1}-colouring and the "
                       f"threshold would be the {colours - 1}-colour Ramsey "
                       f"number, which is not known here")
    if p < R_4_4_3:
        return False, (f"base has {p} points, fewer than R(4,4;3) = {R_4_4_3}; "
                       f"a good 2-colouring of the base may exist")
    assert s == 4 and colours == 3, "the threshold below is R(4,4;3)"
    return True, (f"|G| = {order} = C({p},2) and p = 3 (mod 4), so -1 is not a "
                  f"quadratic residue and the action on unordered pairs is "
                  f"regular: all triples through a fixed point share one orbit "
                  f"and one colour. The base then needs a 2-colouring of its "
                  f"triples with no mono K_4^(3) on {p} >= R(4,4;3) = "
                  f"{R_4_4_3} points, which does not exist.")


R_4_4_3 = 13
