#!/usr/bin/env bash
# Self-test for the helper scripts against synthetic fixtures. Needs node and python3.
# Every check here must also be seen to FAIL once (falsify §5): the bad fixtures below do that.
set -u
cd "$(dirname "$0")"
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }

node -e '
const k=require("./tvkit.js"), fs=require("fs");
const want = {
  "fixtures/report-stacked.txt": {net_profit_usd:10000,net_profit_pct:1,gross_profit_usd:20000,gross_loss_usd:10000,profit_factor:2,
    max_drawdown_usd:3000,max_drawdown_pct:0.3,closed_trades:40,win_rate_pct:45,winners:18,losers:22,breakevens:0,
    largest_winning_trade_usd:4000,largest_losing_trade_usd:-500,average_trade_usd:250,commission_load_pct:0.5,
    tester_date_range:"Jan 1, 2024 — Jun 30, 2025",deep_backtesting:true,session_badge:"RTH",detalization:"Default detalization"},
  "fixtures/report-inline.txt": {net_profit_usd:-2500,net_profit_pct:-0.25,gross_profit_usd:22500,gross_loss_usd:25000,profit_factor:0.9,
    max_drawdown_usd:7250.5,closed_trades:50,win_rate_pct:60,winners:30,losers:20,breakevens:0,
    largest_losing_trade_usd:-1200,average_trade_usd:-50,session_badge:"ETH",detalization:"High detalization"}
};
let bad=0;
for (const [f,w] of Object.entries(want)) {
  const r=k.parseReport(fs.readFileSync(f,"utf8"));
  for (const [key,v] of Object.entries(w)) if (r[key]!==v) { bad++; console.log("  "+f+" "+key+": got "+r[key]+" want "+v); }
  if (r.missing.length || r.checks_failed.length) { bad++; console.log("  "+f+" missing/checks: "+r.missing+" "+r.checks_failed); }
}
const side=k.parseReport(fs.readFileSync("fixtures/report-inline.txt","utf8")).pnl_by_side_usd;
if (side.long!==1000 || side.short!==-3500) { bad++; console.log("  side pnl wrong "+JSON.stringify(side)); }
const mut=k.parseReport(fs.readFileSync("fixtures/report-stacked.txt","utf8").replace("10,000.00USD1.00%","10,500.00USD1.00%"));
if (mut.checks_failed.length<2) { bad++; console.log("  mutated gross loss not caught"); }
process.exit(bad?1:0);' && ok "tvkit.js parses both page layouts and catches a corrupted number" || bad "tvkit.js"

out=$(python3 split_trades.py fixtures/trades.csv --window Y24:2024-01-01:2024-12-31 --window Y25:2025-01-01:2025-12-31 --json)
python3 - "$out" <<'PY' && ok "split_trades.py windows, legs vs entries, open and multi-day legs" || bad "split_trades.py"
import json, sys
d = json.loads(sys.argv[1])
exp = {
 "all": dict(trades=4, entries=3, open_at_export=1, net_usd=584.0, profit_factor=2.446, exits_on_later_date=1),
 "Y24": dict(trades=2, entries=2, open_at_export=0, net_usd=-208.0, profit_factor=0.485),
 "Y25": dict(trades=2, entries=1, open_at_export=1, net_usd=792.0, profit_factor=None, exits_on_later_date=1),
}
errs = [f"{w}.{k}: got {d[w][k]} want {v}" for w, e in exp.items() for k, v in e.items() if d[w][k] != v]
errs and print("\n".join("  " + e for e in errs))
sys.exit(1 if errs else 0)
PY

python3 validate_result.py fixtures/result-good.json >/dev/null && ok "validate_result.py accepts a complete record" || bad "validate_result.py good"
msg=$(python3 validate_result.py fixtures/result-bad.json); rc=$?
n=$(printf '%s\n' "$msg" | grep -c '^     - ')
[ $rc -eq 1 ] && [ "$n" -eq 6 ] && ok "validate_result.py rejects the bad record with all 6 findings" || { bad "validate_result.py bad ($n findings)"; printf '%s\n' "$msg"; }

exit $fail
