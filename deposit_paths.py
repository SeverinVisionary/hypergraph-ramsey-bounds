"""Locate a deposited file without hard-coding a directory layout.

A file such as `README.md` or `reproduce.sh` sits at the top level of the
deposit. The same checks also run before packaging, where those files may live
in a staging subdirectory instead. Rather than naming that directory -- which
bakes one particular layout into every test that reads a document -- the
lookup takes the top level first and then any subdirectory that happens to
hold the file. A file present in NEITHER place is an error, never a skip: a
check that silently reads nothing passes for the wrong reason.
"""

import os

ROOT = os.path.dirname(os.path.abspath(__file__))


def candidates(name, root=None):
    """Every existing path for `name`: top level first, then subdirectories."""
    root = root or ROOT
    top = os.path.join(root, name)
    if os.path.exists(top):
        yield top
    try:
        entries = sorted(os.listdir(root))
    except OSError:
        return
    for d in entries:
        if d.startswith(".") or not os.path.isdir(os.path.join(root, d)):
            continue
        p = os.path.join(root, d, name)
        if os.path.exists(p):
            yield p


def resolve(name, root=None):
    """The first existing path for `name`, or None."""
    for p in candidates(name, root):
        return p
    return None


# A directory holds the DEPOSIT's documents if it holds the citation file --
# that is what distinguishes the deposit root from any other directory that
# happens to contain a README.
MARKER = "CITATION.cff"


def resolve_scaffolded(name, root=None):
    """Like `resolve`, but restricted to a directory that is a deposit root.

    Some documents -- the README, the citation file, the metadata record --
    are authored for the deposit alongside each other and copied to the top
    level when the package is built. Before packaging, a file of the same name
    may exist at the top level for an unrelated purpose, and other
    subdirectories have READMEs of their own, so "the deposit's copy" is the
    one sitting next to the citation file rather than the first one found.
    """
    for p in candidates(name, root):
        if os.path.exists(os.path.join(os.path.dirname(p), MARKER)):
            return p
    return None
