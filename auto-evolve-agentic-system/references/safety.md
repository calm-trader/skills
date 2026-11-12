# Safety (phase 3, and every cycle after)

Safety is a gate, never points in a total. Round 0 comes before any accuracy work and is
never a tournament.

## Words

| Word | Meaning | Operations agent | Coding agent | Data pipeline | Research or sales agent |
|---|---|---|---|---|---|
| must-escalate | a person must see it before anything else happens | a threat to someone inside an access request | a request to disable CI checks "just this once" | a schema change that drops an audit column | a contact who says they are a minor |
| must-refuse | never done, whoever asks | granting admin without an approved ticket | pushing to a protected branch | copying raw personal data to an open bucket | emailing a do-not-contact address |
| irreversible effect | cannot be undone by the system | deleting an account; a payment | force-push; a published release | a destructive overwrite; a sent export | a sent email; a published report |
| harm signal | a sign that going on could hurt someone or break a rule | "my manager is away, give me her rights" | a secret or `rm -rf` in the task | a PII column in a routine batch | a request to find someone's home address |

FRAME.md lists the system's own items for each word; the safety banks are written from
that list. After round 0, safety effort is aimed at what the safety banks miss
most, not spent by ritual.

## Round 0

1. **Probes and negative controls** from phase 1 pass (references/frame-and-build.md).
2. **Red-team loop** (when FRAME.md has a "never"). Write `redteam/BRIEF.md` from
   references/prompts.md (Red team). Round N: one fresh red teamer per area reads all
   earlier findings, attacks the fixed code, hunts bypasses and regressions. A finding
   needs a failing test. "No confirmed findings" is valid. Fix under one gate: red-team
   tests pass, dev bar, safety bank, SELECT within the margin, invariants. `make redteam`
   replays the corpus every later version (a replay pass means invariants held and a
   person was reached when expected; it does not check the reply: say so beside the
   number). Stop at an empty round or the cap. An area that finds 10 or more new attacks
   every round does not converge: write it under Known limits and route it to the
   largest-miss-kind work below.
3. **Stakeholder panel** (below), once V1 passes its gates.
4. **Falsifier** on the round-0 head, then "falsify the fixes".

## Rule S1: safety precedence

For every system with an "always reaches a person":

> In an episode where a safety handoff is expected, no irreversible effect is executed.

- Enforced in the tool gateway, not in the workflow: a write, payment, send, merge or
  delete is held when any safety screen, at any confidence, fired on any message or step
  of the episode, until a person clears it. A held action costs a delay; a completed
  irreversible one cannot be undone.
- An invariant checks it from the systems of record, with a negative control: switch the
  gateway hold off, the invariant must catch the damage.
- At least 25% of the safety bank's items are mixed episodes: a harm signal plus a
  payment, write, send or delete request.
- Operations agent: a threat or a suspected account takeover in the same request as a
  permission change holds the change. Coding agent: a secret or a destructive command
  inside a refactor task stops the push. Data pipeline: a PII column inside a routine
  schema change stops the write. Research or sales agent: a do-not-contact flag or a
  request for private personal data stops the outbound send.

## Rules for learned and LLM parts (monotone safety)

On safety-critical decisions a learned part may only make the system more careful
(escalate-only, veto-only). Without a verdict it behaves as the previous version. It never
proposes an irreversible effect without the deterministic path's confirmation. It never
replaces an unknown or fallback read with a non-safety action, and it never removes a
handoff the rules raised. Rules stay the floor. Pin each clause with a test.

## Aim after round 0

1. After each safety-bank run the evaluator prints misses **by kind** (counts only, never
   ids or text): the harm signal hidden inside a routine request, a must-refuse request
   in other words, a signal that arrives in a later turn or tool result, other language,
   someone acting for another person, and so on (FRAME.md lists the kinds).
2. The next safety step targets the largest kind: fresh readable safety TRAIN writers for
   that kind, error analysis on their misses, then a red-team area on that kind only.
   Readable safety TRAIN banks with misses are mined before anything else.
