"""Certificates for the UNSAT side of the sweep.

Every witness this repo reports is an object: a bitstring anyone can re-verify
by enumerating cliques. Every *null* is the opposite -- a solver said UNSAT and
we wrote it down. That asymmetry is the weakest part of the sweep, because the
nulls are what the case analysis rests on.

A DRAT proof closes it. The solver emits the sequence of clauses it derived;
this module replays that sequence against the original CNF and confirms each
step, ending at the empty clause. Nothing here trusts the solver that produced
the proof, and nothing here shares code with `ansatz.py`.

Two deliberate limits, both stated rather than hidden:

* The check is **full DRAT**: RUP first, and RAT on the pivot literal when RUP
  fails. A RUP step is one whose negation unit-propagates to a conflict; a RAT
  step on pivot `l` is one where, for every clause `D` containing `-l`, the
  resolvent of the new clause with `D` is itself RUP. Solvers that eliminate
  variables emit RAT steps, so RUP alone rejects their proofs -- two of the
  five n=63 classes failed exactly that way before RAT was added.
  `check` returning False still means "not verified", never "satisfiable".

* PySAT's Cadical195, which `ansatz.py` uses, emits an empty proof in this
  build even on a plainly UNSAT instance. Proofs here are re-derived with
  Glucose42, so the certificate and the sweep come from different solvers --
  which is a feature, not a workaround: a bug in one does not produce a proof
  the other accepts.

* **Deletion lines are ignored, and that is deliberate.** PySAT's Glucose proof
  for these instances turned out to be almost entirely deletions: one class
  emitted 13,975 steps of which 13,973 were deletions and only two were
  additions, and 6,975 of those deletion lines named clauses the checker never
  had. The learned clauses being deleted were never handed to us, so honouring
  the deletions strips the database of clauses the solver had replaced with
  clauses we cannot see -- and the remaining steps then fail to follow.
  Skipping deletions checks every step against F plus every clause accepted so
  far -- a SUPERSET of the database the solver held. RUP is monotone in the
  database, so that makes each RUP check EASIER to pass: the checker is the
  more permissive of the two readings, not the stricter one, and any argument
  of the latter shape would be false.

  Soundness rests on the chain instead. Each accepted clause is checked against
  the accumulated database at that point; a RUP step is logically implied by
  it, and a RAT step preserves its satisfiability. (RAT is monotone in neither
  direction, so the superset argument is unavailable there and
  satisfiability-preservation is what carries those steps.) If F were
  satisfiable then every accumulated database would be, and the proof ends by
  deriving the empty clause, which is not. So F is unsatisfiable. Deletion is a
  solver-side memory optimisation with no logical content this needs.

  Because this is the permissive reading, the discriminating control in the
  tests -- weakening a real instance until it is satisfiable, and requiring the
  checker to stop certifying at exactly that point -- is what establishes the
  checker is not simply accepting whatever it is handed.
"""

from collections import defaultdict


def emit_proof(clauses, solver="Glucose42"):
    """Run `clauses` and return (is_sat, proof_lines).

    proof_lines are DRAT: a list of int-lists, where a leading 0 sentinel is
    absent and deletions arrive as ('d', [lits]).
    """
    import pysat.solvers as ps

    S = getattr(ps, solver)
    s = S(bootstrap_with=[list(c) for c in clauses], with_proof=True)
    try:
        sat = s.solve()
        if sat:
            return True, []
        raw = s.get_proof() or []
    finally:
        s.delete()

    proof = []
    for line in raw:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "d":
            lits = [int(x) for x in parts[1:] if x != "0"]
            proof.append(("d", lits))
        else:
            lits = [int(x) for x in parts if x != "0"]
            proof.append(("a", lits))
    return False, proof


