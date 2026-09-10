# The DS1 §7.1(a) sweep

Six cells are printed in DS1 rev #18 p.73 item 7.1(a). This file tracks what the
group-invariant search reaches in each. **Records are quoted from DS1, never
derived here.**

| cell | DS1 rev #18 record | needs a witness on | this repo | status |
|---|---|---|---|---|
| `R(4,5;3)` | `>= 35` `[Dyb2]` | 34 points | 45 classes at n=35: 29 UNSAT, 16 undecided at the cap | not reached |
| **`R(4,6;3)`** | `>= 63` `[Dyb3]` | 62 points | **witness on 63 points** | **`>= 64`** |
| `R(5,5;3)` | `>= 88` `[Dyb3]` | 87 points | 15 classes at n=88: 3 UNSAT, 12 TIMEOUT | not reached |
| **`R(4,4,4;3)`** | `>= 79` `[Dyb3]` | 78 points | **witnesses on 79-83 points** | **`>= 84`** |
| **`R(5,5;4)`** | `>= 35` `[Ex24]` | 34 points | **witness on 35 points** | **`>= 36`** |
| `R(5,5,5;3)` | `>= 163` `[BudHR1]` | 162 points | not attempted | out of reach |

DS1 notes of the last cell that it *"can be much improved to 7570 <= R(5,5,5;3)"*,
so its printed value is not the live record and should not be treated as a target.

## The two improvements

### `R(4,4,4;3) >= 84`

Five witnesses, one vertex apart each.

`witness_444_3_n79.json` — a **three**-colouring of the 79,079 triples of a
79-set with no 4-set monochromatic in any colour. Found by `multicolour.py`
under `Z_79 : C_39` (order 3081): 27 orbits x 3 colours = 81 variables, 1,560
clauses, SAT in under a second. Verified by enumerating all **1,502,501**
four-subsets: 0 monochromatic in each colour. Colour classes 24,648 / 27,729 /
26,702.

`witness_444_3_n80.json` — the same thing one vertex further, on the 82,160
triples of an 80-set. Found under `Z_79 : C_13 + 1 fixed` (order 1027): 80
orbits x 3 colours = 240 variables, 4,931 clauses, SAT after **4,860 s**.
Verified by enumerating all **1,581,580** four-subsets: 0 monochromatic in each
colour. Colour classes 25,675 / 28,756 / 27,729. SHA-256 of the colour vector:
`79fdda50c2f00363b32c1a72f988afacf0a3f7f989735d3d297d649a3f023cec`.

`witness_444_3_n81.json` — one further again, on the 85,320 triples of an
81-set. Found under `Z_79 : C_13 + 2 fixed` (order 1027): 84 orbits x 3 colours
= 252 variables, 5,187 clauses, SAT in **71 s**. Verified by enumerating all
**1,663,740** four-subsets: 0 monochromatic in each colour. Colour classes
28,756 / 27,729 / 28,835. SHA-256 of the colour vector:
`6980873abe5f16e44e15ba8c8fb6832b958dbf8888daf200f9b88842021eaf56`.

`witness_444_3_n82.json` — on the 88,560 triples of an 82-set. Found under
`Z_73 : C_9 + 9 fixed` (order 657): 256 orbits x 3 colours = 768 variables,
9,772 clauses, SAT in **185 s**. Verified by enumerating all **1,749,060**
four-subsets: 0 monochromatic in each colour. Colour classes 24,309 / 31,798 /
32,453. SHA-256 `07f3501596260ad2fc247df3b7f744157dc4f048ed513b8cb8b2c737e3073b3e`.

`witness_444_3_n83.json` — on the 91,881 triples of an 83-set, and the cheapest
of the five. Found under `Z_83 : C_41` (order 3403): 27 orbits x 3 colours = 81
variables, 1,728 clauses, SAT in **under 0.05 s**. Verified by enumerating all
**1,837,620** four-subsets: 0 monochromatic in each colour. The three colour
classes are **exactly equal at 30,627 each**, which is the signature of an
algebraic colouring. SHA-256
`a08602b488ec0f899412ce5cc31ec34a69c05995c1432fd74c04cae9467ecce2`.

