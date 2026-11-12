# Data discipline (phase 2)

Write the holdouts and the safety bank right after the dev bank, before anything is tuned,
and seal them before any result exists. Tick every line before a sealed look.

## Who wrote what, who may read what

| Data | Who wrote it | Builder reads | Used for |
|---|---|---|---|
| dev | builder | yes | rules, training, dev gate |
| TRAIN | seed-side expert cases and writer swarms (one swarm = one set-up); at least 2 new swarms per cycle (references/data-and-experts.md) | yes | error analysis, training, prompt hill-climb, coverage map |
| SELECT (pool of at least 3) | fresh writers, 3 set-ups; retired CONFIRM banks join | counts and the runner's paired summaries | choosing between candidates |
| CONFIRM | 2 fresh writers per cycle | counts only | one paired test per cycle: the cycle's claim |
| targeted bank | a fresh writer briefed on one cell, after the candidate froze | counts only; the runner prints the paired result | the mechanism route, run once per system |
| TUNE | fresh writers, after the tuned version froze | counts only | tuning objective; after the tuning decision it is retired to train and joins the refit |
| SAFETY gate | domain owner (sealed side, wrote no readable seeds), or a writer the owner briefed | counts only (misses by kind) | the safety gate, every candidate and version |
| SAFETY final | as above, a different writer | counts only | once, on the final version |
| gold slice | two people from the domain label 100 to 200 episodes | read | label agreement; checking the generator's labels |
| HOLDOUT (2 or more) | independent writers given only `schema.json` (below), never a dev example | never | one score per budgeted look |
| FINAL | independent writer | never | once ever |
| production holdout | sealed by someone other than the builder (references/continuous.md) | never | live-era claims |
| red-team corpus, incidents | red teamers, real incidents | yes | gates and regression suite, never a holdout |

`seal.py` still accepts the older role `validation`; it means a SELECT bank.

## Writer set-ups

- A writer set-up is the brief, its author, the persona, the model (family) and the week.
  Two banks from one set-up are one writer for statistics (references/statistics.md).
- At least 3 set-ups across the sealed banks. Holdout set-ups differ from TRAIN set-ups
  in persona, brief author and, where possible, model family and date.
- Writers prefer a different model family from the builder; say which was used.
- The writer prompt states minimums per key, in distinct clusters (phrasings for an
  operations agent; repositories, sources or templates for other kinds): at least 30 per
  later-step key (a reply, a confirmation, a second file, a follow-up), 12 per first-step
  key, and asks the writer to report the distinct clusters per key (references/prompts.md,
  Writer). FRAME.md may set other minimums per agent kind.
- One swarm is one writer set-up, however many contexts it runs.

## Before writing banks
- [ ] The schema is fixed: keys, placeholders per key, which are mandatory, the meaning of
      each key in one sentence. It is generated into `schema.json` (keys, placeholders,
      meanings, no example text). Writers of sealed banks get that file only; they never
      open a dev or TRAIN entry, which would seed the same phrasings.
- [ ] A generation check fails on a missing placeholder or an unknown key; the writer runs
      only that.
- [ ] Every writer gets a persona. Holdout personas differ from TRAIN personas.
- [ ] Writers run in fresh contexts and are told what they may not open: agent code,
      tests, red team, other banks, results, data folders, runs.

## Sealing
- [ ] `seal.py init` once; per bank `seal.py seal NAME --role ROLE --writer "..."
      --manifest M.json [--looks N] [--expires DATE] FILES`. A holdout needs `--looks`
      before it can run; count the baseline, every head you will score and any comparison
      system (`seal.py budget` changes it, logged).
- [ ] The manifest holds episodes, phrasings per key, segments, writer set-up, source
      (synthetic, production, incident) and period. Without it the report says
      "phrasings: not recorded" and every interval is too narrow by an unknown amount.
- [ ] `seal.py gitattributes` lines added; ledger committed with the banks.
- [ ] Sealed files have distinctive names; `seal.py refs` and `seal.py wear` are in
      `make check`.
- [ ] Scoring tools refuse to print failures for sealed banks; phrase-level debugging tools
      refuse them entirely; `simulate` runs dev and controls only.
