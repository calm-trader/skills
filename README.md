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
- **Findings first, emitted incrementally**, and a run ending with no verdict counts as FAIL rather
  than clean — because a silent run and a clean run must never look the same.

Read-only. It never edits, stages, or commits.

Borrows three of its best rules from
[`mcarlssen/claude-adversarial-review`](https://github.com/mcarlssen/claude-adversarial-review) (MIT)
and says exactly which, in [`falsify/ATTRIBUTION.md`](./falsify/ATTRIBUTION.md). MIT.

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

## Using them

Copy a skill directory into a project's `.claude/skills/`:

```bash
git clone git@github.com:calm-trader/skills.git
cp -r skills/falsify /path/to/project/.claude/skills/
```

Claude loads a skill when the work matches its frontmatter `description`, or on request by name.

## Writing more

Two conventions worth keeping:

1. **Every rule carries the failure that produced it.** "Never do X" gets ignored; "never do X, it
   cost ten days and here is the signature" does not.
2. **Tag what is evidence and what is belief.** A skill that cannot tell you which of its claims were
   actually observed will eventually be trusted about something nobody checked — which is the exact
   failure `falsify` exists to catch.
