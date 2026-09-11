# Three improved lower bounds for hypergraph Ramsey numbers

Explicit, machine-checkable colourings improving three entries of §7.1(a) of
Radziszowski's dynamic survey *Small Ramsey Numbers* (DS1, revision #18,
24 April 2026, [doi:10.37236/21](https://doi.org/10.37236/21)).

| cell | DS1 rev #18 | this work | witness |
|---|---|---|---|
| `R(4,4,4;3)` | `>= 79` | **`>= 84`** | 83 points, 3 colours |
| `R(4,6;3)` | `>= 63` | **`>= 64`** | 63 points, 2 colours |
| `R(5,5;4)` | `>= 35` | **`>= 36`** | 35 points, 2 colours |

DS1's convention (p. 5): `R` is the **least** `n` forcing a monochromatic
clique, so a good colouring on `n` points proves `R >= n+1`.

## The objects, not the search

Each result is a group-invariant colouring, and each is given here as a small
table rather than as solver output. `construction.py`, `construction_n63.py`
and `construction_n35.py` each rebuild their entire colouring from that table
alone — no solver, no witness file — and each is tested to reproduce the
committed witness entry by entry.

**`R(4,4,4;3) >= 84`.** Let `p = 83`, `a = 9` (a generator of the order-41
subgroup of `Z_83^*`), and `G = {x -> a^i x + b}`, of order 3403. `G` acts on
the 91,881 triples of `Z_83` with exactly **27 orbits, each free of size 3403**
(91,881 = 27 x 3403).
Twenty-seven numbers give the colours, nine per colour, so the three colour
classes are exactly equal at 30,627.

That equality is **not forced**. Regularity forces every colour class to be a
multiple of 3403, which permits 8/9/10 as readily as 9/9/9. Enumerating all
invariant good colourings of this class gives **36** of them: twelve split
9/9/9 (30,627 each) and twenty-four split 8/9/10 (27,224 / 30,627 / 34,030).
`enumerate_n83.py` is the enumeration — it blocks each model and re-solves until
the formula is UNSAT, so the count is exhaustive rather than a search that
stopped — and `logs/enumerate_n83.log` is the run. The colouring published here
is balanced; the class does not require it.

**`R(4,6;3) >= 64`.** `H = <10,19,37,46,55> <= Z_63^*` of order 6, `G` of order
378, **120 orbits** on the 39,711 triples of `Z_63`. The action is *not* free:
its orbit sizes are 378, 189, 126, 63 and 21. The displayed orbit-colour
assignment has colour-class sizes 14,070 and 25,641; these sizes are properties
of that assignment, not consequences of nonfreeness.

**`R(5,5;4) >= 36`.** `G = Hol(Z_34)` of order 544 acting on 35 points with one
point fixed, **107 orbits** on the 52,360 four-subsets. Also not free (orbit
sizes 544, 272, 136).

## Verification

Every one of the twelve deposited witnesses is verified by full enumeration,
each under a hash-bound run kept in `logs/`, by a checker that shares no
imports with the search code. Two different claims were run together here and
they are not the same: *shares no search implementation* holds for every
witness; *uses no `itertools`* holds for `verify_scratch.py`, which builds the
face order and the clique scan from explicit nested loops and is applied to the
four-uniform witness. The other checkers (`verify.py`, `independent_check.py`
and the hash-bound `verify_witness_*` wrappers) do use
`itertools.combinations` for their face indexing, which is why
`verify_scratch.py` exists at all -- to derive the ordering convention a second
time, by different means:

| cell | enumerated | monochromatic |
|---|---:|---|
| `R(4,4,4;3)` | 1,837,620 four-subsets | 0 in each of 3 colours |
| `R(4,6;3)` | all 4- and 6-subsets | 0 and 0 |
| `R(5,5;4)` | 324,632 five-subsets | 0 in each of 2 colours |

The `R(4,6;3)` check is run **both ways round**: under the intended reading
there are no monochromatic cliques, and under the inverse reading there are
102,627. The second number is what makes the first meaningful.

Negative results are checkable too, with one honest qualification.
`drat_check.py` replays a solver's proof with its own propagation engine (RUP,
with RAT), and re-running `certify_nulls.py` machine-checks the five classes of
`groups63.json`. **The proofs themselves are not deposited** —
`certs_46_3_n63.json` records the outcome and step counts, not the proof
clauses, so replaying them means re-running the solver rather than reading a
committed certificate. The full `n = 63` tower has **22** classes (15 UNSAT,
6 SAT, 1 timeout, in `cell_46_3_n63_all.json`); only those five were certified. Its discriminating test
weakens a real instance until it becomes satisfiable and requires the checker to
refuse it.

    pip install python-sat pytest      # the only dependencies
    ./reproduce.sh                     # constructions, witnesses, theorems
    ./reproduce.sh --full              # also the certificates and engines

