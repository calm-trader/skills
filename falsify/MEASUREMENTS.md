# Measurements

What was measured about this skill's own rules, with the numbers. `ATTRIBUTION.md` lists every
addition with a one-word tag; this file is the record behind the tags. A rule with no entry here
has not been measured, whatever its prose says.

The method in every entry is the blind-reader test: a small target with planted defects and a
committed answer key, readers dispatched with and without the change, findings scored against the
key by someone who did not write the readers' prompts. `fixtures/README.md` describes the fixture
this repository ships for it.

## 2026-09-21 — "Not checked" names which kind of gap it is (§7)

Blind readers audited this skill's own `SKILL.md` and `supervision/agents/supervisor-evals.md`,
with `falsify` as the protocol, and caught the files' internal contradictions about one time in
three. Every miss had the same shape: the reader hit the conflict, disobeyed a line to get past it,
and filed that under its own "Not checked" as a personal scoping choice rather than a defect in the
document. §7 already required the list, so the reader was already writing the answer down; it was
not being asked which kind of gap it was.

A second run with only this change deployed caught the same two contradictions **6/6** across three
fresh readers, against **2/4** in the baseline. Small n; the effect was large enough to read anyway.
Result: kept.

## 2026-09-24 — measurement claim rows 7–8 and §3e

Proposed from the skill's first whole-repository run on a trading-research repo (2026-09-01/02),
where every finding about a *number* (a benchmark of zero, windows already used to decide, cost
billed at half the stated rate) had been improvised by the operator while the code-shaped findings
came from the text.

Tested before merge with six planted measurement defects in a small synthetic target, readers with
and without the rows. **Null**: 3.83 vs 4.00 of 6 (Haiku, 6 per arm, p = 0.71), 4.50 vs 4.75
(Sonnet, 4 per arm). The rows came out, per the rule written into `ATTRIBUTION.md` before the test
ran.

Limits: small sample, small legible target. It rules out a large effect on evidence a reader opens
anyway, not a modest one, and not the buried-history case that motivated the rows (defects findable
only by joining two or more files across a long history). Write-up:
https://github.com/calm-trader/claude-plugins/tree/main/docs/measurements/falsify-measurement-rows.
Result: withdrawn. The three additions made in the same change (one-reader fallback, Underpowered,
the last line) change what a report looks like, not what a reader finds, and were not what the test
measured.

## 2026-11-01 — the one-reader fallback (§0), issue #21

Eighteen blind readers (Haiku, no Agent tool, 6 per arm) audited the fixture in `fixtures/`, each in
its own sandbox from `make-sandbox.sh`, scored with `score.py --no-gate` and `check_report.py`.
Arm 1 had no one-reader bullet, arm 2 the current bullet, arm 3 a priority-ordered bullet (§3c, §4
and §5 first, then lens 1, then §3a).

| arm | planted defects found | control found | decoys flagged | says "one reader" | `FALSIFY:` line passes `check_report.py` |
|---|---|---|---|---|---|
| 1 no bullet | 24/24 | 6/6 | 3 | 0/6 (3/6 mention the skipped panel in other words) | 2/6 |
| 2 current bullet | 24/24 | 6/6 | 3 | 6/6 | 0/6 |
| 3 priority-ordered | 24/24 | 6/6 | 1 | 6/6 | 1/6 |

**Detection: at the ceiling.** Every reader in every arm found all four planted defects, so the
fixture cannot tell the arms apart on what a reader finds. This is the floor the issue named: the
fixture is too easy for this question and needs a harder target, not a conclusion. Arm 3's
ordering showed nothing over arm 2 and was not adopted.

**Disclosure: the bullet does what it says.** With it, 12/12 reports say the panel was one reader;
without it, none use those words and half do not mention the skipped panel at all. That is the
failure the bullet was written for (a reader improvises past "run these in parallel" and the report
does not say so). Result: kept, tagged for disclosure only.

**Last line (§7):** 3/18 pass `check_report.py`, with no pattern by arm. The usual failures are a
count on the line that disagrees with the body, and findings labelled without `severity ×
confidence`. Readers could not run the checker (it was outside their sandbox), so this measures the
line written by hand.

Limits: one model, one small fixture, n = 6. Not run here: arm 4 (the same bullet **with** the
Agent tool; a sub-agent here cannot dispatch its own), so whether fan-out beats one reader is still
open. One arm-2 reader deleted scratch directories under `/tmp` it had not created; later reader
prompts say to keep scratch inside the sandbox.

## 2026-11-01 — a positive control for negatives (§4 in reverse), issue #22 Candidate B

The candidate paragraph, after §4's guardrail line: a kill, a null or "no effect found" is a guard
claim too, so plant a known effect and check the method detects it; if not, the negative is
decorative. Issue #22's rule, written before the run: drop it if null, or if readers already flag
the underpowered kill without it.

Target: a three-study research repo (not committed) with three seeded kills: an underpowered one
(14 trades, t 1.93 against a bar of 2.0), one undetectable by construction (matched controls drawn
from the event days themselves, so a real effect of about +0.2 to +0.3 points cancels), and a legitimate one (a
permutation test with power, p 0.48). Twelve blind readers (Haiku, no Agent tool, 6 per arm), each
in its own copy, scored by hand against the three keys.

| arm | underpowered kill flagged | undetectable kill flagged | legitimate kill wrongly attacked | planted a known effect to test a negative |
|---|---|---|---|---|
| without the paragraph | 6/6 | 6/6 | 0/6 | 2/6 |
| with the paragraph | 6/6 | 6/6 | 0/6 | 6/6 |

**Result: dropped, per the rule.** Every reader without the paragraph flagged the underpowered
kill (n, the interval, or the one trade that decides it), and every one found the event-drawn
controls by reading the code and sabotaging the default. The paragraph changed the method (6/6
planted an effect against 2/6) without changing what was found. Several readers in both arms also
found an unplanted defect in the target (a bootstrap p-value that does not move with effect size).

Limits: one model, one target, n = 6; the undetectable kill was findable by reading, so a target
where only a planted effect exposes the blind spot could still separate the arms.

## Not yet measured

- Fan-out against one reader (§2, §3b): arm 4 of #21, on a fixture hard enough to leave misses.
- Cumulative messages and `FALSIFY_PARTIAL:` (§0): planned as a dispatch with the turn limit forced
  low, counting findings the caller actually receives.
- The `FALSIFY:` last line (§7): compliance across the runs above; `scripts/check_report.py` is the
  scorer.
