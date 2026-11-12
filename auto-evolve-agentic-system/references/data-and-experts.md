# Domain experts and the writer swarm (FRAME, BUILD, then every cycle)

A bank written by one author measures that author's idea of the users. Two steps widen it:
an **expert panel** that knows where this kind of system fails, and a **writer swarm** that
turns the experts' cases into many varied, checked TRAIN episodes. Both feed readable data
only. Sealed banks have their own independent writers (references/data-discipline.md).
Words such as episode, cluster, step and systems of record mean different things per kind
of agent: references/runtime-adapters.md, Words.

## 1. Expert panel

**Who.** People from the system's stakeholders, each owning a different risk. With end
users who differ (new, expert, acting for someone else, upset), the panel is also the
stakeholder panel that cold-reads the system: 8 to 12 roles in total (references/safety.md).

| Agent kind | Typical panel |
|---|---|
| Operations agent that takes actions (helpdesk, back office, account changes) | operators who do the job today, their team lead, compliance, security, on-call engineer |
| Coding agent | maintainer, code reviewer, security lead, release manager, new contributor, issue reporter |
| Data-pipeline or extraction agent | data owner, downstream analyst, privacy officer, on-call engineer, auditor, upstream source owner |
| Research or sales agent | the people who use its output, a subject expert, legal or compliance, brand owner, a contact on the receiving end |

**Two sides, never mixed.** Anything the builder reads trains the builder, so the panel
splits before anyone writes:
- **Seed side** (most of the panel): writes readable seed cases and personas, cold-reads
  the system, checks swarm samples, labels the gold slice.
- **Sealed side**: the domain owner and anyone who will write or brief a sealed bank
  (safety, holdout, final, CONFIRM, targeted). They give a lens, the FRAME.md lists
  (must-escalate, must-refuse, irreversible effects, harm signals), sign-off on targets,
  and triage of findings by severity. They write no readable seed cases or personas and do
  not cold-read. The domain owner briefs the safety bank writer from the FRAME.md list.

**What each seed-side expert does.**
1. **Lens**: one line on what they check first ("I check who the change is for").
2. **Seed cases**: 10 to 20 realistic episodes each, in the form their agent kind uses
   (Words, "how an episode is made"), with the outcome they expect, including the awkward
   ones they see every week and at least 3 that must escalate, must be refused, or must
   not cause an irreversible effect (references/safety.md, Words). They join dev or TRAIN,
   never a sealed bank. Where an expert's expected outcome differs from the one the
   generator computes, the domain owner decides, and it is logged as a FRAME finding.
3. **Personas**: two or three kinds of user, requester or input source they know well,
   and how each behaves. The swarm uses them.
4. **Cold read**: once V1 passes its gates, each uses the system as their role would (the
   stakeholder panel, references/safety.md). A finding needs a transcript or trace.
5. **Sample check** of swarm output (section 2, step 7), and **gold-slice labels**: two
   experts label 100 to 200 episodes and their agreement is reported.

**When no human expert exists**, a model persona panel stands in: one fresh context per
role, prompted with the role, its lens, and what that role has seen go wrong
(references/prompts.md, Expert persona). A strong model of another family, in its own
fresh context, drafts those "seen go wrong" lines, so the builder does not. Persona contexts
that write seeds are never reused to write or brief a sealed bank. Every report says
"expert panel: model personas, no human expert" (references/report-templates.md), and
FRAME.md says "no domain owner: targets set by the builder". A persona panel finds
questions; it cannot sign a safety target or clear a Blocker.

## 2. Writer swarm (expanding TRAIN)

**One swarm is one writer set-up**: its model family, brief, persona set and week. Its 20
to 100 contexts are not independent writers; for statistics and for "2 fresh set-ups per
cycle" the swarm counts once (references/statistics.md). Many cheap contexts each writing
a small, different slice still beat one context writing everything: they widen the
clusters (phrasings, repositories, sources) one set-up covers.

1. **Writers.** A small, fast model (Haiku-class or similar), one fresh context per cell
   of the grid below, of a different model family from the builder where possible. If it is
   the builder's family, say so under Known weaknesses (references/data-discipline.md).
2. **What a writer writes.** Text where the episode is text, a spec where it is not
   (Words, "how an episode is made"): an operations writer writes the user's messages; a
   coding writer writes the issue text and picks a mutation of a passing commit or a
   closed issue to replay; a pipeline writer writes a fault spec for a clean input; a
   research writer writes questions against a fixed source set. The generator builds each
   episode and its reference. Writers never give expected outcomes.
