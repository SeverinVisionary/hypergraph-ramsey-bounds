# Prior art: what was searched, and what could not be reached

## The three claims and their incumbents

Source of record: S. Radziszowski, *Small Ramsey Numbers*, Electronic Journal of
Combinatorics, Dynamic Survey DS1, **revision #18, 24 April 2026**, §7.1(a),
[doi:10.37236/21](https://doi.org/10.37236/21).

| cell | DS1 rev #18, verbatim | key | this work |
|---|---|---|---|
| `R(4,4,4;3)` | `79 <= R(4,4,4;3)` | `[Dyb3]` | `>= 84` |
| `R(4,6;3)` | `63 <= R(4,6;3)` | `[Dyb3]` | `>= 64` |
| `R(5,5;4)` | `35 <= R(5,5;4)` | `[Ex24]` | `>= 36` |

**Neither key is a paper.** DS1 p. 102 expands `[Dyb3]` as J. Dybizbański,
*personal communication* (2018), together with a public online addendum;
`[Ex24]` is G. Exoo, *personal communication* (2021). This is the single most
important fact about the novelty question and it is why no result below is
stated as an absolute.

## The incumbent's public objects

Every file linked from the addendum was retrieved and its declared vertex count
read from its first line:

| file | vertices | implies | DS1 prints |
|---|---:|---|---|
| `r444_78.txt` | 78 | `R(4,4,4;3) >= 79` | 79 |
| `r46_62.txt` | 62 | `R(4,6;3) >= 63` | 63 |
| `r55_87.txt` | 87 | `R(5,5;3) >= 88` | 88 |

The printed values are therefore backed by public objects of the right size,
and no linked file claims more. **These files were not re-verified here as valid
colourings** — their sizes and hashes were read, not their contents checked.

Exoo's public construction page is *older* than DS1's value for his cell: it
shows a 33-vertex construction against DS1's printed 35. An old page and a later
personal communication coexist without contradiction, and this is not evidence
against the communication.

## What was searched

**MathSciNet.** The incumbent's one published paper on this topic is
`MR3897228` — J. Dybizbański, *A lower bound on the hypergraph Ramsey number
R(4,5;3)*, Contrib. Discrete Math. **13** (2018) 112-115. Its record shows
**Citations: From References 0, From Reviews 0**. Author sweeps: Dybizbański,
24 indexed items, of which `MR3897228` is the only hypergraph Ramsey one; Exoo,
95 items, none of which states a stronger bound for any cell here. Exoo's
indexed work is largely on graph Ramsey numbers, but not exclusively -- his
public page carries the 33-vertex `R(5,5;4)` construction discussed above, and
that object is a 4-uniform hypergraph colouring.
Title search `ti:(hypergraph Ramsey number)` returned 71 results, none on the
small complete 3-uniform cells.

**Google Scholar.** The same paper shows **Cited by 1**: W. J. Wesley, *New
bounds for some small multicolor Ramsey numbers* (arXiv:2509.03784). It is
principally a graph Ramsey paper: its abstract gives `R(K_4, K_4-e, K_4-e) >=
35`, `R(K_3, K_4, C_4, C_4) >= 49` and `R(C_3,C_6,C_6) = R(C_5,C_6,C_6) = 15`,
all for colourings of the edges of `K_n`. Its body does also treat one
3-uniform object -- a formula for `(K_4^-, K_4^-, K_4^-)`, where `K_4^-` is, in
its own words, "the 3-uniform hypergraph on 4 vertices with all but one
hyperedge present". That is **not** the complete `K_4^(3)` of the cells here,
and the paper states no improvement to any of them.

**zbMATH.** `Zbl 1409.05135` for the same paper. Author sweeps returned 13 and
11 documents respectively over the relevant windows, none on these cells.

**DataCite** responded to `"hypergraph Ramsey"` with 60 records, screened by
title. **HAL** returned nothing on an exact-phrase query.

**DS1 itself.** Revision 18 is current; the author's own revision list ends
there and no erratum was located.

Accession numbers above (`MR3897228`, `Zbl 1409.05135`, `MR4491582`) were read
from the databases' own records at the time of the search. The citation counts
are time-varying by nature and are quoted as displayed then; anyone relying on
them should re-run the query rather than cite this file.

One nearby item was checked and excluded: `MR4491582`, Budden & Clifton,
*Hypergraph Ramsey numbers involving trees, stars, and complete hypergraphs*,
Integers **22** (2022) A92. Its abstract states that it investigates multicolour
hypergraph Ramsey numbers "for various combinations of `r`-uniform trees, stars,
and complete hypergraphs", proving existence theorems and bounds for trees and
stars and exact values in a few star cases. Berge paths and cycles appear as the
definitions used to say what an `r`-uniform tree is, not as the subject. It is
therefore about tree- and star-versus-complete numbers, not the
complete-versus-complete cells of §7.1(a) improved here.

## What could not be reached

Stated because a search that fails and a search that finds nothing look
identical in a summary:

- **Zenodo's API returned HTTP 400** on the attempted query — a failed request,
  not a negative result.
- **Wayback** requests for the addendum directory failed, so a formerly posted
  and since removed larger construction is not excluded.
- Some database queries were run through domain-restricted web search rather
  than the native interface, which is weaker coverage.
- **The personal communications themselves are unobtainable.**

## The honest verdict

**No source located states a stronger bound for any of the three cells.** That
is what a search can establish. "No such source exists" is not, and is not
claimed here.

The single residual risk is the same for all three cells and was not reachable
by any database searched here: **a newer personal communication to the survey's maintainer, not yet
incorporated into DS1**. Both incumbents work directly in this area, and DS1
records their bounds as personal communications -- a channel none of the
sources searched here indexes.

Two further cautions belong on the record. DS1's own next line, for a different
cell, notes that its printed `163 <= R(5,5,5;3)` "can be much improved to 7570"
— a printed DS1 value is not automatically the live record. And the searches
here were cheap: several of the witnesses in this package were found in
seconds. That is a reason to expect the cells have attracted little attention,
not a demonstration that they were unexplored, and not a claim that anything
difficult was done here.
