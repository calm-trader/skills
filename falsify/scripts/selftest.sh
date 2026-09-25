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


# check_citations.py finds exactly the 3 keyed defects on the fixture and nothing else.
got=$(python3 check_citations.py --json fixtures/citations | python3 -c '
import json, sys
findings = json.load(sys.stdin)
print(" ".join(sorted(f["kind"] + ":" + f["citing"] for f in findings)))
')
want=$(python3 -c '
import json
key = json.load(open("fixtures/citations-key.json"))
print(" ".join(sorted(b["kind"] + ":" + b["citing"] for b in key["bad"])))
')
[ "$got" = "$want" ] && ok "check_citations finds exactly the 3 keyed defects: $got" || bad "check_citations fixture: got '$got' want '$want'"

# A clean copy (the 3 defects patched) passes.
tmp=$(mktemp -d)
cp -R fixtures/citations "$tmp/citations"
python3 fixtures/fix-citations.py "$tmp/citations"
python3 check_citations.py "$tmp/citations" >/dev/null
clean_rc=$?
rm -rf "$tmp"
[ "$clean_rc" -eq 0 ] && ok "check_citations exits 0 once the 3 defects are patched" || bad "check_citations clean copy: exit $clean_rc"

# A shorter cited number must not falsely match as a substring of a longer one in the cited file.
tmp=$(mktemp -d)
printf 'Result: 0.61 (data.csv)\n' > "$tmp/note.md"
printf 'value,0.615\n' > "$tmp/data.csv"
out=$(python3 check_citations.py --json "$tmp")
rc=$?
rm -rf "$tmp"
echo "$out" | grep -q '"kind": "number-not-found"' && [ "$rc" -eq 1 ] \
  && ok "check_citations: 0.61 is not credited against a file that only holds 0.615" \
  || bad "check_citations number boundary: rc=$rc out=$out"

# check_citations.py is quiet on the falsify fixtures/target repo (no citation false positives
# from its .py source, once .py is out of the scanned set).
out=$(python3 check_citations.py --json ../fixtures/target)
n=$(echo "$out" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')
[ "$n" = "0" ] && ok "check_citations is quiet on falsify/fixtures/target" || bad "check_citations fixtures/target: $n finding(s), want 0"

exit $fail
