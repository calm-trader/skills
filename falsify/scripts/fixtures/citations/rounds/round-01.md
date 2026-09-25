# Round 1: table size 1024

Baseline run of the toy hash at the smallest table size in the sweep.

- Collision rate came in at 0.081 (results/r01.json).
- Throughput measured 412.5 MB/s, see results/r01.json.
- results/r01.json puts the mean probe length at 1.23.
- Memory footprint: 64 KB per results/r01.json.

Carried forward to round 2 without changes to the hash function itself.
