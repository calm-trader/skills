# Fair comparison of two versions, runs or systems

Use this whenever two numbers are put side by side that did not come from the same
episodes: an earlier run against this run, a vendor system against yours, the old version
against a component swap. "A scored 91%, B scored 81%" on different banks says nothing
about A and B; it may only say the banks differ.

## Procedure

1. **Fresh sealed banks neither system has seen.** At least 2 banks from 2 writer set-ups
   that neither system trained on, chose on or was error-analysed on. Write and seal them
   for the comparison (`--manifest`, `--looks` counting every system you will run).
   Check each system's training manifest for the bank names (`compare.py` refuses
   otherwise).
2. **Same harness.** Same simulator, same seeds, same evaluator version, same metric
   (systems of record). Run the other system through your harness, not its own scorer.
   Check the harness first: it must reproduce the other system's own reported score on
   its own banks.
3. **Every system scored once per bank**, each run a logged look:
   `AGENT=earlier seal.py run cmp_a --version V5 --system earlier-run --purpose compare --env AGENT --fingerprint <evaluator files> --output cmp_a.json -- make bank-cmp_a`
   (the command writes the map to `$SEAL_OUTPUT_DIR/cmp_a.json`; the runner copies it into
   the system's maps folder).
   Pass every variable that selects the agent with `--env`, or two agents on one tree look
   like one version and the second run is refused. `compare.py --ledger` verifies the
   ledger's chain and mirror and checks that each system has exactly one clean run per bank
   (ok, exit 0, purpose compare, not forced, not dirty) whose `--output` hash matches the
   map used, and that every run used the same evaluator fingerprint. The runner keeps the pass maps and runs
   `compare.py`; the builder gets the printed tables.
4. **Paired, per segment, cluster-aware.** Report B, C, net, interval and p, per bank and
   pooled, and the per-segment table. A total can hide a segment loss.
5. **Common-baseline row.** Run the common ancestor (often V1) on every bank. If it scores
   the same everywhere, the banks are equally hard and the differences belong to the
   systems. If not, compare within a bank only.
6. **Transfer table.** For each system: its gain over the baseline on its own holdouts,
   and on the fresh banks. Transfer share = fresh gain / own gain. The rest is
   familiarity with its own writers.
7. **Wording.** Never "A scored 91, B scored 81". Always: "On the same N fresh episodes
   from W writers: A x, B y, paired difference d (interval), by segment ...".
   `compare.py` prints this sentence.
8. **A sealed bank's segment counts, once reported, are spent.** New claims need new banks.

## Command

```
python3 tools/compare.py --a earlier runs/cmp/earlier/ --b current runs/cmp/current/ \
    --base V1 runs/cmp/v1/ --clusters runs/cmp/clusters/ --segments runs/cmp/segments/ \
    --train-manifest-a earlier-train.json --train-manifest-b current-train.json \
    --own-a N_OWN V1_ON_OWN EARLIER_ON_OWN --own-b N_OWN V1_ON_OWN CURRENT_ON_OWN --markdown
```

Each folder holds one pass map per comparison bank (`<bank>.json`). A training manifest is
exactly `{"system": NAME, "banks": [ledger bank names], "files": [{"path": P, "sha256": S}]}`:
what that system trained on, chose on or was error-analysed on. It needs `--ledger`: every
bank must be in the ledger (its file hashes and writer set-up come from there, so a
renamed copy is caught), and every file must exist and hash as given. Unknown banks, other
shapes, another system's name or an empty manifest are refused. Without both manifests
the sentence says freshness was not checked. A pooled "reliable" difference (the cluster
test) is kept only if it points the same way on 3 distinct writer set-ups (the banks'
manifest `writer_setup` in the ledger, else `--writers`); that agreement is described,
not tested. `--in-sample`
prints such banks as "in-sample, not comparable" and leaves them out of the pooled result.

## Report table (paste into STRATEGIES.md and CYCLES.md)

| Bank (writer set-up) | Episodes | Phrasings | Baseline | A | B | B (only A) | C (only B) | Net | Interval | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|

| System | Gain on own holdouts | Gain on fresh banks | Transfer share |
|---|---|---|---|

## Common mistakes

- Comparing each system's score on its own holdouts.
- Scoring the other system once on your holdouts without logging it as a look.
- Re-using banks one of the systems trained on, because "they were the earlier run's
  holdouts".
- Reporting the strict count for one system and the records count for the other.
- Quoting the pooled total without the segment table.
