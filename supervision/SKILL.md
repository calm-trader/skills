---
name: supervision
description: The operating protocol for a team of advisory supervisors and an independent verifier — when to consult which one, what a brief must carry, and the rules that stop a verification gate from quietly becoming decorative. Load when running a build loop that uses the supervisor agents, or when deciding whether a task is done.
---

# Supervision

A team of advisors is inert without a protocol. Six well-written supervisor agents that nobody
consults, and a verifier whose verdict is advisory, produce exactly the same output as having
neither. This skill is the part that makes them fire.

It was extracted from a long autonomous build where every rule below was added *after* the failure
that made it necessary. None of it is a priori.

## Installing the team

This skill is the protocol. The agents it refers to ship beside it, in `agents/`:

```bash
cp -r skills/supervision /path/to/project/.claude/skills/
mkdir -p /path/to/project/.claude/agents
cp skills/supervision/agents/*.md /path/to/project/.claude/agents/
```

`supervisor-evals` loads the **`falsify`** skill and is much weaker without it. It is a sibling in
this library — install that too:

```bash
cp -r skills/falsify /path/to/project/.claude/skills/
```

`supervisor-quant` is options dealer-positioning expertise, not a supervisory stance. In a project
that is not about markets, delete it or replace its body with your own domain's ground truths; the
reusable part is the *shape* — a domain expert who states its conventions and refuses to guess.

## The two failure modes this exists to prevent

**Consulting nobody.** The builder retries the same approach eight times because each attempt feels
close. Attempt counting is the fix, and it has to be mechanical — "am I stuck?" is a question a
builder mid-flow always answers no.

**A gate that stopped measuring.** The verifier returns nothing, or returns "looks good", and the
task is marked done. Once that happens twice it is not a gate, it is a ritual. Most of the rules
below are about this one.

## When to consult which supervisor

| Supervisor | Consult when | Timing |
|---|---|---|
| `supervisor-product` | anything with a user-facing promise | **BEFORE building** |
| `supervisor-architect` | design, structure, dependency, API shape, "this approach feels wrong" | after 3 failed attempts |
| `supervisor-design` | UI: visual language, hierarchy, motion, any redesign | before a restyle, or after 3 |
| `supervisor-evals` (loads `falsify`) | a claim you suspect is untrue; tests that pin bugs; guards that never fire; **a measured claim a decision rests on** (a headline figure, a kill, a promotion) — the verifier's four checks do not cover falsify §3e | **before such a claim is accepted**; otherwise any time |
| `supervisor-quant` | domain math and sign conventions *(replace with your domain)* | after 3 failed attempts |
| `verifier` | every task, before it can be marked done | **always** |

`supervisor-product` is the odd one: it runs **before** the work, not after three attempts, because
its whole job is to stop work that should not start. It has **no tools on purpose** — "if any line
needs a fact I did not give you, ask me; that gap is a finding, not a blank to fill" only holds if
the gap cannot be quietly closed by reading the repo. Give it the initiative explicitly in the brief.

## The stuck protocol

Track attempts per task in a state file that survives your context resetting.

1. **After 3 failed attempts on the same task, stop.** Retrying blindly past three is how an
   afternoon disappears. Consult the matching supervisor.
2. **Give it what it needs to disagree with you**: the task, the relevant spec excerpt, what you
   already tried, and the *exact* errors. A brief that only contains your current theory gets your
   current theory back.
3. **Log its advice and your decision**, including the parts you rejected and why. A consult you do
   not record is a consult you will repeat.
4. **Attempt once more**, following the advice.
5. **Still failing?** Mark the task blocked with a written analysis and move to the next unblocked
   task. A blocked task with a written cause is progress; a task retried eleven times is not.
6. **Two or more blocked tasks in one phase** means the phase is wrong, not the tasks. Get a
   phase-level review.

## The verifier protocol — where gates go to die

**The brief carries at most FOUR numbered checks.** Collapse the acceptance criteria; do not write
one check per sub-clause. Also name the two or three files that changed, and paste the output of
your test command so the verifier need not reproduce it — spend its budget on judgement, not setup.

**If a task needs more than four checks, it is two tasks.** Six changes in one commit cannot be
verified in one pass, by construction. This rule prevents more bad verifications than any other.

**The verdict is binding.** If you can overrule it, it is not a verifier.

**No verdict counts as FAIL.** A run that ends without an explicit `VERDICT:` line has told you
nothing, and treating "it didn't complain" as a pass is precisely how a gate becomes decorative.
Re-invoke **once**, with a brief of at most two checks.

**If the second run also returns no verdict**, split by risk:

- For anything touching your guardrails — money movement, auth, deletion, whatever your project's
  dangerous paths are — mark the task **blocked**. Builder self-verification is not independence,
  and those are exactly the paths the guardrails rest on.
- For everything else, self-verify and record *in writing* that the task is done on **unverified**
  evidence. Never silently.

**Ask for the check you most want to be wrong about.** A verifier told "confirm X works" confirms X
works. A verifier told "I claim X; the failure mode I fear is Y; try to produce Y" is worth ten of
those. Name the sabotage you already ran and ask it to reproduce one independently.

## Do not take a supervisor at face value

They are confident and they are sometimes wrong. In the build this came from:

- An architect claimed a counter could be gamed a specific way. Constructed, the case did not
  reproduce — the reconciler already caught it. **The real divergence ran the other way**, and was
  only found because the claim was checked rather than accepted.
- A suggested guard, once implemented, fired on the project's own function name. It was dropped
  rather than tuned until green — a weak guard beside a strong one dilutes the claim the strong one
  makes.

Check the claim, then act. Record which parts you rejected; that record is worth as much as the
advice.

## The rule underneath all of it

**A test must assert the intended property, not the observed output**, and **a guardrail test must be
seen to fail**: break the thing it guards, watch it go red, restore it. A test never observed failing
is a claim, not a check.

This applies to the supervisors themselves. If the verifier has returned PASS many times in a row
and never once caught anything, it is quieter, not better — feed it a deliberately broken change and
confirm it fails. A gate you have never seen reject anything is not known to be a gate.
