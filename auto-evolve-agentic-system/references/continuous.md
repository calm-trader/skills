# Continuous improvement after readiness (phases 6 to 7, then back to 4)

The run does not end at READINESS.md. It moves one stage at a time, and what it sees in
each stage feeds the next improvement cycle.

## Stages and promotion

| Stage | What runs | Enter when | Guardrails that stop it automatically |
|---|---|---|---|
| Offline | simulation only | gates green | - |
| Shadow | real inputs, no replies, no writes; decisions logged beside what people did | review has no blocker for shadow; owner-signed safety target; adjudicator named; off switch tested | feed stops on any invariant breach in the logs |
| Human-approved | the agent drafts, a person acts | shadow safety recall at the owner's target, every miss adjudicated; sim-to-live gap per segment reported | edit or reject rate above the bar |
| Canary | autonomous for a small, low-risk share: reads first, then reversible writes; split by user or account, repository, pipeline or team, never by message | approved-stage rates accepted; durable ledger; reconciliation against the real systems; rollback drill done | any safety miss or unauthorised effect; wrong-action rate, handoff rate, p95 latency or cost per episode above the bar |
| Expanded | wider share, higher-risk writes last | canary results per segment; every wrong action reviewed | same, plus drift checks |

- One stage at a time. Each has an owner, an entry bar with numbers the owner set, and a
  switch that has been used once in a drill.
- A canary's sample size and length are fixed before it starts (`noise.py --mde` sizes
  it). No early "win" from looking daily.
- Safety guardrails stop at once and do not wait for significance.
- Rule S1 holds in every stage: no irreversible effect in an episode with an unresolved
  harm signal.

## Traces feed the data (the flywheel)

1. Assign every account (or repository, or source) to holdout or TRAIN by a fixed hash,
   once, before any sampling, review or access; disjoint across all periods.
2. Log every episode with versions (model, prompt, tools, policy, data) and outcome.
   Reconcile weekly: inbound inputs (messages, tasks, batches, requests) and the
   system-of-record changes against the traces.
   Below the trace completeness the owner signed (in FRAME.md), promotion freezes: missing
   traces hide exactly the failures that matter.
3. De-identify before anything else touches it. Then sample weekly: random, plus oversampling of handoffs, human overrides, low-confidence
   reads, unknown or fallback reads, long episodes, complaints, re-contacts and reopened tasks or re-run batches.
   The oversampled sample is drawn from TRAIN accounts only.
4. People adjudicate the sample (two people for the safety slice; report their
   agreement). Labels are versioned.
5. The sealed production holdout is a separate uniform random sample of holdout accounts'
   recent episodes. If stratified, its manifest records the strata and each stratum is
   analysed on its own (the scripts take no weights). Sealed by someone other than the
   builder (`seal.py seal ... --manifest` with source `production`). An incident from a
   holdout account goes to the regression suite only (or that holdout is burned), never to
   TRAIN. A case is never in both. The agent's own later resolution of a case is removed
   from what it can retrieve.
6. Error analysis on the TRAIN share starts the next cycle (references/improve.md step 1).

Before live traffic exists, the same loop runs on fresh synthetic writers; say which.

## Incident to regression

1. Stop the harm: off switch or narrowed scope first.
2. A minimal reproduction as a failing test, plus two near variants.
3. Name the class, not the phrase. If a guarantee was broken, add or fix an invariant and
   its negative control.
4. A fresh writer writes 30 or more examples of the class as readable TRAIN; fix against
   those; falsify the fix.
5. A FINDINGS.md row with severity, test, owner and time to fix.
6. The incident text goes to the regression suite, and to TRAIN (source `incident`) only
   if it came from a TRAIN account. From a holdout account it goes to the regression suite
   only, or the holdout is burned. It never enters a holdout, confirm or final bank.

## Drift and scheduled checks

| When | Check |
|---|---|
| Every change | CI: `make check`, regression suite, safety gate, cost and latency gate |
| Daily, live | invariants on the logs; guardrail rates; queue time-to-human |
| Weekly | `drift.py mix ref.json week.json` (segment, intent, channel, language, step-count buckets); `drift.py rate` for handoff, fallback read, judge abstain, human override, wrong action; sample adjudication; judge against 50 fresh human labels (false accepts, false rejects, abstain rate); new error classes into the coverage map |
| Each cycle | fresh TRAIN writers or traces; fresh CONFIRM; ablation; `drift.py gap sim.json live.json --max-gap G` per segment (G registered in FRAME.md); a CYCLES.md row |
| Quarterly, or when a look budget is spent | fresh sealed holdout and safety bank; red-team round; readiness re-review; rollback drill; `seal.py wear` clean |
| Any component swap (model, prompt family, judge, retriever, tool version) | a new system: regression suite, fresh holdout, safety bank, red-team round, shadow before canary, and `compare.py` against the current version on fresh banks |

A drift alarm (exit 1) does three things: freezes promotion, pulls a fresh sample for
adjudication, and opens a cycle aimed at the segment that moved.

## Rollback rule

Roll back to the last released version, without waiting for significance, when: any
safety guardrail fires (a missed handoff, an unauthorised effect, rule S1 broken); a
reconciliation finds an effect the ledger did not record; or a cost or latency guardrail
is breached for longer than FRAME.md allows. Roll back after the fixed canary sample when
a pre-registered rate is reliably worse (`drift.py rate`). The operator rolls back first and
asks second; the rollback is an incident (below), and the rolled-back version re-enters
at shadow.

## Cumulative check across cycles

Each cycle's claim is head against that cycle's base, so small losses can pile up over many
cycles. Every release, and at least quarterly, the runner scores the current head and the
last release (and V1) on fresh sealed banks with `compare.py`. CYCLES.md keeps a running
total of claimed gains beside this measured gain; if the measured gain is reliably below
the claimed total, stop and find out where it went before the next cycle.

## Bank life cycle

fresh → sealed (holdout, confirm, final, safety) → looks spent (clean) → retired to select
→ runs spent → retired to train. A tainted or burned bank goes straight to train. Never
the other way. A holdout older than the
period in FRAME.md (default two quarters; `seal --expires`) is reported as stale and
replaced: users and products move, and a bank written for last year's mix measures last
year. `seal.py wear` in `make check` fails on any worn, over-budget, burned or expired bank.

## Judges, cost and latency

- A judge used for grading or in the product is calibrated on human labels before it
  counts, and again when its model or prompt changes. Report false accepts and false
  rejects with intervals. A deterministic check is preferred wherever one exists.
- FRAME.md sets cost per episode and p95 latency. They are gates for every candidate and
  guardrails in every live stage. Each cycle reports the cost per additional passed
  episode.

## CYCLES.md

One row per cycle, newest last:

| Cycle | Dates | Data added (swarms, traces; sample error) | Top failure classes and coverage cells | Candidates: proven / mechanism / dropped / pruned | CONFIRM (paired, cluster-aware) | Safety gate (misses by largest kind) | Holdout looks used of budget | Stage | Incidents closed | Next cycle targets |
|---|---|---|---|---|---|---|---|---|---|---|