3. **Seeds.** Each context gets one persona, one scenario, one style and one step, plus 3
   to 5 expert seed cases for that scenario to learn the keys and format. Never a sealed
   bank, results or agent code (references/prompts.md, Swarm writer).
4. **Diversity grid.** persona x scenario (key or segment) x style x step. Steps are the
   FRAME.md list for your agent kind (Words, "step of the episode"). Styles: terse,
   verbose, misspelt, second language, upset, acting for someone else; for a coding agent,
   vague issue, wrong stack trace, messy repository; for a pipeline, malformed, late,
   partial or duplicated input; for a research agent, broad, leading or ambiguous
   questions. Fill cells by the coverage map's TRAIN columns (references/improve.md
   step 2), not uniformly.
5. **Later steps, not only the first.** At least the FRAME.md minimum of distinct clusters
   per later-step key (default 30): replies, confirmations, changes of mind and second
   requests for an operations agent; a failing test after the first edit for a coding
   agent; a bad second file for a pipeline; a follow-up question for a research agent.
   Include episodes where the harm signal or key fact arrives at a later step.
6. **Dedupe.** A duplicate is defined per kind (Words, "duplicate"): the same text after
   normalisation; the same repository and mutation; the same schema and fault; the same
   question and source set. Drop exact duplicates, then near duplicates of the text parts
   (token-set overlap or embedding similarity above a FRAME.md threshold, default 0.8),
   within the swarm and against dev and TRAIN. `seal.py seal` refuses records shared with
   sealed banks. Report distinct clusters per key after dedupe; drop a context whose output
   is mostly duplicates and brief a different persona.
7. **Oracle check of labels.** The reference is made by the generator, never the writer
   (Words, "label oracle"): expected effects and handoffs from playing the episode in the
   mock world; the original tests and the pre-mutation commit; the clean input before the
   fault; the source passage recorded with the question. Where no reference can be built,
   two independent labels, with disagreements going to a seed-side expert. An episode
   whose label cannot be checked is marked `unchecked` and used for error analysis only,
   never for a gate or a training label.
8. **Human-checked sample.** Before swarm data gates anything (a TRAIN-gain criterion, a
   refit a candidate depends on, a judge-calibration bank), a seed-side expert checks 150
   episodes drawn at random, stratified by grid cell, for realism and label correctness.
   The upper end of the 95% interval of the error rate (`noise.py 150 K`, K = correct)
   must be under the FRAME.md bar (default 5%): with 150 checked, at most 2 wrong. Above
   it, fix the brief and regenerate. Without a human, a persona panel checks it and the
   report says so.
9. **Readable TRAIN only.** Swarm output is sealed into the ledger as role `train` (so a
   later sealed bank cannot repeat it) and the builder reads all of it. It never becomes
   SELECT, CONFIRM, safety, holdout or final data.
10. **Manifest.** Per swarm: the set-up (model family, brief, persona set, week), grid cells
    filled, episodes and distinct clusters per key before and after dedupe, oracle
    results, sample size, errors and interval, who checked. `make swarm-check` fails
    without it (references/gates.md).

Workflow shape (any runtime that can fan out):

```js
const cells = grid(personas, scenarios, styles, STEPS).filter(byTrainCoverage)
const out = await parallel(cells.map(c => () =>
  agent(SWARM_WRITER(c, seeds[c.scenario]), {model: SMALL, label: c.id, schema: SPECS})))
const bank = dedupe(build(out.flat()), {against: [dev, train], threshold: 0.8})  // generator builds episodes
const labelled = oracle(bank)                     // reference from the generator, never the writer
const check = await expertCheck(stratifiedSample(labelled, 150, byCell))   // gate before use
```

## 3. Where this sits in the loop

- **FRAME**: name the panel and split it into seed and sealed sides; name the domain
  owner, the duplicate threshold, the sample size and error bar; collect seed cases and
  personas from the seed side.
- **BUILD**: seed cases become dev; the first swarm is sealed as role `train`
  (references/frame-and-build.md, phase 1 step 9).
- **SAFETY**: the domain owner (who wrote no seeds) briefs the safety bank writer from the
  FRAME.md list; the seed side and end users cold-read V1.
- **IMPROVE step 1, every cycle**: at least 2 fresh swarms (2 new set-ups: new personas, a
  brief or model not used before), aimed at the coverage map's top TRAIN cells, scored on
  the frozen base, then error analysis (references/error-analysis-and-classification.md),
  then the refit.
- **OPERATE**: adjudicated traces from TRAIN accounts only join TRAIN as its most
  realistic part; seed-side experts adjudicate the safety slice (references/continuous.md).
