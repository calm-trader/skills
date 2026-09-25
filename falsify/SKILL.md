---
name: falsify
description: >-
  Adversarial audit that attacks every claim a codebase makes until it breaks or survives — not only
  the code, but the tests that supposedly guard it, the guards that supposedly fire, the conventions
  that supposedly define correctness, and the claim that any of it ever ran. Fans out specialist
  reviewers, refutes both the findings AND the all-clears using a different search modality, then
  demands empirical proof: a guard is not a guard until it has been seen to fail. Invoke with
  /falsify, or when asked to "attack this", "adversarial review", "audit before commit", "what is
  wrong with this", or when a review keeps coming back clean and you do not believe it.
---

# Falsify

Reviewing a diff finds bugs in code someone wrote. It does not find the defects that survive review,
and those are the expensive ones. Every defect below passed code review, passed CI, and shipped:

| what shipped | why review missed it |
|---|---|
| A guard whose failing branch was unreachable — its one caller passed the literal `true` | the guard's code was correct |
| Three tests that *pinned* the bug they existed to catch | the tests passed |
| A hedge-direction sign inverted since the file was written | no convention said which sign meant what, so the sentence could not be wrong |
| A capture pipeline dead for ten days behind a healthy-looking page | every function was correct; nothing called them with real data |
| A module with complete unit tests and zero production rows | 100% of its tests passed |

None of these is a coding error. Each is a **claim that could not be falsified** — and a review that
only reads the diff will confirm all five.

**The discipline: treat every claim as a hypothesis and try to kill it.** A claim that survives a
genuine attack is worth something. A claim nobody attacked is worth nothing, however green the suite.

---

## 0. Budget and output discipline — read this first

Adversarial audits fail in a specific way: the reviewer explores, runs out of budget, and returns
narration instead of findings. That is not a null result, it is a wasted run, and it is the single
most common failure of this kind of agent.

- **Emit findings as you confirm them, not at the end.** If you are cut off at 60%, the operator must
  still have 60% of the value.
- **Never open with what you are about to do.** No "I'll start by mapping the test surface." Lead
  with the first finding, or with "no findings yet" and a fact.
- **Budget explicitly.** Decide up front how many probes you can afford. Depth on one confirmed
  finding beats breadth across five unconfirmed ones.
- **A run that ends with no verdict counts as FAIL, not as "clean."** Say `NO FINDINGS` and what you
  actually checked, so the gap is visible. Silence and cleanliness must never look the same.
- **If you cannot dispatch agents, run the lenses (§2) and the skeptics (§3b) yourself, in order,**
  and say in the report that the panel was one reader. A reader without an Agent tool otherwise
  improvises past "run these in parallel" and "run three skeptics", and the report does not say
  so. `[untested]`
- **When you run as a sub-agent, only your final message reaches the caller.** So make every
  message cumulative: every finding confirmed so far, in full, then a last line
  `FALSIFY_PARTIAL: <n> findings so far · next: <what you are attacking>`. A run halted at its turn
  limit then hands the caller everything it found instead of the sentence it was in the middle of.
  `FALSIFY:` goes on the finished report only (§7), never on a partial one. `[untested]`

---

## 1. The claim taxonomy

Before attacking, name what is being claimed. Most reviews only attack the first row.

| # | claim | how it fails | how to attack it |
|---|---|---|---|
| 1 | **This code is correct** | logic, state, concurrency, injection | ordinary review lenses (§2) |
| 2 | **This test proves it** | asserts observed output, so cannot fail for its reason | §4 sabotage |
| 3 | **This guard prevents it** | branch unreachable; every caller passes a constant | trace callers, not the guard |
| 4 | **This value means X** | no stated convention, so no reading is wrong | §3d unfalsifiable claims |
| 5 | **This runs** | correct code, never called with real input | §5 empirical reachability |
| 6 | **This succeeded** | reports success while storing, sending, or changing nothing | compare the report against the side effect |

