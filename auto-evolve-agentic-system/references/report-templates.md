# Report templates

## Rules for every report
- One commit per version: `V{n}: {strategy in one line}` plus the attribution lines the
  session requires. The user approves every push.
- Each version ships `README.md`, `IMPROVEMENTS.md`, `FINDINGS.md`,
  `prompts/{runtime,simulation,build-team}` with every writer, red-team, panel, review and
  workflow prompt verbatim, `docs/`, the Makefile.
- Every count comes from a generated file (`make docs` writes `docs/results.json` and fills
  the tables). `make docs` fails when README.md or STRATEGIES.md is older than the last
  version commit.
- The headline is the systems-of-record count, with its bank's writer, episodes and
  phrasings. The agent-label ("strict") count sits beside it as a diagnostic.
- The data-discipline section is `seal.py statement --markdown` pasted, never prose.
- Each report has "What these numbers do not measure": real users, real systems,
  human-agreed labels, live judge, seeds beyond one, a human expert panel, a
  human-checked swarm sample. Tick what this version has.
- Without human experts, the report's first section says "expert panel: model personas,
  no human expert" (references/data-and-experts.md).
- A number from another system or run is quoted only from a fair comparison
  (references/compare.md).

## IMPROVEMENTS.md (per version)

```markdown
# V{n} improvements

V{n} adds **{strategy}** to [V{n-1}](../{prev}/), kept **{proven | on mechanism}**.
[STRATEGIES.md](STRATEGIES.md) compares all versions.

## What it does
{3 to 8 lines: what the component reads, what it may decide, what it may never do, what
happens when it abstains. The root cause it addresses, from the candidate card.}

## Before and after
| Measure | V{n-1} | V{n} |
|---|---|---|
| Headline: records count on {bank} ({writer set-up}; {episodes} episodes, {phrasings} phrasings) | | |
| Agent-label count, same bank (diagnostic) | | |
| Pooled SELECT ({banks}, {set-ups} set-ups): B, C, net, cluster-aware interval | | |
| Targeted bank (mechanism route only) | | |
| CONFIRM (cycle head only) | | |
| Safety gate: recall, misses by largest kind, new misses, false alarms | | |
| By segment: success, correct handoff, wrong action | | |
| Wrong actions by effect type and severity | | |
| TRAIN: gained, lost | | |
| Falsifier and panel findings, by severity | | |
| Tests; dev clean and under faults; corpus replays; invariants | | |
| Cost per episode; p95 latency | | |

{One paragraph: which route kept it and why; is any gain outside the noise.}

What these numbers do not measure: real users [ ], real systems [ ], human-agreed labels
[ ], live judge [ ], seeds beyond one [ ], human expert panel [ ], human-checked swarm
sample [ ].

## What changed
- `{path}`: {what}
- `tests/{file}`: {which clauses are pinned}

## Data discipline
{`seal.py statement --markdown`, pasted. Add only what the ledger cannot know: which banks
were read, which only counted.}

## Known limits
{New limits this version adds; link to the previous list.}
```

## FINDINGS.md
| Id | Source | Severity | Finding | Status | Fix (file:function) | Test | Near variants |
|---|---|---|---|---|---|---|---|

Plus one line: `Falsifier reviewed commit: {sha} on {date}` (read by `make falsifier-check`).

## TOURNAMENT.md, CYCLES.md, READINESS.md
TOURNAMENT.md per cycle: references/improve.md (Report). CYCLES.md: references/continuous.md.
READINESS.md: references/readiness.md.

## STRATEGIES.md (latest version)

Sections, in order:
1. First line: "Ready for {stage}" or "Not ready for {stage}: {reason}".
2. Intro: why the loop started, the baseline numbers.
3. Strategy table: Version | Strategy | Route (proven, mechanism) | Proven in | Folder.
4. Results table, rows: each holdout (records count, then label count), final bank,
   pooled SELECT, CONFIRM per cycle, TRAIN, dev, safety gate and final safety bank, false
   alarms, tests, corpus replays; columns: versions. Each bank's writer set-up, episodes
   and phrasings in its row label.
5. The whole journey:
   ```markdown
   | Version | What changed | Route | Holdouts (records, of {2N}) |
   |---|---|---|---|
   ```
6. "What each strategy did, honestly": one bullet per version, the number, inside or
   outside the noise, what did not work, what the ablation removed.
7. Fair comparison (if another system or run exists), from `compare.py --markdown`:
   ```markdown
   | Bank (writer set-up) | Episodes | Phrasings | Baseline | A | B | B (only A) | C (only B) | Net | Interval | Verdict |
   |---|---|---|---|---|---|---|---|---|---|---|

   | System | Gain on own holdouts | Gain on fresh banks | Transfer share |
   |---|---|---|---|
   ```
8. Data discipline (`seal.py statement`), reviews (who, when, findings by severity),
   reproduce (exact commands).

## README.md (per version)
First line as in STRATEGIES.md. What it does; **The guarantee**; **What V{n} adds** (with
holdout numbers and V1 numbers); commands; results table (controls and holdouts); how it
was built; layout; known limits; provenance.

## prompts/build-team/NN-role.md
```markdown
# {Title}
- Role: {writer | red teamer | advisor | falsifier | workflow | ...}
- Sent: {ISO time}
- Model: {tier or name}
- Used for: {what, and whether its output may be read}
The prompt, verbatim:
{fenced text}
```
