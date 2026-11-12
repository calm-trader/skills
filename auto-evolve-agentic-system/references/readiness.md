# Readiness (phase 6)

A good benchmark score is not readiness. An independent review routinely finds what the
banks never measured: an unsafe effect on fresh text, a limit checked on a declared value,
no rollback switch, nobody named to act on a handoff. This phase exists so the system finds
those before a person does. Readiness is a stage decision, made again before every
promotion (references/continuous.md), not an end.

## Day-one basics (checked at FRAME, confirmed here)

FRAME.md already lists these (references/frame-and-build.md); the review confirms they
exist and work, rather than discovering they do not:
- a CI config that runs `make check` on every change;
- a tested switch that turns learned parts off, and one that sends everything to people;
- named owners: domain owner, each queue's owner, the operator (or "not named");
- an owner-signed safety target and false-alarm ceiling;
- cost and latency budgets.

## Independent review

Review the final version in a fresh context, with a strong model: a review skill if you
have one, otherwise the checks in this file, READINESS.md and references/failure-modes.md. Give it
the claims, the sealed paths it must not open, and a scratch folder.
- Any Blocker puts "Not ready for {stage}: {reason}" in the first line of README.md and
  STRATEGIES.md.
- The reviewer's fresh probes that reproduce a defect become failing tests, each with two
  near variants, **before** any fix. Then fix the class (references/safety.md), then
  "falsify the fixes".
- Its findings join FINDINGS.md like any other source.

## READINESS.md

| Section | What it holds |
|---|---|
| Verdict | the furthest stage it is ready for, and the single most important reason it is not ready for the next |
| What the numbers mean | each claimed number in plain words: which bank, which writer, how many looks, records or strict, episodes and phrasings, interval |
| Replacements | each mock or in-process part (stores, ledger, idempotency store, queues, identity, clock, sender) and what replaces it in production, with its owner |
| Handoff queues | each queue: consumer, owner, response-time target, paging for urgent items, measured time-to-human (or "not measured") |
| Switched off | anything disabled (guardrails, judges, a reader), with the reason |
| Information gap | what a person doing this job sees that the agent does not, from one frontline interview or the panel's frontline role |
| Labels | who adjudicated the gold slice, their agreement, and every expectation a product decision changed, signed by its owner |
| Wrong actions | broken down by effect type and severity (payment, write, send, delete ...), from pass maps, counts only |
| Not measured | real users, real systems, human-agreed labels, live judge, seeds beyond one, load: tick what this version has |
| Staged plan | the table below |

## Staged plan

| Stage | Entry bar (numbers, set by the owner) | Rollback switch (tested) | Owner |
|---|---|---|---|
| Shadow | | | |
| Human-approved | | | |
| Canary | | | |
| Expanded | | | |

Stage definitions and guardrails: references/continuous.md. A bar the builder set is a
placeholder until the owner replaces it; say so in the table.

## Evidence each stage needs

- **Before shadow**: blockers closed with tests; safety bank results against an
  owner-signed target; a holdout with a look budget, built and scored outside the
  builder's repository, with labels from two people and their agreement; `seal.py
  statement` pasted, not paraphrased; the shadow plan (sample size, duration, who
  adjudicates, how simulated and shadow results are compared per segment).
- **Before human-approved**: shadow safety recall at the owner's target with every miss
  adjudicated; sim-to-live gap per segment (`drift.py gap`).
- **Before any autonomous stage**: approved-stage edit and override rates; live judge error
  rates, or the judge removed from the claims; external identity, a durable ledger and a
  reconciliation report against the real systems; queue owners, a paging test and measured
  time-to-human; a rollback drill; a fresh red-team round against the final build.

## Component swaps

Any planned swap (rules reader to an LLM reader, a new judge model, a new retriever) makes
a new system for evaluation: fresh holdout, fresh safety bank run, fresh red-team round,
shadow before canary, and a fair comparison against the current version
(references/compare.md).
