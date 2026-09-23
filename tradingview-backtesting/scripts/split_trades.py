#!/usr/bin/env python3
"""Split one exported TradingView List of Trades into windows, offline.

One Deep read over the whole span + this script replaces one read per window
(SKILL.md §10, "One read, many windows"). Valid only for engines that are flat
every night and carry no state across window boundaries; confirm once per engine
against a direct read of one window.

Usage:
  split_trades.py TRADES.csv --window H1:2025-04-28:2025-12-31 \
      --window H2:2026-01-01:2026-07-08 [--per-year] [--json]

Windows are inclusive and assigned by ENTRY date. Standard library only.

Reports per window: trades (trade numbers, which TradingView counts as legs),
entries (distinct entry timestamps: a scale-out entry is one entry, two legs),
net, gross profit/loss, PF, win%, first/last entry, legs still open at export,
and legs whose exit falls on a later date than their entry (must be 0 for an
intraday engine; SKILL.md §12 and the desk's flat-every-night rule).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import OrderedDict


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"{path}: no rows")
    pnl_col = next((c for c in rows[0] if c.startswith("Net PnL")), None)
    if pnl_col is None or "Type" not in rows[0] or "Date and time" not in rows[0]:
        sys.exit(f"{path}: not a TradingView List of Trades export (columns: {list(rows[0])})")
    legs: "OrderedDict[str, dict]" = OrderedDict()
    for r in rows:
        leg = legs.setdefault(r["Trade number"], {"id": r["Trade number"]})
        kind = r["Type"].split()[0].lower()           # "entry" / "exit"
        leg[kind] = r["Date and time"]
        leg["side"] = r["Type"].split()[-1].lower()    # "long" / "short"
        leg["pnl"] = float(r[pnl_col].replace("−", "-").replace(",", ""))
        if kind == "exit":
            leg["exit_signal"] = r.get("Signal", "")
    return list(legs.values())


def summarise(legs: list[dict]) -> dict:
    if not legs:
        return {"trades": 0}
    closed = [l for l in legs if l.get("exit") and l.get("exit_signal", "").lower() != "open"]
    gp = sum(l["pnl"] for l in closed if l["pnl"] > 0)
    gl = -sum(l["pnl"] for l in closed if l["pnl"] < 0)
    wins = sum(1 for l in closed if l["pnl"] > 0)
    entries = sorted(l["entry"] for l in legs if l.get("entry"))
    return {
        "trades": len(closed),
        "entries": len({(l["entry"], l["side"]) for l in closed}),
        "open_at_export": len(legs) - len(closed),
        "net_usd": round(gp - gl, 2),
        "gross_profit_usd": round(gp, 2),
        "gross_loss_usd": round(gl, 2),
        "profit_factor": round(gp / gl, 3) if gl else None,
        "win_rate_pct": round(100.0 * wins / len(closed), 2) if closed else None,
        "long_trades": sum(1 for l in closed if l["side"] == "long"),
        "short_trades": sum(1 for l in closed if l["side"] == "short"),
        "first_entry": entries[0] if entries else None,
        "last_entry": entries[-1] if entries else None,
        "exits_on_later_date": sum(1 for l in closed if l["exit"][:10] > l["entry"][:10]),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--window", action="append", default=[], metavar="NAME:FROM:TO")
    ap.add_argument("--per-year", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    legs = [l for l in load(a.csv) if l.get("entry")]
    out: "OrderedDict[str, dict]" = OrderedDict(all=summarise(legs))
    for w in a.window:
        try:
            name, lo, hi = w.split(":")
        except ValueError:
            sys.exit(f"bad --window {w!r}; want NAME:YYYY-MM-DD:YYYY-MM-DD")
        out[name] = summarise([l for l in legs if lo <= l["entry"][:10] <= hi])
    if a.per_year:
        for y in sorted({l["entry"][:4] for l in legs}):
            out[y] = summarise([l for l in legs if l["entry"][:4] == y])
    if a.json:
        print(json.dumps(out, indent=2))
        return
    cols = ["trades", "entries", "profit_factor", "net_usd", "win_rate_pct", "first_entry", "last_entry",
            "open_at_export", "exits_on_later_date"]
    print("window".ljust(10) + "".join(c.rjust(21) for c in cols))
    for k, v in out.items():
        print(k.ljust(10) + "".join(str(v.get(c, "")).rjust(21) for c in cols))


if __name__ == "__main__":
    main()
