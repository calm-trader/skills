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

## Not yet measured

- The one-reader fallback (§0): for `supervisor-evals` the one-reader path is the normal path, not a
  fallback. Planned: three arms (no bullet, current bullet, a priority-ordered bullet) plus a fourth
  with the Agent tool, n ≥ 6 each, scored on the fixture in `fixtures/`.
- Cumulative messages and `FALSIFY_PARTIAL:` (§0): planned as a dispatch with the turn limit forced
  low, counting findings the caller actually receives.
- The `FALSIFY:` last line (§7): compliance across the runs above; `scripts/check_report.py` is the
  scorer.
