# Running the roles in different runtimes

## Words used in this skill (map them to your system)

| Word | Operations agent (takes actions for users) | Coding agent | Data-pipeline or extraction agent | Research or sales agent |
|---|---|---|---|---|
| episode | one conversation or ticket | one task (issue + repo state) | one input batch or document | one request (question or outreach task) |
| bank | phrasings per intent key, with placeholders | task specs per task family | input files per case family | requests per request type |
| key | intent ("reset access") | task family ("fix failing test") | case family ("late file", "bad schema") | request type ("compare vendors") |
| writer persona | a kind of user | a kind of issue reporter or codebase | a kind of upstream source | a kind of requester or contact |
| reach a person / safe stop | hand off to a human queue | open a draft PR, never merge | quarantine the batch, alert | answer "not enough evidence"; hold the send for review |
| safety bank item | a threat or takeover attempt inside a routine access request | `rm -rf` or a secret inside a refactor task | a PII column inside a routine schema change | a request for someone's private data inside a market question |
| enforcement probe | a credit with a declared amount under the cap, executed over it | push to a protected branch with a forged reviewer | write to a production table with a staging token | send to a do-not-contact address through another tool |
| domain owner | operations lead, compliance officer | maintainer, security lead | data owner, privacy officer | research lead, legal |
| dev N/N gate | every dev conversation passes | a fixed pass bar on dev tasks set in FRAME.md | every dev batch passes | every dev request passes |
| systems of record (the headline reads these) | the stores the tools write, the handoff queue, the sent replies | repository state and the hidden-test result in CI | the output tables, the quarantine and the alert log | the sent or published artefact, with its citations checked against the source set |
| how an episode is made | writer text rendered by the generator into a conversation with placeholders | mutate a passing commit, or replay a closed issue with its fix commit; the writer writes the issue text and picks the mutation | corrupt a clean input with a known fault; the writer writes the fault spec | the writer writes questions against a fixed source set; the supporting passage is recorded |
| label oracle (who makes the reference) | the generator plays the episode in the mock world and derives effects, handoffs, refusals | the original tests and the pre-mutation commit (or the fix commit) | the clean input and its known-good output | the recorded passage; claims checked against the source set |
| duplicate | the same text after normalisation | the same repository and mutation | the same schema and fault | the same question (normalised) and source set |
| cluster slots (the unit of evidence) | the phrasing in each slot: opening, each reply | repository; task family | upstream source; fault kind | source set; request template |
| step of the episode (coverage map column) | opening, reply or later turn, tool step, final answer | plan, edit, test run, PR text | parse, validate, transform, write | plan, search, read, synthesise, cite or send |
| safety precedence (rule S1) | no account, permission or payment change in an episode with a harm signal | no push or merge in a task with a secret or destructive command | no write in a batch with a PII signal | no outbound send or publish in a task with a harm or privacy signal |
| canary unit | a share of users or accounts | a set of repositories | a set of pipelines or sources | a set of teams or campaigns |
| operator | operations lead | release or platform owner | data platform on-call | research or campaign owner |

A stochastic agent may need a bar below N. Wherever this skill says "phrasings" (per key,
per slot, failing phrasings), read "distinct clusters" in your kind's cluster slots: 20
phrasings per slot means 20 repositories, sources or templates per slot for those kinds.
FRAME.md sets the step list and the cluster minimums per agent kind.

## Who runs each role

| Role | Best | Acceptable | Last resort (say so in the report) |
|---|---|---|---|
| Expert panel | people from the system's stakeholders (references/data-and-experts.md) | some people plus model personas for the missing roles; say which | model personas only, labelled "no human expert"; they cannot sign targets |
| Writer swarm (TRAIN) | many fresh-context subagents, a small fast model, one grid cell each, different family from the builder; one swarm counts as one writer set-up | a few subagents covering several cells each | you, in a fresh context per cell before reading failures; mark "not independent" |
| Writers | subagents in fresh contexts, cheap model, different family from the builder | the user pastes the writer prompt into another tool and gives back the file | you write it in a fresh context before reading failures; mark "not independent" |
| Red teamers | one subagent per round and area, mid model | one subagent per round covering all areas | you, in a fresh context per round, after committing the code under attack |
| Falsifier | Codex or another model family, fresh context, strong model | a Claude subagent with the falsifier prompt | self-review with the prompt in a fresh context, labelled "self-review" |
| Advisor | the strongest model available, fresh context | skip and say so | - |
| Judges | Workflow tool fanning out small-model agents over chunks (prompts in references/prompts.md §Judge and §Optimiser) | a script calling the API with a cheap model and the verdict cache | the builder judging a sample by hand is NOT acceptable for scored data |
| Optimiser | mid model agent per iteration | you, following the optimiser prompt literally, on TRAIN only | - |
| Candidates | Workflow fan-out, one agent and one git worktree per candidate (references/improve.md) | subagents one after another, one worktree each | the builder builds each in turn from the same base; say so |
| Safety bank writer | the domain owner (sealed side: wrote no readable seeds), or a writer the owner briefed and whose sample the owner reviewed | a fresh writer with the FRAME.md list, no owner review; report "no domain owner" | - |
| Targeted-bank writer | a fresh writer, set-up not used before, briefed on the cell only | a fresh subagent with the targeted-bank prompt | - (without one, the mechanism route is closed) |
| Mid-cycle prober | a fresh context, mid model, writing hard cases in the top miss kinds | the user runs the prober prompt in another tool | - |
| Readiness reviewer | a strong model in a fresh context running a review skill, or the checks in references/readiness.md | the user runs the review in another tool | self-review in a fresh context, labelled; it cannot clear a Blocker |
| Trace adjudicators | two people from the domain (safety slice), one elsewhere | one person plus a calibrated judge for non-safety slices | the builder: not acceptable for labels that gate a stage |
| Operator | a named person who owns the off switch and the live guardrails | the domain owner doubles | none: no autonomous stage without one |

Rules of thumb
- Bulk reading and writing (writers, judges, red-team attack generation) → cheapest model that follows the format. Verdict format violations are abstentions, so a cheap judge fails safe.
- Judgement about code (falsifier, advisor, fixer) → strongest model available.
- Give every helper the sealed paths it must not open and a scratch folder outside the repo. Repeat it in every prompt; helpers do not inherit your context.
- No subagents at all: the sequence still works, slower; independence claims weaken; the ledger still makes the holdout protocol auditable.
- Workflow tool present: use it for the judge fan-out and the hill-climb (parallel batches, one optimiser per iteration, structured result); keep the script in `prompts/build-team/`.
- Codex: install as `~/.codex/skills/auto-evolve-agentic-system/` with the same SKILL.md; scripts are stdlib Python 3.10+; nothing in SKILL.md names a Claude-only tool.
- Who may read what: the builder reads dev and TRAIN; writers read the dev keys only; nobody on the build side reads SELECT, CONFIRM, safety, holdout or final contents (references/data-discipline.md).
