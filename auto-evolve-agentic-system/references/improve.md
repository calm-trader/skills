# Improve (phase 4): one cycle

A cycle builds every applicable strategy from one frozen base, keeps what is proven or
what works by a named mechanism, confirms the whole stack on a fresh bank, then prunes
dead weight. Candidates are not versions: only a stacked step is a version (one strategy,
one commit, full gates). Holdouts never choose.

## Banks (seal them with these roles)

| Bank | seal.py role | Used for | Builder sees |
|---|---|---|---|
| TRAIN | train | error analysis, spikes, ranking, coverage map | everything |
| SELECT pool (at least 3 banks, 3 writer set-ups) | select | picking candidates; re-checking each stacked step | counts and the runner's paired summaries |
| targeted bank (one per mechanism candidate per cycle) | select | the mechanism route, run once per system | counts only; the runner prints the paired result |
| CONFIRM (2 fresh writers per cycle) | confirm (2 looks: base, head) | one paired test per cycle: head against base | counts only; the runner prints the paired result |
| SAFETY gate | safety | every candidate and every version | misses by kind; new and fixed misses against the base, counted by the evaluator without ids |
| HOLDOUT | holdout | one score per budgeted look | the score only |
| FINAL, final SAFETY | final, safety | once, at the end | the score only |

**Who computes on sealed maps.** Pass maps of SELECT, CONFIRM, targeted, holdout and
comparison banks never enter the builder's tree. The runner (`SEAL_RUNNER`) keeps them in its own
store, runs `noise.py` or `compare.py` there, and hands the builder the printed result only.
A builder who opens those maps has made a probe (`seal.py probe`).

After a cycle, CONFIRM has fed one decision: `seal.py retire NAME --to select --reason
"confirmed cycle N"`. It joins the SELECT pool, and fresh writers seal the next CONFIRM.

Every `seal.py run` from a candidate's worktree sets `SEAL_LEDGER=<main checkout>/seal-ledger.json`
and `--root <worktree>`; `seal.py run` refuses to log into a worktree's copy.

## Step 0. Carry forward (entry point B)

Start from the best known version, not from V1, unless the purpose is to test the method.
If you restart, port the earlier run's error-analysis rules as a "legacy knowledge"
candidate in cycle 1, and write in FRAME.md what was left behind. Earlier banks become
TRAIN, named as "earlier-run writers". An earlier run's final version is a comparison
system: run it with `seal.py run --system NAME --purpose compare` (it counts as a look).

## Step 1. Data first, every cycle

Not a candidate; a precondition.
- At least 2 fresh TRAIN swarms per cycle (2 writer set-ups not used before: new
  personas, a new brief or model), seeded by the seed-side experts' cases, with the
  diversity grid, dedupe, oracle check and human-checked sample
  (references/data-and-experts.md). Ask for later steps, not only first steps.
- Score each new swarm with the frozen base first. Error analysis reads those failures
  before any candidate is listed: sample, open-code, cluster into the failure taxonomy,
  count by cell, rank classes (references/error-analysis-and-classification.md).
- Then refit every learned part on all TRAIN banks.
- **Saturation trigger**: TRAIN pass rate at least 90% and more than 5 points above
  pooled SELECT means TRAIN has nothing left to teach. Write new TRAIN before anything else.
- **Leave-one-set-up-out**: fit on all TRAIN set-ups (swarms, earlier writers) but one,
  score that one; repeat. The gap between in-set-up and out-of-set-up scores is the
  familiarity estimate. Report it.
- Live system: the week's adjudicated TRAIN share of traces counts as fresh data
  (references/continuous.md).

## Step 2. Coverage map

A generated table, `docs/coverage.json`, from the error analysis's counts on TRAIN
failures and, for SELECT, per-cell counts the runner computes from its pass maps. Rows:
segment x step of the episode (the FRAME.md step list for your agent kind, for example
opening, reply or later turn, tool step, final answer; a coding agent: plan, edit, test
run, PR text). Columns: TRAIN failures and their failure classes; SELECT base failures and
failing clusters; which component handles that step; which candidates target it.

Rules: one selection rule, used here, in step 5 and in the error analysis: rank failure
classes by share of TRAIN failures x expected fix rate / cost (a class maps to one or more
cells). The largest cell must either hold the first candidate or be written into the cycle
plan as "not addressed, because ...". So must any cell with many TRAIN failures and no
candidate. A learned part that
handles only one column (say, openings) is stated as such in the report. A `make check`
gate fails when `docs/coverage.json` or `docs/failure-taxonomy.md` is older than the
newest TRAIN bank.

## Step 3. Visibility check

For each candidate's target cell, the runner runs
`noise.py --visible select/ --cells cells/ --clusters clusters/` and hands over the counts. If pooled SELECT has
fewer than 8 failing phrasings in the cell for the base, SELECT cannot see the fix. Then
either add a fresh SELECT writer briefed on that cell (the brief names the cell, never the
fix), or register the candidate for the mechanism route. Decide before SELECT is scored
and write it on the candidate card.