Rows 2–6 are where the durable defects live, because rows 2–6 are what nobody checks.

---

## 2. Fan out — specialist lenses

Run these in parallel. Each returns candidate findings with `file:line`, a failure scenario, and a
severity 1–5. Candidates are not findings yet.

1. **Correctness** — logic, state transitions, ordering, races, off-by-one, unit and sign errors,
   silent coercion, error paths that swallow.
2. **Security** — injection, authz, secrets, deserialization, SSRF, PII. Escaping is judged against
   the *target grammar's* full metacharacter set, never by copying local precedent.
3. **Convention and idiom** — escape-hatch types, unhandled unions, non-idiomatic API use, but only
   where it affects correctness or safety.
4. **Project precedent** — the repo's own stated rules (`CLAUDE.md`, `CONTRIBUTING.md`, lint config).
   Reuse is the default; if the precedent is itself broken, flag it as **shared exposure** rather
   than propagate it.
5. **Blast radius** — downstream consumers, migrations, cache and job interactions, backward
   compatibility. Find callers by *path strings and reflective dispatch*, not symbol grep alone.
6. **Complexity** — dead code, reinvented stdlib, single-implementation abstractions. Reported
   separately; never blocks on its own.
7. **Falsifiability** *(this skill's addition)* — for every claim of kinds 2–6 above, can it be
   wrong? If nothing could distinguish this code from a broken version of itself, that is the finding.

---

## 3. Refutation — try to destroy your own findings

A finding survives only if a skeptic **cannot** refute it. Attack each candidate on:

- **Reachability** — is the flagged path dead or guarded upstream?
- **Already handled** — mitigated by validation, a framework default, or the type system?
- **Does it reproduce** — or does it rest on a misreading? Construct the failing input. If you cannot,
  say so and drop confidence.
- **Pre-existing** — unchanged on the base branch is out of scope *unless* this change widens exposure.
- **Underpowered** — the finding itself rests on too few observations to stand: one failing input,
  one run, one window. Say how many it took and cap confidence accordingly.
- **Not a valid refutation:** "it matches existing code." If the precedent shares the gap, both are
  exposed.

### 3a. Refute the all-clears too

**This is the highest-yield rule in the skill.** Every "verified clean", "no callers", "handled
elsewhere" is itself a claim, and it is the claim nobody attacks.

**Re-attack it with a different search modality than the one that produced it.** Symbol grep said no
callers? Search path strings, string-keyed dispatch, config, DI registration, generated code, and the
network surface. An all-clear survives only if the second modality also fails to break it.

### 3b. Panel size

For expensive or destructive findings, run three skeptics with *different lenses* (correctness,
security, does-it-reproduce) rather than three identical ones. Keep the finding if two or more fail
to refute it. Redundancy catches noise; diversity catches failure modes.

### 3c. Decorative guards

For each guard, assert, or validation: **find a caller that can make it fire.** A guard whose every
caller passes a constant is decorative — its failing branch is unreachable and it protects nothing
while reading as protection. Grep the call sites for literal arguments in the guarded parameter.

### 3d. Unfalsifiable claims

For every field, flag, or return value carrying a **sign, unit, direction, or timezone**: is the
convention stated where it is declared? If not, the code cannot be wrong, and *that* is the defect —
not a style issue. An unstated convention defeats every reviewer, every test and every supervisor
simultaneously, because none of them can say what correct would look like.

Fix order matters: **state the convention first, then correct the code.** Correcting first leaves the
next reader with the same undecidable question.

---

## 4. Sabotage — a guard is not a guard until it has been seen to fail

The strongest technique here, and the one most reviews skip because it requires *running* things.

**For every test that guards something important:**

0. **Decide where the mutation happens, before you make one.** If the working tree is clean, break
   the file in place — git is the restore. If it carries uncommitted changes, work on a copy
   instead: restoring would take that uncommitted work with it, and nothing brings it back.
1. Break the thing it guards — invert a condition, weaken a check, delete a branch.
2. Run the test.
3. **If it still passes, the test is decorative.** Report it as a finding of its own, at the severity
   of the thing it failed to guard.
4. Restore, and confirm with `git diff` that nothing of the mutation remains.

A test written by running the code and pasting the result cannot fail for the reason it exists. The
signature: assertions on exact output strings; oddly precise floats with no derivation; comments
explaining *what* the code returns rather than *why* that is correct.

**Prefer tests that encode the mechanism over tests that encode the output.** A test asserting
`hedge = −vanna × Δσ` and checking the prose agrees cannot silently invert; a test asserting the
string "dealers sell" pins whatever was there when it was written.

Apply the same to guardrails, kill switches and rate limits: engage it and observe the refusal. An
untested guardrail is a claim.

---

## 5. Empirical reachability — did a row appear?

Static reachability answers "could this run." The expensive question is **"has it ever run."**

For any pipeline that persists, sends, or changes something, get the count:

```
rows in the table this writes · messages actually sent · files actually produced
```

Zero, against a passing suite, is a finding — often the largest one available. Complete tests over a
path with no production rows means the tests describe imagined inputs.

Score by *operational* reachability, not just structural:

- **latent** — cannot run in current config (no route, flag off) → drop one bucket, unless this change
  makes it reachable.
- **env/data-gated** — the code runs; whether it *manifests* depends on an operational fact
  (a mode string, an unset token, an empty table). **Full weight, and name the fact.** This is where
  the ten-day silent failure lived.
- **inert infrastructure** — correct, complete, and called by nothing yet. Score at would-be-reachable
  weight and label it, so the risk is tracked rather than discovered later.

**Silent success** is the paired check: does anything report success while its side effect did not
happen? Compare the report to the artefact — the row, the file, the message. Prefer designs where the
artefact settles the claim and the report cannot.

A cited file is a claim too: `scripts/check_citations.py DIR` checks that every path a document
cites resolves to a real file, and that any number attributed to it occurs there.

---

## 6. Score

`risk = severity (1–5) × confidence (0–1, post-refutation)`

- **BLOCK** — `risk ≥ 3.5`, or any confirmed reachable security/authz/data-loss issue, or a
  decorative guard on a money, auth, or destructive path.
- **CONSIDER** — `2.0 ≤ risk < 3.5`
- **NOTE** — `< 2.0`

Confidence is set by refutation, not by how strongly you feel. A finding you could not reproduce
caps at 0.5 and says so.

---

## 7. Report

Findings first. For each: `file:line` · one-sentence defect · the concrete failure scenario (inputs →
wrong result) · what refutation you attempted and why it failed · severity × confidence.

Then, and only then:

- **All-clears re-attacked** — what you re-checked with a second modality, and how.
- **Not checked** — say it plainly. An unstated gap reads as a clean bill of health. For each item,
  say whether it went unchecked because you ran out of budget, or because the instruction could not
  be followed as written. The second is a finding about the instructions you were given, not a gap
  in your run.
- **NO FINDINGS**, if that is the answer, with what you actually attacked. A silent run and a clean
  run must never look the same.

The report's last line, with nothing after it, is exactly:

```
FALSIFY: <n> BLOCK · <n> CONSIDER · <n> NOTE · <n> UNMEASURED · attacked: <claim kinds> · not checked: <n> (budget <n>, instruction <n>)
```

UNMEASURED counts the claims you attacked and could not score either way, so they are not lost in
a bucket that means something else. Treat a report without this line as FAIL: it has not finished.
`scripts/check_report.py` reads the line and checks it against the body (counts, the §6 thresholds,
the budget/instruction split); the sibling `supervision` skill's history says why it matters: a
verdict that a reader cannot find is a gate that did not happen. If you score a finding outside the
§6 thresholds on purpose, write `override:` and the reason on the same line, so the checker can tell
a decision from a slip.

Never edit, stage, or commit. This skill diagnoses; the operator decides.
