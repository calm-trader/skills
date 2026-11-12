# Statistics: what a number can and cannot say

## What a cluster is

Episodes rendered from the same phrasing pass or fail together. 1000 episodes built from
125 phrasings carry about as much information as 125 fresh ones, not 1000.

| System | Cluster (per slot) | Top-level cluster |
|---|---|---|
| operations agent (conversational) | the phrasing used in each slot (opening, each reply) | the writer set-up |
| coding agent | slots: repository; task family | the writer set-up or issue source |
| data pipeline | slots: upstream source; fault kind | the source system |
| research or sales agent | slots: source set; request template | the writer set-up |

Wherever this skill or `noise.py` says "phrasings", read distinct clusters in your kind's
slots (references/runtime-adapters.md, Words). The evaluator writes a clusters file per
bank, one entry per slot: `{episode: {"opening": "o_12", "reply": "y_03"}}` for an
operations agent, `{episode: {"repo": "r_4", "family": "f_2"}}` for a coding agent. Every episode names every slot, or `noise.py` stops. Without it every test
counts episodes and is too optimistic by an unknown amount.

The top level is described, not tested. With a folder of maps (one file per bank),
`--ledger` reads each bank's writer set-up from the verified ledger (`--writers W` works
too, printed as not verified). The pooled cluster test alone decides "reliable"; the
writer line only describes agreement ("same direction on 3 of 3 writer set-ups") and a
pooled gain is kept only when 3 distinct set-ups point its way. Three set-ups that agree
are not a test of new writers (a sign-flip over 3 writers can never reach p < 0.05), so
never call a gain "general" or "reliable across writers".
The bank manifest records phrasings per key so a reader can judge this too.

## Which test when

| Question | Command |
|---|---|
| How sure is one count? | `noise.py N K` (add `--clusters M` for a rough widening) |
| Two versions, no pass maps | `noise.py N A B` (unpaired) |
| Two versions with pass maps (the normal case) | `noise.py --paired-maps BASE CAND --clusters C --ledger L [--segments S]` |
| Best of K candidates | `noise.py --family-maps BASE C1 C2 ... --clusters C --ledger L` (Holm over K) |
| Is a candidate not worse (mechanism route)? | `--paired-maps ... --not-worse MARGIN --of K [--segments S]` (every segment must pass too) |
| Gain in one cell, not worse elsewhere | `--paired-maps ... --cells CELLS --cell NAME --not-worse MARGIN --ledger L --cycle N` |
| Can this bank see a fix in a cell? | `noise.py --visible BASE --cells CELLS --clusters C` |
| How big a gain can this bank show? | `noise.py --mde N --clusters M --base-rate P --of K` |
| How big must a safety bank be? | `noise.py --need RATE` |
| Two systems on fresh banks | `compare.py` (references/compare.md) |
| Has a live rate or mix moved? | `drift.py rate`, `drift.py mix` |

`--paired-maps` takes a file or a folder of per-bank maps. With a folder, results are also
printed per bank, with "gain on n of m banks". The test is a sign-flip permutation test
over clusters, the interval a cluster bootstrap. With several phrasing slots each slot is
tested and the widest result is reported, with the slot named: approximate, on the
cautious side.

## Reading results

- "Reliable on this writer" is not "reliable on new writers". With fewer than 3 writer
  set-ups, say so and quote the cluster-aware interval.
- A pure gain needs at least 6 flipped *phrasings* (not episodes) to pass at 0.05, and 8
  under Holm with K = 4. One phrasing flipping 80 episodes is one piece of evidence.
- A total can hide a segment loss. Read the segment table before the total.
- The winner's gain on the bank that picked it is biased upward. Quote CONFIRM.
- "Not worse" (`--not-worse`) is a one-sided test over phrasing clusters with one
  pseudo-loss as large as the biggest cluster that moved, and it needs at least 20
  phrasings per slot. In a simulation where whole phrasings flip and the true net equals
  minus the margin, it passed 0% of trials at 12 phrasings (refused: too few) and 1.8% at
  30 (nominal 2.5%; the old interval rule passed 32% and 6%). The price is power: with
  whole phrasings flipping both ways it rarely passes. Write more phrasings rather than
  widen the margin; a margin above 2% needs `--wide-margin` and a FRAME.md reason.
- A threshold picked on counts is not a calibrated confidence. If routing depends on a
  score, check calibration on a counts-only bank.

## Repeated looks and wear

Every decision a bank feeds biases it toward the versions it chose. That is why:
- CONFIRM is fresh every cycle and feeds exactly one decision;
- SELECT is a pool that grows with retired CONFIRM banks, and a SELECT bank is retired to
  train after 20 runs (every run counts, whatever its declared purpose);
- a safety gate bank is replaced after 12 runs or any probe;
- a holdout has a look budget, and every look counts, a baseline or another system's
  included. `seal.py wear` checks all of this.

## Stochastic agents

Run 3 or more seeds on dev; report pass^k for write episodes (the share passing on every
seed) and the range across seeds. One seed on a sealed bank is one draw: say so.

## Honest limits

With one writer no test says anything about new writers; the cluster test only stops
phrasings from being counted as independent episodes. The per-slot cluster test is an
approximation of a crossed design: in a simulated crossed opening x reply design with no
true effect it rejected 7.7% at 0.05. Treat p values near 0.05 as inside the noise. Defaults (3 set-ups, 8 failing phrasings, 1% margin)
were chosen, not measured: they are FRAME.md settings.

## Multiplicity across cycles

A mechanism keep is a test the builder may run every cycle. The runner opens each cycle
once, before any candidate is scored: `seal.py cycle open --of K --reason T` gives it the
next number N and records K, the mechanism tests it may run. `noise.py ... --cell NAME
--ledger L --cycle N` then tests at 0.05 / K / 2^N, records each use in the ledger, and
refuses a K+1th test or an older cycle. So the false keeps over all cycles add up to at
most 0.05. Copy N and K into CYCLES.md. Per-segment and per-bank verdicts use the same
corrected threshold as the headline.
