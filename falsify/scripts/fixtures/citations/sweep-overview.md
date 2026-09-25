# Sweep overview — toy hash table, five rounds

Table size doubled each round from 1024 to 16384. Numbers below are pulled straight
from each round's result file; see `rounds/` for the run notes.

- Round 1 (results/r01.json): collision rate 0.081, throughput 412.5 MB/s.
- results/r01.json also reports throughput of 412.5 MB/s at a mean probe length of 1.23.
- Round 2 (results/r02.json): collision rate 0.047, throughput 398.2 MB/s.
- results/r02.json also reports a memory footprint of 128 KB.
- Round 3 (results/r03.csv): collision rate 0.026, table size 4096.
- results/r03.csv also reports a mean probe length of 1.05.
- Round 4 (results/r04.json): collision rate 0.014, throughput 389.9 MB/s.
- results/r04.json also reports a memory footprint of 512 KB.
- Round 5 (results/r05.csv): collision rate 0.008, throughput 371.4 MB/s.
- results/r05.csv also reports a memory footprint of 1024 KB.

Two follow-ups are queued but not yet run:

- Follow-up planned against results/r06.json once the next table size is collected.
- Archived pre-sweep baseline at results/archive/r00.csv for comparison, once it is
  pulled out of cold storage.

The nightly batch job globs results/*.csv for the CSV rounds only; the JSON rounds
run through a separate importer (`bench.metrics.summarize()`), version v1.4.2 of
the hashing library used throughout. A public mirror of round 1 lives at
https://example.org/bench/results/r01.json for anyone without repo access.
