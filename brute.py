"""Decide a small CNF by exhaustive enumeration, with no solver involved.

WHY.  Four consecutive rungs of the Z_33 ladder ran to a 30-minute cap without
a verdict, and the arithmetic says they should not have.  Rung 1 has 166
variables and, once the 40920 clauses are deduplicated (translates of a base
4-set give literally the same clause, and every Z_33-orbit of 4-sets has full
size 33, so 40920/33 = 1240 survive), 1240 clauses of width 4.  Density 7.5, at
166 variables, below the random 4-SAT threshold of about 9.93.  CDCL should
settle that in milliseconds.

Two explanations fit the timeouts and they need opposite responses.  Either the
plumbing is defective -- and I have already shipped two cap bugs and a deadlock
on this same path, so that is not a hypothesis I get to dismiss -- or the
instances are genuinely hard for resolution, which design-existence problems
famously are (the pigeonhole principle is the standard example: few variables,
short clauses, provably no subexponential resolution proof).

This module distinguishes them.  The tower's top rungs have 12 to 16 variables,
so they can be decided by enumerating all 2^v colourings.  If brute force and
CaDiCaL agree instantly there, the encoding and the plumbing are sound and the
166-variable timeout is real hardness.  If a 12-variable instance times out,
it is a bug, full stop.

HOW.  One big integer per clause, with bit m set iff assignment m satisfies it,
then AND them together; the answer is SAT iff the result is non-zero, and the
lowest set bit is a model.  Python's big-int AND runs at C speed over the whole
2^v-bit word, so this stays fast to about v = 20 (a 128 KB integer per clause).
"""

from __future__ import annotations

# Enumerating 2^v assignments costs 2^v bits per clause; 20 variables is a
# 128 KB integer, which is comfortable.  Past that, memory grows by 2x a
# variable and this stops being the cheap check it is meant to be.
MAX_VARS = 20


def _var_index(lit, n_vars):
    """DIMACS literal -> 0-based variable index, rejecting what is not a literal.

    Literal 0 is not a DIMACS literal -- it is the clause terminator -- and
    `abs(0) - 1` is -1, which silently indexes the LAST variable's mask instead
    of raising. A decider used as a cross-check must never quietly accept
    malformed input and return a confident answer about it.
    """
    if lit == 0:
        raise ValueError("0 is not a literal (it terminates a DIMACS clause)")
    v = abs(lit) - 1
    if v >= n_vars:
        raise ValueError(f"literal {lit} exceeds n_vars={n_vars}")
    return v


def _var_masks(n_vars):
    """masks[i] has bit m set iff assignment m sets variable i+1 true.

    Bit i of the assignment index m IS the value of variable i+1, so the mask
    for variable i is the periodic pattern of 2^i zeros then 2^i ones, repeated
    across all 2^n_vars bits.
    """
    full = (1 << (1 << n_vars)) - 1
    masks = []
    for i in range(n_vars):
        block_bits = 1 << i                     # run length
        block = ((1 << block_bits) - 1) << block_bits
        period = (1 << (block_bits * 2)) - 1    # 2^(2^(i+1)) - 1
        masks.append(block * (full // period))
    return masks, full


def decide(clauses, n_vars, max_vars=MAX_VARS):
    """Exhaustively decide a CNF.  Returns (status, model) with no solver.

    `clauses` is a list of lists of non-zero ints, DIMACS style.  `model` is in
    the same form as a pysat model: one signed literal per variable.
    """
    if n_vars > max_vars:
        raise ValueError(
            f"{n_vars} variables is beyond brute force (limit {max_vars}); "
            f"2^{n_vars} assignments would need "
            f"{(1 << n_vars) // 8 // 1024} KB per clause"
        )
    if n_vars == 0:
        return ("UNSAT", None) if any(not c for c in clauses) else ("SAT", [])

    masks, full = _var_masks(n_vars)
    alive = full
    for clause in clauses:
        if not clause:                      # the empty clause: unsatisfiable
            return "UNSAT", None
        sat = 0
        for lit in clause:
            v = _var_index(lit, n_vars)
            sat |= masks[v] if lit > 0 else (full ^ masks[v])
        alive &= sat
        if not alive:
            return "UNSAT", None

    m = (alive & -alive).bit_length() - 1    # lowest surviving assignment
    return "SAT", [(i + 1) if (m >> i) & 1 else -(i + 1) for i in range(n_vars)]


def satisfies(clauses, model):
    """Independent re-check of a model, not trusting whoever produced it."""
    true_lits = set(model)
    return all(any(lit in true_lits for lit in c) for c in clauses)


def count_models(clauses, n_vars, max_vars=MAX_VARS):
    """How many colourings survive.  Useful for saying how tight a class is."""
    if n_vars > max_vars:
        raise ValueError(f"{n_vars} variables is beyond brute force")
    masks, full = _var_masks(n_vars)
    alive = full
    for clause in clauses:
        if not clause:
            return 0
        sat = 0
        for lit in clause:
            v = _var_index(lit, n_vars)
            sat |= masks[v] if lit > 0 else (full ^ masks[v])
        alive &= sat
    return bin(alive).count("1")
