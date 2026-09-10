"""Turn the sweep's UNSAT classes into checkable certificates.

Usage:
    python3 certify_nulls.py --groups groups63.json --n 63 --s 4 --t 6 --k 3 \
        --out certs_46_3_n63.json

For each group it rebuilds the CNF with `ansatz.build_cnf`, re-solves with a
proof-emitting solver, and replays the proof with `drat_check.check`. Only
classes that came back UNSAT get a certificate; SAT classes are recorded as SAT
and skipped, since those already have a witness object.
"""

import argparse
import json
import os
import sys
import time

import ansatz
import contracts
import drat_check
import multicolour
import grouporder


def gate(rows, expect_certified=None, compare_path=None):
    """Every reason these rows fail to back the deposit's null claims.

    Returns a list of strings; empty means the claims are checked. Kept apart
    from main() and from any I/O so it can be falsified directly: a gate whose
    failing path is never executed is indistinguishable from one that cannot
    fail. See test_certify_gate.py, which drives every branch below to a
    non-empty result.

    A count printed to stdout is not a gate. Anything that is neither a
    replayed UNSAT certificate nor an explicitly SAT class (those carry a
    witness object instead) leaves a claimed null unchecked.
    """
    problems = []

    # Unusable identities are rejected FIRST: {"n":3,"k":2} and {"n":9,"k":4}
    # are both truthy and both normalise to None, and a gate that lets None
    # match None treats two different unspecified questions as the same one.
    for r in rows:
        problems.extend(contracts.identity_problems(r, "recomputed row"))

    # BEFORE selecting certified rows. Filtering to checked-UNSAT first removes
    # exactly the contradiction the reducer needs to see: a history holding
    # SAT and UNSAT for one instance passed because only the UNSAT survived
    # the filter.
    try:
        contracts.reduce_history(rows)
    except contracts.Contradiction as exc:
        problems.append(f"recomputed rows: {exc}")

    def _pkey(row):
        """The problem key, via the ONE canonical identity.

        This used to be a local json.dumps of whatever dict the row carried,
        which made rows from different producers -- (n,s,t,k) vs (n,sizes,k)
        -- fail to compare equal even when they decided the same question.
        ansatz.row_problem_identity normalises every shape, legacy rows
        included.
        """
        return ansatz.row_problem_identity(row)

    for r in rows:
        if not r.get("checked") and r.get("status") != "SAT":
            problems.append(f"{r.get('name')}: status={r.get('status')} "
                            f"checked={r.get('checked')} -- null not certified")
        # A row without a generator fingerprint says which LABEL was certified,
        # not which GROUP. Everything below keys on the pair, so a row that
        # cannot supply one is refused rather than silently keyed on the name.
        if not r.get("gens_sha"):
            problems.append(f"{r.get('name')}: no gens_sha -- the row records a "
                            f"name, not an instance")
        # Same argument one level up: a row that does not say WHICH QUESTION it
        # decided cannot certify a null about any particular question.
        if not r.get("problem"):
            problems.append(f"{r.get('name')}: no problem key -- the row "
                            f"records a group, not a decision")

    # "checked" is not certification on its own. A row saying status=ERROR
    # with checked=True was counted as a certificate, because nothing compared
    # the two fields. Only a CERTIFIED UNSAT counts.
    for r in rows:
        if r.get("checked") and r.get("status") != "UNSAT":
            problems.append(f"{r.get('name')}: checked=True with "
                            f"status={r.get('status')!r} -- a certificate is a "
                            f"replayed UNSAT proof, and these two fields "
                            f"disagree")

    # DISTINCT instances. Five copies of one certified class satisfied
    # "expected 5 certified class(es)": the count was over rows, and rows are
    # not instances. The identity is the same triple the comparison uses.
    certified = [r for r in rows
                 if r.get("checked") and r.get("status") == "UNSAT"]
    # NOT the display name. Five copies of one certified class under five
    # different labels passed "expected 5 distinct certified classes": the
    # label was in the key, so renaming defeated the guard. The identity is
    # the generators and the problem.
    ids = [contracts.instance_identity(r) for r in certified]
    dupes = {i for i in ids if ids.count(i) > 1}
    for d in sorted(str(x) for x in dupes):
        problems.append(f"{d}: certified more than once; the same instance "
                        f"repeated is one class, not several")
    n_ok = len(set(ids))
    if expect_certified is not None and n_ok != expect_certified:
        problems.append(f"expected {expect_certified} distinct certified "
                        f"class(es), got {n_ok}")
    # A certification run that certified nothing is not a success. With no
    # expected count this gate returned clean on an empty row list, and main()
    # printed "0/0 class(es) certified UNSAT; written to ..." and exited 0.
    if not rows:
        problems.append("no class was certified: this run decided nothing, "
                        "and an empty certification is not a null result")

    if compare_path:
        with open(compare_path) as f:
            dep_rows = json.load(f)
        # The reference is a history too, and it was reduced by last-write-
        # wins: a later row silently replaced an earlier contradictory one, so
        # the same file was accepted or rejected depending on row ORDER.
        try:
            contracts.reduce_history(dep_rows)
        except contracts.Contradiction as exc:
            problems.append(f"{compare_path}: {exc}")

        deposited = {}
        for d in dep_rows:
            if not d.get("gens_sha"):
                problems.append(f"{d.get('name')}: deposited row in "
                                f"{compare_path} carries no gens_sha; it cannot "
                                f"be matched to an instance")
                continue
            # The PROBLEM is part of the identity of a certified null. The
            # same group on the same points decides different questions at
            # different clique sizes -- the cyclic group on 7 points is UNSAT
            # for (7,3,3,2) and SAT for (7,4,4,2) -- so a row keyed only on
            # the group lets a genuine result for one problem certify a
            # deposited claim about another. A deposited row that cannot say
            # which problem it decided is refused, exactly as one with no
            # gens_sha is.
            if not d.get("problem"):
                problems.append(f"{d.get('name')}: deposited row in "
                                f"{compare_path} carries no problem key; it "
                                f"records a group, not a decision")
                continue
            deposited[(d["name"], d["gens_sha"], _pkey(d))] = d
        # Keyed on (name, gens_sha), never the name alone: swap one class's
        # generators for another's and every name still matches, so a name-keyed
        # comparison certifies one instance twice and never sees the other.
        # Compared field by field, and deliberately NOT on `steps`: a proof's
        # length depends on the solver build and its search order, so requiring
        # it to match would fail for a reason that says nothing about the
        # mathematics. status/checked/route are the invariants.
        for r in rows:
            key = (r.get("name"), r.get("gens_sha"), _pkey(r))
            d = deposited.get(key)
            if d is None:
                problems.append(f"{r.get('name')} [{r.get('gens_sha')}] on "
                                f"{r.get('problem')!r}: no class with this "
                                f"name AND these generators AND this problem "
                                f"in {compare_path}")
                continue
            for field in ("status", "checked", "route"):
                if r.get(field) != d.get(field):
                    problems.append(
                        f"{r['name']}.{field}: recomputed {r.get(field)!r} "
                        f"!= deposited {d.get(field)!r}")
        seen = {(r.get("name"), r.get("gens_sha"), _pkey(r))
                for r in rows}
        for name, sha, prob in sorted(set(deposited) - seen):
            problems.append(f"{name} [{sha}] on {prob!r}: deposited but not "
                            f"recomputed")

    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--s", type=int)
    ap.add_argument("--t", type=int)
    ap.add_argument("--sizes", help="comma-separated clique sizes; "
                    "selects the multi-colour encoding instead of --s/--t")
    ap.add_argument("--k", type=int, required=True)
    ap.add_argument("--solver", default="Glucose42")
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect-certified", type=int, metavar="N",
                    help="fail unless exactly N classes certify UNSAT")
    ap.add_argument("--compare", metavar="CERTS.json",
                    help="fail unless the recomputed result matches this "
                         "deposited certificate file class for class")
    a = ap.parse_args()

    if a.sizes:
        sizes = [int(x) for x in a.sizes.split(",")]
        label = f"R({','.join(map(str, sizes))};{a.k})"
    else:
        if a.s is None or a.t is None:
            ap.error("give either --sizes or both --s and --t")
        sizes = None
        label = f"R({a.s},{a.t};{a.k})"

    # --out is written INSIDE the solve loop, before gate() ever opens
    # --compare. Point both at one path and the reference is replaced by this
    # run's own output before it is read, after which "matches the deposited
    # ..." is a comparison of the results against themselves. Refuse the alias
    # before anything is written, and follow links and inodes: a symlink or a
    # hard link is the same file under a different name.
    if a.compare:
        if not os.path.exists(a.compare):
            print(f"--compare {a.compare} does not exist; there is nothing to "
                  f"compare against", file=sys.stderr)
            return 2
        same = os.path.realpath(a.out) == os.path.realpath(a.compare)
        if not same and os.path.exists(a.out):
            try:
                same = os.path.samefile(a.out, a.compare)
            except OSError:
                same = False
        if same:
            print(f"--out {a.out} and --compare {a.compare} are the same file; "
                  f"the reference would be overwritten by this run before it "
                  f"was read, and the gate would compare the results against "
                  f"themselves", file=sys.stderr)
            return 2
        # Held in memory from BEFORE the computation, so that nothing this run
        # writes can become the thing it is checked against.
        with open(a.compare) as fh:
            reference_bytes = fh.read()
    else:
        reference_bytes = None

    groups = json.load(open(a.groups))
    ansatz.refuse_ambiguous_names(groups, a.groups)
    problem = ansatz._problem_key(n=a.n, s=a.s, t=a.t, k=a.k, sizes=sizes)
    print(f"certifying {len(groups)} class(es) at n={a.n}, "
          f"{label}, solver {a.solver}")

    rows = []
    for g in groups:
        name, gens = g["name"], g["generators"]
        order = grouporder.group_order(gens, a.n)
        t0 = time.time()
        if sizes is None:
            cnf, _, stats = ansatz.build_cnf(gens, a.n, a.s, a.t, a.k)
        else:
            cnf, _, _, stats = multicolour.build_cnf(gens, a.n, sizes, a.k)
        nv = stats["vars"]
        build = time.time() - t0

        t0 = time.time()
        r = drat_check.certify(cnf, solver=a.solver)
        cert = time.time() - t0

        r.update(name=name, order=order, vars=nv, clauses=len(cnf),
                 build_s=round(build, 1), certify_s=round(cert, 1),
                 gens_sha=ansatz.gens_fingerprint(gens), problem=problem)
        rows.append(r)
        mark = "CERTIFIED" if r.get("checked") else r["status"]
        print(f"  {name:<28} |G|={order:<6} {nv:>4} vars {len(cnf):>7} clauses"
              f"  {mark:<10} {r['steps']:>6} proof steps  ({cert:.1f}s)")
        json.dump(rows, open(a.out, "w"), indent=1)

    n_ok = sum(1 for r in rows if r.get("checked"))
    print(f"\n{n_ok}/{len(rows)} class(es) certified UNSAT; written to {a.out}")

    # The reference read before the run is the one compared against; if the
    # file changed underneath us mid-run, that is itself a failure.
    if a.compare:
        with open(a.compare) as fh:
            if fh.read() != reference_bytes:
                print(f"{a.compare} changed while this run was in progress; "
                      f"refusing to compare against a moving reference",
                      file=sys.stderr)
                return 2
    problems = gate(rows, expect_certified=a.expect_certified,
                    compare_path=a.compare)
    if problems:
        print("\nCERTIFICATE GATE FAILED:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    if a.compare:
        print(f"matches the deposited {a.compare} on status, checked and "
              f"route for all {len(rows)} class(es), matched by name AND "
              f"generator fingerprint AND the problem decided")
    return 0


if __name__ == "__main__":
    sys.exit(main())
