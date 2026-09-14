#!/usr/bin/env bash
# Does this copy of the supervision skill carry the six defects we measured?
#
# Reads the agent files and reports. Changes nothing, needs nothing installed,
# runs in under a second. Each check looks for the textual fingerprint of a
# failure we watched happen in real runs -- so a PRESENT here means the agent is
# still being told the thing that produced it.
#
#   ./check-verifier.sh [path-to-supervision-dir]

set -uo pipefail
DIR="${1:-supervision}"
V="$DIR/agents/verifier.md"
A="$DIR/agents/supervisor-architect.md"
[[ -f "$V" ]] || { echo "no verifier at $V — pass the path to your supervision/ dir" >&2; exit 2; }

present=0; fixed=0
report() { # state label detail
  if [[ "$1" == PRESENT ]]; then present=$((present+1)); printf '  \033[31mPRESENT\033[0m  %s\n' "$2"
  else fixed=$((fixed+1));   printf '  \033[32mfixed  \033[0m  %s\n' "$2"; fi
  [[ -n "${3:-}" ]] && printf '            %s\n' "$3"
}

echo "checking $DIR"
echo

# 1 — a placeholder that parses as a real verdict. Only the FINAL message
# propagates, so a turn-limit halt makes the placeholder the final word.
if grep -qiE '^\s*VERDICT:\s*(PASS\s*[|/]\s*FAIL|FAIL\s*[|/]\s*PASS)' "$V"; then
  report PRESENT "placeholder parses as a verdict" \
    "a halt makes it the final word; a gate that never ran reads as one that passed"
else
  report FIXED "placeholder cannot be read as a verdict"
fi

# 2 — the output TEMPLATE showing a menu. Agents copy the shape they are shown.
if grep -qE '^\s*(VERDICT:.*[|/].*|\*\*?VERDICT:\*\*?\s*(PASS|FAIL)\s*[|/])' "$V" \
   && grep -qiE 'output|template|format' "$V"; then
  report PRESENT "output template shows a PASS/FAIL menu" \
    "one verifier echoed the menu and stated FAIL below it; the reader scored it PASS"
else
  report FIXED "output template shows a finished verdict"
fi

# 3 — cleanup ordered ahead of the verdict. Test for the RULE being present, not
# for an anti-pattern being absent: a file that says nothing about ordering is not
# fixed, it is silent, and silence is what produced the failure.
if grep -qiE 'verdict and evidence BEFORE you clean|state your verdict.{0,40}before|cleanup is best effort|abandon cleanup' "$V"; then
  report FIXED "verdict is ordered before cleanup"
else
  d='no rule orders the verdict ahead of cleanup'
  grep -qiE 'kill it before you finish' "$V" && d='this file says "kill it before you finish" — cleanup ahead of the verdict'
  report PRESENT "cleanup is not ordered after the verdict" "$d"
  printf '            %s\n' 'one agent'"'"'s entire final message was "All checks pass. Now clean up processes."'
fi

# 4 — killing by port rather than by PID. Same shape: the rule must be PRESENT.
if grep -qiE 'by PID|kill only what you started' "$V"; then
  report FIXED "kills are scoped to what the agent started, by PID"
else
  report PRESENT "no rule scoping what the agent may kill" \
    "a verifier freed a port that belonged to the dispatching session's review server"
fi

# 5 — a check budget counted in checks rather than in setups.
if grep -qiE '\b(four|4)\b[^.]{0,40}check' "$V" && ! grep -qiE 'count setup|setup, not checks|setup-heavy' "$V"; then
  report PRESENT "check budget counts checks, not setups" \
    "briefs with 4 setup-heavy checks mostly halted; with 2, every one returned"
else
  report FIXED "check budget is priced by setup"
fi

# 6 — the architect's triggers all require someone to concede a failure.
if [[ -f "$A" ]]; then
  if grep -qiE 'start of a build|before the work is partitioned|propose how to split' "$A"; then
    report FIXED "architect has a trigger that needs no admission"
  else
    report PRESENT "every architect trigger requires admitting failure" \
      "0 dispatches across 21 instrumented builds, vs 158 verifier and 92 builder"
  fi
fi

echo
printf '  %s present, %s fixed\n' "$present" "$fixed"
[[ "$present" == 0 ]] && echo "  nothing to do." || echo "  see the PRs linked from the issue."
exit 0