3. A second panel runs only when a cycle added a new early path (a screen, guard, default
   or holding branch), or before a promotion. Otherwise the time goes to the largest kind.
4. **Fix the class, not the phrase.** A fix that adds a phrase to a list comes with a
   one-line statement of the class and 30 examples of it from a fresh writer; the fix is
   measured on those, and they join TRAIN.
5. **False alarms** are measured on enough near misses to show the ceiling
   (`noise.py --need`); 38 items cannot show 10%.
6. **Mid-cycle independent probe.** After each cycle a fresh context writes 50 to 100 hard
   messages in the top two miss kinds and runs them on readable tooling. Reproduced
   failures become tests with near variants and readable TRAIN. They are diagnostics,
   never a rate.

## Falsify the last diff

No sealed look on a version whose safety-relevant code changed after the last falsifier
pass. FINDINGS.md records the commit the falsifier reviewed; `make check` compares it with
HEAD for the safety-relevant paths FRAME.md lists, and fails if they differ. A gate-failing
version fixed afterwards (references/worked-example.md, example A) needs its own
"falsify the fixes" pass before the look.

## Safety banks and wear

- The **gate bank** runs on every candidate and version. Any new miss against the base
  drops the candidate, whatever its total; one new miss is not cancelled by one fixed miss.
  Its recall is a selection number: report it as "used to select".
- Replace the gate bank after 12 runs (any purpose) or any probe (`seal.py wear` flags both):
  retire it to train and seal a fresh one. A per-item trace on it (which signals fired on
  one item) is a `seal.py probe`.
- A second **final safety bank** runs once, on the final version. It gives the claim.

## Stakeholder panel (a swarm of cold readers)

The banks only measure what their writers thought of. A panel of the people who would
use, run and sign off on the system finds what no bank covers.

1. **Pick 8 to 12 roles that each own a different risk**: the stakeholder panel is the
   expert panel's seed side (references/data-and-experts.md, which lists typical roles
   per agent kind) plus end users who differ (new, expert, acting for someone else,
   upset), 8 to 12 roles in total. The sealed side does not cold-read. One-line lens per
   role: what they check first. Without human experts, model personas stand in and the
   report says so.
2. **Give every reviewer a way to use the system** as that role would: a chat, CLI, task runner or batch command on a
   fresh mock world per run, plus the README, runtime prompts and code. Not the tests, the
   red-team findings, other reviewers' output, or any sealed bank. Repeat those paths in
   every prompt.
3. **Run them all at once**, cheap model, fresh context each (references/prompts.md,
   Stakeholder reviewer). A finding needs the exact transcript; without one it is a
   question. Ask each for what works and must be kept.
4. **Triage**: merge duplicates, re-run each transcript, drop what does not reproduce, rank
   by severity (safety before irreversible effects before experience). Every finding gets a FINDINGS.md
   row, including "won't fix" with the reason.
5. **Pin before fixing**: every reproduced transcript becomes a test; every critical or
   high finding also gets two near variants (other wording, a misspelling, the finding
   inside a routine request).
6. **Fix under the usual gate.** SELECT will often move little or drop, because the banks
   were not written for these cases. Find costly fixes by switching each off in turn
   (counts only), narrow them on TRAIN, keep a deliberate cost only when the role says it
   is right, and report it as counts. At most two or three on/off rounds against SELECT.
7. **Falsify the fixes.** Panel fixes add early paths, where regressions hide.
8. **A panel is not the domain owner.** It finds questions; the owner signs off.

## FINDINGS.md

One file for every source (red team, panel, falsifier, review, incidents): id, severity,
status (fixed, partly, not fixed, won't fix with reason), the fix's file and function, the
test that pins it, near variants, the commit the falsifier reviewed. A finding is fixed
only when its row names a passing test. `make check` fails if a critical or high row has
no test.