Under the DS1 convention a good colouring on 83 points gives `R(4,4,4;3) >= 84`,
against DS1 rev #18's printed `79 <= R(4,4,4;3) [Dyb3]`.

**The ladder climbs by adding fixed points, not by finding cleverer groups.**
The n=79, 80 and 81 witnesses all use an affine group over `Z_79`,
`x -> a*x + b` with `a` in a subgroup of `Z_79^*`, extended by points the group
fixes pointwise — but not the *same* subgroup, and not the same number of fixed
points: the n=79 witness is `Z_79 : C_39` (order 3081, none adjoined), the n=80
witness is `Z_79 : C_13 + 1 fixed` and the n=81 witness is
`Z_79 : C_13 + 2 fixed` (order 1027).
Dropping to the smaller subgroup and adding fixed points both multiply
the number of triple-orbits and so buy the solver freedom: 81 variables at
n=79, 240 at n=80, 252 at n=81. Above n = 79 the rigid classes of each tower (`C_78 + m`, `C_39 + m`,
`C_26 + m` for every `m >= 1` tried) are UNSAT in milliseconds. At n = 80 and
n = 81 the witness sits at `C_13 + 1 fixed` and `C_13 + 2 fixed`; at n = 82 the
p = 79 tower runs out — `C_13 + 3 fixed` is UNSAT as well — and the n=82
witness comes from a different base, `Z_73 : C_9 + 9 fixed`. At n = 79 itself
— the tower with no fixed points adjoined —
`C_39` is where the witness is: 27 orbits leave the solver enough freedom there,
and adjoining even one fixed point closes it (`Z_79 : C_39 + 1 fixed` is UNSAT,
which is what Theorem B explains). `make_groups_79fixed.py` builds these towers
for any n >= 79.

**Why the pair-regular class of each tower fails — a proof, not a search
result.** (Pair-regular, not top: `Z_83 : C_82` and `Z_79 : C_78` sit above
`C_41` and `C_39` in their towers. It is the index-two multiplier subgroup that
Theorem B covers.)
`Z_83 : C_41` has order 3403, and `C(83,2) = 3403` exactly; `Z_79 : C_39` has
order 3081 and `C(79,2) = 3081`. Both act **regularly on unordered pairs**, so
there is a single pair orbit. Adjoin a point `inf` that the group fixes: every
triple `{inf, x, y}` now lies in one orbit and a `G`-invariant colouring must
give them all one colour `c`. No triple inside the base may then take colour
`c`, since it would close a monochromatic `K_4^(3)` with `inf`. So the base
needs its triples 2-coloured with no monochromatic `K_4^(3)` on 83 (or 79)
points, and `R(4,4;3) = 13`. Impossible.

That excludes the entire fixed-point extension of the full group without a SAT
call — **for `m` colours, and only while `p >= R(4,...,4;3)` on `m - 1`
colours.** That last condition is the whole argument, not a footnote: the base
has to be uncolourable in one fewer colour.

At `m = 3` and `p = 79` or `83` the base needs a 2-colouring and `R(4,4;3) =
13`, so the condition holds comfortably. At `m = 4` it does not, and the
conclusion fails — using this package's own object: take the good 3-colouring
of the 79-set (`witness_444_3_n79.json`), adjoin `inf`, and give every triple
through `inf` a fourth colour. That is `Z_79 : C_39`-invariant and has **zero**
monochromatic `K_4^(3)` in all four colours, so a good invariant colouring of
the fixed-point extension exists. So the threshold hypothesis is doing real
work, and the exclusion must not be stated "for any base colouring and any
number of colours": that object refutes exactly that reading.

It matches the data exactly at `m = 3`: `Z_83 : C_41 + 1 fixed` and
`Z_79 : C_39 + 1 fixed` are both UNSAT.
The witnesses live at reduced `d`, where the pair action is no longer regular.
`obstruction_general.pair_regular_fixed_point_obstruction` implements it, with
a test that it fires on both regular classes and on none of the classes that
hold witnesses.

