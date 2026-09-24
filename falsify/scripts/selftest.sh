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

exit $fail
