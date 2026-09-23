# Attribution

This skill takes ideas from prior work and says which, because a skill about falsifiable claims
should not make an unfalsifiable one about its own originality.

## From `mcarlssen/claude-adversarial-review` (MIT)

https://github.com/mcarlssen/claude-adversarial-review

Three ideas were taken more or less whole, and they are the best ideas in that skill:

1. **A finding survives only if a skeptic cannot refute it.** Candidate findings are attacked before
   they are reported, rather than filtered by the reviewer's own confidence.
2. **Refute the negatives, not only the positives** — re-attack every all-clear using a *different
   search modality* than the one that produced it. This is the single highest-yield rule in either
   skill, and it is theirs.
3. **`risk = severity × confidence`** with reachability adjustments, including the distinction
   between *latent* (cannot run) and *env/data-gated* (runs; manifestation depends on an operational
   fact), and scoring inert infrastructure at would-be-reachable weight.

That skill in turn vendors its over-engineering lens from `DietrichGebert/ponytail-review` (MIT).

## What this skill adds

The additions come from defects that shipped in a real trading codebase, each of which passed review
and a green test suite:

- **The claim taxonomy** — six kinds of claim, only the first of which ordinary review attacks.
- **Sabotage verification** (§4) — a guard is not a guard until it has been *seen* to fail. Break the
  guarded thing, run the test, and if it still passes the test is decorative. Three such tests were
  found in one codebase, each *pinning* the bug it existed to catch.
- **Decorative guards** (§3c) — a check whose failing branch no caller can reach because every caller
  passes a constant. Found on an execution path as `assertCanSubmit({ released: true })`, which read
  as a hard guardrail while being a literal.
- **Unfalsifiable claims** (§3d) — a sign, unit, direction or timezone with no convention stated
  where it is declared. Nothing can be wrong, so nothing can be caught. Found as a hedge-direction
  inversion that had shipped for the life of the file.
- **Empirical reachability** (§5) — "did a row appear", not "could this run". A module with complete
  passing tests and zero production rows is a finding, usually the largest available.
- **Silent success** (§5) — anything reporting success while its side effect did not happen. One such
  pipeline ran dead for ten days behind a page that looked healthy.
- **Budget and output discipline** (§0) — findings first, emitted incrementally, and a run that ends
  with no verdict counts as FAIL rather than clean. Added because an adversarial agent in that
  codebase twice burned its whole turn budget exploring and returned only preamble.
- **"Not checked" names which kind of gap it is** (§7) — budget, or an instruction that could not be
  followed. Added 2026-09-21 after blind readers audited this skill's own `SKILL.md` and
  `supervision/agents/supervisor-evals.md`, with `falsify` as the protocol, and caught its internal
  contradictions about one time in three. Every miss had the same shape: the reader hit the conflict,
  disobeyed a line to get past it, and filed that under its own "Not checked" as a personal scoping
  choice rather than a defect in the document. §7 already required the list, so the reader was
  already writing the answer down; it was not being asked which kind of gap it was. A second run with
  only this change deployed caught the same two contradictions 6/6 across three fresh readers,
  against 2/4 in the baseline.
- **Measurement claims** (§1 row 7, §3e), **source fidelity** (§1 row 8), **kills as findings**
  (§3 "Underpowered"), **cited artefacts** (§5) and the **parsable last line** (§7). Added
  2026-09-23 from the skill's first whole-repository run on a trading-research repo. Where the
  claim was code-shaped the text produced the finding: the largest one (a headline figure carried
  by a leg that could only close at a profit, behind a decorative end-of-day guard) was row 3 plus
  §5, and a self-test that still passed after its engine was sabotaged was §4 verbatim. Every
  finding about a *number* was improvised by the operator instead: a benchmark of zero where the
  honest one was the trivial alternative, "out-of-sample" windows inside the selection window, a
  validation window that had already decided eight rounds, cost billed at half the stated rate,
  family size counted as catalogue size. Days later a second round found a cited leaderboard that
  had never existed, and a cut made on 14 observations had been filed as a falsification. The
  rows are written generically; the trading instance lives in `tradingview-backtesting`.

## Scope difference

`claude-adversarial-review` reviews an uncommitted diff. `falsify` audits claims, which includes
diffs but also whole-repo questions a diff cannot express: is this test able to fail, has this code
path ever executed, does this convention exist.

MIT, like its parents.
