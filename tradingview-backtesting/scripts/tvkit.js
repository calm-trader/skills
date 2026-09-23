// tvkit.js — read TradingView state and Strategy Tester metrics as JSON, one call each.
//
// Browser (operator): paste this whole file into ONE javascript tool call per page load.
// It installs window.__tvkit and returns the page state. Later calls are tiny:
//   __tvkit.state()    -> chart/tester health checks (§8, §12)
//   __tvkit.report()   -> Strategy Tester metrics parsed from the report's page text
// A navigation or reload drops window.__tvkit; re-inject after one.
//
// Node (tests / offline): node tvkit.js <captured-page-text.txt>  -> prints report JSON.
//
// Status: parseReport is tested against captured Strategy Tester text (fixtures/ and
// four private captures). state() uses DOM heuristics that have NOT been run against a
// live page yet: treat an unexpected value as "check by hand", not as a finding.
(function (root) {
  "use strict";

  // TradingView prints U+2212 for minus and uses thousands separators.
  function num(str) {
    if (str == null) return null;
    const m = String(str).replace(/−/g, "-").match(/-?[\d,]*\.?\d+/);
    return m ? parseFloat(m[0].replace(/,/g, "")) : null;
  }
  function nums(str) {
    return (String(str).replace(/−/g, "-").match(/[+-]?[\d,]*\.?\d+/g) || [])
      .map(function (t) { return parseFloat(t.replace(/,/g, "")); });
  }
  function lines(text) {
    return String(text).split(/\r?\n/).map(function (l) { return l.trim(); }).filter(Boolean);
  }
  // Value on the line after an exact label; the first match wins (Key stats come first).
  function after(ls, label, from) {
    for (let i = from || 0; i < ls.length - 1; i++) if (ls[i] === label) return ls[i + 1];
    return null;
  }
  function idx(ls, label, from) {
    for (let i = from || 0; i < ls.length; i++) if (ls[i] === label) return i;
    return -1;
  }
  // "Winners  43 trades  60.56%" (one line) or "Winners" / "20 trades" / "46.51%" (three lines).
  function bucket(ls, label, from) {
    for (let i = from; i < ls.length; i++) {
      if (ls[i] === label) return num(ls[i + 1]);
      if (ls[i].indexOf(label + " ") === 0 && /trades/.test(ls[i])) return nums(ls[i])[0];
    }
    return null;
  }
  // "+8,127.00 USD" on one line, or "+8,127.00" then "USD".
  function sidePnl(ls, from, tag) {
    for (let i = from; i < Math.min(ls.length, from + 12); i++) if (ls[i] === tag) return num(ls[i + 1]);
    return null;
  }

  function parseReport(text) {
    const ls = lines(text);
    const out = {};
    const net = after(ls, "Total PnL");
    if (net) { const n = nums(net); out.net_profit_usd = n[0]; out.net_profit_pct = n[1] != null ? n[1] : null; }
    const dd = after(ls, "Max drawdown");
    if (dd) { const n = nums(dd); out.max_drawdown_usd = Math.abs(n[0]); out.max_drawdown_pct = n[1] != null ? Math.abs(n[1]) : null; }
    const pt = after(ls, "Profitable trades");           // "46.51%20/43"
    if (pt) { const m = pt.match(/([\d.]+)%\s*(\d+)\s*\/\s*(\d+)/); if (m) { out.win_rate_pct = +m[1]; out.winners = +m[2]; out.closed_trades = +m[3]; } }
    out.profit_factor = num(after(ls, "Profit factor"));
    const gp = after(ls, "Gross profit"); if (gp) out.gross_profit_usd = Math.abs(nums(gp)[0]);
    const gl = after(ls, "Gross loss");   if (gl) out.gross_loss_usd = Math.abs(nums(gl)[0]);
    const cl = after(ls, "Commission load"); if (cl) out.commission_load_pct = num(cl);
    const ex = after(ls, "Expectancy"); if (ex) out.average_trade_usd = nums(ex)[0];
    const lp = after(ls, "Largest profit"); if (lp) out.largest_winning_trade_usd = Math.abs(num(lp));
    const ll = after(ls, "Largest loss");   if (ll) out.largest_losing_trade_usd = -Math.abs(num(ll));
    const tt = idx(ls, "Total trades");
    if (tt > 0) {
      const n = num(ls[tt - 1]);
      if (out.closed_trades == null) out.closed_trades = n;
      else if (n !== out.closed_trades) out.closed_trades_conflict = [out.closed_trades, n];
      const w = bucket(ls, "Winners", tt); if (w != null) out.winners = w;
      out.losers = bucket(ls, "Losers", tt);
      out.breakevens = bucket(ls, "Breakevens", tt);
    }
    const as = idx(ls, "All signals");
    if (as >= 0) out.pnl_by_side_usd = { short: sidePnl(ls, as, "S"), long: sidePnl(ls, as, "L") };
    // Header facts that live in the same page text.
    const dr = ls.find(function (l) { return /^[A-Z][a-z]{2} \d{1,2}, \d{4} — [A-Z][a-z]{2} \d{1,2}, \d{4}$/.test(l); });
    out.tester_date_range = dr || null;
    out.deep_backtesting = ls.indexOf("DEEP") >= 0;
    out.session_badge = ls.indexOf("RTH") >= 0 ? "RTH" : (ls.indexOf("ETH") >= 0 ? "ETH" : null);
    const det = ls.find(function (l) { return /detalization$/i.test(l); });
    out.detalization = det || null;
    // Consistency checks the reader should never skip.
    const want = ["net_profit_usd", "profit_factor", "closed_trades", "win_rate_pct", "gross_profit_usd", "gross_loss_usd", "max_drawdown_usd"];
    out.missing = want.filter(function (k) { return out[k] == null || Number.isNaN(out[k]); });
    const checks = [];
    if (out.gross_profit_usd != null && out.gross_loss_usd) {
      const pf = out.gross_profit_usd / out.gross_loss_usd;
      if (out.profit_factor != null && Math.abs(pf - out.profit_factor) > 0.002 + 0.001 * pf) checks.push("profit_factor != gross_profit/gross_loss (" + pf.toFixed(3) + ")");
    }
    if (out.gross_profit_usd != null && out.gross_loss_usd != null && out.net_profit_usd != null &&
        Math.abs(out.gross_profit_usd - out.gross_loss_usd - out.net_profit_usd) > 1) checks.push("net != gross_profit - gross_loss");
    if (out.winners != null && out.losers != null && out.closed_trades != null &&
        out.winners + out.losers + (out.breakevens || 0) !== out.closed_trades) checks.push("winners+losers+breakevens != closed_trades");
    if (out.closed_trades_conflict) checks.push("two different trade counts on the page");
    out.checks_failed = checks;
    return out;
  }

  function state() {
    const d = root.document;
    const text = d.body ? d.body.innerText : "";
    const ls = lines(text);
    const canv = Array.prototype.slice.call(d.querySelectorAll("canvas"));
    const stuck = canv.filter(function (c) { return c.width === 300 && c.height === 150 && c.clientWidth > 300; }).length;
    const btn = function (re) {
      return Array.prototype.slice.call(d.querySelectorAll("button,[role=button]")).some(function (b) { return re.test(b.innerText || b.getAttribute("aria-label") || ""); });
    };
    const dr = ls.find(function (l) { return /^[A-Z][a-z]{2} \d{1,2}, \d{4} — [A-Z][a-z]{2} \d{1,2}, \d{4}$/.test(l); });
    const di = dr ? ls.indexOf(dr) : -1;
    return {
      title: d.title,                                   // ticker and last price: check both
      hidden: d.hidden, visibility: d.visibilityState,  // must be false / "visible" (§8)
      canvases: canv.length, canvases_stuck_300x150: stuck,
      legend_empty: ls.indexOf("∅") >= 0,
      session_badge: ls.indexOf("RTH") >= 0 ? "RTH" : (ls.indexOf("ETH") >= 0 ? "ETH" : null),
      deep_badge: ls.indexOf("DEEP") >= 0,
      detalization: ls.find(function (l) { return /detalization$/i.test(l); }) || null,
      date_range: dr || null,
      strategy_title_guess: di > 0 ? ls[di - 1] : null, // heuristic: the line before the range
      update_report_visible: btn(/update report/i),     // true => the report is stale (§4)
      requires_trade_data: /This report requires trade data/.test(text),
      compiler_codes: (text.match(/\bC[EW]\d{4,5}\b/g) || []).filter(function (v, i, a) { return a.indexOf(v) === i; })
    };
  }

  const kit = { parseReport: parseReport, state: state,
                report: function () { return parseReport(root.document.body.innerText); } };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = kit;
    if (require.main === module) {
      const f = process.argv[2];
      if (!f) { console.error("usage: node tvkit.js <page-text.txt>"); process.exit(2); }
      const r = parseReport(require("fs").readFileSync(f, "utf8"));
      console.log(JSON.stringify(r, null, 2));
      process.exit(r.missing.length || r.checks_failed.length ? 1 : 0);
    }
  } else {
    root.__tvkit = kit;
    return JSON.stringify(state());
  }
})(typeof window !== "undefined" ? window : globalThis);
