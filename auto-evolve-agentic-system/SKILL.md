---
name: auto-evolve-agentic-system
description: Build any agentic system (an operations agent that takes actions, a coding agent, a data-pipeline or extraction agent, a research or sales agent) and keep improving it, honestly. A domain-expert panel (or model personas) seeds cases; a cheap writer swarm expands the data every cycle; error analysis builds a failure taxonomy and names the next fix; classification climbs a calibrated ladder with rules as the safety floor. Sealed holdouts with a look budget, a separate safety gate, cluster-aware selection on pooled banks, fair comparison between versions or systems, an independent readiness review, staged rollout, and a production loop (traces, incidents, drift) that feeds the next cycle. Use when starting such a system, running an improvement cycle, comparing two versions or runs, reporting results, or operating one after launch.
---

# Auto-evolve an agentic system

## Principles
1. Measure every change on data the builder never read. A read bank is training data.
2. Safety is a hard gate, never points in a total. No irreversible effect runs in an
   episode with an unresolved harm signal.
3. The unit of evidence is the writer set-up and the cluster (a phrasing, repository,
   source or template: your kind's slots, references/runtime-adapters.md), not the
   episode. A score from one writer is that writer's idea of the users.
4. Admit a change on proof, or on mechanism plus "not worse" plus a fresh targeted bank;
   claim a gain only on a fresh bank; prune what an ablation shows adds nothing.
5. Fresh readable data comes before every other strategy, every cycle.
6. Two numbers are comparable only on the same fresh episodes.
7. A benchmark is not readiness, and readiness is a stage, not an end.

## The loop
FRAME → BUILD → SEAL → SAFETY → [IMPROVE → CLAIM → READINESS → PROMOTE → OPERATE], repeated.
From an existing system, earlier run or live traffic: begin at IMPROVE step 0 (carry
forward); never restart from V1 without porting what the earlier run learned.

| Phase | Do | Done when | Details |
|---|---|---|---|
| 0 FRAME | nevers, exactly-onces, always-reach-a-person; invariants; metric on systems of record; expert panel split into seed and sealed sides; owner-signed safety target; budgets; day-one basics: CI, off switch, owners | FRAME.md reviewed | references/frame-and-build.md, data-and-experts.md; safety words (must-escalate, must-refuse, irreversible effect, harm signal): safety.md |
| 1 BUILD | lean path; rules enforced inside tools; deterministic simulator; probes; negative controls; first writer swarm as TRAIN | all gates green | references/frame-and-build.md, gates.md |
| 2 SEAL | banks from at least 3 writer set-ups, each with a manifest and a look budget, sealed before any result | `seal.py statement` clean | references/data-discipline.md |
| 3 SAFETY | red team, panel, falsifier; rule S1; then aim at the largest miss kind | safety gate at target, or the gap reported | references/safety.md |
| 4 IMPROVE | swarm data → error analysis → coverage → visibility → candidates → keep → confirm → prune | stop rule | references/improve.md, statistics.md |
| 5 CLAIM | falsify the last diff; one budgeted holdout look; fair comparison if another system exists | numbers in the ledger | references/compare.md |
| 6 READINESS | independent review; staged plan | READINESS.md | references/readiness.md |
| 7 OPERATE | shadow, canary, traces, incidents, drift, bank rotation | each cycle logged in CYCLES.md | references/continuous.md |

## The four working steps (references/data-and-experts.md, error-analysis-and-classification.md)
- **Experts (FRAME, SAFETY, sample checks each cycle)**: a stakeholder panel; its seed side
  writes seed cases and personas and cold-reads; its sealed side (domain owner, sealed-bank
  briefers) writes no readable data. No human expert: model personas, and reports say so.
- **Writer swarm (BUILD, then IMPROVE step 1)**: one set-up of many fresh small-model
  contexts fills a persona x scenario x style x step grid, later steps included; dedupe;
  the generator's reference labels; a 150-item human-checked sample; readable TRAIN only.
- **Error analysis (IMPROVE step 1)**: sample, open-code, failure taxonomy, count by
  segment x step, rank classes by share x fix rate / cost, track per cycle.
- **Classification ladder (a candidate, IMPROVE steps 4 to 7)**: rules → classifier →
  agreeing learners → calibrated thresholds → LLM, one rung per version, rules the floor;
  learned parts only add escalations; every step read, not only the first.

## Hard rules (never traded for a score)
- Nothing reads a result before the banks it could leak into are sealed.
- Sealed banks run only through `seal.py run`, by the runner, with `$SEAL_MIRROR` and
  `$SEAL_RUN_DIR` owned by the runner outside the builder's tree (the scripts refuse
  otherwise, and cannot stop a builder who owns them: references/data-discipline.md).
  Every run is a look: baselines, other systems, failed runs and earlier roles included.
  The budget lives in the ledger; raising it needs `--approved-by`; nothing overrides a
  refusal on a claim bank. Pass maps of every sealed bank, SELECT included, stay with the
  runner: the builder gets summaries.
