"""Does the certificate checker discriminate, or does it certify anything?

`drat_check` ignores deletion lines, which makes it the PERMISSIVE reading of
the proof (see its module docstring): every step is checked against a superset
of the database the solver held, and RUP is monotone. Soundness comes from the
accumulated-database chain rather than from strictness -- so the question "does
this checker ever refuse?" has to be answered by experiment, on instances the
size of the real ones.

The experiment: take a deposited UNSAT class, keep a random fraction of its
clauses, and re-decide and re-certify. Weakening a formula can only make it
easier to satisfy, so far enough down it must turn SAT -- and a satisfiable
formula must NOT be certified UNSAT, whatever proof the solver emits.

    python3 negative_control.py --groups groups63.json --class "Z_63 : <2,11> order 1134"

The default class is chosen deliberately: it certifies by PROOF REPLAY with
tens of thousands of steps, not by unit propagation. An earlier control ran on
the class whose route is unit propagation with zero proof steps, which never
exercised the replay machinery it was offered as evidence for. Every row below
records its route and step count so that cannot go unnoticed again.

Exits non-zero unless the full instance certifies UNSAT by proof replay, at
least one weakened instance is SAT, and NO satisfiable instance is certified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys

import ansatz
import drat_check


def weaken(clauses, keep, rng):
    return [c for c in clauses if rng.random() < keep]


def run(clauses, solver="Glucose42", replay=None):
    """Decide and certify `clauses`. If `replay` is given, ALSO replay that
    proof against these clauses and record whether the checker accepts it.

    `certify` returns on SAT before calling `check`, so a satisfiable instance
    on its own never reaches the proof checker: it establishes that the SOLVER
    disagrees, not that the CHECKER refuses. Replaying the full instance's real
    proof against a weakened, satisfiable formula is what puts the checker in
    the position of having to say no.
    """
    r = drat_check.certify(clauses, solver=solver)
    row = {"clauses": len(clauses), "status": r["status"],
           "checked": bool(r.get("checked")), "route": r.get("route"),
           "steps": r.get("steps")}
    if replay is not None:
        row["replayed_original_proof"] = bool(drat_check.check(clauses, replay))
    return row


def problems_with(rows):
    """Every reason this run fails to be a discriminating control."""
    out = []
    if not rows:
        return ["no instances were run"]
    full = rows[0]
    if full["status"] != "UNSAT" or not full["checked"]:
        out.append(f"the full instance came back {full['status']} "
                   f"checked={full['checked']}; the control needs a certified "
                   f"null to weaken")
    elif full["route"] != "proof replay":
        out.append(f"the full instance certified by {full['route']!r} with "
                   f"{full['steps']} step(s); a control on a class that never "
                   f"replays a proof is not evidence about proof replay")
    # The replayed proof must be THE proof, not merely a proof. `run` emits its
    # own inside certify(), so without this the control would pass with
    # `original_proof = []`: every replay would fail for the trivial reason
    # that an empty proof derives nothing, and the log would look identical.
    # Step counts alone do not identify a proof. An equal-length substitute --
    # a deletion-only sequence of the same length, say -- has the right count,
    # fails against the full instance, and therefore fails against every
    # weakening too, for a reason that has nothing to do with the weakening.
    # The proof that is replayed below must be one that ACTUALLY DERIVES THE
    # NULL it claims to: it has to verify against the full CNF first.
    if not full.get("replay_valid_on_full"):
        out.append("the proof replayed below does not itself verify against "
                   "the full instance, so its rejection against a satisfiable "
                   "weakening establishes nothing about the checker")
    if full.get("replay_steps") is None:
        out.append("the length of the replayed proof was not recorded, so the "
                   "rows below do not say WHICH proof was replayed")
    elif full["replay_steps"] != full["steps"]:
        out.append(f"the replayed proof has {full['replay_steps']} step(s) but "
                   f"the full instance certified with {full['steps']}; they are "
                   f"not the same proof")
    elif not full["replay_steps"]:
        out.append("the replayed proof is empty; rejecting it against a "
                   "satisfiable formula shows nothing")
    if not any(r["status"] == "SAT" for r in rows[1:]):
        out.append("no weakened instance turned satisfiable, so the checker "
                   "was never offered one it had to refuse")
    for r in rows:
        if r["status"] == "SAT" and r["checked"]:
            out.append(f"a SATISFIABLE instance ({r['clauses']} clauses) was "
                       f"CERTIFIED UNSAT -- the checker does not discriminate")
        if r["status"] == "SAT" and r.get("replayed_original_proof"):
            out.append(f"the original proof REPLAYED successfully against a "
                       f"satisfiable {r['clauses']}-clause formula -- the "
                       f"checker accepts a proof of a false statement")
    replayed = [r for r in rows[1:]
                if r["status"] == "SAT" and "replayed_original_proof" in r]
    if not replayed:
        out.append("no satisfiable instance was put to the proof CHECKER; "
                   "certify() returns on SAT before checking, so a SAT row "
                   "alone shows only that the solver disagreed")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", default="groups63.json")
    ap.add_argument("--class", dest="cls", default="Z_63 : <2,11> order 1134")
    ap.add_argument("--n", type=int, default=63)
    ap.add_argument("--s", type=int, default=4)
    ap.add_argument("--t", type=int, default=6)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--keep", default="0.9,0.7,0.5,0.3")
    ap.add_argument("--seed", type=int, default=20260908)
    a = ap.parse_args()

    with open(a.groups) as fh:
        groups = json.load(fh)
    matching = [g for g in groups if g["name"] == a.cls]
    if len(matching) != 1:
        print(f"{a.groups}: {len(matching)} class(es) named {a.cls!r}",
              file=sys.stderr)
        return 2
    gens = matching[0]["generators"]
    sha = ansatz.gens_fingerprint(gens)

    clauses, _orbit_of, stats = ansatz.build_cnf(gens, a.n, a.s, a.t, a.k)
    _sat, original_proof = drat_check.emit_proof(clauses)
    print(f"class     {a.cls}")
    print(f"gens      SHA-256 {sha}")
    print(f"instance  {stats['vars']} vars, {len(clauses)} clauses\n")

    rows = [run(clauses)]
    # Bind the replayed proof to the one the full instance certified with, and
    # PROVE that binding rather than asserting it: the proof about to be
    # replayed is first put to the checker against the full CNF. Matching step
    # counts were the whole of this check before, and a same-length invalid
    # substitute walks straight through a count comparison.
    rows[0]["replay_valid_on_full"] = bool(
        drat_check.check(clauses, original_proof))
    rows[0]["replay_steps"] = len(original_proof)
    rows[0]["replay_sha"] = hashlib.sha256(
        repr([(k, tuple(l)) for k, l in original_proof]).encode()).hexdigest()
    print(f"  full          {rows[0]['clauses']:>6} clauses -> "
          f"{rows[0]['status']:<5} checked={rows[0]['checked']} "
          f"route={rows[0]['route']!r} steps={rows[0]['steps']}")
    print(f"  proof replayed below: {rows[0]['replay_steps']} steps, "
          f"sha256 {rows[0]['replay_sha'][:16]}, "
          f"verifies against the full instance="
          f"{rows[0]['replay_valid_on_full']}")

    rng = random.Random(a.seed)
    for keep in [float(x) for x in a.keep.split(",")]:
        row = run(weaken(clauses, keep, rng), replay=original_proof)
        row["keep"] = keep
        rows.append(row)
        print(f"  keep~{keep:<8.2f} {row['clauses']:>6} clauses -> "
              f"{row['status']:<5} checked={row['checked']} "
              f"route={row['route']!r} steps={row['steps']}"
              f"  original proof replays here: "
              f"{row['replayed_original_proof']}")

    problems = problems_with(rows)
    if problems:
        print("\nNOT A DISCRIMINATING CONTROL:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("\nGOOD: the full instance certifies by proof replay, weakening it "
          "far enough turns it satisfiable, no satisfiable instance was "
          "certified, and the original proof does NOT replay against any "
          "satisfiable weakening")
    return 0


if __name__ == "__main__":
    sys.exit(main())