## Step 4. Candidate card (pre-registered)

One per candidate, committed before SELECT is scored: strategy (menu row); root cause in
one sentence; target cell; expected direction per segment; route (proven or mechanism);
cost; the targeted bank's brief if the route is mechanism.

## Step 5. Rank, spike, build

1. **Rank** every menu strategy whose "use when" matches a current class or cell:
   `coverage x fix_rate / cost`, the step 2 rule. Coverage is the share of TRAIN failures
   in its classes.
   Ties follow the menu's default order (data first). List the rest as "not applicable",
   with the reason.
2. **Spike** the top 2K (default K = 4; all when there are 6 or fewer): a capped build in
   its own worktree, measured on dev and TRAIN only. Spike gains are optimistic: they
   rank, they never keep.
3. **Build** the top K in full, each in its own worktree from the same base. Cheap gate on
   each (lint, tests, dev bar, red-team corpus, safety gate counts). Any new safety miss
   drops the candidate; one repair attempt is allowed, then the gate runs again.

## Step 6. Select on pooled SELECT

`noise.py --family-maps select-base/ cand1/ cand2/ ... --clusters clusters/` runs the
cluster-aware paired test per candidate, Holm-corrected over K, and prints "gain on n of m
banks". Add `--segments` for the per-segment view. The winner's SELECT gain is biased
upward because it was picked there.

## Step 7. Stack and keep

Stack candidates in order of pooled net gain, each on the current head as its own
version, with full gates, TRAIN and a paired test against the head on pooled SELECT
(`noise.py --paired-maps head/ step/ --clusters clusters/ --ledger seal-ledger.json --segments segments/`). Keep the
step only if gates are green, there is no new safety miss, and one route holds:

- **Proven**: the marginal gain against the head is reliable on pooled SELECT, overall or
  in its pre-registered target segment (one extra comparison: `--of 2`).
- **Mechanism**, every one of:
  1. root cause named on the card before SELECT was scored;
  2. TRAIN gain with zero episodes lost against the head (necessary, but weak: the builder
     read TRAIN, so this mostly shows the fix does what it was written to do);
  3. not worse than the head on pooled SELECT:
     `noise.py --paired-maps head/ step/ --clusters clusters/ --ledger seal-ledger.json --not-worse MARGIN`
     (margin from FRAME.md as `N%` or whole episodes, default 1%; it needs at least 20
     phrasings per slot, see references/statistics.md);
  4. a reliable gain on a **targeted bank**: 200 or more episodes in the target cell,
     written by a fresh writer after the candidate froze, briefed on the cell (never on
     the fix), never seen by the candidate's builder, sealed as role `select` with
     `--looks 2` (head and step), run once each. The runner runs `noise.py --paired-maps
     head.json step.json --clusters C --cells CELLS --cell NAME --not-worse MARGIN --ledger L
     --cycle N`: the gain is tested on the target cell alone, `--not-worse` on the
     distractors, both at 0.05 / K / 2^N. N and K come from `seal.py cycle open --of K`,
     run once per cycle before any candidate is scored; each test uses one of the K, so
     false keeps summed over all cycles stay under 0.05.
  One targeted bank per candidate per cycle. A failed candidate may come back only as a
  new candidate in a later cycle, counted in that cycle's K under Holm.
  The report calls it "kept on mechanism", never a SELECT win, and the targeted bank then
  joins the SELECT pool.
- Otherwise **dropped**, with the reason, plus "re-test when a bank can see it" if step 3
  said SELECT was blind.

Why: a keep rule that asks each strategy to beat the noise, on one writer, on what the
previous one left over, tests the bank, not the fix (references/worked-example.md, example
A, shows how two working fixes get dropped that way).

## Step 8. Confirm

One paired, cluster-aware test on the 2 fresh CONFIRM banks, cycle head against cycle base
(`seal.py run conf_x --purpose confirm ...`, then the runner runs `noise.py --paired-maps`
and `--not-worse` with `--segments`). This is the only number quoted for the cycle.
- Losses add up across kept steps, each "not worse" on its own. So the head must also pass
  `--not-worse` against the base on CONFIRM, in total and in every segment (`--segments`
  tests each segment, margin pro rata). If it fails, bisect the kept steps on retired
  CONFIRM banks (role select) to find the one responsible, revert it, proven or
  mechanism-kept, and say so.
- Inside the noise but not worse: the cycle reads "no reliable gain on a fresh bank";
  kept-on-mechanism parts stay, and step 9 decides whether they earn it.

## Step 9. Prune by ablation

Before a cycle's last version, switch each kept part off in turn and score on retired
CONFIRM banks (role select). A part whose removal changes nothing, in total and in its
target segment (`--not-worse` with the part off passes and its target cell does not move),
is removed as its own version. So is a part whose removal improves any segment: it hurts
somewhere. This is the guard that makes the mechanism route safe.

## Step 10. Claim

