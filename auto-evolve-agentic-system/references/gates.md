# Gates and negative controls

Statistics (intervals, paired tests, clusters): references/statistics.md.

## The gate every version passes before a sealed look

| Gate | Command | Pass |
|---|---|---|
| Lint | `make lint` | clean |
| Tests (incl. red-team, panel, falsifier, review and incident reproductions) | `make test` | all pass |
| Dev, clean and under faults (timeouts after commit, retries, crashes, duplicate delivery, races) | `make simulate` | the FRAME.md bar, invariants all hold |
| Dev, 3 or more seeds | `make simulate SEEDS=...` | every seed at the bar; pass^k for write episodes reported |
| Negative controls, the S1 gateway hold included | `make simulate` | invariants CATCH the removed layer's damage |
| Enforcement probes | `make probes` | every probe refused by the service |
| Safety gate bank | `seal.py run saf_x --purpose gate ...` | no new miss against the base; misses by kind printed; at or above target, or the gap reported |
| Headline on records | `make docs` | README, IMPROVEMENTS and STRATEGIES headline the systems-of-record count; the agent-label count appears only beside it |
| Coverage map and taxonomy fresh | `make coverage` | `docs/coverage.json` and `docs/failure-taxonomy.md` newer than the newest TRAIN bank |
| Swarm data checked | `make swarm-check` | every TRAIN swarm has a manifest with dedupe counts, oracle results and a human-checked sample whose upper 95% error bound is under the FRAME.md bar (references/data-and-experts.md) |
| Falsifier reviewed the last diff | `make falsifier-check` | the commit in FINDINGS.md equals HEAD for the FRAME.md safety-relevant paths |
| Cost and latency | `make cost` | cost per episode and p95 latency within FRAME.md budgets |
| Shipped verdict cache holds no sealed keys | `verdict_cache.py overlap judge_verdicts.json <sealed request files>` | no overlap |
| Findings traced | `make findings` | every critical and high row names a passing test |
| Red-team corpus replay, clean and under faults | `make redteam` | all pass; a person reached whenever expected |
| SELECT counts | `{banks command}` | not below previous minus margin (`noise.py --paired-maps --not-worse`), or the drop explained by kind |
| Ledger | `seal.py verify --require-mirror && seal.py refs --allow ... && seal.py wear` (CI runs as the runner, with `$SEAL_MIRROR` and `$SEAL_RUN_DIR` it owns) | clean: hashes unchanged, hash chain intact and matching `$SEAL_MIRROR` (set, outside the repository), no stray references, no worn, over-budget, burned or expired bank |
| Evaluator unchanged | every sealed run passes `--fingerprint` with exactly the manifest's `evaluator` files (else refused); `seal.py statement` | no bank flagged "Rescore the base"; an evaluator change rescored the base before any comparison |
| Docs freshness | `make docs && git diff --exit-code docs prompts README.md STRATEGIES.md` | clean; README and STRATEGIES no older than the last version commit |

## Cheap gate (spikes and candidates)
Lint, tests, dev bar clean, red-team corpus, safety gate counts. Full gates run on stacked
versions only.

## Negative controls, recipe
1. List the layers that make a guarantee hold (input dedupe, idempotency key, the
   downstream transaction, a ledger cap, branch protection, the quarantine step, the S1
   gateway hold).
2. Add a runner flag that disables one layer, and one that disables two.
3. Run dev with the flag. Expect: pass count drops AND the relevant invariant reports
   violations.
4. If the invariant stays green with the layer off, it is vacuous: rewrite it to read the
   systems of record directly.
5. Keep every control in `make simulate` forever; print its row in the README results.

## Make targets (same names in every system)
`test`, `lint`, `simulate` (dev + probes + controls), `probes`, `findings`, `coverage`,
`swarm-check`, `falsifier-check`, `cost`, `safety` (only through `seal.py run`),
`holdout-1`, `holdout-2` (only through `seal.py run`), `redteam`, `banks` (TRAIN and SELECT
counts and maps), `docs`, `check` (lint, test, probes, redteam, findings, coverage,
swarm-check, falsifier-check, cost, seal verify, seal refs, seal wear, verdict-cache
overlap, docs freshness).