**An inference that does not hold.** The UNSATs at p = 103, 107, 109, 127, 131
might look like evidence that 79 and 83 "sit near the edge" of the family. They
are not, and the argument fails at the first step. Deleting points from a
`Z_q`-invariant colouring does not generally leave a `Z_p`-invariant one, so
these classes are not nested and the usual hereditary argument behind Ramsey
thresholds does not transfer to a parameterised symmetry class. Those UNSATs
say what they say — those classes are empty — and nothing about a maximum.

**And the infinite family that motivated the parameter sweep cannot exist.**
`R(4,4,4;3)` is finite, so any good colouring lives on fewer than `R` points;
there are only finitely many `(p, d, m)` with `p + m < R`. Searching for an
infinite family of successful parameters *for a fixed cell* was ill-posed from
the start, and the sweep was stopped for that reason rather than for lack of a
pattern. An infinite family would need the clique sizes, colour count, or
uniformity to vary — a different problem.

**One base is not enough, and that is the main practical lesson.**

 The `p = 79`
tower carried 79, 80 and 81 and then stalled: at n=82 its `C_13` class is UNSAT
and its `C_6` class has no recorded result at all — `logs/n82.log` ends at that
class's build line, so nothing is claimed about it. Rebasing on `p = 73` with 9
fixed points found n=82 in 185 seconds. `climb.py` now tries every base at a
given n rather than descending one tower.

**A trap on the way: most of those rebased classes are empty before the solver
starts.** At n=82 the `p = 73` tower's top classes report UNSAT at 426-624
variables in under a tenth of a second, which reads as a searched-and-empty
class and is nothing of the kind. A singleton orbit-set bars its orbit from
every colour at once while the exactly-one clause demands it take one, so the
class is contradictory by construction. `multicolour.build_cnf` now reports
`empty_by_construction`; such classes are not nulls and should not be counted
as evidence about anything.

Solve times are not monotone in n and should not be read as difficulty: 0.0 s at
n=79, 4,860 s at n=80, 71 s at n=81, 185 s at n=82 (each the `solve_s` field of
the corresponding `cell_444_3_n*.json`), on a host that has produced a 10.5x
wall-clock spread on identical work — see the timing section below.

**Every witness file carries an explicit `certifies` field**, naming the bound
it supports. That is deliberate and worth stating, because it makes the set of
claims in this package enumerable: listing every `certifies` field across the
tree and accounting for each one is a check anyone can run, and it is the check
that catches a witness file and a write-up disagreeing about what the object
supports.