Falsifier on the last diff (references/safety.md), then one budgeted holdout look per bank
for the cycle head (a reused holdout's score is biased once shown and used to decide when
to stop; only FINAL and the final safety bank back the unbiased claim), then the fair comparison if another system exists
(references/compare.md). Run the panel again before the final version, and after any
cycle that added a new early path. Log the cycle in CYCLES.md.

## Budget (FRAME.md)

A time and spend cap per track (accuracy, safety, operations), a look budget per sealed
bank, K and the spike cap. No fixed round count: the stop rule in SKILL.md decides.
Holdout looks per bank: baseline (once), each cycle head you will claim, the final version,
and each comparison system. Write that number into `seal.py seal --looks`.

## With a Workflow tool

Fan out one agent per candidate: its own git worktree, scratch folder, copy of the verdict
cache, ports, and the sealed paths repeated in its prompt. Candidates never see each
other's results. Every agent returns:

`{id, worktree, commit, cost, card: {root_cause, cell, route}, gates: {cheap, all}, safety: {misses, new_misses, false_alarms}, train: {passed, n, gain, lost}, select: {map_dir}, targeted: {map, passed, n}, notes}`

```js
// one cycle; base = frozen tag. Holdouts are never touched here.
const data = await agent(FRESH_TRAIN(base), {schema: DATA})        // step 1: writers, refit, error analysis
const plan = await agent(COVERAGE_AND_CARDS(base, data), {schema: PLAN})  // steps 2-4, cards committed
const spikes = await parallel(plan.ranked.slice(0, 2 * K).map(s => () =>
  agent(SPIKE(s, base, spikeCap), {label: `spike-${s.id}`, isolation: 'worktree', schema: RESULT})))
const shortlist = spikes.filter(x => x && x.gates.cheap === 'green')
  .sort((a, b) => b.train.gain / b.cost - a.train.gain / a.cost).slice(0, K)
const cands = await pipeline(shortlist,
  s => agent(BUILD(s, base), {label: `build-${s.id}`, isolation: 'worktree', schema: RESULT}),
  r => agent(GATE(r), {label: `gate-${r.id}`, schema: RESULT}))
const ok = cands.filter(c => c && c.gates.cheap === 'green' && c.safety.new_misses === 0)
const sel = await agent(SELECT_POOLED(ok), {schema: VERDICTS})   // noise.py --family-maps --clusters
let head = base; const log = []
for (const c of ok.sort((a, b) => sel.net[b.id] - sel.net[a.id])) {   // one strategy per version
  const v = await agent(STACK(c, head), {label: `stack-${c.id}`, schema: STACKED})
  let route = null
  if (v.gates.all === 'green' && v.safety.new_misses === 0) {
    if (v.marginal === 'reliable') route = 'proven'
    else if (c.card.route === 'mechanism' && v.train.lost === 0 && v.not_worse === 'pass') {
      const t = await agent(TARGETED(c, head, v), {schema: PAIRED})  // fresh writer, sealed, run once
      if (t.verdict === 'reliable gain') route = 'mechanism'
    }
  }
  log.push({...c, stacked: v, route})
  if (route) head = v.tag; else await agent(REVERT(v, head), {label: `revert-${c.id}`})
}
const confirm = await agent(CONFIRM(base, head), {schema: PAIRED})
const pruned = await agent(ABLATE(head, log.filter(x => x.route)), {schema: ABLATION})
return {data, plan, spikes, cands, sel, log, confirm, pruned}   // falsifier, holdout: outside
```

Keep the script in `prompts/build-team/`. Without a Workflow tool: `git worktree add
../cand-<cycle>-<id> <base>` per candidate, built by subagents or by the builder in turn;
each writes `cycles/<n>/<id>.json` in the schema above.

## Report: TOURNAMENT.md (per cycle), linked from STRATEGIES.md and CYCLES.md

- Data added this cycle (swarms, traces), each swarm's manifest line (set-up, episodes
  and distinct clusters after dedupe, oracle results, sample size, errors and interval),
  and the leave-one-set-up-out gap.
- The failure taxonomy table: class, count before, count after, on which bank, fixed by
  which version; new classes; classes that came back.
- The coverage map's top cells and what targeted each.
- One table per cycle, losers included: strategy; card (root cause, cell, route); spike
  TRAIN delta; built (y/n); gates; safety deltas; TRAIN gained and lost; pooled SELECT B
  and C; cluster-aware p; Holm verdict; gain on n of m banks; visibility; targeted bank
  result; outcome (proven, mechanism, dropped, pruned) with the reason; cost.
- Stack table: version, strategy, route, solo and marginal gain (each marked inside or
  outside the noise), CONFIRM result, ablation result.
- `seal.py statement` pasted.

## Sequential mode (fallback)

When fewer than 3 strategies apply, candidates cannot be built in parallel, or the profile
is Lite: one strategy per version in priority order, each kept by the same two routes on
pooled SELECT, CONFIRM once per cycle, ablation before the last version. Say which and why
in FRAME.md.
