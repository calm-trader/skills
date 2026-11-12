#!/usr/bin/env python3
"""Noise margin for pass counts, so a gain inside the noise is not called a win.

Counts only:
    noise.py N PASSED                 # 95% Wilson interval of one count
    noise.py N PASSED_A PASSED_B      # two frozen versions on the same bank, unpaired:
                                      #   Fisher exact test when N <= 200, else a z test
    noise.py N PASSED ... --clusters M  # episodes rendered from only M distinct phrasings
    noise.py --paired B C [--of K]    # McNemar: B passed only in A, C passed only in B
                                      #   (exact binomial when B + C < 25); Bonferroni 0.05/K
    noise.py --need RATE              # episodes needed, with zero misses, to show the
                                      #   miss rate is below RATE (e.g. 0.01)
    noise.py --mde N --clusters M --base-rate P [--churn D] [--of K]
                                      # smallest gain a bank of N episodes over M phrasings
                                      #   can show in a paired test, at 0.05 (and Holm with K)

Pass maps (cluster-aware; use these where choices are made):
    noise.py --paired-maps BASE CAND [--clusters C] [--segments S] [--not-worse MARGIN] [--of K]
                           [--cells CELLS --cell NAME] [--ledger L [--cycle N]] [--writers W]
    noise.py --family-maps BASE CAND [CAND ...] [--clusters C] [--segments S]
    noise.py --family BASE CAND ...   # old name of --family-maps; warns without --clusters
    noise.py --visible BASE --cells CELLS [--clusters C] [--min-phrasings 8] [--slot NAME]

A pass map is a JSON file {episode id: true/false} over the whole bank, or a directory of
such files, one per bank; then ids become "bank:episode" (bank = file stem) and results are
also printed per bank. --ledger L reads each bank's writer set-up from the verified
ledger (its manifest's writer_setup); --writers W ({bank: writer set-up}) works too and is
printed as not verified. "Reliable" comes from the pooled cluster test only; writer
agreement is described ("same direction on 3 of 3 writer set-ups"), never tested, and a
pooled gain is kept only when 3 distinct set-ups point its way (else "not reliable across
writers"). One bank reads "reliable gain (one writer set-up)". --clusters, --segments and --cells take a file (ids as in the
pooled map) or a directory with the same file stems.

--clusters (a file or directory) maps each episode to the phrasing it was rendered from:
    "e1": "yes_03"                              one phrasing slot
    "e1": {"opening": "o_12", "reply": "y_03"}  several slots (a list works too)
In a directory, phrasing ids are taken per bank. Every episode must name every slot with
a non-empty id, or the command stops (exit 2). Episodes that share a phrasing pass or
fail together, so they are one cluster, not many trials. The test is a sign-flip
permutation test over clusters: each cluster's net (passed only by CAND minus passed only
by BASE) keeps or flips its sign. Its exact distribution is computed when that is cheap and
estimated from 10,000 seeded draws otherwise. The interval for the net is a 95% cluster
bootstrap (2000 seeded draws). With several slots each slot is tested on its own and the
widest result is reported, with the slot named: approximate, and on the cautious side.
Without --clusters every episode is its own cluster: the test is then an exact sign test,
the same as an exact McNemar test.

--not-worse MARGIN (needs --clusters) is a one-sided test of "the candidate is worse by
MARGIN or more": the cluster nets, plus one pseudo-cluster that lost as much as the largest
cluster that moved, are sign-flipped; it passes when the observed net + MARGIN is reached
by under 2.5% of flips, on every phrasing slot, and every slot has at least 20 phrasings.
Fewer phrasings cannot show "not worse": one phrasing flipping is then too large a share.
MARGIN is a whole number of episodes (10) or a share with % (1%); above 2% of the
episodes it needs --wide-margin. With --segments every segment is tested too, with the
margin pro rata, and any failure fails. --of K tests at 0.025/K. Exit 1 when it fails.
--cells CELLS --cell NAME tests the gain on that cell's episodes only and --not-worse on
all the others (the mechanism route's targeted bank). It needs --ledger L --cycle N, the
open cycle from `seal.py cycle open --of K`: every threshold is 0.05 / K / 2^N, each test
uses one of the cycle's K (recorded in the ledger), and an older cycle is refused, so the
false keeps over all cycles sum to at most 0.05. Per-bank and per-segment verdicts use the
same corrected threshold. Every episode needs a non-empty segment or cell label, or exit 2.
Every episode in the maps must have an entry in --clusters, or the command stops.

--visible lists, per cell (a cells file maps episode -> cell, e.g. "writes/reply"), the
base's failures and its distinct failing phrasings. A cell with fewer than --min-phrasings
(default 8) failing phrasings is flagged: this bank cannot see a fix there.

Honest limit: with one writer, no test can say anything about new writers. The cluster
test only stops phrasings from being counted as independent episodes. Pool at least three
writer set-ups, and still never call a gain general: three writers cannot be tested.

--clusters M with counts (not a file) scales the margin by the design effect
sqrt(N/M), a rough upper bound; with --paired it is only noted, because McNemar counts
episodes: use --paired-maps with a clusters file for the real correction.

Standard library only, Python 3.10+. Binary pass/fail per episode.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from pathlib import Path
from statistics import NormalDist

Z = 1.959964  # 95%
ALPHA = 0.05
DRAWS = 10_000      # sign-flip draws when the exact distribution is too large
BOOT = 2000         # cluster bootstrap draws
SEED = 0
EXACT_LIMIT = 5_000_000
USAGE = ("usage: noise.py N PASSED [PASSED_B] [--clusters M]\n"
         "       noise.py --paired B C [--of K]\n"
         "       noise.py --paired-maps BASE CAND [--clusters C] [--segments S] [--not-worse M --clusters C] [--of K]\n"
         "       noise.py --family-maps BASE CAND [CAND ...] [--clusters C] [--segments S]\n"
         "       noise.py --visible BASE --cells CELLS [--clusters C] [--min-phrasings 8]\n"
         "       noise.py --mde N --clusters M --base-rate P [--churn D] [--of K]\n"
         "       noise.py --need RATE\n"
         "  N > 0 episodes, 0 <= PASSED <= N, 1 <= M <= N, all whole numbers; -h for help")


def fail(msg: str) -> None:
    print(f"noise.py: {msg}\n{USAGE}", file=sys.stderr)
    raise SystemExit(2)


def whole(s: str, what: str) -> int:
    try:
        return int(s)
    except ValueError:
        fail(f"{what} must be a whole number, got {s!r}")
        raise  # unreachable


def number(s: str, what: str) -> float:
    try:
        return float(s)
    except ValueError:
        fail(f"{what} must be a number, got {s!r}")
        raise


# ---------------------------------------------------------------- counts

def wilson(n: int, k: int) -> tuple[float, float]:
    """95% Wilson score interval for k successes in n trials, as proportions."""
    p = k / n
    d = 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / d
    half = Z / d * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return max(0.0, centre - half), min(1.0, centre + half)


def fisher_p(n: int, a: int, b: int) -> float:
    """Two-sided Fisher exact p for a/n vs b/n passes (exact integer arithmetic)."""
    k = a + b
    lo, hi = max(0, k - n), min(k, n)
    w = {x: math.comb(n, x) * math.comb(n, k - x) for x in range(lo, hi + 1)}
    obs = w[a]
    return min(1.0, sum(v for v in w.values() if v <= obs) / math.comb(2 * n, k))


def ztest_p(n: int, a: int, b: int) -> float:
    return ztest2_p(n, a, n, b)


def ztest2_p(n1: int, k1: int, n2: int, k2: int) -> float:
    """Two-sided two-proportion z test, k1/n1 against k2/n2."""
    pooled = (k1 + k2) / (n1 + n2)
    if pooled in (0.0, 1.0):
        return 1.0
    z = (k2 / n2 - k1 / n1) / math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    return math.erfc(abs(z) / math.sqrt(2))


def mcnemar_p(b: int, c: int) -> tuple[float, str]:
    n = b + c
    if n < 25:
        tail = sum(math.comb(n, i) for i in range(min(b, c) + 1))
        return min(1.0, 2 * tail / 2 ** n), "exact binomial"
    stat = (abs(b - c) - 1) ** 2 / n
    return math.erfc(math.sqrt(stat / 2)), "chi-square, continuity corrected"


def verdict(p: float) -> str:
    return "reliable" if p < ALPHA else "inside the noise"


def holm(ps: list[float], alpha: float = ALPHA) -> list[tuple[bool, float]]:
    """Holm step-down: (reliable, threshold) per p, in the input order."""
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    out: list[tuple[bool, float]] = [(False, 0.0)] * len(ps)
    still = True
    for rank, i in enumerate(order):
        thr = alpha / (len(ps) - rank)
        still = still and ps[i] < thr
        out[i] = (still, thr)
    return out


# ---------------------------------------------------------------- pass maps and side files

def load_json(path: Path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        fail(f"cannot read {path}: {e}")


def read_map_file(path: Path) -> dict[str, bool]:
    data = load_json(path)
    if isinstance(data, dict) and data:
        bad = [k for k, v in data.items() if not isinstance(v, bool)]
        if bad:
            fail(f"{path}: values must be true or false; {len(bad)} are not (e.g. id {bad[0]!r})")
        return {str(k): v for k, v in data.items()}
    fail(f"{path}: expected a non-empty {{episode id: true/false}} map over the whole bank")
    raise AssertionError  # unreachable


def json_files(d: Path) -> list[Path]:
    files = sorted(d.glob("*.json"))
    if not files:
        fail(f"{d}: no .json files")
    return files


def read_maps(path: str) -> dict[str, bool]:
    """A pass map from a file, or pooled from a directory (ids become bank:episode)."""
    p = Path(path)
    if p.is_dir():
        out: dict[str, bool] = {}
        for f in json_files(p):
            out.update({f"{f.stem}:{k}": v for k, v in read_map_file(f).items()})
        return out
    return read_map_file(p)


def read_passes(path: str) -> tuple[set, set]:
    """(passed ids, all ids) from an {id: bool} map (kept for older callers)."""
    m = read_maps(path)
    return {k for k, v in m.items() if v}, set(m)


def read_side(path: str, transform=None) -> dict[str, object]:
    """{episode id: value} from a file, or from a directory with the maps' file stems
    (ids become bank:episode; transform(bank, value) can rewrite each value)."""
    p = Path(path)
    if not p.is_dir():
        data = load_json(p)
        if not isinstance(data, dict):
            fail(f"{p}: expected a JSON object {{episode id: value}}")
        return {str(k): transform(None, v) if transform else v for k, v in data.items()}
    out: dict[str, object] = {}
    for f in json_files(p):
        data = load_json(f)
        if not isinstance(data, dict):
            fail(f"{f}: expected a JSON object {{episode id: value}}")
        for k, v in data.items():
            out[f"{f.stem}:{k}"] = transform(f.stem, v) if transform else v
    return out


def cluster_entry(bank: str | None, v) -> dict[str, str]:
    """{slot: phrasing id} from one clusters entry; empty or odd entries stop the command."""
    if isinstance(v, dict):
        items = [(str(s), x) for s, x in v.items()]
    elif isinstance(v, list):
        items = [(str(i), x) for i, x in enumerate(v)]
    else:
        items = [("phrasing", v)]
    if not items or any(isinstance(x, (dict, list, bool)) or x is None or str(x).strip() == ""
                        for _, x in items):
        fail(f"clusters: entry {v!r} must give a non-empty phrasing id for every slot")
    return {s: (f"{bank}:{x}" if bank else str(x)) for s, x in items}


def read_clusters(path: str | None) -> dict[str, dict[str, str]] | None:
    """{episode: {slot: phrasing id}}; a plain value is the slot 'phrasing'."""
    if path is None:
        return None
    return read_side(path, cluster_entry)


def slots_of(clusters: dict[str, dict[str, str]] | None) -> list[str]:
    if not clusters:
        return ["episode"]
    return sorted({s for v in clusters.values() for s in v})


def bank_of(eid: str) -> str | None:
    return eid.split(":", 1)[0] if ":" in eid else None


def same_ids(a: dict, b: dict, what_a: str, what_b: str) -> None:
    if set(a) != set(b):
        only_a, only_b = len(set(a) - set(b)), len(set(b) - set(a))
        fail(f"{what_b}: not the same episode set as {what_a} "
             f"({only_a} only in the first, {only_b} only in the second)")


# ---------------------------------------------------------------- cluster-aware paired test

def cluster_sums(d: dict[str, int], clusters, slot: str) -> list[int]:
    """Net difference per cluster (all clusters, zeros included)."""
    sums: dict[str, int] = {}
    for eid, v in d.items():
        c = clusters[eid][slot] if clusters else eid
        sums[c] = sums.get(c, 0) + v
    return list(sums.values())


def signflip_p(sums: list[int], draws: int = DRAWS, seed: int = SEED) -> float:
    """Two-sided p of the sign-flip permutation test on per-cluster nets."""
    nz = [abs(s) for s in sums if s]
    if not nz:
        return 1.0
    t = abs(sum(s for s in sums if s))
    if len(nz) * (2 * sum(nz) + 1) <= EXACT_LIMIT:
        dist = {0: 1.0}
        for a in nz:
            new: dict[int, float] = {}
            for s, pr in dist.items():
                new[s + a] = new.get(s + a, 0.0) + pr / 2
                new[s - a] = new.get(s - a, 0.0) + pr / 2
            dist = new
        return min(1.0, sum(pr for s, pr in dist.items() if abs(s) >= t))
    rng = random.Random(seed)
    hits = sum(1 for _ in range(draws)
               if abs(sum(a if rng.random() < 0.5 else -a for a in nz)) >= t)
    return (hits + 1) / (draws + 1)


def bootstrap(sums: list[int], draws: int = BOOT, seed: int = SEED) -> tuple[int, int]:
    """95% cluster bootstrap interval for the total net."""
    if not any(sums):
        return 0, 0
    rng = random.Random(seed)
    m = len(sums)
    nets = sorted(sum(rng.choices(sums, k=m)) for _ in range(draws))
    return nets[math.floor(0.025 * (draws - 1))], nets[math.ceil(0.975 * (draws - 1))]


def paired(base: dict[str, bool], cand: dict[str, bool], clusters=None,
           ids=None, interval: bool = True) -> dict:
    """B, C, net and the cluster-aware p and interval, over ids (default: all)."""
    ids = list(base) if ids is None else list(ids)
    d = {i: int(cand[i]) - int(base[i]) for i in ids}
    b = sum(1 for v in d.values() if v < 0)
    c = sum(1 for v in d.values() if v > 0)
    per = {}
    for slot in slots_of(clusters):
        sums = cluster_sums(d, clusters, slot)
        lo, hi = bootstrap(sums) if interval else (None, None)
        per[slot] = {"p": signflip_p(sums), "lo": lo, "hi": hi, "clusters": len(sums),
                     "moved": sum(1 for s in sums if s)}
    slot = max(per, key=lambda s: (per[s]["p"], -per[s]["clusters"]))
    lows = [v["lo"] for v in per.values() if v["lo"] is not None]
    highs = [v["hi"] for v in per.values() if v["hi"] is not None]
    return {"n": len(ids), "base": sum(base[i] for i in ids), "cand": sum(cand[i] for i in ids),
            "b": b, "c": c, "net": c - b, "p": per[slot]["p"], "slot": slot,
            "clusters": per[slot]["clusters"], "moved": per[slot]["moved"],
            "lo": min(lows) if lows else None, "hi": max(highs) if highs else None,
            "slots": per}


def word(r: dict, thr: float = ALPHA) -> str:
    if r["p"] < thr and r["net"] > 0:
        return "reliable gain"
    if r["p"] < thr and r["net"] < 0:
        return "reliably worse"
    return "inside the noise"


def describe(r: dict, clustered: bool) -> str:
    how = (f"cluster sign-flip p = {r['p']:.3f} over {r['clusters']} clusters by {r['slot']}"
           if clustered else f"exact sign test p = {r['p']:.3f}")
    s = (f"base {r['base']}/{r['n']}, cand {r['cand']}/{r['n']}: B {r['b']} vs C {r['c']}, "
         f"net {r['net']:+d}, {how}")
    if r["lo"] is not None:
        s += f", 95% interval for the net {r['lo']:+d} to {r['hi']:+d}"
    return s


MAX_MARGIN = 0.02  # a wider not-worse margin needs --wide-margin


def margin_episodes(s: str, n: int, wide: bool = False) -> float:
    """MARGIN is 'N%' of the episodes or a whole number of episodes; nothing else."""
    if s.endswith("%"):
        v = number(s[:-1], "--not-worse MARGIN") / 100 * n
    else:
        try:
            v = int(s)
        except ValueError:
            fail(f"--not-worse MARGIN is a whole number of episodes (10) or a share with % (1%), "
                 f"got {s!r}")
            raise
    if v < 0:
        fail("--not-worse MARGIN cannot be negative")
    if v > MAX_MARGIN * n and not wide:
        fail(f"--not-worse margin {v:.0f} is more than {MAX_MARGIN:.0%} of the {n} episodes; "
             "pass --wide-margin if FRAME.md really set it that wide")
    return v


MIN_CLUSTERS = 20  # fewer phrasings than this in a slot cannot show "not worse"


def not_worse(base: dict[str, bool], cand: dict[str, bool], clusters, margin: float,
              ids=None, draws: int = DRAWS, seed: int = SEED, alpha: float = ALPHA / 2) -> dict:
    """One-sided test of H0: net <= -margin, over phrasing clusters.

    Per slot: the cluster nets plus one pseudo-cluster that lost as much as the largest
    cluster that moved (a rule-of-one guard against losses this bank happened not to
    show); p = share of sign flips whose sum reaches the observed sum + margin. Pass when
    every slot has at least MIN_CLUSTERS clusters and p < 0.025 on every slot (no movement
    at all passes)."""
    ids = list(base) if ids is None else list(ids)
    d = {i: int(cand[i]) - int(base[i]) for i in ids}
    for slot in slots_of(clusters):
        k = len(cluster_sums(d, clusters, slot))
        if k < MIN_CLUSTERS:
            return {"ok": False, "p": 1.0, "slot": slot, "net": sum(d.values()),
                    "why": f"only {k} phrasings in slot {slot}; at least {MIN_CLUSTERS} are "
                           "needed to show not-worse (one phrasing is too large a share)"}
    if not any(d.values()):
        return {"ok": True, "p": 0.0, "slot": None, "net": 0, "why": "no episode moved"}
    worst = None
    for slot in slots_of(clusters):
        sums = cluster_sums(d, clusters, slot)
        vals = [x for x in sums if x] + [-max(abs(x) for x in sums)]
        t = sum(vals) + margin
        if t <= 0:
            pv = 1.0
        elif len(vals) <= 16:
            hits = sum(1 for mask in range(1 << len(vals))
                       if sum(x if mask >> k & 1 else -x for k, x in enumerate(map(abs, vals))) >= t - 1e-9)
            pv = hits / (1 << len(vals))
        else:
            rng = random.Random(seed)
            a = [abs(x) for x in vals]
            hits = sum(1 for _ in range(draws)
                       if sum(x if rng.random() < 0.5 else -x for x in a) >= t - 1e-9)
            pv = (hits + 1) / (draws + 1)
        if worst is None or pv > worst[0]:
            worst = (pv, slot)
    return {"ok": worst[0] < alpha, "p": worst[0], "slot": worst[1], "net": sum(d.values()),
            "why": (f"one-sided cluster sign-flip test of net <= -{margin:.1f} with one "
                    f"pseudo-loss, p = {worst[0]:.3f} (slot {worst[1]})")}


def check_cluster_ids(ids, clusters, where: str) -> None:
    """Every episode must have a cluster entry, or the 'cluster-aware' label is a lie."""
    if clusters is None:
        return
    ids = list(ids)
    missing = [i for i in ids if i not in clusters]
    if missing:
        ex = next(iter(clusters), "none")
        fail(f"{where}: {len(missing)} of {len(ids)} episodes have no entry in the clusters "
             f"file (e.g. map id {missing[0]!r}, clusters id {ex!r}). With a folder of maps, ids "
             "are bank:episode: give a clusters folder with the same file names.")
    slots = set(slots_of({i: clusters[i] for i in ids}))
    short = [i for i in ids if set(clusters[i]) != slots]
    if short:
        fail(f"{where}: {len(short)} episodes do not name every phrasing slot "
             f"({', '.join(sorted(slots))}), e.g. {short[0]!r}: {clusters[short[0]]}. An episode "
             "without a slot would count as its own cluster and make the test too optimistic.")


def by_group(ids, key) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for i in ids:
        g = key(i)
        if g is not None:
            groups.setdefault(str(g), []).append(i)
    return dict(sorted(groups.items()))


MIN_WRITERS = 3  # writer set-ups a pooled gain must point the same way on to be kept


def writer_rule(same: int, setups: int) -> tuple[bool, str]:
    """Writer agreement, described: no test at the writer level is run, so it is never
    called reliable; a pooled gain is kept only when MIN_WRITERS set-ups point its way."""
    return (same >= MIN_WRITERS,
            f"same direction on {same} of {setups} writer set-ups (a description, not a "
            f"test); {MIN_WRITERS} needed")


def ledger_writers(path: str, banks) -> dict[str, str]:
    """{bank: writer set-up} from the manifests of a verified ledger (chain and mirror)."""
    seal = seal_module()
    lp = Path(path).resolve()
    ledger = seal.load_checked(lp)
    out = {}
    for b in banks:
        ws = ((ledger["banks"].get(b) or {}).get("manifest") or {}).get("writer_setup")
        if not (isinstance(ws, str) and ws.strip()):
            fail(f"--ledger: bank {b!r} has no writer_setup in its ledger manifest")
        out[b] = ws
    return out


def seal_module():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import seal
    return seal


def read_labels(path: str, ids, what: str) -> dict:
    """{episode: label}; every episode needs a non-empty string label, or the command stops."""
    lab = read_side(path)
    bad = [i for i in ids if not (isinstance(lab.get(i), str) and lab[i].strip())]
    if bad:
        fail(f"{what} {path}: {len(bad)} episodes have no non-empty label (e.g. {bad[0]!r}); "
             "an unlabelled episode would drop out of every per-group test")
    return lab


def read_writers(path: str | None, banks) -> dict[str, str] | None:
    """{bank file stem: writer set-up}; every bank needs one."""
    if path is None:
        return None
    data = load_json(Path(path))
    if not isinstance(data, dict):
        fail(f"--writers {path}: expected {{bank: writer set-up}}")
    bad = [b for b in banks if not (isinstance(data.get(b), str) and data[b].strip())]
    if bad:
        fail(f"--writers {path}: no writer set-up for bank {bad[0]!r}")
    return {str(k): v for k, v in data.items()}


def general(verdict: str, base, cand, clusters, ids, writers) -> tuple[str, str]:
    """The verdict after the writer rule, and the line that explains it."""
    banks = by_group(ids, bank_of)
    if len(banks) <= 1:
        note = "one bank: one writer set-up says nothing about new writers"
        return (verdict + " (one writer set-up)" if verdict == "reliable gain" else verdict), note
    if writers is None:
        note = ("writer set-ups unknown (give --ledger, or --writers): no pooled gain is kept")
        return ("not reliable across writers (writer set-ups unknown)" if verdict == "reliable gain"
                else verdict), note
    groups = by_group(ids, lambda i: writers[bank_of(i)])
    same = sum(paired(base, cand, clusters, g, interval=False)["net"] > 0 for g in groups.values())
    ok, rule = writer_rule(same, len(groups))
    if verdict == "reliable gain":
        verdict = ("reliable gain (pooled cluster test)" if ok
                   else f"not reliable across writers ({rule})")
    return verdict, rule


def writer_map(opts: dict, banks) -> dict[str, str] | None:
    """Writer set-ups: from the verified ledger when given, else from --writers (printed as
    unverified), else None."""
    if len(banks) <= 1:
        return None
    if opts.get("ledger"):
        return ledger_writers(opts["ledger"], banks)
    if opts.get("writers"):
        print("note: writer set-ups from --writers, not verified against the ledger")
        return read_writers(opts["writers"], banks)
    return None


def cmd_paired_maps(opts: dict) -> None:
    files = opts["files"]
    if len(files) != 2:
        fail("--paired-maps takes BASE and CAND")
    base, cand = read_maps(files[0]), read_maps(files[1])
    same_ids(base, cand, files[0], files[1])
    clusters = read_clusters(opts.get("clusters"))
    check_cluster_ids(base, clusters, opts.get("clusters", ""))
    if "not_worse" in opts and clusters is None:
        fail("--not-worse needs --clusters: without them every episode counts as independent "
             "and a loss can pass")
    if bool(opts.get("cells")) != bool(opts.get("cell")):
        fail("--paired-maps takes --cells CELLS and --cell NAME together: the gain is tested in "
             "that cell and --not-worse on every other episode")
    if opts.get("cycle") and not opts.get("ledger"):
        fail("--cycle needs --ledger: the cycle number and its K come from `seal.py cycle open`")
    if opts.get("cell") and not opts.get("cycle"):
        fail("--cell (the mechanism route) needs --ledger L --cycle N, opened with `seal.py "
             "cycle open --of K`: cycle N tests at 0.05 / K / 2^N, so the false keeps over all "
             "cycles add up to at most 0.05")
    if opts.get("cycle") and "of" in opts:
        fail("with --cycle, K comes from the ledger's cycle; drop --of")
    k = opts.get("of", 1)
    if opts.get("cycle"):
        tag = hashlib.sha256(json.dumps(sorted(cand.items())).encode()).hexdigest()[:16]
        k, used = seal_module().use_cycle(Path(opts["ledger"]).resolve(), opts["cycle"], tag)
        print(f"cycle {opts['cycle']}: mechanism test {used} of {k} (recorded in the ledger)")
    spend = 2 ** opts.get("cycle", 0)
    thr = ALPHA / k / spend
    ids = list(base)
    rest = []
    if opts.get("cell"):
        cells = read_labels(opts["cells"], base, "--cells")
        ids = [i for i in base if cells.get(i) == opts["cell"]]
        rest = [i for i in base if cells.get(i) != opts["cell"]]
        if not ids:
            fail(f"--cell {opts['cell']}: no episode of the maps is in that cell")
        print(f"target cell {opts['cell']}: {len(ids)} episodes; the other {len(rest)} are "
              "checked with --not-worse")
    nw_ids = rest if opts.get("cell") else ids
    margin = (margin_episodes(opts["not_worse"], len(nw_ids), opts.get("wide_margin", False))
              if "not_worse" in opts else None)
    r = paired(base, cand, clusters, ids)
    extra = (f" (threshold {thr:.4f}: 1 of {k}" + (f", cycle {opts['cycle']}" if spend > 1 else "")
             + ")") if thr < ALPHA else ""
    banks = by_group(ids, bank_of)
    writers = writer_map(opts, banks)
    verdict, rule = general(word(r, thr), base, cand, clusters, ids, writers)
    print(f"{'cell' if opts.get('cell') else 'pooled'}: {describe(r, clusters is not None)}: "
          f"{verdict}{extra}")
    if clusters and len(r["slots"]) > 1:
        for sl, v in r["slots"].items():
            print(f"  slot {sl}: p = {v['p']:.3f} over {v['clusters']} clusters, "
                  f"interval {v['lo']:+d} to {v['hi']:+d}")
    if clusters is None:
        print("  note: no --clusters, so every episode counts as independent; episodes that "
              "share a phrasing make this too optimistic")
    if len(banks) > 1:
        print("per bank:")
        for bank, bids in banks.items():
            rb = paired(base, cand, clusters, bids, interval=False)
            print(f"  {bank}: B {rb['b']} vs C {rb['c']}, net {rb['net']:+d}, p = {rb['p']:.3f}: {word(rb, thr)}")
    print(rule)
    seg = read_labels(opts["segments"], base, "--segments") if opts.get("segments") else None
    if seg is not None:
        print("per segment:")
        for name, sids in by_group(base, seg.get).items():
            rs = paired(base, cand, clusters, sids, interval=False)
            print(f"  {name}: {rs['base']} -> {rs['cand']} of {rs['n']}, B {rs['b']} vs C {rs['c']}, "
                  f"net {rs['net']:+d}, p = {rs['p']:.3f}: {word(rs, thr)}")
    if margin is not None:
        alpha = ALPHA / 2 / k / spend
        failed = False
        parts = [("all" if not opts.get("cell") else "outside the cell", nw_ids)]
        if seg is not None:
            parts += [(f"segment {n}", [i for i in sids if i in set(nw_ids)])
                      for n, sids in by_group(nw_ids, seg.get).items()]
        for name, pids in parts:
            m = margin * len(pids) / len(nw_ids)
            nw = not_worse(base, cand, clusters, m, pids, alpha=alpha)
            print(f"not worse ({name}), margin {m:.1f} of {len(pids)} episodes, net {nw['net']:+d}"
                  f", one-sided threshold {alpha:.4f}: {nw['why']}: {'PASS' if nw['ok'] else 'FAIL'}")
            failed = failed or not nw["ok"]
        if failed:
            raise SystemExit(1)


def cmd_family_maps(opts: dict, alias: bool = False) -> None:
    files = opts["files"]
    if len(files) < 2:
        fail("--family-maps needs BASE and at least one candidate")
    if alias and not opts.get("clusters"):
        print("warning: --family without --clusters counts every episode as independent; "
              "use --family-maps with --clusters", file=sys.stderr)
    base = read_maps(files[0])
    clusters = read_clusters(opts.get("clusters"))
    check_cluster_ids(base, clusters, opts.get("clusters", ""))
    banks = by_group(base, bank_of)
    writers = writer_map(opts, banks)
    rows = []
    for p in files[1:]:
        cand = read_maps(p)
        same_ids(base, cand, files[0], p)
        r = paired(base, cand, clusters, interval=False)
        rows.append((p, r, cand))
    for (p, r, cand), (ok, thr) in zip(rows, holm([x[1]["p"] for x in rows])):
        w = "reliable gain" if ok and r["net"] > 0 else ("reliably worse" if ok else "inside the noise")
        w, rule = general(w, base, cand, clusters, list(base), writers)
        w = w.replace("reliable gain", "reliable", 1) if w.startswith("reliable gain") else w
        tail = ", " + rule
        how = f" [clusters by {r['slot']}: {r['clusters']}]" if clusters else ""
        print(f"{p}: B {r['b']} vs C {r['c']}, net {r['net']:+d}, p = {r['p']:.3f}, "
              f"Holm threshold {thr:.4f}: {w}{tail}{how}")
    print(f"best of {len(rows)} picked on this bank: its gain is biased upward; "
          "confirm it on a bank that picked nothing")
    if opts.get("segments"):
        seg = read_labels(opts["segments"], base, "--segments")
        for p, _, _ in rows:
            cand = read_maps(p)
            parts = []
            for name, ids in by_group(base, seg.get).items():
                rs = paired(base, cand, None, ids, interval=False)
                parts.append(f"{name} {rs['net']:+d}")
            print(f"  {p} by segment: " + ", ".join(parts))


def cmd_visible(opts: dict) -> None:
    files = opts["files"]
    if len(files) != 1 or not opts.get("cells"):
        fail("--visible takes BASE and --cells CELLS")
    base = read_maps(files[0])
    cells = read_labels(opts["cells"], base, "--cells")
    clusters = read_clusters(opts.get("clusters"))
    check_cluster_ids(base, clusters, opts.get("clusters", ""))
    need = opts.get("min_phrasings", 8)
    slot_opt = opts.get("slot")
    if clusters is None:
        print("note: no --clusters, so each failing episode counts as its own phrasing; "
              "this overstates what the bank can see")
    if slot_opt and slot_opt not in slots_of(clusters):
        fail(f"--slot {slot_opt}: not a phrasing slot of the clusters ({', '.join(slots_of(clusters))})")
    slots = [slot_opt] if slot_opt else slots_of(clusters)
    blind = 0
    for name, ids in by_group(base, cells.get).items():
        fails = [i for i in ids if not base[i]]
        counts = {}
        for s in slots:
            counts[s] = len({clusters[i][s] if clusters else i for i in fails})
        s = min(counts, key=counts.get)
        k = counts[s]
        flag = "" if k >= need else "  <- this bank cannot see a fix here"
        blind += k < need
        how = f" (by {s})" if clusters else ""
        print(f"{name}: {len(ids)} episodes, base fails {len(fails)}, "
              f"distinct failing phrasings {k}{how}{flag}")
    print(f"{blind} cell(s) below {need} failing phrasings. For each: add a fresh writer briefed "
          "on that cell (never on the fix), or use the mechanism route with a targeted bank.")


# ---------------------------------------------------------------- sizing

def min_flips(alpha: float) -> int:
    """Fewest clusters that must all flip one way, none the other, for p < alpha."""
    c = 1
    while 2 * 0.5 ** c >= alpha:
        c += 1
    return c


def cmd_mde(args: list[str]) -> None:
    n, m, p, k, churn = None, None, None, 1, None
    it = iter(args)
    for a in it:
        if a == "--clusters":
            m = whole(next(it, ""), "--clusters")
        elif a == "--base-rate":
            p = number(next(it, ""), "--base-rate")
        elif a == "--of":
            k = whole(next(it, ""), "--of")
        elif a == "--churn":
            churn = number(next(it, ""), "--churn")
        elif n is None:
            n = whole(a, "N")
        else:
            fail(f"unexpected argument {a}")
    if n is None or n < 1:
        fail("--mde needs N, the number of episodes")
    m = n if m is None else m
    if not 1 <= m <= n:
        fail(f"--clusters must be between 1 and N={n}")
    if p is None or not 0 < p < 1:
        fail("--mde needs --base-rate P between 0 and 1 (the base's pass rate)")
    if k < 1:
        fail("--of must be at least 1")
    if churn is None:
        churn = min(1.0, 2 * p * (1 - p))
        churn_note = "assumed: two independent versions at the base rate; pass --churn"
    else:
        if not 0 < churn <= 1:
            fail("--churn is the share of episodes that change between versions, in (0, 1]")
        churn_note = "given"
    f1, fk = min_flips(ALPHA), min_flips(ALPHA / k)
    per = n / m
    print(f"pure gain, nothing lost: at least {f1} phrasings must flip (about {f1 * per:.0f} "
          f"episodes at {per:.1f} per phrasing) to pass at 0.05"
          + (f"; {fk} under Holm with K = {k}" if k > 1 else ""))
    zpow = NormalDist().inv_cdf(0.8)
    levels = [("0.05", ALPHA)] + ([(f"Holm, K = {k}", ALPHA / k)] if k > 1 else [])
    for label, a in levels:
        z = NormalDist().inv_cdf(1 - a / 2)
        # paired (McNemar-style): net share detectable when a share `churn` of units moves
        d_cl = (z + zpow) * math.sqrt(churn / m)
        d_ep = (z + zpow) * math.sqrt(churn / n)
        print(f"paired, churn {churn:.1%} ({churn_note}), 80% power at {label}: about {d_cl:.1%} "
              f"({d_cl * n:.0f} episodes) counting phrasings; {d_ep:.1%} if the {n} episodes "
              "were independent (they are not)")
    print("rough: phrasings treated as equal-sized clusters; one writer says nothing about "
          "new writers")


def need(rate_s: str) -> None:
    try:
        rate = float(rate_s)
    except ValueError:
        fail(f"RATE must be a number between 0 and 1, got {rate_s!r}")
        raise
    if not 0 < rate < 1:
        fail(f"RATE must be between 0 and 1, got {rate}")
    n = math.ceil(math.log(0.05) / math.log(1 - rate))
    print(f"{n} episodes with zero misses show the miss rate is below {rate:.2%} (95%, one-sided); "
          f"with misses you need more. Zero misses in 40 only shows it is below "
          f"{1 - 0.05 ** (1 / 40):.1%}.")


# ---------------------------------------------------------------- CLI

def map_opts(argv: list[str]) -> dict:
    opts: dict = {"files": []}
    it = iter(argv)
    for a in it:
        if a in ("--clusters", "--segments", "--cells", "--cell", "--slot", "--not-worse", "--writers",
                 "--ledger"):
            v = next(it, None)
            if v is None:
                fail(f"{a} needs a value")
            opts[a[2:].replace("-", "_")] = v
        elif a == "--wide-margin":
            opts["wide_margin"] = True
        elif a == "--min-phrasings":
            opts["min_phrasings"] = whole(next(it, ""), "--min-phrasings")
        elif a == "--cycle":
            opts["cycle"] = whole(next(it, ""), "--cycle")
            if opts["cycle"] < 1:
                fail("--cycle must be at least 1")
        elif a == "--of":
            opts["of"] = whole(next(it, ""), "--of")
            if opts["of"] < 1:
                fail("--of must be at least 1")
        elif a.startswith("--"):
            fail(f"unknown option {a}")
        else:
            opts["files"].append(a)
    return opts


def main(argv: list[str]) -> None:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    mode = argv[0]
    if mode == "--paired-maps":
        cmd_paired_maps(map_opts(argv[1:]))
        return
    if mode in ("--family", "--family-maps"):
        opts = map_opts(argv[1:])
        if "not_worse" in opts:
            fail("--not-worse applies to --paired-maps")
        cmd_family_maps(opts, alias=mode == "--family")
        return
    if mode == "--visible":
        cmd_visible(map_opts(argv[1:]))
        return
    if mode == "--mde":
        cmd_mde(argv[1:])
        return
    if mode == "--need":
        if len(argv) != 2:
            fail("--need takes one RATE")
        need(argv[1])
        return
    args, clusters, is_paired, of = [], None, False, 1
    it = iter(argv)
    for a in it:
        if a == "--paired":
            is_paired = True
        elif a == "--of":
            v = next(it, None)
            if v is None:
                fail("--of needs a number")
            of = whole(v, "--of")
            if of < 1:
                fail("--of must be at least 1")
        elif a == "--clusters":
            v = next(it, None)
            if v is None:
                fail("--clusters needs a number")
            clusters = whole(v, "--clusters")
        elif a.startswith("--clusters="):
            clusters = whole(a.split("=", 1)[1], "--clusters")
        elif a.startswith("--"):
            fail(f"unknown option {a}")
        else:
            args.append(a)

    if is_paired:
        if len(args) != 2:
            fail("--paired takes exactly two counts, B and C")
        b, c = whole(args[0], "B"), whole(args[1], "C")
        if b < 0 or c < 0:
            fail("discordant counts cannot be negative")
        if clusters is not None and clusters < 1:
            fail("--clusters must be at least 1")
        if b + c == 0:
            print("no discordant episodes: the versions are identical on this bank")
            return
        p, how = mcnemar_p(b, c)
        thr = 0.05 / of
        w = "reliable" if p < thr else "inside the noise"
        extra = f", Bonferroni threshold {thr:.4f} for 1 of {of}" if of > 1 else ""
        print(f"discordant {b} vs {c}: net {c - b:+d}, McNemar p = {p:.3f} ({how}{extra}): {w}")
        if clusters is not None:
            print(f"note: this p counts episodes, not the {clusters} phrasings; it is too "
                  "optimistic. For the cluster-aware test use --paired-maps BASE CAND "
                  "--clusters FILE")
        return

    if of != 1:
        fail("--of applies to --paired only")
    if len(args) not in (2, 3):
        fail("give N and one or two pass counts")
    n = whole(args[0], "N")
    ks = [whole(a, "PASSED") for a in args[1:]]
    if n <= 0:
        fail("N must be at least 1")
    for k in ks:
        if not 0 <= k <= n:
            fail(f"a pass count must be between 0 and N={n}, got {k}")
    if clusters is not None and not 1 <= clusters <= n:
        fail(f"--clusters must be between 1 and N={n}, got {clusters}")
    deff = n / clusters if clusters else 1.0
    note = (f" [--clusters {clusters}: margin x{math.sqrt(deff):.2f}, a rough upper bound]"
            if clusters else "")

    def describe_count(k: int) -> str:
        lo, hi = wilson(n, k)
        centre, half = (lo + hi) / 2, (hi - lo) / 2 * math.sqrt(deff)
        lo, hi = max(0.0, centre - half), min(1.0, centre + half)
        return (f"{k}/{n} = {k / n:.1%}, 95% interval {lo:.1%} to {hi:.1%} (Wilson: "
                f"{lo * n:.0f} to {hi * n:.0f} episodes), margin about ±{half * n:.0f} episodes")

    print(describe_count(ks[0]) + note)
    if len(ks) == 1:
        return
    a, b = ks
    print(describe_count(b) + note)
    ne = clusters or n
    ae, be = (round(a * ne / n), round(b * ne / n)) if clusters else (a, b)
    if ne <= 200:
        p, how = fisher_p(ne, ae, be), "Fisher exact"
    else:
        p, how = ztest_p(ne, ae, be), "two-proportion z test"
    if clusters:
        how += f" on an effective {ae}/{ne} vs {be}/{ne}"
    tail = "" if p < 0.05 else " (use --paired for a sharper test)"
    print(f"difference {b - a:+d}, {how} p = {p:.3f}: {verdict(p)}{tail}")


if __name__ == "__main__":
    main(sys.argv[1:])
