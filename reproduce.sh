#!/usr/bin/env bash
# One-command reproduction. Exits non-zero if ANY check fails.
#
#   ./reproduce.sh          the three constructions and their verifications
#   ./reproduce.sh --full   also the refutation certificates (slower)
#   ./reproduce.sh --crosscheck   re-decide the n=63 nulls with two solvers
#                           this package does not otherwise use (~1 hour,
#                           almost all of it CNF construction)
#
# Every step below is self-asserting: it raises rather than printing a wrong
# number, so a zero exit status is the whole result.
set -u
PY=${PY:-python3}
if [ -n "${PY+x}" ] && [ "$PY" != "python3" ]; then
  echo "NOTE: PY is set to '$PY'. The checks below run under an interpreter" >&2
  echo "this script cannot vouch for; the guarantee is only as good as it." >&2
  echo >&2
fi

# Dependencies: python-sat (for the solver-backed checks) and pytest. The
# solver BACKENDS are named explicitly -- python-sat builds without Cadical195
# or Glucose42 exist, and the failure they produce otherwise arrives deep in a
# run as an unfamiliar exception.
# $PY IS CHECKED, NOT ASSUMED -- and this check alone is not sufficient.
# Everything below runs through $PY, so a $PY that ignores its input and exits
# 0 (`PY=true ./reproduce.sh` is the one-word case) would turn this script into
# a list of labels and the word "ok". The preflight cannot settle that by
# itself, because the preflight also runs through $PY: it prints a value the
# shell then compares, which catches an interpreter that runs nothing, but a
# shim written against THIS script can print that value. The canary below
# catches a shim that cannot fail on demand, and it too can be special-cased.
# What cannot be special-cased cheaply is `run`'s EXPECT requirement: every
# step must produce the output its check produces. Those three together, not
# any one of them.
nonce=$RANDOM$RANDOM$$
proof=$($PY - "$nonce" <<'PREFLIGHT' 2>/dev/null
import sys
try:
    import pytest  # noqa: F401
    from pysat.solvers import Cadical195, Glucose42  # noqa: F401
except ImportError as e:
    sys.stderr.write(
        f"missing dependency: {e}\n"
        "run:  python3 -m pip install -r requirements.txt\n"
        "(the checks need the Cadical195 and Glucose42 backends by name;\n"
        " requirements.txt pins the versions every number here was made on)\n")
    sys.exit(2)
if sys.version_info[0] != 3:
    sys.stderr.write("this package needs Python 3\n")
    sys.exit(2)
# Not an echo: the interpreter has to compute it.
print("PREFLIGHT-OK-%d" % (int(sys.argv[1]) * 2 + 1))
PREFLIGHT
) || {
  echo "preflight failed; see the message above" >&2
  exit 2
}
if [ "$proof" != "PREFLIGHT-OK-$(( nonce * 2 + 1 ))" ]; then
  echo "PY=$PY did not run the preflight: expected PREFLIGHT-OK-$(( nonce * 2 + 1 ))," >&2
  echo "got '${proof}'. Every check below would report ok without running." >&2
  exit 2
fi

FULL=0
CROSS=0
case "${1:-}" in
  "")           ;;
  --full)       FULL=1 ;;
  --crosscheck) CROSS=1 ;;
  *)  echo "usage: $0 [--full | --crosscheck]" >&2; exit 2 ;;  # never treat an
esac                                          # unknown argument as ordinary mode
pass=0; fail=0; failed=()

# One securely-created scratch DIRECTORY for the whole run, removed on any
# exit. Everything this script generates goes inside it: a predictable name
# like a fixed path under the system temp directory truncates a file the
# reader may own, and
# follows a symlink planted at that path.
work=$(mktemp -d "${TMPDIR:-/tmp}/repro.XXXXXX") || exit 2
trap 'rm -rf "$work"' EXIT INT TERM
out="$work/step.out"

# Write no bytecode and no pytest cache into the package directory: a
# reproduction should leave the tree it was run against unchanged.
export PYTHONDONTWRITEBYTECODE=1

# PYTEST CONFIGURATION IS AMBIENT, AND THE GATES BELOW RUN THROUGH IT.
# `PYTEST_ADDOPTS='--deselect=<a test>'` makes a step exit 0 with "7 passed,
# 1 deselected" -- an advertised check silently not run, under a label saying
# it was. The environment is cleared rather than trusted, plugin autoloading
# is turned off so a third-party plugin cannot alter collection, and `run`
# refuses any pytest step whose output reports a deselection.
# A conftest.py or pytest.ini ABOVE the package is loaded too, and one line of
# it (`item.add_marker(pytest.mark.xfail)`) turns a failing check into
# "1 passed, 1 xfailed" with exit 0. So the config file is replaced with an
# empty one, conftest collection is cut at the package directory, and `run`
# refuses any step reporting xfailed or xpassed.
unset PYTEST_ADDOPTS PYTEST_PLUGINS PYTEST_CURRENT_TEST
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
: > "$work/pytest.ini"
PYTEST_ARGS="-q -p no:cacheprovider -o addopts= -c $work/pytest.ini --confcutdir=."

