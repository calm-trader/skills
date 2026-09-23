#!/usr/bin/env python3
"""Reject a backtest result record that is missing what every read must record.

Usage: validate_result.py RESULT.json [RESULT.json ...]   (exit 1 on any failure)

Field names follow the operator's result schema in references/operator.md. The
checks are arithmetic, not judgment: they catch a stale or partial read before
anyone reasons about it. Standard library only.
"""
from __future__ import annotations

import json
import sys

REQUIRED = [
    "script", "symbol", "timeframe", "session", "detalization", "deep_backtesting",
    "tester_date_range", "actual_first_trade_entry", "actual_last_trade_entry",
    "net_profit_usd", "gross_profit_usd", "gross_loss_usd", "profit_factor",
    "max_drawdown_usd", "closed_trades", "win_rate_pct", "winners", "losers",
    "commission_type", "commission_value", "slippage_ticks", "qty",
    "trades_exiting_on_later_date", "open_position_at_range_end",
    "inputs", "report_updated_after_input_change", "compile_error",
]


def check(rec: dict) -> list[str]:
    errs = [f"missing: {k}" for k in REQUIRED if k not in rec]
    g = rec.get
    if g("compile_error"):
        return errs  # a compile error is a complete, valid result on its own
    gp, gl, pf, net = g("gross_profit_usd"), g("gross_loss_usd"), g("profit_factor"), g("net_profit_usd")
    if None not in (gp, gl, pf) and gl:
        if abs(abs(gp) / abs(gl) - pf) > 0.002 + 0.001 * pf:
            errs.append(f"profit_factor {pf} != gross_profit/gross_loss {abs(gp) / abs(gl):.3f}")
    if None not in (gp, gl, net) and abs(abs(gp) - abs(gl) - net) > 1:
        errs.append("net_profit_usd != gross_profit - gross_loss")
    n, w, l = g("closed_trades"), g("winners"), g("losers")
    if None not in (n, w, l) and w + l + (g("breakevens") or 0) != n:
        errs.append("winners + losers + breakevens != closed_trades")
    if None not in (n, w, g("win_rate_pct")) and n and abs(100.0 * w / n - g("win_rate_pct")) > 0.05:
        errs.append("win_rate_pct != winners / closed_trades")
    a, b = g("actual_first_trade_entry"), g("actual_last_trade_entry")
    if a and b and a > b:
        errs.append("first trade after last trade")
    if n == 0:
        errs.append("zero trades: check Strategy Properties took the declaration (SKILL.md §11) before calling it a result")
    if g("trades_exiting_on_later_date") not in (None, 0) and not g("multi_session_expected"):
        errs.append(f"{g('trades_exiting_on_later_date')} trades exit on a later date: intraday run is void unless multi_session_expected")
    if g("report_updated_after_input_change") is False:
        errs.append("report not updated after an input change: numbers may be the previous configuration's (SKILL.md §4)")
    return errs


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    failed = False
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as fh:
            errs = check(json.load(fh))
        print(f"{'FAIL' if errs else 'ok  '} {path}")
        for e in errs:
            print(f"     - {e}")
        failed |= bool(errs)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