`reproduce.sh` creates its scratch directory under `${TMPDIR:-/tmp}` and removes
it on exit.

`reproduce.sh` covers the constructions, their agreement with the committed
witnesses, the obstruction theorems and the certificates. It does not re-derive
every number quoted in the prose.

## Theorems

`THEOREMS.md` states the three obstruction results, which rule out symmetry
classes before any solver runs. The one worth reading is **Theorem B**: if
`|G| = C(p,2)` and the index-two multiplier subgroup omits `-1` — equivalently,
within that index-two family, `p = 3 (mod 4)` — then the affine group is regular on unordered pairs, so
adjoining a fixed point forces every triple through it into one orbit and one
colour; the base must then be coloured with one fewer colour while avoiding a
monochromatic `K_4^(3)`, impossible once `p >= R(4,4;3) = 13`. This explains why
the pair-regular class of each tower here -- `Z_83 : C_41` and `Z_79 : C_39`,
not the top of either tower -- dies the moment a fixed point is added.

**The order condition alone is insufficient.** For `p = 1 (mod 4)`, `-1` is a
quadratic residue, `x -> -x + (a+b)` stabilises every pair, and there are two
pair-orbits rather than one. The conclusion genuinely fails, with satisfiable
classes at `p = 13` and `p = 37`; these examples target the omitted-`-1`
hypothesis and do not by themselves establish independence of every condition
in a broader generalisation. The classes are accompanied by the run recorded
in `logs/theorem_b_counterexamples.log`, which produces and verifies them.
Dropping the second hypothesis excludes thirteen
classes that are not in fact excluded; the counterexamples are recorded in
`THEOREMS.md`.

## What is not claimed

- **Novelty is provisional.** Both incumbents are *personal communications*
  (`[Dyb3]` 2018, `[Ex24]` 2021), which were not obtained through the sources
  searched. MathSciNet, zbMATH,
  Google Scholar, DataCite and the incumbent's own public addendum were
  searched and nothing stronger was found. The incumbent's one published paper
  on this topic (`MR3897228`) carries zero citations in MathSciNet and one in
  Google Scholar, and that citing work is principally on graph Ramsey numbers
  (its one 3-uniform object is `K_4` minus a hyperedge, not the complete
  `K_4^(3)` of these cells). But a
  newer unpublished communication was not excluded by the searches reported
  here.
  `PRIOR_ART.md` records exactly what was and was not reachable, including the searches that returned nothing
  because a database was unreachable rather than because nothing was there.
- **The prior-art search covered the earlier claims, not all the current
  ones.** It was run for `R(5,5;4) >= 36` and for `R(4,4,4;3) >= 80` and
  `>= 81`. The later climb to `>= 84` and the `R(4,6;3) >= 64` result are
  covered only by the broader database pass, which returned no stronger source
  but was not a per-claim search.
- **No upper bounds.** DS1 prints none for any §7.1(a) cell, so these
  improvements have no denominator and do not narrow a stated gap.
- **The incumbent constructions have not been re-verified here.** For the two
  `[Dyb3]` cells, the public addendum's files were retrieved and their sizes,
  hashes and declared vertex counts read — but not checked to be valid
  colourings. For `R(5,5;4)` there is no comparable object at all: `[Ex24]` is a
  personal communication and the author's public page shows only a weaker
  33-vertex construction, so that incumbent was never seen.
- **Every negative result is about a symmetry class, never about a Ramsey
  number.** A class can be empty while the cell is wide open.
- **Runtime is not a novelty argument.** A short local run can coexist with
  prior unpublished, poorly indexed or differently described work; the
  priority limits above remain in force.

## Layout

    construction*.py     the three results as defining tables
    THEOREMS.md          the obstruction theorems
    ansatz.py            two-colour orbit-SAT engine
    multicolour.py       m-colour engine
    obstruction_general.py
    drat_check.py        separate RUP/RAT proof checker
    verify_scratch.py    verifier sharing no code with the producer
    witness_*.json       the certificates
    groups*.json         the symmetry towers
    logs/                run evidence
    CELLS.md             per-cell record, and what each cell does not settle
    PRIOR_ART.md         what was searched, and what could not be reached

## Licence

Code MIT (`LICENSE`); documentation and data CC BY 4.0 (`LICENSE-DOCS`).
