#!/usr/bin/env bash
# Does this copy of the falsify skill carry every change that was merged, and do the
# files around it cite its sections correctly?
#
# Reads and reports. Changes nothing, needs nothing installed, runs in under a second.
# Part 1 looks for one phrase per merged change, so a MISSING here means the copy is
# behind the repository and is still being read without that rule. Part 2 finds every
# "falsify §N" in the tree around it and checks that N is a section that exists and,
# where the citing line says what it is citing for, that N is the section that says it.
#
#   ./check-falsify.sh [path-to-falsify-dir] [tree-to-scan-for-citations]
#
# Exit 0 when nothing is missing or mismatched, 1 otherwise, 2 when there is no skill.

set -uo pipefail
DIR="${1:-falsify}"
TREE="${2:-$(dirname "$DIR")}"
S="$DIR/SKILL.md"
[[ -f "$S" ]] || { echo "no skill at $S — pass the path to your falsify/ dir" >&2; exit 2; }

missing=0; carried=0; mismatched=0
report() { # state label detail
  case "$1" in
    MISSING)  missing=$((missing+1));     printf '  \033[31mMISSING \033[0m %s\n' "$2" ;;
    MISMATCH) mismatched=$((mismatched+1)); printf '  \033[31mMISMATCH\033[0m %s\n' "$2" ;;
    *)        carried=$((carried+1));     printf '  \033[32mcarried \033[0m %s\n' "$2" ;;
  esac
  [[ -n "${3:-}" ]] && printf '            %s\n' "$3"
}

echo "checking $S"
echo

# ---- Part 1: one fingerprint per merged change ------------------------------------
# phrase | section | when it landed and what it guards
fp() { # phrase label detail
  if grep -qF -- "$1" "$S"; then report CARRIED "$2"; else report MISSING "$2" "$3"; fi
}
fp 'Rows 2–6 are where the durable defects live' \
   'claim taxonomy (§1)' 'the original skill; without it this is an ordinary review'
fp 'different search modality' \
   'all-clears re-attacked with a second modality (§3a)' 'the original skill'
fp 'ran out of budget' \
   '"Not checked" names which kind of gap (§7)' \
   '2026-09-21, PR #9; the one change measured to work (2/4 → 6/6 on planted contradictions)'
fp 'Decide where the mutation happens' \
   'sabotage step 0: choose where to mutate (§4)' \
   '2026-09-22, PR #13; restoring in place takes uncommitted work with it'
fp 'confirm with `git diff`' \
   'sabotage step 4: restore is confirmed (§4)' '2026-09-22, PR #13'
fp 'panel was one reader' \
   'one-reader fallback (§0)' '2026-09-24, PR #16; a reader without an Agent tool otherwise improvises past the fan-out'
fp 'Underpowered' \
   '"Underpowered" refutation (§3)' '2026-09-24, PR #16'
fp 'FALSIFY: <n> BLOCK' \
   'parsable last line with UNMEASURED slot (§7)' '2026-09-24, PR #16; a verdict a reader cannot find is a gate that did not happen'
fp 'FALSIFY_PARTIAL' \
   'cumulative messages when run as a sub-agent (§0)' '2026-09-24; only a sub-agent'"'"'s final message reaches the caller'

# ---- Part 2: citations of "falsify §N" around the skill ---------------------------
echo
echo "citations under $TREE"
echo

# Section numbers and letters that exist in this copy.
sections=$(grep -oE '^##+ ([0-9]+)[a-z]?\.' "$S" | sed -E 's/^##+ ([0-9]+[a-z]?)\..*/\1/' | tr '\n' ' ')
# A citing line that says what it cites for, and the section that says it.
# keyword regex | section it belongs to
declare -a KW=(
  'seen to fail|sabotag|mutation|break the guarded|decorative test|4'
  'second modalit|all-clear|3'
  'decorative guard|constant|3'
  'convention|sign, unit|unfalsifiable|3'
  'row appear|ever run|empirical reach|silent success|5'
  'not checked|last line|UNMEASURED|FALSIFY:|7'
  'budget|findings first|cumulative|FALSIFY_PARTIAL|one reader|0'
  'severity|confidence|risk|threshold|6'
  'taxonomy|claim kind|rows 2|1'
  'lens|fan out|fan-out|2'
)
cites=0
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  file="${line%%:*}"; rest="${line#*:}"; lno="${rest%%:*}"; text="${rest#*:}"
  while read -r n; do
    cites=$((cites+1))
    base="${n%%[a-z]}"
    if ! grep -qw -- "$n" <<<"$sections"; then
      report MISMATCH "$file:$lno cites falsify §$n, which this copy does not have" "sections: $sections"
      continue
    fi
    for entry in "${KW[@]}"; do
      want="${entry##*|}"; re="${entry%|*}"
      grep -qiE -- "$re" <<<"$text" || continue
      [[ "$base" != "$want" ]] && report MISMATCH "$file:$lno cites falsify §$n for something §$want says" "$(sed -E 's/^\s+//' <<<"$text" | cut -c1-110)"
      break  # the first keyword that matches decides; the list is ordered most specific first
    done
  done < <(grep -oE 'falsify §[0-9]+[a-z]?' <<<"$text" | sed -E 's/falsify §//')
done < <(grep -rnE 'falsify §[0-9]' "$TREE" --include='*.md' --include='*.sh' --include='*.py' --include='*.js' --include='*.txt' 2>/dev/null \
         | grep -v -- "$S:" | grep -v 'check-falsify.sh:')
[[ "$cites" == 0 ]] && echo "  (no citations found)" || printf "  %s citation(s) checked\n" "$cites"

echo
printf '  %s carried, %s missing, %s citation mismatches\n' "$carried" "$missing" "$mismatched"
if [[ "$missing" == 0 && "$mismatched" == 0 ]]; then echo "  nothing to do."; exit 0; fi
[[ "$missing" -gt 0 ]] && echo "  STALE: copy the current falsify/SKILL.md over this one."
exit 1
