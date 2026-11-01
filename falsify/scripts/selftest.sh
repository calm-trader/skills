#!/usr/bin/env bash
# Self-test for check_report.py and the fixture harness. Needs python3 only.
# Every check here must also be seen to FAIL once (falsify §4): the bad reports below do that.
set -u
cd "$(dirname "$0")"
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }

names() { python3 check_report.py --json "$1" | python3 -c 'import json,sys; print(" ".join(sorted(set(f["name"] for f in json.load(sys.stdin)["findings"]))))'; }

python3 check_report.py fixtures/report-good.md >/dev/null && ok "check_report accepts a consistent report (with an override)" || bad "check_report good"

got=$(names fixtures/report-mislabeled.md)
want="mislabel no-verdict-line straddles two-labels unscored"
[ "$got" = "$want" ] && ok "check_report flags the R64-shaped report: $got" || bad "check_report mislabeled: got '$got' want '$want'"
n=$(python3 check_report.py --json fixtures/report-mislabeled.md | python3 -c 'import json,sys; print(sum(f["name"]=="mislabel" for f in json.load(sys.stdin)["findings"]))')
[ "$n" = 2 ] && ok "two CONSIDER findings scoring 3.6 and 3.8 are called BLOCK" || bad "mislabel count $n"

got=$(names fixtures/report-echo.md)
want="count-mismatch duplicate-verdict gap-arithmetic partial-in-final"
[ "$got" = "$want" ] && ok "check_report flags an echoed template, a partial marker and bad arithmetic" || bad "check_report echo: got '$got' want '$want'"

# §6 makes some findings BLOCK whatever the number; a report that says which one is consistent.
python3 check_report.py fixtures/report-categorical.md >/dev/null && ok "check_report accepts a BLOCK below 3.5 that names a §6 category" || bad "check_report categorical"
got=$(names fixtures/report-block-low.md)
want="count-mismatch mislabel"
[ "$got" = "$want" ] && ok "check_report still flags a BLOCK below 3.5 with no category: $got" || bad "check_report block-low: got '$got' want '$want'"

# Shapes readers write: score on the line under its heading, a label word in passing, "3x3", a table.
python3 check_report.py fixtures/report-shapes.md >/dev/null && ok "check_report reads a heading's score from the next line and ignores a label in passing and 3x3" || bad "check_report shapes: $(names fixtures/report-shapes.md)"

# Grouping must not let an aside's score stand in for the finding's own: two scores, no decision.
got=$(names fixtures/report-two-scores.md)
[ "$got" = "two-scores" ] && ok "check_report flags a finding with two different scores instead of picking one" || bad "check_report two-scores: got '$got'"

# The fixture target's own suite is green; that is the point of the fixture.
( cd ../fixtures/target && python3 -m unittest discover -q -s tests -t . 2>&1 | tail -1 | grep -q '^OK' ) \
  && ok "fixture target: its test suite passes with every planted defect in place" || bad "fixture target suite"

# The scorer refuses an unfinished report and scores a finished one against the key.
python3 ../fixtures/score.py fixtures/report-mislabeled.md >/dev/null 2>&1; [ $? -eq 1 ] && ok "score.py refuses a report check_report rejects" || bad "score.py gate"
out=$(python3 ../fixtures/score.py --json fixtures/report-good.md) \
  && python3 - "$out" <<'PY' && ok "score.py credits the sample report for D1, D2, D3 (named UNMEASURED) and the control, and no decoy" || bad "score.py scoring"
import json, sys
d = json.loads(sys.argv[1])
hits = sorted(k for k, v in d["defects"].items() if v["found"])
assert hits == ["C1", "D1", "D2", "D3"], hits
assert d["false_positives"] == [], d["false_positives"]
PY

# --no-gate scores a report with no FALSIFY: line (the no-skill arm) and reports compliance apart.
# The report names D4 as a module (`adapter.SIDE`) and has two near-misses the old key credited:
# a side-mapping complaint that is not about the missing convention, and a released=False test gap.
out=$(python3 ../fixtures/score.py --no-gate --json fixtures/report-noskill.md) \
  && python3 - "$out" <<'PY' && ok "score.py --no-gate scores a report without a verdict line: D4 by module name, no near-miss credit" || bad "score.py --no-gate"
import json, sys
d = json.loads(sys.argv[1])
hits = sorted(k for k, v in d["defects"].items() if v["found"])
assert hits == ["D4"], hits
assert d["compliance"] == ["no-verdict-line"], d["compliance"]
PY

exit $fail