class _DB:
    """Clause database with two-watched-literal propagation.

    Written for replay, not for search: it never learns and never restarts, so
    the only operations are add, delete, and propagate-under-assumptions.
    """

    def __init__(self):
        self.clauses = {}          # id -> list of lits
        self.by_key = defaultdict(list)  # frozenset(lits) -> [clause id]
        self.watch = defaultdict(set)   # lit -> {clause id}
        self.units = []            # lits asserted by unit clauses in the DB
        self.empty = False         # a zero-length clause is in the DB
        self._next = 0

    def add(self, lits):
        lits = list(dict.fromkeys(lits))   # drop duplicate literals, keep order
        cid = self._next
        self._next += 1
        self.clauses[cid] = lits
        self.by_key[frozenset(lits)].append(cid)
        if not lits:
            self.empty = True
        elif len(lits) == 1:
            self.units.append(lits[0])
        else:
            self.watch[lits[0]].add(cid)
            self.watch[lits[1]].add(cid)
        return cid

    def delete(self, lits):
        """Remove one clause equal to `lits` as a set. Absent clause: no-op.

        DRAT deletion lines routinely name clauses the checker never had (a
        solver may delete a clause it derived and we merged), and ignoring
        those is what the default path does. Deleting less than the solver did
        makes every later RUP step EASIER to satisfy, so this is the permissive
        reading -- it does NOT follow that a proof accepted here would also
        check against the solver's exact database, and the module docstring
        gives the argument that does hold (the accumulated-database chain).
        """
        # Indexed by clause key, not scanned. A DRAT proof deletes on the order
        # of one clause per step, so a linear scan here is quadratic in the
        # proof length -- 13,973 deletions against 54,060 clauses is ~700M
        # comparisons, which is what made certification take minutes.
        key = frozenset(lits)
        bucket = self.by_key.get(key)
        while bucket:
            cid = bucket.pop()
            c = self.clauses.pop(cid, None)
            if c is None:
                continue                      # already deleted
            if len(c) > 1:
                self.watch[c[0]].discard(cid)
                self.watch[c[1]].discard(cid)
            elif len(c) == 1:
                try:
                    self.units.remove(c[0])
                except ValueError:
                    pass
            return True
        return False

    def is_rat(self, lits):
        """RAT on the pivot `lits[0]`: every resolvent must be RUP.

        Only clauses containing the complement of the pivot can resolve, and a
        resolvent that is a tautology is trivially satisfied and skipped --
        without that skip a legal proof is rejected, because self-resolution on
        the pivot always produces one.
        """
        pivot = lits[0]
        base = set(lits)
        for cid in list(self.clauses):
            c = self.clauses.get(cid)
            if c is None or -pivot not in c:
                continue
            resolvent = base | {x for x in c if x != -pivot}
            if any(-x in resolvent for x in resolvent):
                continue                       # tautology
            if not self.propagate([-x for x in resolvent]):
                return False
        return True

    def propagate(self, assumptions):
        """True iff unit propagation from `assumptions` + DB units conflicts."""
        if self.empty:
            return True
        value = {}
        trail = []

        def enqueue(lit):
            v = abs(lit)
            want = lit > 0
            if v in value:
                return value[v] == want      # False => conflict
            value[v] = want
            trail.append(lit)
            return True

        for lit in list(self.units) + list(assumptions):
            if not enqueue(lit):
                return True

        i = 0
        while i < len(trail):
            lit = trail[i]
            i += 1
            false_lit = -lit
            # Copy: the set is mutated while we re-watch.
            for cid in list(self.watch[false_lit]):
                c = self.clauses.get(cid)
                if c is None:
                    self.watch[false_lit].discard(cid)
                    continue
                # Put false_lit in slot 1 so slot 0 is the other watch.
                if c[0] == false_lit:
                    c[0], c[1] = c[1], c[0]
                other = c[0]
                if value.get(abs(other)) == (other > 0):
                    continue                      # already satisfied
                for j in range(2, len(c)):
                    cand = c[j]
                    if value.get(abs(cand)) != (cand < 0):
                        c[1], c[j] = c[j], c[1]    # new watch
                        self.watch[false_lit].discard(cid)
                        self.watch[c[1]].add(cid)
                        break
                else:
                    if not enqueue(other):
                        return True
        return False


def check(clauses, proof, honour_deletions=False):
    """Replay `proof` against `clauses`; True iff it ends in the empty clause.

    Sound and incomplete -- see the module docstring. False means "this proof
    was not verified", never "satisfiable".
    """
    db = _DB()
    for c in clauses:
        db.add(c)

    reached_empty = db.empty
    for kind, lits in proof:
        if kind == "d":
            if honour_deletions:
                db.delete(lits)
            continue
        # RUP first: assume every literal of the new clause false, propagate,
        # expect a conflict. Cheap and covers most steps.
        if not db.propagate([-l for l in lits]):
            # RAT fallback. DRAT's pivot is the FIRST literal of the clause;
            # the step is valid if resolving on it against every clause holding
            # the complement yields a RUP clause each time. This is what makes
            # variable-eliminating preprocessors checkable.
            if not lits or not db.is_rat(lits):
                return False
        db.add(lits)
        if not lits:
            reached_empty = True

    # An empty proof is not a failed proof. A solver that refutes the instance
    # by unit propagation alone learns nothing and so emits nothing -- which is
    # the strongest outcome available, not the weakest: the empty clause is RUP
    # directly from the original CNF, and this checker can confirm it without
    # replaying anything. Every UNSAT class in this sweep is of that kind.
    return reached_empty or db.propagate([])


def certify(clauses, solver="Glucose42"):
    """Emit and immediately re-check a proof. Returns a summary dict."""
    sat, proof = emit_proof(clauses, solver=solver)
    if sat:
        return {"status": "SAT", "checked": False, "steps": 0}
    ok = check(clauses, proof)
    adds = sum(1 for k, _ in proof if k == "a")
    dels = sum(1 for k, _ in proof if k == "d")

    # Say which kind of certificate it is, so "0 steps" cannot be misread as
    # "no proof".
    db = _DB()
    for c in clauses:
        db.add(c)
    by_propagation = db.propagate([])

    return {"status": "UNSAT", "checked": ok, "steps": len(proof),
            "additions": adds, "deletions": dels, "solver": solver,
            "route": "unit propagation" if by_propagation else "proof replay"}
