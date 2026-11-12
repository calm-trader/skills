#!/usr/bin/env python3
"""Drift checks for a live (or shadow) agent: has the input mix or a key rate moved?

    drift.py mix REF.json CUR.json [--threshold 0.2]
        Population stability index (PSI) over a categorical mix: segment, intent, channel,
        language, step-count bucket. Each file is {category: count} or a list of category
        labels. Exit 1 when PSI is above the threshold (set it in FRAME.md; 0.2 is a
        common default, 0.1 to 0.2 is "watch").
    drift.py rate N_REF K_REF N_CUR K_CUR [--name handoff] [--alpha 0.05]
        One rate (handoff, unknown or fallback read, judge abstain, human override, wrong
        action): Wilson intervals for both periods and a two-proportion z test. Exit 1
        when the change is reliable at --alpha.
    drift.py gap SIM.json LIVE.json --max-gap 5
        Simulated minus live verified success per segment. Each file is
        {segment: [passed, n]} or {segment: {"passed": k, "n": n}}. --max-gap (points) is
        required: register it in FRAME.md. Exit 1 when a live segment has no simulated
        counterpart, or when the gap is above --max-gap points even between the near ends
        of the two Wilson intervals (sim lower bound minus live upper bound). Segments with
        too few episodes, on either side, to tell are marked.

Thresholds must be finite: --threshold > 0, 0 < --alpha < 1, --max-gap >= 0.

A drift alarm freezes promotion, pulls a fresh sample for people to adjudicate, and opens
a cycle aimed at the segment that moved (references/continuous.md).

Standard library only, Python 3.10+. Imports noise.py from the same folder.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import noise  # noqa: E402

EPS = 1e-4  # share given to a category absent in one period, so PSI stays finite


def bad(msg: str) -> None:
    print(f"drift.py: {msg}", file=sys.stderr)
    raise SystemExit(2)


def read(path: str):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        bad(f"cannot read {path}: {e}")


def counts(path: str) -> dict[str, int]:
    data = read(path)
    if isinstance(data, list):
        out: dict[str, int] = {}
        for x in data:
            out[str(x)] = out.get(str(x), 0) + 1
        data = out
    if not isinstance(data, dict) or not data:
        bad(f"{path}: expected {{category: count}} or a list of labels")
    for k, v in data.items():
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            bad(f"{path}: count for {k!r} must be a whole number >= 0")
    if sum(data.values()) == 0:
        bad(f"{path}: all counts are zero")
    return {str(k): v for k, v in data.items()}


def psi(ref: dict[str, int], cur: dict[str, int]) -> tuple[float, list[tuple[str, float, float, float]]]:
    nr, nc = sum(ref.values()), sum(cur.values())
    rows = []
    total = 0.0
    for cat in sorted(set(ref) | set(cur)):
        r = max(ref.get(cat, 0) / nr, EPS)
        c = max(cur.get(cat, 0) / nc, EPS)
        part = (c - r) * math.log(c / r)
        total += part
        rows.append((cat, r, c, part))
    return total, rows


def finite(v: float, what: str, lo: float, hi: float = math.inf, lo_open: bool = True) -> None:
    if not math.isfinite(v) or v > hi or v < lo or (lo_open and v == lo):
        bad(f"{what} must be a finite number {'>' if lo_open else '>='} {lo}"
            + (f" and below {hi}" if math.isfinite(hi) else "") + f", got {v}")


def cmd_mix(args) -> None:
    finite(args.threshold, "--threshold", 0)
    ref, cur = counts(args.ref), counts(args.cur)
    total, rows = psi(ref, cur)
    for cat, r, c, part in sorted(rows, key=lambda x: -x[3]):
        print(f"{cat:24} ref {r:6.1%}  cur {c:6.1%}  contribution {part:.3f}")
    state = "DRIFT" if total > args.threshold else ("watch" if total > args.threshold / 2 else "stable")
    print(f"PSI {total:.3f} (threshold {args.threshold}): {state}")
    if total > args.threshold:
        raise SystemExit(1)


def cmd_rate(args) -> None:
    finite(args.alpha, "--alpha", 0, 1)
    if args.alpha >= 1:
        bad("--alpha must be below 1")
    for n, k, what in ((args.n_ref, args.k_ref, "reference"), (args.n_cur, args.k_cur, "current")):
        if n <= 0 or not 0 <= k <= n:
            bad(f"{what}: need N > 0 and 0 <= K <= N")
    lines = []
    for label, n, k in (("reference", args.n_ref, args.k_ref), ("current", args.n_cur, args.k_cur)):
        lo, hi = noise.wilson(n, k)
        lines.append(f"{args.name} {label}: {k}/{n} = {k / n:.2%} (95% interval {lo:.2%} to {hi:.2%})")
    print("\n".join(lines))
    p = noise.ztest2_p(args.n_ref, args.k_ref, args.n_cur, args.k_cur)
    diff = args.k_cur / args.n_cur - args.k_ref / args.n_ref
    moved = p < args.alpha
    print(f"change {diff:+.2%}, two-proportion z test p = {p:.3f}: "
          f"{'MOVED' if moved else 'no reliable change'}")
    if moved:
        raise SystemExit(1)


def seg_counts(path: str) -> dict[str, tuple[int, int]]:
    data = read(path)
    if not isinstance(data, dict) or not data:
        bad(f"{path}: expected {{segment: [passed, n]}}")
    out = {}
    for seg, v in data.items():
        if isinstance(v, dict):
            v = [v.get("passed"), v.get("n")]
        if (not isinstance(v, list) or len(v) != 2 or not all(isinstance(x, int) for x in v)
                or v[1] <= 0 or not 0 <= v[0] <= v[1]):
            bad(f"{path}: {seg!r} must be [passed, n] with 0 <= passed <= n, n > 0")
        out[str(seg)] = (v[0], v[1])
    return out


def cmd_gap(args) -> None:
    finite(args.max_gap, "--max-gap", 0, lo_open=False)
    sim, live = seg_counts(args.sim), seg_counts(args.live)
    alarm = False
    for seg in sorted(set(sim) | set(live)):
        if seg not in live:
            print(f"{seg:16} only in simulation: no live data yet")
            continue
        if seg not in sim:
            print(f"{seg:16} ALARM: live traffic the simulation does not cover; add it to the simulator")
            alarm = True
            continue
        (ks, ns), (kl, nl) = sim[seg], live[seg]
        gap = (ks / ns - kl / nl) * 100
        slo, shi = noise.wilson(ns, ks)
        llo, lhi = noise.wilson(nl, kl)
        surely = (slo - lhi) * 100  # the gap's lower bound: both rates are estimates
        line = (f"{seg:16} sim {ks / ns:6.1%} ({ns}, {slo:.1%} to {shi:.1%})  live {kl / nl:6.1%} "
                f"({nl}, {llo:.1%} to {lhi:.1%})  gap {gap:+.1f} points (at least {surely:+.1f})")
        if surely > args.max_gap:
            line += f"  ALARM: above {args.max_gap} points even between the interval ends"
            alarm = True
        elif ((lhi - llo) + (shi - slo)) * 50 > args.max_gap:
            line += f"  too few episodes to tell a {args.max_gap}-point gap"
        print(line)
    print("a positive gap means the simulation flatters the agent in that segment")
    if alarm:
        raise SystemExit(1)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("mix")
    s.add_argument("ref")
    s.add_argument("cur")
    s.add_argument("--threshold", type=float, default=0.2)
    s.set_defaults(fn=cmd_mix)
    s = sub.add_parser("rate")
    for a in ("n_ref", "k_ref", "n_cur", "k_cur"):
        s.add_argument(a, type=int)
    s.add_argument("--name", default="rate")
    s.add_argument("--alpha", type=float, default=0.05)
    s.set_defaults(fn=cmd_rate)
    s = sub.add_parser("gap")
    s.add_argument("sim")
    s.add_argument("live")
    s.add_argument("--max-gap", type=float, required=True, help="points (registered in FRAME.md)")
    s.set_defaults(fn=cmd_gap)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
