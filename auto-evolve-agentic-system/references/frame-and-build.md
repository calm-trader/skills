# Frame and build (phases 0 and 1)

## Phase 0: FRAME.md

1. **What and for whom.** What the system does, for whom, its inputs (channels,
   repositories, sources or request types), tools, external systems (to be mocked), and
   the agent kind's words: systems of record, steps, cluster slots, how an episode is made
   (references/runtime-adapters.md, Words). Then three lists: what it must **never** do;
   what must happen **exactly once**; what must **always** reach a person or a safe stop.
   Name the must-escalate, must-refuse, irreversible-effect and harm-signal items
   (references/safety.md, Words). Name the expert panel, split into seed side and sealed
   side, and the domain owner, or write "model personas, no human expert"; collect seed
   cases and personas from the seed side only (references/data-and-experts.md).
2. **Invariants.** Turn every never, exactly-once and always into a named invariant,
   checked from the systems of record or an evidence ledger, never from the agent's own
   report. Aim for 6 to 12. Include rule S1 (references/safety.md) for every system that
   has an "always reaches a person".
3. **Metric.** An episode passes only if every check passes, and every check reads systems
   of record: effects, handoffs, sent replies, CI results, output tables, published
   artefacts (your kind's row in the Words table). This records count is the headline.
   The agent's own record of intent or status is a diagnostic, reported beside it. Report
   per segment (for example routine, high-risk writes, access, safety; name your own):
   autonomous success, correct
   handoff, correct refusal, wrong action. Every failure gets a severity class, and wrong
   actions are broken down by effect type (payment, write, send, delete, merge ...).
4. **Safety target, signed.** With the domain owner, set a safety recall target and a
   false-alarm ceiling, and size the safety bank for them (`noise.py --need RATE`: zero
   misses in 40 only shows the miss rate is below 7.2%). Without an owner, write "no
   domain owner: targets set by the builder" at the top of FRAME.md.
5. **Budgets.** Time and spend per track (accuracy, safety, operations; 60/30/10 after
   round 0 is a starting point), K and the spike cap, look budget per sealed bank, cost
   per episode, p95 latency, model tier per role, wall clock. No fixed round count
   (SKILL.md, Stop rule).
6. **Settings.** Write these as FRAME.md settings, starting from the defaults; change
   them with a reason, before any result:

   | Setting | Default |
   |---|---|
   | writer set-ups across sealed banks | at least 3 |
   | SELECT pool | at least 3 banks from 3 set-ups |
   | fresh TRAIN swarms (writer set-ups) per cycle | at least 2 |
   | steps of the episode and cluster slots (set per agent kind) | the Words table row |
   | distinct clusters per later-step key / per first-step key (set per agent kind) | 30 / 12 |
   | failing clusters for SELECT to "see" a cell | 8 |
   | not-worse margin (mechanism route) | 1% of pooled SELECT episodes |
   | targeted bank size | 200 episodes in the target cell |
   | wear thresholds (runs, any purpose): select, safety gate, confirm | 20, 12, 2 |
   | distinct clusters per slot needed for a not-worse test | 20 (fixed in `noise.py`, which says "phrasings") |
   | who may raise a look budget (`--approved-by`) | the runner or the domain owner |
   | unaddressed-cell share that keeps a cycle going | 10% of TRAIN failures |
   | holdout age before "stale" | two quarters |
   | swarm near-duplicate threshold / human sample size / error bar (upper 95% bound) | 0.8 / 150 / 5% |
   | drift alarm (PSI) | 0.2 |
   | safety-relevant paths (for the falsifier-commit check) | list them |

7. **Day-one basics** (the readiness review must not be the first to find these):
   - a CI config that runs `make check` on every change (a Makefile comment is not CI);
   - one tested switch that turns learned parts off, and one that sends everything to
     people;
   - the owner table: domain owner, queue owners, operator, with "not named" where true;
   - cost and latency budgets.
8. **Profile.** **Full**: everything. **Lite**: one holdout, one red-team round, falsifier
   as self-review, sequential improvement; every report says "lite: weaker evidence". The
   safety bank, rule S1 and readiness are in both.
9. **Layout.** One folder or one tag per version; one commit per version either way.
10. **Carry forward** (entry point B). Name the earlier run, its best version and what is
    carried over (code, rules, banks as TRAIN). If you restart from V1, say why and list
    what was left behind (references/improve.md step 0).
11. Advisor review of FRAME.md (references/prompts.md, Advisor).

## Phase 1: lean V1, simulator, probes, negative controls

1. **Lean path first.** One scenario end to end through the real architecture (typed
   tools, policy guard, ledger, reply path, atomic commit). Every limit, permission and
   eligibility rule is enforced inside the tool handler or service, on the arguments it
   executes and on state it reads at execution time. Workflow code and models may
   propose; they never enforce. Identity comes from outside the agent process as a token
   the gateway verifies; the agent never builds its own principal or holds signing keys.
   Then widen to all scenarios.
2. **Deterministic and offline.** Keep the understanding layer swappable: rules, or an LLM
   behind a hash-keyed verdict cache (`verdict_cache.py`). No network in `make test` or
   `make simulate`. Inject time, randomness and ids: no date constant in agent code, and a
   test moves the clock across every time rule.
3. **Simulator** = generator (a world plus N episodes with expected outcomes) + runner
   (plays the counterpart or the environment; injects timeouts after commit, retries,
   crashes, duplicate delivery, concurrent inputs) + evaluator (reads systems of record
   and the ledger; checks every invariant; writes per-episode pass maps, cluster files (episode →
   cluster per slot) and segment files for dev, TRAIN and selection banks, all into the
   runner's store for sealed banks; never prints sealed failures). Each sealed bank's
   manifest lists the evaluator, judge prompt and simulator files (`"evaluator"`), and
   every sealed run passes exactly those to `seal.py run --fingerprint`, so an evaluator
   change cannot pass for a gain. The evaluator writes a flat report `{passed: N}` to
   `$SEAL_REPORT` and pass maps into `$SEAL_OUTPUT_DIR`; nothing per item in the report.
   The counterpart also misbehaves (a user changes their mind, goes silent, sends two
   topics at once; a repository has flaky tests; a source sends a late or partial file; a
   search returns nothing); it never branches on the agent's exact wording.
   Check each mock against the real contract or logged cases, or report "mock fidelity:
   not checked". Every decision's evidence records the policy, prompt, model and
   data versions; the evaluator fails an episode whose evidence lacks them.
4. **Enforcement probes.** Call each write tool directly, bypassing the agent, with
   arguments that break a rule: a declared amount under the cap with an executed amount
   over it, an ineligible record, another account's id, a weaker principal. The service
   must refuse each one; a probe that executes is a critical finding.
5. **Negative controls.** One run per safety layer with that layer removed, including the
   S1 gateway hold; the invariants must catch the damage. A control that still passes
   means the invariant is vacuous: fix it first (references/gates.md, recipe).
6. **Gates** for V1 and every later version: references/gates.md.
7. **Make targets** everywhere (list in references/gates.md). `simulate` runs dev, probes
   and controls only, never a sealed bank. `check` adds the ledger, findings, cache and
   docs checks.
8. **Falsifier** review of the simulator before the agent exists, then of V1. Fix. Then
   "falsify the fixes".
9. **First swarm.** Seed-side expert cases become dev; the first writer swarm, with its
   dedupe, oracle check and human-checked sample, is sealed as role `train`
   (references/data-and-experts.md).
