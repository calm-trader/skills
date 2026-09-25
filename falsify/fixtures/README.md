# Fixture: a target with the defects this skill claims to catch

`target/` is a small Python project, green under its own tests, that carries one planted defect
for each of the claim kinds in `SKILL.md` §1 rows 2–5, one ordinary bug as a control, and two
decoys that look like findings and are not. `answer-key.json` names them. It exists so that a
change to `SKILL.md` can be tested rather than argued: dispatch readers at the target with and
without the change, score the reports, and keep the change only if the numbers move.

The 2026-09-24 blind-reader test (see `../MEASUREMENTS.md`) used a target where both arms found the
code-shaped control every time, which put a ceiling on what it could say about rows 2–6. This
target has no ceiling by construction: the four planted defects are the kinds ordinary review
misses, and the control is the kind it does not.

## Running an arm

```bash
SANDBOX=$(falsify/fixtures/make-sandbox.sh)      # target/ only; the key stays behind
# dispatch a reader at $SANDBOX, with or without falsify/SKILL.md loaded; save its report
falsify/fixtures/score.py report.md              # refuses a report check_report.py rejects
falsify/fixtures/score.py --no-gate report.md    # the no-skill arm: scores it, reports compliance apart
```

`make-sandbox.sh` commits the copy, so a reader following §4 can mutate in place and restore with
git. Do not put "falsify", "audit" or "defect" in the sandbox path or the brief; name the task as a
review of `ledger` before a release.

## Reading the numbers

- Each arm needs enough readers to see a difference: n ≥ 6 per arm, and say the n.
- `score.py` credits a defect when the report names one of its files and one of its keywords. It
  is a floor. Read the misses by hand before believing them, and read the finds too: a report
  that names `hedge.py` and "sign" for the wrong reason gets credit it did not earn.
- A control found by every reader in every arm is expected; that is what a control is for. Four
  planted defects found by every reader in the no-skill arm means the target is too easy, and the
  answer is a harder target, not a conclusion that the skill works. That arm has no `FALSIFY:`
  line to give, so score it with `--no-gate`.
- In an arm with the skill, a report with no `FALSIFY:` line, or one whose line disagrees with its
  body, is not scored. Count those per arm; they are the compliance number for the line itself.

## The planted defects, in one line each (details in `answer-key.json`)

| id | row | defect |
|---|---|---|
| D1 | 3 | `check_released` cannot fire: its only caller passes `released=True`, and that caller is reached only through string dispatch |
| D2 | 2 | `test_hedge.py` pins the inverted sign in `hedge_qty`; the docstring states the convention the code violates |
| D3 | 5 | the capture pipeline has written zero rows for ten days of "capture ok"; `status()` reports healthy from the log line |
| D4 | 4 | `signed_qty` says side is ±1 and never says which is long; `adapter.SIDE` maps B to −1 as "exchange convention" |
| C1 | 1 | control: `report.last_n` is off by one |
| X1 | — | decoy: `check_qty` is a real guard, reachable and seen to fail in its tests |
| X2 | — | decoy: `delta_hedge` is correct and its test encodes the mechanism |