- [ ] Judge requests for sealed banks carry scrubbed inputs only; verdict files hold
      `{key, verdict}` only; nobody reads the requests.
- [ ] Full profile: holdouts kept outside the builder's repository and run by someone else
      (`SEAL_RUNNER` names who). If real traffic exists, a de-identified sample of it is
      the best holdout.

## One ledger, owned by the runner

**What the scripts cannot do.** `seal.py` runs on a machine. A builder who can write the
ledger, the mirror, the run folder or the scripts themselves can fake any record, and no
check inside the script stops that. Every guarantee here holds only when the runner (a
person or service other than the builder) owns `$SEAL_MIRROR` and `$SEAL_RUN_DIR`, keeps
the sealed banks, and runs every sealed look; the builder gets read access to the ledger
and the printed results. `seal.py run` enforces the configuration it can see: a run on a
sealed bank is refused unless `$SEAL_MIRROR` and `$SEAL_RUN_DIR` are set and outside the
builder's tree (the ledger's folder, `--root` and their git top levels). Who owns those
paths it cannot check: say who does in FRAME.md. When the builder and the runner are the
same account, the report says so and calls every sealed number "self-run".

The evaluated code is the second gap. It runs with the runner's rights, so it could
undo the read-only mode of the bank files, or swap an evaluator file and restore it,
and the hashes after the run would match. `seal.py` re-hashes the bank and the evaluator
files after every run (a cheap check that catches a careless change), but only the setup
stops a careful one: run the evaluated program as a separate unprivileged user, or with
the banks and the evaluator on a read-only mount, and let the runner (not the builder)
write each bank's manifest, including its `evaluator` entry point list. The scripts
cannot enforce this; without it, the report says "self-run".

- One ledger per system, written only through `seal.py`, owned by the runner (the person
  or service that runs sealed banks). The builder may read it, never edit it.
- Set `$SEAL_MIRROR` to an append-only file outside the repository that the builder cannot
  rewrite, and `$SEAL_RUN_DIR` to a runner-owned folder outside it. Sealed runs refuse
  without both. Run `seal.py require-mirror` once (or `init --require-mirror`) so every
  other change refuses without the mirror too. CI runs `seal.py verify --require-mirror`,
  which catches hand edits, a rewound ledger and a side ledger. Every write checks the
  chain first, and a ledger whose chain is missing is refused, so a normal command never
  turns a hand edit into a valid chain. A ledger from an older `seal.py` gets a chain only
  through `seal.py migrate --approved-by NAME`, and `statement` says its earlier history is
  taken on trust.
- Seal TRAIN and dev banks into the ledger too (roles train, dev), so `seal` can refuse a
  "fresh" bank that repeats readable text. `seal` compares records (JSON strings, quoted
  strings, else lines; case and punctuation ignored, any length) over all the new bank's
  files together, and refuses any record shared with a sealed bank, or shared with a
  readable bank when sealing a sealed one. Records every bank shares by design (schema
  keys, placeholders, answer labels) go in the common list once: `seal.py common
  schema.json --reason T`.

## What every sealed run records (config fingerprint)

`seal.py run` stores the commit, command, runner, the values of `--env` variables (pass
every variable that selects an agent, model or mode) and the sha256 of the evaluator, judge
prompt and simulator files. A sealed bank's manifest fixes that list (`"evaluator": [...]`),
and every sealed run must pass exactly those files with `--fingerprint`, or it is refused. `statement` flags a bank whose
scored runs used different evaluator files: rescore the base with the current evaluator
before comparing, or an evaluator change reads as a gain. The evaluator's report adds, and
the runner keeps beside the score: model and provider version, a hash of every runtime
prompt, judge model, seed. A score without a fingerprint is not quoted.
The score comes from a flat report `{name: whole number}` the command writes to
`$SEAL_REPORT`, in a fresh runner-owned folder per run, read at `--key`: from 0 to the
manifest's episodes (required), or the run gets no score. A report holding any text, list
or object is refused, and the file is deleted once the score is read. Pass maps go to
`$SEAL_OUTPUT_DIR` (`--output NAME`), in the same fresh folder, hashed into the record.
The sealed files are read-only during the run and hashed again after it; a command that
changed them burns the bank.