- Per-item information from a sealed bank (an id, a signal trace, a per-item score) is
  logged with `seal.py probe` and taints that bank. On a holdout, confirm or final bank it
  is a burn.
- No new safety miss against the base, on any safety bank, for any candidate or version.
  A safety gate bank is replaced when `seal.py wear` says so or after any probe.
- No sealed look on a version whose safety-relevant code changed after the last falsifier
  pass. Falsify the last diff, not the one before it.
- The headline is the systems-of-record count; the agent's own labels are a diagnostic.
- Every number is reported with its bank's writer set-up, episode and cluster counts.
- One strategy per version, one commit per version; the user approves every push.
- Every critical or high finding has a passing test and two near variants.
- Every report pastes `seal.py statement`; a claim it does not support is a defect.

## Deciding what to keep (references/improve.md)
- **Keep, proven**: a reliable marginal gain on pooled SELECT (at least 3 writer set-ups,
  pointing the same way on 3 distinct set-ups read from the ledger, cluster-aware:
  `noise.py --family-maps`, then `--paired-maps` against the head).
- **Keep, on mechanism**: all of: root cause named in one sentence on the candidate card
  before scoring; TRAIN gain with zero episodes lost; no new safety miss; not worse than
  the head on pooled SELECT, in total and per segment (`noise.py --paired-maps ...
  --not-worse MARGIN --of K --segments S`, at least 20 phrasings per slot); and a reliable
  gain in the target cell (`--cell`, `--cycle N` from `seal.py cycle open`: alpha spent
  across cycles; distractors not worse) of a fresh targeted bank written after the
  candidate froze, by a writer its builder never saw, run once (one bank per candidate
  per cycle). Reported as "kept on mechanism", never as a SELECT win.
- **Drop**: anything else, with the reason; "re-test when a bank can see it" if `--visible`
  said SELECT was blind.
- **Prune**: before a cycle's last version, switch each kept part off in turn on retired
  CONFIRM banks; remove any part whose removal changes nothing or helps a segment.
- The cycle's claim is the CONFIRM result for the whole stack, never a SELECT number. The
  head must also be not worse than the base on CONFIRM in every segment, or the step
  responsible is found by bisection and reverted, proven or not.

## Priority
1. Safety before accuracy; the largest safety miss kind before another panel.
2. Fresh swarm data and error analysis before a classifier rung, tuning or judges.
3. Rank failure classes by share x fix rate / cost; the largest cell holds a candidate
   or is written "not addressed, because ..." (references/improve.md step 2); if no bank
   can see it, write one first. Cheap checks first. Re-rank after every version.

## Stop rule
Stop a cycle when: the budget is spent; or two cycles in a row show no reliable CONFIRM
gain *and* no unaddressed cell holds more than the FRAME.md share of TRAIN failures; or
the remaining failures need a product decision; or a needed sealed bank is burned or spent
and no fresh writer exists. A round count alone never stops a cycle while a
kept-on-mechanism candidate, a blind cell or an unread fresh TRAIN bank is waiting.

## Roles, scripts, reports
Roles (builder, expert and stakeholder panels, writer swarm, writers, domain owner, red
teamers, falsifier, reviewer, advisor, operator who owns the off switch), who reads what,
and the words per agent kind: references/runtime-adapters.md. Scripts, standard library
only (copy into `tools/` and commit; run as `python3 tools/<script>.py`): `seal.py`
(ledger, looks, probes, manifests, wear, statement); `noise.py` (cluster-aware intervals,
paired and family tests, `--not-worse`, `--visible`, `--mde`); `compare.py`; `drift.py`;
`verdict_cache.py`. Tests: `python3 -m unittest discover -s scripts -p 'test_*.py'`.
FRAME.md, FINDINGS.md, IMPROVEMENTS.md, STRATEGIES.md, CYCLES.md, READINESS.md:
references/report-templates.md; prompts: references/prompts.md; mistakes:
references/failure-modes.md; two hypothetical walk-throughs: references/worked-example.md.
