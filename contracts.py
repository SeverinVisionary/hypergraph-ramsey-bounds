"""The contracts that every consumer of a result row must share.

WHY THIS FILE EXISTS.  A rule about result rows that each consumer
implements for itself is not one rule but several, and they drift: two
implementations of the same question-identity disagree about whether two rows
are about the same problem, and two definitions of "a distinct certified
instance" disagree about how many classes a file records.  These definitions
are therefore kept here, once, and imported.

One limit is worth stating rather than assuming: `instance_identity`
identifies a GENERATOR PRESENTATION, not a group.  Two presentations of the
same group have different fingerprints and count as different instances.  That
is correct for binding a row to the bytes that produced it, and it is NOT a
deduplication of mathematically identical symmetry classes.

  * `problem_identity`   -- which QUESTION a row decided
  * `instance_identity`  -- which INSTANCE decided it (never the display name)
  * `reduce_history`     -- what a pile of attempt rows amounts to
  * `theorem_b_hypotheses` -- the hypotheses of Theorem B, derived not declared

Nothing here does I/O or imports a solver, so every branch can be driven from a
test directly.
"""

import json

# Statuses that are a VERDICT about the mathematics. Everything else -- TIMEOUT,
# ERROR, OVER_CAP -- records that an attempt was made, and an attempt is not an
# answer. Keeping these apart is what H2 turned on: a TIMEOUT between a SAT and
# an UNSAT must not erase either.
DECISIONS = ("SAT", "UNSAT", "EMPTY")


def problem_identity(problem):
    """ONE canonical identity for the question a row decided, or None.

    Accepts every shape this repo has written -- (n, s, t, k), (n, s, t, k,
    sizes), (n, sizes, k) -- because `s`/`t` are just the ordered forbidden
    sizes. Returns None when the dict cannot say which question it means; a
    truthy-but-unusable dict is NOT an identity, and callers must reject it
    rather than treat None as a wildcard that matches everything.
    """
    if not problem:
        return None
    sizes = problem.get("sizes")
    if not sizes:
        s, t = problem.get("s"), problem.get("t")
        sizes = [s, t] if s is not None and t is not None else None
    if sizes is None or problem.get("n") is None or problem.get("k") is None:
        return None
    # VALIDATE, do not coerce. Unconditional int() changed the meaning of
    # malformed input rather than rejecting it: {"n":63.9,"k":3.9,
    # "sizes":[4.9,6.9]} and {"n":63,"k":3,"sizes":"46"} -- a string iterated
    # character by character -- both became the well-formed identity of a
    # different question. A bool is an int in Python and is not a size.
    def _int(x):
        if isinstance(x, bool):
            raise ValueError("bool is not a size")
        if isinstance(x, int):
            return x
        if isinstance(x, str):
            return int(x)          # an integer string is deliberately allowed
        if isinstance(x, float) and x.is_integer():
            return int(x)
        raise ValueError(f"{x!r} is not an integer")

    if isinstance(sizes, (str, bytes)) or not isinstance(sizes, (list, tuple)):
        return None
    # An explicit `sizes` alongside a DIFFERENT s/t is two declarations of one
    # question; preferring one silently is a choice the caller cannot see.
    s, t = problem.get("s"), problem.get("t")
    if problem.get("sizes") and s is not None and t is not None:
        try:
            if [_int(x) for x in problem["sizes"]] != [_int(s), _int(t)]:
                return None
        except (TypeError, ValueError):
            return None
    try:
        sizes = [_int(x) for x in sizes]
        n, k = _int(problem["n"]), _int(problem["k"])
    except (TypeError, ValueError):
        return None
    return json.dumps({"n": n, "k": k, "sizes": sizes}, sort_keys=True)


def row_problem_identity(row):
    """The canonical identity of the problem a RESULT ROW decided."""
    return problem_identity(row.get("problem"))


def same_problem(a, b):
    """Do two problem dicts mean the same question?

    Compared through the identity, never as raw dicts. `_resume` used `==` on
    the dicts, so adding `sizes=None` to one side -- or writing the same
    question as sizes=[s,t] -- made it refuse a file it should have accepted,
    while the helper said the two questions were identical.
    """
    ia, ib = problem_identity(a), problem_identity(b)
    return ia is not None and ia == ib


def instance_identity(row):
    """WHICH INSTANCE a row is about: (generators, problem). Never the name.

    A name is a display label chosen by whoever built the groups file. Keying
    on it meant five copies of one certified class under five different names
    counted as five distinct certified classes.
    """
    sha, prob = row.get("gens_sha"), row_problem_identity(row)
    if not sha or prob is None:
        return None
    return (sha, prob)


def identity_problems(row, where="row"):
    """Why `row` cannot be bound to an instance. Empty means it can."""
    out = []
    if not row.get("gens_sha"):
        out.append(f"{where} {row.get('name')!r}: no gens_sha -- it records a "
                   f"name, not an instance")
    if row_problem_identity(row) is None:
        out.append(f"{where} {row.get('name')!r}: no usable problem identity "
                   f"({row.get('problem')!r}) -- it records a group, not a "
                   f"decision")
    return out


