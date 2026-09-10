# Superseded runs — read the correction below before citing one

Every file here is a run that a later run replaced. They are separated from
`logs/` **so that no file presented as evidence contains a statement this
package knows to be false** — and the table below names, for each file, exactly
which statement that is.

Those named statements are false and must not be cited. Everything else in each
file is an ordinary record of a run that happened, and may be cited with this
page: `CELLS.md` cites `n63.log`'s build time that way, as one of three
measurements of how much this host's wall-clock varies on the same
construction -- same group, same 29 variables and 14,384 clauses, though this
run predates the correction to the emptiness diagnostic, so "identical code"
would overstate it. The
directory is quarantined because of specific false statements, not because the
runs did not happen.

| file | why it is superseded | what to read instead |
|---|---|---|
| `n63.log` | prints `NOTE: N orbit(s) are forced both ways -- this class is empty by construction` for four classes. **That diagnosis is false.** It was computed from the positive clause family alone, which is sound only on the diagonal; this cell is `s = 4`, `t = 6`, and `contradictory_vars` is empty for all five classes. | `../n63_all.log`, and the correction in `CELLS.md` and `THEOREMS.md` |
| `certs63.log` | ends `3/5 class(es) certified UNSAT` — an incomplete certification attempt | `../certs63_final.log` (`5/5`) |
| `certs63_rat.log` | also ends `3/5`; the attempt that added full RAT checking, which changed nothing because the real cause was deletion handling | `../certs63_final.log` |

The two `3/5` runs are worth keeping because the reason they failed is a
property of the proofs themselves, described in `CELLS.md`: these DRAT proofs
are almost entirely deletion steps naming clauses the checker was never given.