## Storage, retention and access for sealed outputs

- Sealed bank files, their pass maps, per-run verdict caches and captured output live in
  the runner's store, outside the builder's tree, readable by the runner and the reviewer.
- The builder receives counts, segment counts and the printed results of `noise.py` or
  `compare.py`. This holds for SELECT too: its pass maps stay with the runner, who runs
  `noise.py` and hands over the paired summary. Anything per item is a probe.
- Keep pass maps until the bank is retired to train (they are needed for later paired
  tests and audits); delete per-run verdict caches after the run. Record who accessed a
  sealed store; access outside the runner role is logged with `seal.py probe`.

## Looks, taint, burns and wear
- Every `seal.py run` is a look, whatever its purpose, system or the bank's role at the
  time: retiring a bank never resets its count. A run over budget is refused. On select,
  tune and validation banks `--force --reason` logs OVER BUDGET; on holdout, confirm,
  final and safety banks nothing overrides a refusal. A safety bank's default budget is 12.
- A bank's manifest and expiry freeze at its first run; a correction is a new bank.
- Wear is a ceiling (select 20, safety 12, confirm 2, validation 20 runs): no budget,
  approval or `--force` raises it.
- Per-item information leaving a sealed bank (an id, which signals fired on one item, a
  per-item score) is a probe: `seal.py probe NAME --items N --reason T`. The bank is
  tainted; on a holdout, confirm or final bank it is burned.
- A burn: `seal.py burn`, then `seal.py retire NAME --to train`, and a fresh writer seals a
  new bank. No bank is ever retired into holdout, safety, confirm or final.
- Life cycle: fresh → sealed → looks spent (clean) → retired to select → runs spent →
  retired to train. A tainted or burned bank goes straight to train. Never the other way:
  `retire` refuses any readable bank (dev, train, other) into a sealed role. `seal.py wear`
  flags each step; a bank at its wear threshold is a breach until retired.
- Raising a look budget needs someone other than the builder: `seal.py budget NAME --looks
  N --reason T --approved-by NAME`. Lowering does not.
- `--purpose` is declared by whoever runs the command; the ledger records it but cannot
  check it. That is why budgets and wear count every run.
- A bank's segment counts, once reported, are spent for new claims about those segments.

## During a cycle
- [ ] Every fix, feature or prompt edit cites a TRAIN failure, a red-team finding, a
      review finding or an incident.
- [ ] Training sets are listed by name in code (`TRAIN_BANKS`); no sealed bank in them
      (the falsifier checks). Refit on all TRAIN banks; a list pinned to an older set is a
      finding unless FRAME.md says why.
- [ ] Holdout verdicts in a per-run cache, deleted after the run; `verdict_cache.py
      overlap` clean.
- [ ] The report's data-discipline section is `seal.py statement --markdown`, pasted.

## Production data (once live traffic exists)
De-identify first. Split by rule before anyone reads it: hash accounts (or repositories,
or sources) once into holdout accounts and TRAIN accounts, disjoint across all periods.
The production holdout is a separate uniform random sample of holdout accounts' episodes
from the most recent period, never the oversampled adjudication sample; if it must be
stratified, store the strata in its manifest and analyse each stratum on its own (the
scripts take no weights; never pool strata as one sample). Sealed
by someone other than the builder (`--manifest` source `production`). A case is never in
both. Incident texts from TRAIN accounts go to TRAIN and the regression suite; from holdout
accounts, to the regression suite only, or the holdout is burned. Never to a holdout. Details: references/continuous.md.

## Known weaknesses to state in every report
- SELECT, TUNE and the safety gate bank were used to choose. Reused holdouts are biased
  too: their scores were shown each cycle and helped decide when to stop. Only the final
  bank and the final safety bank back an unbiased claim.
- How many looks each holdout had (from the ledger), and which systems they covered.
- Writers or swarms share a model family with the builder (if they do); how many writer
  set-ups.
- The expert panel was model personas, not people (if it was); the swarm sample was
  checked by a persona panel, not a person (if it was).
- Expected outcomes were written by the builder's generator, unless a gold slice was
  labelled by people from the domain.
- Holdouts kept in the builder's repository can be read; only fresh contexts and the
  ledger stand in the way.