# EXIT 0 IS NOT EVIDENCE. Every step must also PRODUCE what its check produces:
# set EXPECT to an extended regex before a step, and a pytest step defaults to
# its own summary line. A step that exits 0 while its own output reports
# failures is a failure.
#
# WHAT THIS CANNOT DO. These checks -- the preflight, the canary, EXPECT, and
# the distinctness check at the end -- catch a MISCONFIGURED interpreter: one
# that is missing, is not Python, is the wrong Python, or is silently doing
# nothing. They do not and cannot defeat a hostile $PY written against this
# script: anything a shell script tests for, a shim that has read the script
# can satisfy. If you did not set PY yourself, that is not your threat model;
# if you did, you are vouching for the interpreter, not this script.
run () {
  label="$1"; shift
  want=${EXPECT:-}
  allow_skip=${ALLOW_SKIP:-}
  EXPECT=
  ALLOW_SKIP=
  if [ -z "$want" ]; then
    case " $* " in
      *" pytest "*|*"-m pytest"*) want='[0-9]+ passed' ;;
    esac
  fi
  printf '%-58s' "$label"
  if "$@" >"$out" 2>&1; then
    if [ -n "$want" ] && ! grep -Eq "$want" "$out"; then
      echo "NO EVIDENCE"
      fail=$((fail+1)); failed+=("$label -- exit 0, but nothing matching /$want/")
      echo "    expected output matching: $want"
      sed 's/^/    /' "$out" | tail -12
      return
    fi
    if grep -Eq '[0-9]+ failed|[0-9]+ error' "$out"; then
      echo "FAILED"
      fail=$((fail+1)); failed+=("$label -- exit 0 with failures in the output")
      sed 's/^/    /' "$out" | tail -12
      return
    fi
    # A deselected test is a check that did not run under a label saying it
    # did. Skips are different: this package has exactly one, and it documents
    # a solver-build fact rather than skipping a check, so a step that expects
    # it says so with ALLOW_SKIP.
    # xfail/xpass: a check that failed, or one marked as expected-to-fail that
    # passed. Either way the step's label no longer describes what happened.
    if grep -Eq '[0-9]+ (xfailed|xpassed)' "$out"; then
      echo "XFAIL"
      fail=$((fail+1)); failed+=("$label -- tests were xfailed/xpassed, so a "\
"check the label covers did not pass on its own terms")
      sed 's/^/    /' "$out" | tail -12
      return
    fi
    if grep -Eq '[0-9]+ deselected' "$out"; then
      echo "DESELECTED"
      fail=$((fail+1)); failed+=("$label -- tests were deselected, so the "\
"label covers checks that did not run")
      sed 's/^/    /' "$out" | tail -12
      return
    fi
    if [ -z "$allow_skip" ] && grep -Eq '[0-9]+ skipped' "$out"; then
      echo "SKIPPED"
      fail=$((fail+1)); failed+=("$label -- tests were skipped and this step "\
"does not expect any")
      sed 's/^/    /' "$out" | tail -12
      return
    fi
    # Distinct checks produce distinct output. One canned line that satisfies
    # every EXPECT at once would not, and that is a cheap way to satisfy a
    # fixed list of patterns without running anything.
    cksum <"$out" >>"$work/outsums"
    echo "ok"; pass=$((pass+1))
  else
    echo "FAILED"; fail=$((fail+1)); failed+=("$label")
    sed 's/^/    /' "$out" | tail -12
  fi
}

# THE HARNESS ITSELF, DRIVEN TO A FAILURE. `run` reports "ok" on exit 0; if
# anything makes exit statuses meaningless -- a stubbed interpreter, a shell
# that cannot see a child's status -- every label below prints "ok" and the
# script's whole output is a lie. This step must FAIL, and the run is aborted
# if it does not.
printf '%-58s' "the harness can see a failure"
if $PY -c 'raise SystemExit(3)' >"$out" 2>&1; then
  echo "DID NOT FAIL"
  echo "  a command that exits 3 was reported as success; nothing below this" >&2
  echo "  line would be meaningful. Aborting." >&2
  exit 2
fi
echo "ok"
echo

