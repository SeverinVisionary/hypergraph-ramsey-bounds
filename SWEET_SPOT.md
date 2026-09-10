# Does the instance size predict whether a symmetry class holds a witness?

**No.** This file records that negative result: the opposite is a natural
hypothesis, and the measurements refute it.

## The hypothesis

The sweeps look, at first, like they show a pattern: the very largest groups leave
so few orbit variables that their classes are empty and UNSAT lands in
milliseconds, while the smallest groups leave so many that CDCL cannot decide
them. So — the story went — there is a *band* of orbit counts where a witness
can live, and if you could characterise it you could predict which group to try
instead of sweeping. That would be methodology, which is what this work
otherwise lacks.

## The data

The evidence is every class this package has a record for: the shipped
`ansatz*_results.json` and `cell_*.json` hold **200 rows**, covering **185
distinct (class, n) pairs** at n = 34, 35, 36, 63, 79, 80, 81, 82, 83, 84 and
88 (a class re-run at a different cap appears more than once).
`test_sweet_spot_counts.py` recomputes both numbers from the shipped files.
The table below is the witnesses this hypothesis was tested against:

| cell | n | vars | faces / var | status |
|---|---|---|---|---|
| R(5,5;4) | 35 | **107** | 489.3 | **SAT** |
| R(5,5;4) | 34 | **95** | 488.2 | **SAT** |
| R(4,4,4;3) | 79 | **81** | 976.3 | **SAT** |

And the neighbourhood of the first one, at n = 35, in variable order:

| group | vars | status |
|---|---|---|
| E_32 : U | 86 | UNSAT |
| AGL(3,2) | 101 | UNSAT |
| **Hol(Z_34)** | **107** | **SAT** |
| S_4 wr S_2 | 133 | UNSAT |
| Hol(Z_32) | 170 | UNSAT |

## Why the hypothesis is dead

**The SAT class is an island, not a threshold.** 101 variables is UNSAT, 107 is
SAT, 133 is UNSAT. Satisfiability is not monotone in the variable count, so no
cutoff — and no band expressed purely in orbit counts — can separate the cases.
A predictor built on instance size would have skipped Hol(Z_34) as
indistinguishable from AGL(3,2) sitting six variables below it.

The same holds against normalised measures. `faces/var` is faces per SAT
variable — NOT the mean orbit size, which differs from it by the colour count:
the n=79 R(4,4,4;3) row has 27 orbits and 81 variables because that encoding is
three-colour, so its mean orbit size is 79,079/27 = 2,928.9 while the column
reads 79,079/81 = 976.3. Two-colour rows coincide. Taken as faces per variable,
and the SAT classes sit at 489, 488 and 976 — but plenty of UNSAT classes sit
between those values (R(5,5;4) at n=36 has UNSAT at 482.8 and 512.2, straddling
489 exactly: those are the 122-variable and 115-variable rows of
`ansatz36_results.json` and `ansatz36b_results.json`, at C(36,4) = 58,905 faces
each).

**What the size DOES predict is decidability, not satisfiability.** The
extremes behave exactly as expected: the largest groups answer instantly, and
below some point nothing finishes. At R(5,5;3), n = 88, 52 variables decides in
milliseconds and the freest classes do not finish at all.

**But the boundary is not sharp, and its position is not known by reasoning.**
It is tempting to read the milliseconds at 52 variables and the timeouts at the
free end as a clean cut somewhere just above 52, with no gap between them where
a witness could sit undetected. There is a gap: `CELLS.md` records two
76-variable classes deciding in 16-60 s. The decidable band reaches at least
that far, and where it ends was settled by re-running, not by argument. So the
*window in which a question can be asked at all* is real and measurable, but
its edges are not known precisely; the *window in which the answer is yes* is
not a function of size at all.

## What this leaves

The honest statement is that group **structure**, not group **size**, decides
whether a class contains a witness, and we cannot currently predict it. Both
R(5,5;4) witnesses came from the holomorph of `Z_34`, but not in the same
shape: at n=35 it acts on 34 points with one fixed (`Hol(Z_34)`), and at n=34
it acts on all 34 with none fixed (`Hol(Z_34) | 34pt`). The R(4,4,4;3)
witnesses came from affine towers `Z_p : C_d`
with fixed points adjoined, acting with no fixed point at the top of the tower
at all, so even that shape does not generalise on this evidence.

Twelve witnesses across three cells — the twelve `witness_*.json` files in
this package — now sit behind this table, and none of them
changes the conclusion — they add points, not a rule. Anyone continuing this
should treat "which groups work" as open, and should not read the size band as
a predictor: it is set out here precisely so that it is not mistaken for one.