class Contradiction(Exception):
    """Two different verdicts for one instance. Not resolvable by ordering."""


def reduce_history(rows, want_problem=None):
    """Attempt rows -> {instance_identity: verdict}, order-independent.

    Three failure modes this must not have:

    * assigning into a dict lets a later row overwrite an earlier one, so SAT
      followed by UNSAT silently becomes UNSAT -- a witness read as a null;
    * comparing each row only against the PREVIOUS status lets
      SAT, TIMEOUT, UNSAT through: the TIMEOUT displaces the SAT from the
      comparison while both verdicts remain in the file;
    * rows about another question get reduced together with these.

    So: non-decisions are ignored entirely rather than recorded, decisions are
    accumulated per instance, and any instance carrying two different verdicts
    raises -- whatever order they appear in, and whatever sits between them.
    """
    verdicts = {}
    for r in rows:
        if want_problem is not None and not same_problem(r.get("problem"),
                                                         want_problem):
            continue
        key = instance_identity(r)
        if key is None:
            continue
        st = r.get("status")
        if st not in DECISIONS:
            continue                      # an attempt, not an answer
        if key in verdicts and verdicts[key] != st:
            a, b = sorted((verdicts[key], st))
            raise Contradiction(
                f"{r.get('name')} [{key[0][:16]}...] on {key[1]}: the history "
                f"holds both {a} and {b} for one instance; that is not a "
                f"decision, and no ordering of the rows makes it one")
        verdicts[key] = st
    return verdicts


def theorem_b_hypotheses(p, order):
    # Same rule as problem_identity: reject malformed input rather than
    # truncating it into well-formed input. Without this, (13.9, 78.9) would
    # answer as though asked about p = 13, |G| = 78.
    """Theorem B's hypotheses, DERIVED from p and |G|.

    Recomputing the arithmetic fields while trusting the two booleans that
    carry the claim admits rows with order=1, with p = 3 mod 4, and with
    composite "primes". The predicate therefore derives both booleans.

    Returns (is_prime, satisfies_first, satisfies_second, C(p,2)).
    """
    for label, v in (("p", p), ("order", order)):
        if isinstance(v, bool) or not (
                isinstance(v, int)
                or (isinstance(v, float) and float(v).is_integer())):
            raise ValueError(f"{label}={v!r} is not an integer")
    p, order = int(p), int(order)
    is_prime = p >= 2 and all(p % d for d in range(2, int(p ** 0.5) + 1))
    c_p_2 = p * (p - 1) // 2
    first = is_prime and int(order) == c_p_2      # |G| = C(p,2)
    second = is_prime and p % 4 == 3              # -1 not in H
    return is_prime, first, second, c_p_2


def resume(results, problem, groups, path, fingerprint, stderr=None):
    """The ONE history/selection reducer, shared by both engines.

    `ansatz` and `multicolour` both resume from an accumulating output file
    and both need identical semantics for what that file records. A single
    body is what makes them identical; two bodies agree only by coincidence.

    Mutates `results` in place to the rows that may be trusted downstream and
    returns the (name, gens_sha) pairs already decided for THIS problem.
    """
    import sys
    say = stderr or sys.stderr

    foreign = [r for r in results
               if r.get("problem") is not None
               and not same_problem(r["problem"], problem)]
    if foreign:
        say.write(
            f"{path} holds {len(foreign)} row(s) for a different problem "
            f"({foreign[0]['problem']}), not {problem}. Writing here would mix "
            f"two questions in one file; point --out at a fresh path.\n")
        raise SystemExit(2)

    # Two groups under one name make "already decided" unresolvable.
    seen = {}
    for g in groups:
        sha = fingerprint(g["generators"])
        if g["name"] in seen and seen[g["name"]] != sha:
            say.write(
                f"{path}: two groups are both named {g['name']!r} with "
                f"different generators. Rename one; 'already decided' cannot "
                f"be resolved by name here.\n")
            raise SystemExit(2)
        seen[g["name"]] = sha

    try:
        reduce_history(results, want_problem=problem)
    except Contradiction as exc:
        say.write(f"{path}: {exc}\n")
        raise SystemExit(2)

    want = {(g["name"], fingerprint(g["generators"])) for g in groups}
    selected_names = {g["name"] for g in groups}
    keep, dropped, done = [], 0, set()
    for r in results:
        key = (r.get("name"), r.get("gens_sha"))
        # History is not selection: a run over class B must not delete a
        # stamped result for class A. A row whose NAME collides with a
        # selected group under different generators stays ambiguous and is
        # dropped.
        retainable = key in want or r.get("name") not in selected_names
        if (same_problem(r.get("problem"), problem)
                and r.get("gens_sha") is not None and retainable):
            keep.append(r)
            if r.get("status") in DECISIONS and key in want:
                done.add(key)
        else:
            dropped += 1
    if dropped:
        say.write(
            f"note: {dropped} row(s) in {path} are unstamped or belong to a "
            f"different group with the same name; they are dropped and re-run "
            f"rather than trusted\n")
    results[:] = keep
    return done
