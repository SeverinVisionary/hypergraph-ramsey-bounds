"""Is the R(4,4,4;3) ladder a family, or five accidents?

Five witnesses exist (n = 79..83) and every one is `Z_p : C_d + m fixed`. That
is either an infinite construction we have sampled five points of, or a run of
sporadic hits. The difference decides whether this work can carry a theorem or
only a table, so it is worth answering directly rather than by climbing further.

This sweeps the parameter space and records SAT/UNSAT for every cell, so the
pattern (if any) can be read off:

    python3 sweep_pdm.py --pmax 120 --mmax 12 --max-vars 800 --cap 120

Each row is one (p, d, m). `empty` marks classes that are contradictory before
the solver runs -- those are not evidence about anything and must not be read as
UNSAT (see `multicolour.build_cnf`).
"""

import argparse
import json
import sys
import time

import multicolour
from capped import run_capped_out_of_process
from make_groups_affine import build as build_tower



def _decide_cell(gens, n, cap_s=None):
    """Build and decide one cell. Module level so the child-process cap can
    reach it; cap_s is accepted and ignored because the deadline that actually
    binds is the OS one applied by the parent."""
    from pysat.solvers import Cadical195
    cnf, orbit_of, _, st = multicolour.build_cnf(gens, n, [4, 4, 4], 3)
    dead = len(st["empty_by_construction"])
    if dead:
        return {"vars": st["vars"], "clauses": st["clauses"],
                "empty": dead, "status": "EMPTY"}
    solver = Cadical195(bootstrap_with=cnf)
    sat = solver.solve()
    model = solver.get_model() if sat else None
    solver.delete()
    if not sat:
        return {"vars": st["vars"], "clauses": st["clauses"],
                "empty": dead, "status": "UNSAT"}

    # A solver's SAT is not a witness. This sweep's headline output is "largest
    # n with a witness", and it used to take the solver's word: an encoding
    # defect would be reported as a discovery. Expand the model and check the
    # property from scratch before the status is allowed to say SAT.
    chi = multicolour.expand(model, orbit_of, n, 3, 3)   # m=3 colours, k=3
    ok, detail = multicolour.verify(chi, n, [4, 4, 4], 3)
    if not ok:
        return {"vars": st["vars"], "clauses": st["clauses"], "empty": dead,
                "status": "ERROR",
                "error": f"solver said SAT but the model is not a witness: {detail}"}
    return {"vars": st["vars"], "clauses": st["clauses"],
            "empty": dead, "status": "SAT"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pmax", type=int, default=120)
    ap.add_argument("--pmin", type=int, default=53)
    ap.add_argument("--mmax", type=int, default=12)
    ap.add_argument("--max-vars", type=int, default=800)
    ap.add_argument("--cap", type=int, default=120)
    ap.add_argument("--out", default="sweep_pdm.json")
    a = ap.parse_args()

    from make_groups_affine import is_prime
    primes = [p for p in range(a.pmin, a.pmax + 1) if is_prime(p)]
    print(f"primes {primes[0]}..{primes[-1]} ({len(primes)}), m up to {a.mmax}, "
          f"max {a.max_vars} vars, cap {a.cap}s", flush=True)

    rows = []
    for p in primes:
        for m in range(0, a.mmax + 1):
            n = p + m
            over_cap = []
            try:
                tower = build_tower(n, p, a.max_vars, skipped=over_cap)
            except Exception as e:
                # Recorded, not swallowed. The docstring above promises a row
                # for every cell, and the conclusion drawn from this sweep is
                # about which cells are SAT -- so a cell that never ran must be
                # visible in the output and must change the exit status, or an
                # exhaustive-looking table is really a table of the cells that
                # happened to work.
                print(f"  p={p} m={m}: ERROR {type(e).__name__}: {e}", flush=True)
                rows.append({"p": p, "m": m, "n": n, "name": None,
                             "status": "ERROR",
                             "error": f"{type(e).__name__}: {e}"})
                json.dump(rows, open(a.out, "w"), indent=1)
                continue
            # A class dropped for being over --max-vars is not a cell that
            # was decided. It has to appear in the output, or a table built
            # from these rows reads as though the tower had no such class.
            for sk in over_cap:
                rows.append({"p": p, "m": m, "n": n, "name": sk["name"],
                             "order": sk["order"], "vars": sk["vars"],
                             "clauses": None, "empty": None,
                             "status": "OVER_CAP", "secs": 0.0})
            # Persisted here, not only inside the solver loop below: a run in
            # which every class is over the cap never reaches that loop, and
            # the --out file the caller asked for was never created at all.
            if over_cap:
                json.dump(rows, open(a.out, "w"), indent=1)
            for g in tower:
                t0 = time.time()
                row = {"p": p, "m": m, "n": n, "name": g["name"],
                       "order": g["order"]}
                # --cap was accepted, printed, and never enforced: the solve
                # ran blocking with no deadline, because Cadical195.interrupt()
                # is a no-op in this python-sat build. A cap the caller can set
                # and the code ignores is worse than no cap. This one is
                # enforced by the OS in a child process.
                capped = run_capped_out_of_process(
                    _decide_cell, {"gens": g["generators"], "n": n}, a.cap)
                if capped.status == "TIMEOUT":
                    row.update({"vars": None, "clauses": None, "empty": None,
                                "status": "TIMEOUT"})
                elif capped.status == "ERROR":
                    row.update({"vars": None, "clauses": None, "empty": None,
                                "status": "ERROR", "error": capped.detail})
                else:
                    row.update(capped.value)
                row["secs"] = round(time.time() - t0, 1)
                rows.append(row)
                if row["status"] == "SAT":
                    print(f"  SAT  n={n:<4} p={p:<4} m={m:<3} {g['name']:<28}"
                          f" {row['vars']} vars ({row['secs']}s)", flush=True)
                json.dump(rows, open(a.out, "w"), indent=1)
        print(f"  p={p} done ({len(rows)} rows)", flush=True)

    # OVER_CAP rows are BOOKKEEPING, not decisions. Testing `not rows` was
    # right only while a skipped class produced no row; recording them to keep
    # the table honest also refilled `rows`, so a run that decided nothing --
    # every class over the cap, no solver ever called -- walked straight past
    # this guard and exited 0 with the same "0 SAT" table a real sweep prints.
    # The guard has to count DECIDED cells.
    decided = [r for r in rows if r["status"] != "OVER_CAP"]
    if not decided:
        # No cell was decided, and with no decided rows there is no ERROR or
        # TIMEOUT to find below -- so an empty selection would otherwise print
        # a table of nothing and exit 0, reading as "swept, found no witness".
        print(f"\nno cell was DECIDED by pmin={a.pmin} pmax={a.pmax} "
              f"mmax={a.mmax} max-vars={a.max_vars}: {len(rows)} class(es) "
              f"were selected and every one of them was over the "
              f"{a.max_vars}-variable cap. Nothing was swept.",
              file=sys.stderr)
        return 1

    sat = [r for r in rows if r["status"] == "SAT"]
    # A TIMEOUT is an UNDECIDED cell, not a decided one. This file's docstring
    # promises a row for every (p, d, m) and the conclusion drawn from it is
    # about which cells are SAT, so a run that leaves cells undecided is not
    # the sweep it claims to be -- whatever the reason.
    errs = [r for r in rows if r["status"] in ("ERROR", "TIMEOUT")]
    over = [r for r in rows if r["status"] == "OVER_CAP"]
    print(f"\n{len(rows)} cells, {len(sat)} SAT, "
          f"{sum(1 for r in rows if r['status'] == 'EMPTY')} empty by construction, "
          f"{len(errs)} undecided (ERROR or TIMEOUT), "
          f"{len(over)} never built (over the {a.max_vars}-variable cap)")
    if over:
        print(f"this sweep is exhaustive over the classes at or under "
              f"{a.max_vars} variables, and says nothing about the "
              f"{len(over)} above it")
    if sat:
        print(f"largest n with a witness: {max(r['n'] for r in sat)}")
    if errs:
        print(f"\n{len(errs)} cell(s) were not decided; this sweep is NOT "
              f"exhaustive:", file=sys.stderr)
        for r in errs:
            why = r.get("error") or f"{r['status']} under the {a.cap}s cap"
            print(f"  p={r['p']} m={r['m']}: {why}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
