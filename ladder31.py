"""One calibration rung at n=31, three repeats.

The repeats are permutations of the same instance, so they are isomorphic and
must agree; a median taken over a SAT/UNSAT/SAT sequence is a runtime statistic
for a run that contradicts itself. `calibrate.py` refuses that, and so does
`rung()` below, which also refuses an unverified SAT and refuses to exit 0 when
no repeat completed -- the rung's entire output is a runtime, so a rung that
produced none measured nothing and must not report success.

    python3 ladder31.py
"""

import json
import sys

from calibrate import timed_run


def problems_with(rows):
    """Every reason these repeats are not a measurement. Empty means they are.

    Pure and separate from the running, so each branch can be driven to a
    refusal in a test -- see test_no_work_is_not_a_result.py.
    """
    problems = []
    decided = {r["status"] for r in rows if r["status"] in ("SAT", "UNSAT")}
    if len(decided) > 1:
        problems.append(f"repeats disagree {sorted(decided)} on an isomorphic "
                        f"instance; this rung measures nothing")
    if any(r["status"] == "ERROR" for r in rows):
        problems.append("at least one repeat ERRORED; a broken tool is not a "
                        "slow one")
    unverified = [r for r in rows if r["status"] == "SAT" and not r.get("verified")]
    if unverified:
        problems.append(f"{len(unverified)} SAT repeat(s) were not verified")
    if not [x for x in rows if x.get("solve_s") is not None]:
        problems.append("no repeat completed; no median, no bound -- this rung "
                        "measured nothing")
    return problems


def rung(runner=timed_run, out="calib_n31.json"):
    rows = []
    for r in range(3):
        rec = runner(31, 5, 5, 4, seed=1000 + r, cap_s=5400)
        rows.append(rec)
        print(f"n=31 rep{r}: {rec['status']:>7} {rec['solve_s'] or 0:9.2f}s"
              + ("  [VERIFIED]" if rec.get("verified") else ""), flush=True)

    if out:
        with open(out, "w") as fh:
            json.dump(rows, fh, indent=2)

    problems = problems_with(rows)
    if problems:
        print("\nNOT A MEASUREMENT:", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1

    ts = [x["solve_s"] for x in rows if x["solve_s"] is not None]
    print(f"n=31 median {sorted(ts)[len(ts)//2]:.2f}s  "
          f"spread {min(ts):.2f}-{max(ts):.2f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(rung())
