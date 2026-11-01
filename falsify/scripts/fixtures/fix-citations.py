#!/usr/bin/env python3
"""Patch the 3 planted defects in a copy of fixtures/citations/, for selftest.sh's clean-copy
check: fix-citations.py DIR fixes DIR/sweep-overview.md and DIR/rounds/round-03.md in place and
adds the two missing result files, so a clean run of check_citations.py against DIR exits 0.
"""
import os
import sys

DIR = sys.argv[1]

os.makedirs(os.path.join(DIR, "results", "archive"), exist_ok=True)
with open(os.path.join(DIR, "results", "r06.json"), "w", encoding="utf-8") as f:
    f.write('{\n  "round": 6,\n  "table_size": 32768,\n  "collision_rate": 0.004,\n'
            '  "throughput_mb_s": 352.1,\n  "mean_probe_len": 1.00,\n  "memory_kb": 2048\n}\n')
with open(os.path.join(DIR, "results", "archive", "r00.csv"), "w", encoding="utf-8") as f:
    f.write("metric,value\ntable_size,512\ncollision_rate,0.140\nthroughput_mb_s,420.3\n"
            "mean_probe_len,1.31\nmemory_kb,32\n")

path = os.path.join(DIR, "rounds", "round-03.md")
text = open(path, encoding="utf-8").read()
fixed = text.replace("415.7 MB/s", "405.7 MB/s")
assert fixed != text, "the wrong number was not found to fix"
open(path, "w", encoding="utf-8").write(fixed)