echo "== the three constructions rebuild from their tables =="
EXPECT='R\(4,4,4;3\) >= 84' run "R(4,4,4;3) >= 84  (83 points, 27 orbits)"  $PY construction.py
EXPECT='R\(4,6;3\) >= 64' run "R(4,6;3)   >= 64  (63 points, 120 orbits)" $PY construction_n63.py
EXPECT='R\(5,5;4\) >= 36' run "R(5,5;4)   >= 36  (35 points, 107 orbits)" $PY construction_n35.py

echo
echo "== each table reproduces its committed witness, and the theorems hold =="
run "construction tests"      $PY -m pytest $PYTEST_ARGS test_construction.py
run "construction_n63 tests"  $PY -m pytest $PYTEST_ARGS test_construction_n63.py
run "construction_n35 tests"  $PY -m pytest $PYTEST_ARGS test_construction_n35.py

echo
echo "== independent verifier, no shared code with the search =="
run "verify_scratch"          $PY -m pytest $PYTEST_ARGS test_verify_scratch.py
# Hash-bound and two-way: the reversed reading must return 102,627, or a
# checker that says zero to everything would pass the line above.
EXPECT='102,?627' run "R(4,6;3) witness, both readings" $PY verify_witness_n63.py
EXPECT='1,?837,?620' run "R(4,4,4;3) witness, 3 colours"   $PY verify_witness_n83.py
# The four intermediate witnesses, under the same verifier and each bound to
# its own colour vector's SHA-256. CELLS.md quotes their colour-class counts.
for spec in \
  "79 10c1f29c7da12970f2e0428c6ebf56ef65da4b42f1168f51cfb6be5dd69db0fa 1502501" \
  "80 79fdda50c2f00363b32c1a72f988afacf0a3f7f989735d3d297d649a3f023cec 1581580" \
  "81 6980873abe5f16e44e15ba8c8fb6832b958dbf8888daf200f9b88842021eaf56 1663740" \
  "82 07f3501596260ad2fc247df3b7f744157dc4f048ed513b8cb8b2c737e3073b3e 1749060" ; do
  set -- $spec
  EXPECT="monochromatic 4-sets: 0" \
  run "R(4,4,4;3) witness at n=$1" \
      $PY verify_witness_n83.py --witness "witness_444_3_n$1.json" \
          --expect-sha "$2"
done
EXPECT='324,?632' run "R(5,5;4) witness, two checkers"  $PY verify_witness_n35.py
for spec in \
  "26 8763e25ffcda100d" "31 a0f97ce58374be9e" "32 66e793adcacd088c" \
  "33 9a82243a8b1f0f3d" "34 461d41f45f1fae48" ; do
  set -- $spec
  sha=$($PY - "$1" <<'SHA'
import hashlib, json, sys
n = sys.argv[1]
with open(f"witness_n{n}.json") as fh:
    print(hashlib.sha256(json.dumps(json.load(fh)["chi"]).encode()).hexdigest())
SHA
)
  case "$sha" in
    "$2"*) ;;
    *) echo "witness_n$1.json hashes to $sha, expected $2..." >&2; exit 2 ;;
  esac
  EXPECT="two independent checkers" \
  run "R(5,5;4) witness at n=$1" \
      $PY verify_witness_n35.py --witness "witness_n$1.json" --expect-sha "$sha"
done

echo
echo "== obstruction theorems =="
run "Theorems A, A', B"       $PY -m pytest $PYTEST_ARGS test_obstruction_general.py
run "obstruction, timeout/error" $PY -m pytest $PYTEST_ARGS test_obstruction.py

echo
echo "== published values, from outside this repository =="
run "known-answer gates"      $PY -m pytest $PYTEST_ARGS test_known_answer.py

echo
echo "== the checkers can fail =="
run "verifier gates"          $PY -m pytest $PYTEST_ARGS test_verify.py
run "certificate gate controls" $PY -m pytest $PYTEST_ARGS test_certify_gate.py
# The result-handling regressions: problem binding, output/reference aliasing,
# an equal-length invalid proof substitute, and the all-over-cap sweep. The test
# The test inside it fails if any test_*.py in the package is not invoked by
# this script, so a shipped check cannot sit off the reproduction path.
run "result-contract regressions" $PY -m pytest $PYTEST_ARGS test_result_contracts_regressions.py
# The shared contracts: one problem identity, one instance identity, one
# history reducer, one Theorem-B hypothesis predicate. Every consumer imports
# these rather than carrying its own copy, so a rule cannot hold in one place
# and not another.
run "shared contracts"        $PY -m pytest $PYTEST_ARGS test_contracts.py
# The one expected skip in this package: a test that documents
# Cadical195.interrupt() raising under this python-sat build. Its count is
# pinned, so the exemption cannot quietly cover a second skip.
ALLOW_SKIP=1 EXPECT='[0-9]+ passed, 1 skipped' \
run "caps are enforced"       $PY -m pytest $PYTEST_ARGS test_caps_are_enforced.py
run "result-cache controls"   $PY -m pytest $PYTEST_ARGS test_result_cache.py
run "witness acceptance can reject" $PY -m pytest $PYTEST_ARGS test_climb_accepts_only_verified.py
run "cross-check coverage gate" $PY -m pytest $PYTEST_ARGS test_crosscheck_coverage.py
run "claims match the deposited objects" $PY -m pytest $PYTEST_ARGS test_claims_match_the_objects.py
run "the aggregate counts are computed"  $PY -m pytest $PYTEST_ARGS test_sweet_spot_counts.py
run "Theorem B counterexample gate"      $PY -m pytest $PYTEST_ARGS test_theorem_b_counterexamples.py
run "negative-control gate"             $PY -m pytest $PYTEST_ARGS test_negative_control.py
run "exhaustive-enumeration controls" $PY -m pytest $PYTEST_ARGS test_enumerate_n83.py
run "no-work-is-not-a-result gates" $PY -m pytest $PYTEST_ARGS test_no_work_is_not_a_result.py