The 4-cycle obstruction (`obstruction_general.py`, Theorem A') would apply here
— `k = s - 1` again, with `s = 4` — but 4 does not divide `79 * 78 = 6162`, so no
element of any group in this tower has a 4-cycle, so **Theorem A′ excludes no
class here**. That is not the same as saying every class holds something: A′
being silent leaves the class to the solver. Checked before the sweep, not
after.

### `R(5,5;4) >= 36`

`witness_n35.json`. See `README.md` and `PRIOR_ART.md`.

## Prior-art search coverage

The searches are not uniform across the claims, and the difference matters.
`R(5,5;4) >= 36` and the earlier `R(4,4,4;3) >= 80` and `>= 81` claims were
each searched individually; no source located states a stronger bound, which
is not the same as no such source existing. The later climb to `>= 84` and the
`R(4,6;3) >= 64` result are covered only by the broader database pass recorded
in `PRIOR_ART.md`, which likewise returned no stronger source but was not a
per-claim search. `README.md` states the same split.

The R(4,4,4;3) search reached something the earlier two did not: Dybizbanski's
live addendum and its 78-vertex construction. The strongest prior bound located
is 79, backed by that public 78-vertex file, so the 80-point witness here moves
the witness order 78 -> 80 and the bound 79 -> 81. No source at 80 or above was
located; `PRIOR_ART.md` lists which databases could not be reached, and no
exhaustive negative is claimed.

One question the searches do settle: **`[Dyb3]` is not a paper.**
DS1 p. 102 expands it as a 2018 personal communication plus an online addendum
to `[Dyb2]`, and `[Dyb2]` — the published Contributions to Discrete Mathematics
article — was read in full and contains no result for `R(4,4,4;3)`.

**The two cells differ in how far clearance can ever go.** `R(5,5;4)`'s
incumbent is an invisible personal communication, so provisional is the ceiling.
`R(4,4,4;3)`'s incumbent is **public**: the addendum at
`inf.ug.edu.pl/ramsey/` links `r444_78.txt`, a 78-vertex construction, so the
baseline can be verified first-hand and the one-vertex improvement demonstrated
rather than asserted.

**Debt: that verification has not been run.** Until it is, our 79-point object
is compared against a number we have read rather than an object we have checked.

`R(5,5,5;3)` is a caution for exactly this reason: DS1's printed 163 is stale by
DS1's own admission.


## The two "too slow" cells are now reachable

`R(5,5;3)` and `R(4,6;3)` were written off above because building the CNF meant
walking C(88,5) = 39,175,752 and C(63,6) = 67,945,521 subsets. The translation
shortcut in `ansatz.distinct_orbit_sets` removes that: when the group contains
every translation, walking only the subsets containing 0 reaches every orbit-set.

Measured at n=88 with `Z_88 : <3,5,7>` (order 3520, the full multiplier group):
**52 variables, 21,924 clauses, built in 5.7 s**. The 3,573.8x figure the tool
prints is `C(88,5) / distinct_pos` = 39,175,752 / 10,962 — one clause family
against one clique family. Measured against all 21,924 clauses the collapse is
1,787x. (The `collapse` field in `stats` is the positive direction only; every
quotation of it should say so.) UNSAT for that class, instantly.

Note what fixed this beyond the shortcut: the first 88-point tower only used
*cyclic* multiplier subgroups and topped out at order 880 with 133 orbits, which
CDCL did not decide under its cap. `Z_88^*` is `C_2 x C_2 x C_10`, so its
non-cyclic subgroups reach order 40, giving groups of order 3520 and instances
four times smaller. **Building the tower from cyclic subgroups only was leaving
the decidable end of it unbuilt.**


## R(5,5;3) at n=88: reachable, three classes decided UNSAT, twelve unknown

15 classes swept, **three decided, all UNSAT**, twelve timed out at a 120 s cap.

| class | \|G\| | vars | clauses | solve | result |
|---|---|---|---|---|---|
| `Z_88 : <3,5,7>` | 3520 | 52 | 21,924 | 0.02 s | UNSAT |
| `Z_88 : <3,17>` | 1760 | 76 | 43,972 | 60.3 s | UNSAT |
| `Z_88 : <7,15>` | 1760 | 76 | 43,724 | 16.0 s | UNSAT |

The 120 s cap is on the **whole child process, build included**, so the solver
budget was less than 120 s and varied: builds of 104.2 s, 96.4 s and 58.9 s
leave roughly 16 s, 24 s and 61 s of actual solving. The timed-out classes run
from 75 variables up to 161, not "75 downward".

Both 76-variable rows were **re-run from the shipped code** rather than carried
over from an earlier run: `logs/n88_recheck.log` is that run, and the two solve
times in the table above are its measurements.

So the decidable band is not confined to the 52-variable class: it reaches 76
variables, at 16-60 s each. **None of the three decided classes holds a
witness**, and the twelve that timed out are unknown — not empty. The classes
that cannot be decided are the freer ones. Twelve classes remain open under a
120 s budget; that is a statement about the budget, not about `R(5,5;3)`, and
this cell supports no claim about whether a witness exists at n = 88.


## R(4,6;3) >= 64 — and the tower that was never built held it

`witness_46_3_n63.json` — a 2-colouring of the 39,711 triples of a 63-set with
no `K_4^(3)` monochromatic in colour 0 and no `K_6^(3)` monochromatic in
colour 1. Found under `Z_63 : <10,19,37,46,55>` (order 378): 120 orbit
variables. Colour classes 14,070 / 25,641. SHA-256
`998c2217a9c3e3cc1d2b082be2a5b9b8d9c30e1d2b62b1dfc1cc896bdbd754cd`.

Verified by explicit nested loops with no repo imports, **both ways round**:
under the intended reading (0 avoids `K_4`, 1 avoids `K_6`) there are zero
monochromatic cliques of each kind, and under the inverse reading there are
102,627 monochromatic `K_4`s in colour 1. The second number is the point — it
shows the check discriminates rather than passing whatever it is handed. Read
with the convention reversed, the same witness looks like a failure with 102,627
violations, so the reading is not a detail.

**These five classes are not the tower.** `groups63.json` holds five
hand-picked classes, all under 64 variables, and every one is UNSAT — which is
not the same as the cell being swept. `Z_63^*`
has 30 subgroups, and 22 classes pass the `--max-vars 200` filter actually
used, so the sweep had covered 5 of 22 — and the 17 missing were the *larger*
ones. Six of them are SAT, all at order 378, at 114, 114, 114, 114, 118 and
**120** orbit variables -- the 120 being `Z_63 : <10,19,37,46,55>`, the class
that holds the deposited witness.

The hand-picked tower excluded precisely the classes that held the answer, and
it did so in a way that looked thorough: five classes, all decided, no
timeouts, a tidy table. Nothing about the result signalled that the search
space had been truncated.

## The rest of the n=63 tower

Five classes, **all five decided, none timed out**. That is the whole of what
happened, and it is much less than "the cell was swept".

`Z_63^*` has 30 subgroups; building `Z_63 : H` for each and applying the
`--max-vars 200` filter actually used leaves **22 eligible classes**.
`groups63.json` holds **five** of them (29, 49, 50, 50, 63 orbit variables).
Never built: a second order-756 class at 63 orbits, order-756 classes at 67 and
77, an order-567 class at 91, twelve order-378 classes at 113-136, and an
order-252 class at 183 orbits.

**The omitted classes are the ones with room to hold something.** The witnesses
this repo has found live well above that: 107 orbit variables for `R(5,5;4)` at
n=35, 240 for `R(4,4,4;3)` at n=80, and 120 for this cell's own witness. Every
class in `groups63.json` is under 64. So this is not a sweep "to completion",
and it is not "empty": five UNSAT classes are five nulls, not a statement about
`R(4,6;3)`, and five of 22 classes is not a sweep of the tower.

| class | \|G\| | vars | clauses | build | solve | result |
|---|---|---|---|---|---|---|
| `Z_63 : <2,5>` | 2268 | 29 | 14,384 | 19.9 s | 0.0 s | UNSAT |
| `Z_63 : <4,5>` | 1134 | 49 | 54,060 | 21.6 s | 0.0 s | UNSAT |
| `Z_63 : <2,11>` | 1134 | 50 | 54,785 | 21.3 s | 0.0 s | UNSAT |
| `Z_63 : <4,10>` | 1134 | 50 | 54,877 | 22.2 s | 0.0 s | UNSAT |
| `Z_63 : <2,31>` | 756 | 63 | 90,594 | 22.7 s | 0.1 s | UNSAT |

**Five UNSAT classes are five nulls, not a result about `R(4,6;3)`.** The tower
is five hand-built symmetry classes out of every colouring of the 39,711 triples
of a 63-set; nothing here bears on the cell itself, and DS1's `>= 63` stands
untouched.

The collapse: the `s = 4` direction takes `C(63,4) = 595,665` four-sets down to
**256** distinct positive clauses, a factor of 2,327 — the largest measured
anywhere in the sweep. The `t = 6` direction takes `C(63,6) = 67,945,521`
six-sets down to 14,128 negative clauses. The two together are the 14,384-clause
row above.

### Certificates: all five nulls are machine-checked

Every witness in this package is an object anyone can re-verify. A *null* is
the opposite by default — a solver reports UNSAT and the outcome is recorded —
and the nulls are what a case analysis would rest on. `drat_check.py` closes that gap:
it replays the solver's proof with its own propagation engine, sharing no code
with `ansatz.py`, and confirms each step.

| class | route | proof steps | certified |
|---|---|---|---|
| `Z_63 : <2,5>` | unit propagation | 0 | **yes** |
| `Z_63 : <4,5>` | proof replay | 13,975 | **yes** |
| `Z_63 : <2,11>` | proof replay | 30,939 | **yes** |
| `Z_63 : <4,10>` | proof replay | 42 | **yes** |
| `Z_63 : <2,31>` | proof replay | 5,250 | **yes** |

`logs/certs63_final.log` is that run and `certs_46_3_n63.json` its output. The
proof-step counts are a property of the proof, not of the host, which is why
they are the column tabulated here; the replay times are in the log.

`Z_63 : <2,5>` is refuted by unit propagation alone — the solver emits an empty
proof because it never had to learn anything. That is the strongest outcome
available, not a missing certificate.

**Why the checker ignores deletion steps.** These proofs are almost entirely
*deletions* — 13,973 of 13,975 steps for one class, with only `[43]` and the
empty clause added, and 6,975 deletion lines naming clauses the checker was
never given. The learned clauses being deleted are not in the emitted proof, so
honouring the deletions strips the database of clauses the solver had replaced
with clauses the checker cannot see, and certification fails on a sound proof.

**Why that is sound, stated carefully.** Ignoring deletions means every step
is checked against `F` plus every clause accepted so far — a superset of the
database the solver held. RUP is monotone in the database, so that makes each
RUP check *easier* to pass, not harder: the checker becomes more permissive,
and an argument of the form "this is the stricter reading" would be false.

Soundness does not rest on strictness. It rests on the chain: each accepted
clause is checked against the accumulated database at that point, a RUP step is
logically implied by it, and a RAT step preserves its satisfiability. (RAT is
not monotone in either direction, so the superset argument is unavailable for
those steps and satisfiability-preservation is what carries them.) Composing
along the chain: if `F` were satisfiable, every accumulated database would be
satisfiable — and the proof ends by deriving the empty clause, which is not.
So `F` is unsatisfiable. Deletion is a solver-side memory optimisation and
carries no logical content that this argument needs.

Because the checker is the more permissive of the two readings, the
discriminating control below is doing real work rather than confirming a
foregone conclusion.

One consequence worth recording: `_DB.delete` previously scanned every clause
linearly, so a proof cost O(deletions x clauses) — about 700 million
comparisons on this instance. Certification took minutes per class and now
takes seconds.

**The control that makes this meaningful.** A checker taking the permissive
reading could in principle accept anything, and small hand-built formulas would
not reveal it. `negative_control.py` weakens a real n=63 instance by dropping a
random fraction of its clauses and re-certifies each one. It runs on
`Z_63 : <2,11>`, which certifies by **proof replay** with 30,939 steps —
deliberately not the class whose route is unit propagation with zero steps,
since a control there would exercise none of the replay machinery it is offered
as evidence for. `logs/negcontrol.log` is the run:

| instance | clauses | status | certified | route | steps |
|---|---:|---|---|---|---:|
| full | 54,785 | UNSAT | **yes** | proof replay | 30,939 |
| keep ~0.9 | 49,292 | UNSAT | **yes** | proof replay | 27,942 |
| keep ~0.7 | 38,273 | **SAT** | no | — | 0 |
| keep ~0.5 | 27,303 | **SAT** | no | — | 0 |
| keep ~0.3 | 16,474 | **SAT** | no | — | 0 |

Weakening a formula can only make it easier to satisfy, so far enough down it
must turn SAT — and no satisfiable instance was certified.

**A SAT row alone is not enough, and the control does more.** `certify` returns
as soon as the solver says SAT, before the proof checker runs, so those rows on
their own record that the SOLVER disagreed — not that the CHECKER refused. So
the original instance's real proof, all 30,939 steps of it, is also replayed
against each weakened formula. It is rejected every time, including against the
formulas that are satisfiable: the checker will not accept a proof of a false
statement about an instance it is handed. That is the rejection the control is
for, and `logs/negcontrol.log` records it per row.

### Independent reproduction of the n=63 nulls

**All five** classes from `groups63.json` were rebuilt from `groups63.json` and
re-decided by two solvers the pipeline does not use anywhere: the sweep decides
with **Cadical195** and the certifier replays with **Glucose42**, so neither
appears below. `crosscheck_n63.py` is the script, `logs/crosscheck_n63.log` the
run, and `crosscheck_46_3_n63.json` the machine-readable result.

| class | vars | clauses | Glucose3 | Minisat22 |
|---|---:|---:|---|---|
| `Z_63 : <2,5>` | 29 | 14,384 | UNSAT | UNSAT |
| `Z_63 : <4,5>` | 49 | 54,060 | UNSAT | UNSAT |
| `Z_63 : <2,11>` | 50 | 54,785 | UNSAT | UNSAT |
| `Z_63 : <4,10>` | 50 | 54,877 | UNSAT | UNSAT |
| `Z_63 : <2,31>` | 63 | 90,594 | UNSAT | UNSAT |

The times are deliberately not tabulated here; they are in
`logs/crosscheck_n63.log`, and the section below says why a wall-clock number
from this host is not a quantity worth quoting.

The variable and clause counts match the sweep's own table above exactly, which
is the part of the rebuild a reader can check line by line.

This matters because `ansatz.run` cross-checks against `brute.py` only below 20
variables and the smallest class here has 29: without this run, every one of
these five nulls rested on a single engine. **All five are solver-independent.**

Both runs also bind each row to the generators it was decided from, not to the
class's name: `crosscheck_46_3_n63.json` and `certs_46_3_n63.json` each carry a
full 64-character SHA-256 `gens_sha` per row, and the cross-check refuses to
start unless those pairs are
exactly the pairs the certificate file records. Five names would match even if
one class had been decided twice and another never.

Host variance is the reason. The same `Z_63 : <2,5>` build — 29 variables,
14,384 clauses — appears in three shipped logs at **16.1 s**
(`crosscheck_n63.log`), **19.9 s** (`superseded/n63.log`) and **168.9 s**
(`n63_all.log`): one machine, the same construction — same group, same 29
variables and 14,384 clauses — and a 10.5x spread. Every
wall-clock number in this package should be read with that in mind; none is a
property of the code, and no claim here rests on one.

### Reproducing it

`ansatz.py` resumes: it reads `--out` and skips classes already decided there,
so the obvious command against the committed tree prints the stored summary and
runs nothing. Point it at a fresh file to actually rebuild:

```
python3 -u ansatz.py --groups groups63.json --n 63 --s 4 --t 6 --k 3 \
  --max-vars 200 --cap 2400 --out <a fresh output path>
```

### What the cheap emptiness tests establish here

Two cheap tests run before the solver. On this cell both clear all five classes
— neither finds anything — and the solver returns UNSAT for all five anyway.
Two distinctions matter for reading that, because the obvious reading of each
is wrong.

`stats["forced_mono_vars"]` is built from the *positive* clause family alone.
On the diagonal (`s == t`) the two families are the same sets, so a singleton
orbit-set emits both `[v]` and `[-v]` and the class really is empty. This cell
is off-diagonal — `s = 4`, `t = 6` — where a singleton in the positive family
is only a unit clause fixing one orbit's colour. It constrains; it proves
nothing. `ansatz.py` separates `forced_mono_vars` (units) from
`contradictory_vars` (forced both ways) and claims emptiness only for the
latter. `contradictory_vars` is empty for all five classes here.

Theorem A′ needs an element with a 4-cycle, and `4 | |G|` is necessary for that
but not sufficient: a group of order divisible by 4 need not contain any
element with a 4-cycle -- the Klein four-group on four points is generated by
products of 2-cycles -- and an element of order 8 must contain an 8-cycle but may
contain a 4-cycle too, so its order settles nothing either way.
Enumerating all 2268, 1134 and 756 permutations directly, **no element of any
of the five groups has a 4-cycle**, so A′ applies to zero classes here. The one
sound divisibility inference is the negative one: `4` does not divide `1134`,
which does rule a 4-cycle out.

### Wall-clock numbers on this host

The `t = 6` direction walks `C(62,5) = 6,471,002` subsets at `C(6,3) = 20`
faces each, and the measured build is **20 s** under the 2400 s cap.

Every runtime in this file is wall-clock on a shared machine, and the spread is
wide enough to swamp most comparisons between encodings: the same `Z_63 : <2,5>`
build is logged at 16.1 s, 19.9 s and 168.9 s in three of this package's own
logs.

The only performance comparison this file makes is the one
`bitmask_experiment.py` prints: the committed `frozenset` path against the
bitmask variant, timed side by side on the same input. No projected or sampled
figures are claimed.

The general point applies to
every timing quoted anywhere in this package — **a wall-clock number from a
loaded host is not a measurement** — and it is why the claims rest on the
solver verdicts, which are load-independent, and never on the times.
