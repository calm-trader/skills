# skills

Custom [Claude Code](https://claude.com/claude-code) skills. Each directory is one skill: a
`SKILL.md` whose frontmatter tells Claude when to load it, plus any assets that skill needs.

Everything here was written from things that actually went wrong. The rules carry the failure that
produced them, because a rule without its reason gets optimised away by the next person who reads it.

## The skills

### [`falsify`](./falsify) — attack every claim until it breaks or survives

Adversarial audit. Not just "is this code correct", but *can this claim even be false*.

Reviewing a diff finds bugs in code someone wrote. It does not find the defects that **survive**
review, and those are the expensive ones. Each of these passed review, passed CI, and shipped:

| what shipped | why review missed it |
|---|---|
| A guard whose failing branch was unreachable — its one caller passed the literal `true` | the guard's code was correct |
| Three tests that *pinned* the bug they existed to catch | the tests passed |
| A hedge-direction sign inverted since the file was written | no convention said which sign meant what, so the sentence could not be wrong |
| A capture pipeline dead for ten days behind a healthy-looking page | every function was correct; nothing called them with real data |
| A module with complete unit tests and zero production rows | 100% of its tests passed |

What it does differently:

- **Refutes its own findings** — a finding survives only if a skeptic cannot kill it.
- **Refutes the all-clears too**, using a *different search modality* than the one that produced
  them. Symbol grep said no callers? Try path strings, string-keyed dispatch, config, DI, generated
  code.
- **Proves guards by breaking them.** Invert the condition, run the test; if it still passes, the
  test is decorative and is reported at the severity of whatever it failed to guard.
- **Asks whether a row appeared.** Static reachability answers "could this run"; the expensive
  question is "has it ever run".
- **Asks whether a measurement means what it says.** The code can be correct and the number can
  still rest on the wrong unit, a window that already decided something, a sample too small to
  say anything, or a benchmark of zero. A kill on such a number is *unmeasured*, not falsified.
- **Findings first, emitted incrementally**, and a run ending with no verdict counts as FAIL rather
  than clean — because a silent run and a clean run must never look the same.

Read-only. It never edits, stages, or commits.

Borrows three of its best rules from
[`mcarlssen/claude-adversarial-review`](https://github.com/mcarlssen/claude-adversarial-review) (MIT)
and says exactly which, in [`falsify/ATTRIBUTION.md`](./falsify/ATTRIBUTION.md). MIT.

### [`tradingview-chart-reading`](./tradingview-chart-reading) — read a live chart without being misled

For getting indicator values, OHLC and a study inventory off a saved TradingView layout. Separate
from the backtesting skill because it loads on a different cue: reading a chart, not writing a
strategy.

The things that cost time to learn:

- **A blank chart is almost never a broken chart** — it is a hidden-tab bug. Six plausible fixes do
  not work; making the tab active does. Ships `tv-tab-watchdog.sh`, which must be stopped when you
  finish because it closes the operator's own chart tabs while it runs.
- **Read the Data Window, not the legend.** On the account this was established against, the legend
  renders only the price source even with four studies loaded. And the Data Window is
  *cursor-anchored*, so its Date header is part of the reading — during market hours the last bar is
  the **forming** one.
- **Some studies cannot be read at all.** A box-drawing study has no plotted series and contributes
  nothing to the Data Window. Reading zero rows for it is the correct result, not a failure.
- **Two instances of one study are indistinguishable** — neither panel exposes the length. Report
  them positionally rather than inventing "TEMA(9)". Prefer a multi-plot study, whose plots are
  named, over N copies of a single one.
- **Never save, and never touch a broker panel or an account modal** — including on sites you were
  not sent to.

### [`tradingview-backtesting`](./tradingview-backtesting) — what actually goes wrong on TradingView

Operational knowledge for backtesting Pine Script strategies and driving TradingView in a browser:
the cost model, lookahead traps that survive validation, Deep Backtesting behaviour, per-instrument
data retention, Strategy Tester quirks, and what TradingView fundamentally cannot backtest.

Its unifying lesson: **TradingView will nearly always give you a plausible number.** It rarely
errors. It silently produces a believable, wrong result — a stale script, a synthetic fill, a blind
counter, an uncosted trade. Assume every number is wrong until a specific check says otherwise.

Findings are tagged `[VERIFIED]` (observed directly), `[AUDITED]` (established from code or docs, not
demonstrated), or `[REPORTED]` (asserted by a reviewer, not reproduced) — so the reader knows what is
evidence and what is belief.

Ships `tv-tab-watchdog.sh`, which fixes the blank-chart bug that is really a hidden-tab bug: a tab
created by browser automation is never the active tab, so `document.visibilityState` stays `hidden`
and TradingView never sizes its canvases. Six plausible fixes do not work; making the tab active
does.

Also ships a small token-efficiency kit for the browser operator: `references/operator.md` (the
runbook an operator loads instead of the whole skill), `scripts/tvkit.js` (one-call page-state and
Strategy Tester report checks), `scripts/split_trades.py` (split one exported trade list into windows
offline), `scripts/validate_result.py` (arithmetic checks on a result record) and `scripts/selftest.sh`.

### [`supervision`](./supervision) — a team of advisors, and the protocol that makes them fire

Six supervisor subagents and an independent verifier, plus the operating rules that decide when each
one is consulted. The agents ship in [`supervision/agents`](./supervision/agents) as assets of the
skill.

A team of advisors is inert without a protocol. Six well-written supervisors that nobody consults,
and a verifier whose verdict is advisory, produce exactly the same output as having neither. Every
rule here was added *after* the failure that made it necessary:

- **`supervisor-product` runs BEFORE the work**, not after three failed attempts, because its job is
  to stop work that should not start. It has **no tools on purpose** — "if any line needs a fact I
  did not give you, ask me; that gap is a finding, not a blank to fill" only holds if the gap cannot
  be quietly closed by reading the repo. It returned *sharpen* on a broker integration and was right:
  the benefit being claimed was separable from the mechanism being bought, at a tenth of the cost.
- **At most four checks per verification.** If a task needs more than four, it is two tasks. Six
  changes in one commit cannot be verified in one pass, by construction.
- **No verdict counts as FAIL.** A run ending without an explicit `VERDICT:` line has told you
  nothing, and treating "it didn't complain" as a pass is how a gate becomes a ritual. Re-invoke
  once; then block the task if it touches a guarded path, because builder self-verification is not
  independence.
- **Do not take a supervisor at face value.** They are confident and sometimes wrong. One architect
  claim about a gameable counter did not reproduce when constructed — and checking it surfaced a
  *different*, real divergence that accepting the claim would have hidden.
- **A guardrail test must be seen to fail.** Break the thing it guards, watch it go red, restore.
  This applies to the verifier itself: a long run of PASS verdicts that never caught anything means
  it is quieter, not better.

`supervisor-evals` loads [`falsify`](./falsify) and is much weaker without it — install both.

`supervisor-quant` is options dealer-positioning expertise rather than a supervisory stance, and is
the one agent here that does not travel. In a project that is not about markets, delete it or replace
its body with your own domain's ground truths; the reusable part is the shape — a domain expert that
states its conventions and refuses to guess.

The agent files are byte-identical to the ones in the project they came from, and a test there
enforces it. A genericised copy, edited for publication and never actually run, is precisely the
failure `falsify` exists to catch.

## Using them

Copy a skill directory into a project's `.claude/skills/`:

```bash
git clone git@github.com:calm-trader/skills.git
cp -r skills/falsify /path/to/project/.claude/skills/
```

Claude loads a skill when the work matches its frontmatter `description`, or on request by name.

`supervision` also carries subagents, which live in a different directory:

```bash
cp -r skills/supervision /path/to/project/.claude/skills/
mkdir -p /path/to/project/.claude/agents
cp skills/supervision/agents/*.md /path/to/project/.claude/agents/
```

A project-level `.claude/agents/<name>.md` takes precedence over every other source of that agent, so
if one of these seems not to apply, look for a local file with the same name first.

## Writing more

Two conventions worth keeping:

1. **Every rule carries the failure that produced it.** "Never do X" gets ignored; "never do X, it
   cost ten days and here is the signature" does not.
2. **Tag what is evidence and what is belief.** A skill that cannot tell you which of its claims were
   actually observed will eventually be trusted about something nobody checked — which is the exact
   failure `falsify` exists to catch.
