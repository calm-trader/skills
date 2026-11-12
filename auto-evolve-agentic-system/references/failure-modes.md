# Common ways this goes wrong

## Leakage
- A sealed failure read; a holdout used to accept a fix; SELECT used as training; a sealed
  bank imported by a training module; a read holdout still called sealed in the docs.
- A per-item probe on a sealed bank (which signals fired on one item) not logged with
  `seal.py probe`, so the bank is still quoted as clean.
- A verdict cache built from sealed messages ships in the agent: the score measures a judge
  that has seen the test.
- Familiarity: every bank from one writer set-up in one week, so the holdouts measure that
  writer, and a new writer set-up costs a large share of the "gain".

## Statistics
- A gain inside the noise reported as a win; the best of K reported without correction.
- 1000 episodes from 100 phrasings treated as 1000 trials; no phrasing count in any
  manifest, so no reader can tell.
- Selection on one writer: a single SELECT bank decides every keep or drop.
- A total that hides a segment loss.
- One seed on a stochastic agent, reported as a rate.

## Safety
- Safety recall left out of the gates because the total did not move; one blended score
  where a safety miss costs one point.
- An irreversible effect in the same episode as a harm signal (a permission change in
  the same message as a takeover attempt; a merge in a task that exposed a secret): rule
  S1 missing or enforced in workflow code instead of the gateway.
- Safety effort spent by ritual (panel after panel) while the largest miss kind in the
  safety bank, and a readable safety TRAIN bank full of misses, go unmined.
- A fix that adds a phrase, marked fixed; a near variant of it comes back.
- Vacuous invariants: they pass with the safety layer removed.
- A learned read bypasses safety through an unknown or fallback path, or removes a handoff
  the rules raised.
- A deterministic screen added for a panel finding that swallows a safety case or fires on
  ordinary inputs.
- Safety wording changed after the last falsifier pass, then a sealed look.
- A safety gate bank used for 20 runs and still called the safety number.
- A limit checked on a declared value, not the executed argument; an eligibility rule only
  in workflow code; a date constant.

## Selection
- Blind SELECT: the bank's writer phrased the target cell in ways the base already
  handles, so a real fix shows +3 and is dropped as noise.
- The keep rule asks each stacked step to beat the noise on what earlier steps left, on
  one bank: a test of the bank, not of the fix.
- Fresh TRAIN banks written, scored, then left "opt-in" and never error-analysed.
- One author writes all the data; no expert seed cases, no swarm, no diversity grid.
- Swarm data with near duplicates, labels taken from the writer, or no human-checked
  sample, used to keep a candidate.
- Error analysis by impression: no open coding, no taxonomy, no counts by cell.
- A classifier rung climbed before error analysis showed the rung below had plateaued;
  an uncalibrated score used for routing.
- TRAIN saturated (above 90%, far above SELECT) and nobody writes new TRAIN.
- Restart without carry-forward: the earlier run's rules are lost and rediscovered, or not.
- A round cap stops the run while working fixes and unread data wait.
- Dead weight: parts kept on mechanism and never ablated.
- Tuning on TRAIN the rules were fixed on; a policy tuned on a model other than the one
  shipped; augmentation deleting protected words.
- Learned parts that read only the opening, while most failures sit in replies or later
  steps; no coverage map shows it.

## Reporting
- Two runs compared on different banks ("91% against 81%") as if the banks were the same.
- An uncounted look: a baseline or another system run on a holdout, outside the budget.
- Prose look budgets that disagree between documents.
- The headline includes the agent's own labels; wrong actions counted but not broken down
  by effect.
- Self-reported outcomes; a scripted counterpart keyed to the agent's own wording.
- Panel findings without transcripts; panel fixes judged by flat holdouts.
- README or STRATEGIES still showing an older version's numbers.
- Writers from the builder's model family and labels from the builder's generator, with no
  human check, and the report does not say so.

## Operations
- CI, off switch and owners first noticed by the readiness review.
- A component swap (new model, prompt family, judge) shipped as "a small change".
- A canary judged early from daily looks; a safety guardrail waiting for significance.
- Incident text put into a holdout; production traces read before the split.
- A drift alarm with no owner and no cycle aimed at the segment that moved.
- Holdouts older than the product they measure.
- Tournament runs logged in a worktree's copy of the ledger, thrown away with it.
- A ledger rewound with git, or a side ledger started for "just one more look"; no mirror
  outside the repository to catch it.
- Two agents on one code tree, told apart only by an environment variable that was not
  passed with `--env`; or one agent re-scored under a new `--system` name.
- Captured output of a sealed run shown "just this once": per-item results leave the bank.
