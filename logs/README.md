# Run logs — the evidence for every timing quoted in this package

This project runs no CI, and "CI is green" would not be admissible
evidence — the local run is quoted instead. These are those runs, kept verbatim.

**Where a number in the write-ups comes from.** Solve and build times for a
symmetry class are recorded in that cell's `cell_*.json`, which is the source
for them; the logs here record the runs that produced those files, plus the
verification, certification and gate runs, which have no JSON. The
microbenchmark table in `CELLS.md` is neither: it is produced by running
`bitmask_experiment.py`, and is labelled there as such. A number that names none
of these three is a number this package should not be quoting.

| file | what it records |
|---|---|
| `gate.log` | the known-answer gate, complete run. R(3,3)=6 and R(3,4)=9 reproduce **both sides** in milliseconds; R(4,4;3)=13 reproduces on the SAT side at n=12; the n=13 UNSAT side **times out** and is recorded as a timeout, not as a pass. |
| `calib_554.log` | full-space (5,5;4) ladder, 3 repeats per n, with per-rep timings and spread. Source for the scaling law. |
| `calib_n31.log` | the single line behind the ">580x" claim: full-space n=31 **TIMEOUT at 5400s**, against 9.3s cyclic. `calib_n31.json` was never produced, so this log is the only record of the rung. |
| `cyclic.log` | cyclic ladder: no witness at n=30, witnesses at n=31/32/33, and the n=34 build line with **no result**. Nothing about n=34 can be read from it. |
| `cyclic_n34.log` | the n=34 restart, which also ends without a result. |
| `n88.log` | R(5,5;3) at n=88. **Stitched, not a single clean run:** a truncated `cap 60s` fragment sits inside the `cap 120s` run, and a headless block of 60 s rows trails the 120 s JSON. Read `cell_55_3_n88.json` for the authoritative statuses. |
| `superseded/n63.log` | R(4,6;3) at n=63, one clean run, `cap 2400s`. The cap survives only here: `cell_46_3_n63.json` records `cap_s: null`, because the deadline is enforced by the OS rather than passed to the solver. |
| `verify_n79_444.log`, `verify_n80_444.log`, `verify_n81_444.log`, `verify_n82_444.log` | the four intermediate `R(4,4,4;3)` witnesses under the same independent verifier as the headline object, each bound to its colour vector's SHA-256: complete scans of all C(n,4) four-subsets, zero monochromatic in any of the three colours, and the perturbation control. These are the evidence for the colour-class counts and hashes quoted for n=79..82 in `CELLS.md`. |
| `verify_n83_444.log` | complete hash-bound verification of the `R(4,4,4;3) >= 84` witness by `verify_witness_n83.py`, bound to the colour vector's SHA-256: all 1,837,620 four-subsets scanned, zero monochromatic in any of the three colours, and a perturbation control that must produce a violation. |
| `verify_n35_554.log` | the `R(5,5;4) >= 36` witness under BOTH from-scratch checkers, `verify_scratch.py` (324,632 five-sets) and `independent_check.py` (649,264 cliques, no rank arithmetic anywhere). |
| `enumerate_n83.log` | **every** `Z_83 : C_41`-invariant good 3-colouring at n=83, by blocking each model and re-solving until the formula is UNSAT: 36 of them, 12 splitting 30627/30627/30627 and 24 splitting 27224/30627/34030. Every model is re-verified from scratch before it is counted. This is the evidence for the exhaustive count in `README.md`; a witness search stops at the first model and cannot establish one. |
| `negcontrol.log` | the discriminating control for the DRAT checker, on the class that certifies by **proof replay** (30,939 steps), not by unit propagation: weakening the instance turns it satisfiable and no satisfiable instance is certified. `negative_control.py` is the script. |
| `verify_n26_554.log`, `verify_n31_554.log`, `verify_n32_554.log`, `verify_n33_554.log`, `verify_n34_554.log` | the five smaller `R(5,5;4)` witnesses under the same two differently implemented checkers as the n=35 object, each bound to its colour vector's SHA-256. With these and the n=79..82 runs, every one of the twelve deposited witnesses has a hash-bound verification log by a checker with a different implementation. |
| `theorem_b_counterexamples.log` | the two `p = 1 (mod 4)` classes that make Theorem B's second hypothesis necessary, produced rather than asserted: `Z_13 : C_6 + 1 fixed` (n=14) and `Z_37 : C_18 + 1 fixed` (n=38) both have `|G| = C(p,2)`, both fail `-1 not in H`, and both are SAT with a colouring re-verified from scratch. `theorem_b_counterexamples.json` is the machine-readable result. |
| `crosscheck_n63.log` | the five n=63 UNSAT classes re-decided by Glucose3 and Minisat22 — neither of which the sweep (Cadical195) or the certifier (Glucose42) uses. This is the evidence that those nulls are solver-independent. |
| `n88_recheck.log` | the two 76-variable `R(5,5;3)` classes at n=88 re-run from the shipped code, so that both rows rest on a run inside this package. Both UNSAT: 60.3 s and 16.0 s. This is the evidence for those two rows in `cell_55_3_n88.json`. |
| `certs63_final.log` | **The authoritative certification run**: all five n=63 UNSAT classes replayed and certified, `5/5 class(es) certified UNSAT`. The timings quoted in `CELLS.md` are this run's. |
| `superseded/certs63.log`, `superseded/certs63_rat.log` | **Superseded attempts, both ending `3/5 class(es) certified UNSAT`.** They are kept because the two failures are the subject of the write-up in `CELLS.md` -- the proofs are almost entirely deletions, and honouring them stripped clauses the checker was never given. Do not read either as evidence for the five-class claim; `certs63_final.log` is that evidence. |
| `verify_n63_46.log` | complete two-way verification of the `R(4,6;3) >= 64` witness by `verify_witness_n63.py`, bound to the colour vector's SHA-256. The run is complete: both the reversed-reading count and the intended-reading result are present, and the exit status is 0. |

Nothing here has been edited. One of these files is **not** a single
continuous run — `n88.log` is stitched from re-runs at different caps, and it is
listed that way rather than presented as clean. Where a run ended without a
result the log simply stops, and the write-ups say so rather than filling the
gap.

**Superseded runs live in `superseded/`, not here.** Three files were moved
there: a run whose printed diagnosis is now known to be false, and two
incomplete certification attempts. `superseded/README.md` says which statement
in each is wrong and what to read instead. Nothing in this directory contains a
claim this package believes to be false.

One naming note: `tower34.log` and `tower35.log` record the witness files they
wrote using transient names that do not ship: `witness_n34_Hol(Z_34)_|_34pt.json`
(a transient name) and `witness_n35_Hol(Z_34).json` (a transient name). The
objects ship as `witness_n34.json` and `witness_n35.json`, byte-identical apart
from the filename.

**Wall-clock numbers in these logs are not measurements of the code.** The same
`Z_63 : <2,5>` build — 29 variables, 14,384 clauses — is logged here three
times at three speeds: **16.1 s** in `crosscheck_n63.log`, **19.9 s** in
`superseded/n63.log` and **168.9 s** in `n63_all.log`, on one machine. The
CNF construction is the same computation in all three — same group, same 29
variables and 14,384 clauses — though the `superseded/n63.log` run predates the
correction to the emptiness diagnostic, so "byte-identical" would overstate it. A timing quoted from these logs is evidence that a run
happened, not evidence of how fast anything is; performance claims need a
calibrated benchmark on an idle machine (see `bitmask_experiment.py` and the
timing section of `CELLS.md`).
