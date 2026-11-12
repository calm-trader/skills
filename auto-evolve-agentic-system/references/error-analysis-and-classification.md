# Error analysis and better classification (every cycle)

Error analysis decides what to fix next. The classification ladder decides how the system
reads its inputs, one rung at a time. Both use readable data only: dev, TRAIN (swarm and
traces), the red-team corpus, panel transcripts and incidents from TRAIN accounts. Sealed
banks give counts, never items.

## 1. Error analysis, step by step

Run it at the start of every cycle (references/improve.md step 1), on the newest TRAIN
first, and after any incident.

1. **Sample.** Up to 100 failures, stratified by segment and step of the episode; all of
   them if there are fewer. Add 20 passes the system was least sure of.
2. **Open-code.** For each failure, one plain line: what went wrong, at which step, what
   the right outcome was. No category list yet. When two people are available, both code
   the same 20 items and compare.
3. **Cluster into a failure taxonomy.** Group the lines into 5 to 15 classes. Each class
   has an id, a one-sentence statement ("confirmations in other words are read as
   unknown"), the component responsible, and the step. Keep it in
   `docs/failure-taxonomy.md`; ids persist across cycles.
4. **Count.** Label every readable failure with a class (rules or a judge may do this;
   spot-check 30 by hand). Count by class and by segment x step: this is the coverage map
   (references/improve.md step 2, `docs/coverage.json`).
5. **Pick.** Rank classes by share of TRAIN failures x expected fix rate / cost (the one
   selection rule, references/improve.md step 2). A class maps to one or more cells. The
   top class names the next candidate; the largest cell either holds a candidate or is
   written "not addressed, because ...". A class no bank can see gets a targeted bank
   first (references/improve.md step 3).
6. **Act.** For the top class: a candidate card whose root cause is the class statement; a
   fresh writer's 30 or more examples of the class as readable TRAIN (fix the class, not
   the phrase); and, for the mechanism route, a fresh targeted bank for that cell, written
   after the candidate freezes.
7. **Track.** One row per class per cycle in TOURNAMENT.md: class, count before, count
   after, on which bank, fixed by which version; new classes; classes that came back.
   A class with many failures and no candidate is written as "not addressed, because ...".

Rules: no class is ever built from a sealed bank's items; safety misses on sealed banks
are counted by kind only, and their text is studied only on readable safety TRAIN
(references/safety.md, Aim after round 0). A fix cites its class id.

## 2. The classification ladder

The understanding layer reads each input and step and decides: what is asked, which
route, whether a harm signal is present. Climb one rung at a time, each rung one strategy
and one version (references/strategy-menu.md rows 3, 5, 6 and 7; row 14 applies them to
later steps), kept only by the proven or mechanism route.

The ladder applies to each decision point that reads an input: a router, a triage or
task-type step, a validator, a harm screen. For an agent that is an LLM end to end, rung 0
is the deterministic guards on tool arguments and the harm screens; the ladder then
governs those screens and any router, and the agent's own reasoning is improved by other
menu rows (8 to 10, 14).

| Rung | What | Climb to it when |
|---|---|---|
| 0 Rules | keywords, patterns, schema and argument checks; deterministic | always the floor; never removed for safety |
| 1 Learned classifier behind the rules | fixed arbitration: rules decide safety and anything they read with certainty; the classifier fills "unknown" | rules plateau on TRAIN over two cycles of fresh data, and labels are cheap (30 or more per class) |
| 2 Agreeing learners | two or more different learners must agree to replace a rule read; disagreement asks, abstains or escalates | one learner is over-confident: confident and wrong on a visible share of TRAIN |
| 3 Calibrated thresholds | probabilities calibrated (Platt, isotonic or temperature) and a threshold per class | routing depends on a score, or false accepts and false rejects cost different amounts |
| 4 LLM classifier or judge, rules as the floor | small model in batches, verdicts cached by hash, off-label = abstain, prompts hill-climbed on TRAIN | the class is open (the space of phrasings is too wide for rules or small learners) and cost and latency allow |

Do not climb when error analysis says the failure is a flow bug, a tool bug, a missing
reader for a later step, or a bad label: fix that instead. A rung that does not move its
class on a fresh targeted bank is removed at ablation (references/improve.md step 9).

**Calibration.** Fit calibration on a readable calibration bank written by a fresh
writer. Pick thresholds on a TUNE bank written after the version froze (counts only),
then retire it to train (references/strategy-menu.md, Automatic tuning). Report false
accepts and false rejects per class with intervals, and the abstain rate on unseen text.
Recalibrate when the model, prompt or input mix changes (`drift.py`).

**Safety stays monotone.** Learned and LLM parts only add escalations, refusals and holds.
The harm-signal decision is the union: rules OR learned. A learned part may read harm
signals for this purpose only, and its extra escalations count against the false-alarm
ceiling in FRAME.md. A learned part never removes a
handoff the rules raised, never turns an unknown or fallback read into a non-safety
action, never proposes an irreversible effect without the deterministic path's
confirmation, and without a verdict behaves as the previous version. Pin each clause with
a test (references/safety.md).

**Later steps and follow-up turns, not only the first step.** Most failures in multi-step
agents sit after the opening. Give each step its own reader and its own coverage-map
column:
- replies: confirming, refusing, choosing, "I don't know", changing their mind, adding a
  second request; a confirmation only confirms the action already proposed and checked;
- later turns: a new topic, a correction, or a harm signal arriving late;
- tool results and intermediate outputs: an error, an empty result, a partial file, a
  failing test after an edit;
- final answers: cites a source, matches the record, says "not enough evidence".
Harm screens run on every input and step, not only the first. A report states which
steps each learned part reads; a part that reads only openings says so.