if [ "$FULL" = "1" ]; then
  echo
  echo "== refutation certificates (RUP/RAT), incl. the discriminating control =="
  run "drat_check"            $PY -m pytest $PYTEST_ARGS test_drat_check.py
  # The control on the class that certifies by PROOF REPLAY, not by unit
  # propagation: weaken a real instance until it is satisfiable and require the
  # checker to stop certifying at exactly that point.
  EXPECT='no satisfiable instance was certified' \
  run "the checker refuses a satisfiable instance" $PY negative_control.py
  # The deposited certificates themselves, rebuilt and re-replayed. Without
  # this the section above checks only that the proof CHECKER works, and
  # --full could pass with every certificate in this package absent or wrong.
  # --compare fails on any class whose recomputed status, checked flag or
  # route differs from the deposited record; --expect-certified fails if the
  # run silently covers fewer classes than the deposit claims.
  EXPECT='5/5 class\(es\) certified UNSAT' \
  run "certify the 5 deposited n=63 nulls" \
      $PY certify_nulls.py --groups groups63.json --n 63 --s 4 --t 6 --k 3 \
          --out "$work/certs_recomputed.json" \
          --compare certs_46_3_n63.json --expect-certified 5
  # The exhaustive count in README.md, recomputed. A witness search stops at
  # the first model, so nothing else in this package can establish it.
  # --expect alone checks the total; the published claim is a distribution,
  # and --expect-gens-sha binds it to the group rather than to a row's name.
  EXPECT='36 invariant good colouring\(s\), search exhausted' \
  run "all 36 invariant colourings at n=83" \
      $PY enumerate_n83.py --groups g83_p83.json --expect 36 \
          --expect-splits "12:30627/30627/30627,24:27224/30627/34030" \
          --expect-gens-sha \
          f64d23e0da257053794f87fe8dc9c0e72718c0817390e6eb0515ad90f9bb0b1a
  # The classes that make Theorem B's second hypothesis necessary. An
  # existential claim needs the object, and the gate also checks each class
  # satisfies the FIRST hypothesis while failing the second.
  EXPECT='all 2 of 2 class\(es\) satisfy \|G\| = C\(p,2\)' \
  run "Theorem B's p = 1 (mod 4) counterexamples" \
      $PY theorem_b_counterexamples.py --expect 2 \
          --out "$work/tb_counterexamples.json"
  echo
  echo "== engines =="
  run "ansatz / multicolour / brute / grouporder" \
      $PY -m pytest $PYTEST_ARGS test_ansatz.py test_multicolour.py test_brute.py test_grouporder.py
fi

if [ "$CROSS" = "1" ]; then
  echo
  echo "== the n=63 nulls, re-decided by solvers this package does not use =="
  EXPECT='all 5 class\(es\) UNSAT under every solver tried' \
  run "Glucose3 and Minisat22 on all five" \
      $PY crosscheck_n63.py --groups groups63.json \
          --out "$work/crosscheck_recomputed.json"
fi

# Every passing step's output, distinct? Real checks report different things.
if [ -f "$work/outsums" ]; then
  nsteps=$(wc -l <"$work/outsums")
  nkinds=$(sort -u "$work/outsums" | wc -l)
  if [ "$nsteps" -ge 6 ] && [ "$nkinds" -le 2 ]; then
    echo
    echo "$nsteps steps passed but produced only $nkinds distinct output(s)." >&2
    echo "Different checks report different things; this does not look like" >&2
    echo "$nsteps checks having run. Treating the run as failed." >&2
    exit 2
  fi
fi

echo
echo "passed $pass, failed $fail"
if [ "$fail" -ne 0 ]; then
  printf 'failed: %s\n' "${failed[@]}"
  exit 1
fi
