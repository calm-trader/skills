---
name: tradingview-backtesting
description: Hard-won operational knowledge for backtesting Pine Script strategies on TradingView — cost model, lookahead traps, Deep Backtesting behaviour, data retention, Strategy Tester quirks, browser automation failures, and what TradingView fundamentally cannot backtest. Load BEFORE writing a Pine strategy, before designing a backtest protocol, before dispatching a browser operator to TradingView, or when a backtest result looks surprising. Triggers: Pine Script, TradingView, Strategy Tester, Deep Backtesting, backtest, strategy(), request.security, bar magnifier, walk-forward on TV, "why does my backtest show".
---

# TradingView backtesting — what actually goes wrong

Every rule below was paid for with a wasted round, a corrupted result, or a defect caught in audit. Tags: **[VERIFIED]** — observed directly in a named Strategy Tester / List of Trades / UI run; **[AUDITED]** — established by code audit or official Pine documentation, acted on, not directly demonstrated in the tester; **[REPORTED]** — asserted by a reviewer or prior report, not independently reproduced. Scoped observations ("on this account", "one 5m engine") mean exactly that — do not promote them to platform laws.

The unifying lesson: **TradingView will nearly always give you a plausible number.** It rarely errors. It silently produces a believable, wrong result — a stale script, a synthetic fill, a blind counter, an uncosted trade. Assume every number is wrong until a specific check says otherwise.

---

## 1. Cost model — the most damaging errors, because results stay plausible

**`slippage` is charged per eligible fill — market and stop orders; limit fills are not slipped.** [AUDITED — reasoned from docs and contract math; never measured in a controlled slippage=1-vs-0 run] A market entry stopped out incurs two slipped ticks round-turn; a market entry reaching a limit target generally incurs one. `slippage = 1` turned an intended $9 NQ round-turn into an outcome-dependent ~$14+. A whole round's numbers can be quietly wrong by 50%.

**Preferred pattern: fold friction into a flat commission and set slippage to zero.** [VERIFIED on one-contract, single-entry/single-exit runs]
```pine
strategy(..., slippage = 0,
         commission_type = strategy.commission.cash_per_order,
         commission_value = 4.5)     // NQ: 4.5/order = $9.00 round turn
```
Per-instrument values used here: **NQ1! → 4.5/order ($9 RT)**, **ES1! → 8.25/order ($16.50 RT)**. Both confirmed in the List of Trades. [VERIFIED] This is a desk all-in cost proxy for that order shape — with partial exits, pyramiding, or multi-contract orders, choose the commission type deliberately and reconcile total charged commission from the List of Trades. **Always verify the realized round-turn in the List of Trades before trusting an instrument's batch.**

**`commission_value` must be const.** Inline `input.float(...)` inside the `strategy()` declaration is not a legal qualifier there (`const int/float` required — a const expression is fine, not only a literal). [REPORTED — flagged by two independent auditors, never compile-tested; do not risk it] Consequence: one script cannot self-adjust cost per instrument. Ship a const and have the operator change it in Strategy Properties for the other instrument, or ship two declaration wrappers around identical logic.

**Insufficient `initial_capital` causes silent order rejection on index futures.** [VERIFIED] When required funds (quantity × price × point value × margin %) exceed equity, TradingView rejects entries **without any error** — a zero-trade or oddly-thin result you hunt in signal logic for days. Desk convention: `initial_capital = 1000000` for one-contract NQ/ES — a convention, not a platform threshold. Scale with size: a 3-contract NQ book was silently capped at $1M and needed $5M (R26). Report realistic margin separately.

---

## 2. Lookahead and repaint — the failures that survive validation

**`barstate.isconfirmed` is TRUE on every historical bar.** [AUDITED] It is *not* an intrabar-versus-close discriminator on history. Code that guards close-only logic with it, while `calc_on_order_fills = true` causes extra intrabar executions, will run the full confirmed-close path from a *fill callback* — reading the bar's final close before the bar's path has completed. That is historical lookahead in a shared module: **invisible in results, identical across every variant, so nothing looks like an outlier.**

**Therefore: keep `calc_on_order_fills = false`** unless you have a specific need and a specific guard. Protection on the fill bar does not require it (see §3).

**`request.security` — choose semantics by context; there is no single safe recipe.** [AUDITED per Pine docs] For a confirmed, non-repainting HTF value, offset the expression *inside the request* and use lookahead: `request.security(sym, "1D", close[1], lookahead = barmerge.lookahead_on)`. **Never `lookahead_on` with an unoffset expression** — that is the classic future leak. The desk's older pattern (`lookahead_off` + outer `[1]`) does not leak on historical bars — Deep BT results stand — but can serve a *developing* HTF value in realtime and repaint on reload; flag any live/forward use for rework. Same-timeframe second-symbol requests need neither; for lower-TF data use `request.security_lower_tf()`. Limit: 40 **unique** `request.*()` calls on non-professional plans (64 on Professional/Ultimate v6) — uniqueness is by context/expression, not source lines. Never pull daily aggregates for the current day. On the NQ continuous-futures feed, a default daily request did **not** equal the desk's 09:30–16:00 RTH aggregate [AUDITED] — accumulate prior-day high/low/close **locally from RTH bars**, or Globex extremes contaminate every level.

**Freeze anything the strategy defines as fixed.** ATR sizing a fixed signal-time bracket must be captured on the signal bar and never recomputed — a live ATR silently widens or erases stops as volatility changes. (If the source rule defines a *dynamic* ATR trail, update it on the stated cadence and tighten one-way — never silently switch between fixed and live semantics.) Levels derived from a range (fibs, extensions) must be computed once from a latched range and stored as absolute prices, tick-normalised with `math.round_to_mintick`.

**Signal-to-fill discipline.** Under the default model (`process_orders_on_close = false`, no `immediately` flags), close-confirmed signals fill no earlier than the next bar's open. Anchor exit levels to `strategy.position_avg_price` (the actual fill), never to the signal bar's close — a next-bar gap otherwise gives longs and shorts different effective risk.

---

## 3. Building a correct exit / bracket

**Protect from the fill instant, not from the next bar.** [AUDITED; fill anchoring confirmed empirically via exact-fill breakeven scratches — a List-of-Trades sighting of a fill-bar stop remains an open operator check] With `calc_on_order_fills = false`, issuing `strategy.exit` only after detecting a non-zero position leaves the position unprotected for its *entire fill bar* — intrabar excursions beyond the stop that recover are silently survived. This **differentially flatters volatile-entry strategies** (opening-range, gap, spike-fade) versus quiet-entry ones, which looks like a real finding.
The fix: submit `strategy.exit(..., profit = ticks, loss = ticks)` **in the same calculation as the entry order**. The emulator anchors relative offsets to the eventual actual fill; the exit is eligible from the next emulator tick, with no observed price path in between.

**OCO within the emulator requires `oca_name` + `oca_type = strategy.oca.cancel`** on paired entries. [AUDITED] Cancelling a sibling at the fill bar's *close* is too late: one bar spanning both sides of a two-sided setup can fill long, then fill short, reversing the position mid-bar with an unmanaged loss. This is *simulated* OCA — it implies nothing about live broker/exchange atomicity.

**Same-bar round trips need a durable record.** [AUDITED for the once-per-close model: `calc_on_order_fills = false`, `calc_on_every_tick = false`] `var` state is subject to rollback. To know that a trade opened and closed inside one bar (so a daily slot is consumed and a persistent setup cannot re-arm), track **changes in `strategy.closedtrades`**, and run that lifecycle block **before** the arming logic. Do not assume the count is rollback-proof under intrabar recalculation — that has no fixture.

**Breakeven semantics.** A stop moved to the exact fill price is a **cash loss** after commission — that is correct and should be reported as such. [VERIFIED — scratch trades returned exactly −$9.00 on NQ] If a scratch shows as zero or positive, the level is wrong. Arm breakeven only on a **confirmed close** through the trigger and change the stop from the next bar — never retroactively — and latch it one-way (`max(oldStop, fill)` long, `min` short) so it can never loosen risk.

**Direction algebra, not mirrored code.** With `d ∈ {+1,−1}`: `target = fill + d*X`, `stop = fill − d*Y`, `trigger = fill + d*Z`. Hand-written long and short branches drift. **Test:** long and short controls entered on the same bars with the same bracket should produce *exactly* mirrored gross figures — one's gross profit equalling the other's gross loss to the dollar. [VERIFIED — a strong, cheap symmetry proof on real data.]

**Stop and target inside one bar cannot be resolved.** TradingView's emulator decides, and you cannot force stop-first. Pre-register the convention, count ambiguous bars, and confirm a candidate's verdict does not flip if all ambiguous bars are scored adversely. [REPORTED] Without finer data the emulator walks open→high→low→close when the open is closer to the high, else open→low→high→close — the up-bar/down-bar folklore is wrong and mis-walked one test matrix.

**EOD flatten on half-days.** `session.islastbar_regular` catching every CME early close is feed-dependent [REPORTED — pending fixtures]; where it misses, the fallback fills at the **18:00 Globex reopen across the halt gap**. Verify half-day fixtures (Jul 3, post-Thanksgiving, Christmas Eve) show the flatten at the last RTH bar — a reopen fill is a visible failure, not "EOD flat".

---

## 4. Deep Backtesting — what it changes

- **Required** for multi-year ranges. Confirm the **DEEP badge** is showing.
- **`plot()` and the Data Window are BLIND under Deep Backtesting.** [VERIFIED] They reflect only the chart's loaded bars (~3 days), not the deep-backtest execution context — diagnostic counters read ~0 while the backtest ran hundreds of trades. Use the **Strategy Tester Performance Summary** and the **List of Trades** for everything.
- **Window-scope every diagnostic counter** (gate with `input.time`). An unscoped `+=` sums whatever bars happen to be loaded and fabricates activity — R31's fake "563-setup funnel collapse" sent a whole diagnosis chasing a ghost. [VERIFIED] Funnels are only readable at all on a **non-Deep** backtest over a recent window where loaded bars == the range.
- Per-leg metrics come from the **All / Long / Short columns** (exact, no scrolling) where that UI revision exposes them.
- **★ THE "FROZEN TESTER" IS MOSTLY NOT FROZEN — THE REPORT DOES NOT AUTO-REFRESH AFTER AN INPUTS-DIALOG EDIT.** [VERIFIED — R68, reproduced and then reversed] Change an input, and the Strategy Tester **keeps displaying the previous configuration's numbers until "Update report" is clicked.** In R68 a diagnostic read returned byte-identical figures to the prior stage; clicking Update Report changed it from 77 trades to the true 34. Toggling back and re-clicking reproduced the original exactly, so both readings were real — the panel was stale, not stuck.
  **This is the mechanism behind the long-standing "identical results across different inputs" folklore, which sat in this document as an unexplained [REPORTED] heuristic for several rounds.** It is not flaky recalculation and it is not a reason to restart Chrome.
  **Rule: after every input change, click "Update report" and re-open the Inputs dialog to confirm the live value, before reading any number.** An input edit that silently reports the previous cell's result is indistinguishable from a real finding — and in a parameter ladder it produces a perfectly plausible, entirely false plateau.
- **Bar detalization** (Bar Magnifier) sits in Properties: `Default (4 ticks/bar)` vs `High (~40 ticks/bar)`, plus `use_bar_magnifier = true`. On one 5m engine (NQ1!, 2024–25) high detalization returned **byte-identical** results including timestamps [VERIFIED] — a useful "is this a fill-resolution artifact?" control *for that engine and window*, not a general theorem. **A byte-identical detalization read is also the frozen-tester symptom above: before crediting the null, prove the tester is live (change any input, observe a different result).** Restore the batch's pre-registered setting afterwards — an unrecorded setting change breaks comparability.

---

## 5. Data availability — instrument-specific, and not what the chart shows

**Chart buffer depth ≠ Deep Backtesting availability.** [VERIFIED on this account/UI] A 2-minute chart's default buffer is only ~3 months, and UI panning adds ~0.5–2 days per drag — establishing retention by scrolling is intractable and answers the wrong question. **Probe retention by reading the first closed-trade date of an actual deep backtest.**

Measured on this account (R34/R35 windows):
| symbol | 2m | 3m | 5m |
|---|---|---|---|
| **NQ1!** (continuous futures) | reaches 2024-01 | reaches 2024-01 | reaches 2024-01, but **NOT 2023-04** (first trade ~2023-07-05) |
| **QQQ** (ETF) | does *not* reach ~15 months back | does not | reaches |

**Retention is instrument-specific** (here NQ1! reached deeper than QQQ — that is an observation, not a futures-vs-ETF law). Never generalise one symbol's retention to another; re-probe per symbol/timeframe.

**Live-edge instability:** [REPORTED — prior desk rounds, not re-measured] 1-minute sub-bar / CVD fetch is unreliable within ~2–4 weeks of the live bar; sign stable, magnitudes wobble. **End development ranges ~5 weeks before today**, trust closed windows, and re-probe the cutoff rather than hard-coding it.

**Warm-up truncates silently.** A 200-session daily filter on a 2024-01 start produces a first trade around 2024-10 — nine months of the window simply gone. **Report first and last closed-trade dates on every read** (the truncation canary). The *fix* is design: **start the Deep-BT range earlier than the analysis window and gate entries with a date input (T0)**, using the early interval as warm-up only. First-trade date is not a readiness proof — distinguish "no signal" from "no data" when a required feed (TICK/VIX/1m) may be missing.

---

## 6. What TradingView fundamentally CANNOT backtest

**Multi-leg / spread / cross-sectional strategies.** [AUDITED — decisive]
Pine strategy orders belong to **the chart symbol**. A script can *read* other symbols via `request.security`, but `strategy.entry` never trades them. Charting a synthetic expression (`QQQ/SPY`) and running a strategy on it produces a profit factor with **no real legs, no real commissions, no real fills, no margin, no dividends** — a plausible, arithmetically meaningless number. (Spread charts also repaint: realtime bars build from ticks, history from minute data.)

**Reject any "spread PF" derived from a synthetic series.** Per-leg Pine runs validate leg mechanics; they are not by themselves a portfolio backtest. The workable method:
1. Pine generates and audits **signals only**.
2. Each leg runs as a **real strategy on its own chart symbol** with real per-leg costs (isolated leg check).
3. Export each leg's **List of Trades as CSV** (works [VERIFIED]).
4. Reconcile **offline** in a ledger that joins legs by a common episode ID + timestamp, **independently recomputes** cash from fills × quantity × multiplier − costs (summing one side and calling it the other is not a test), and pre-defines orphan-leg and portfolio-exit rules. Pine OCA groups do not span symbols or scripts — basket atomicity must be modelled externally. [AUDITED]

Read economics follow: a 2-leg pair costs 2 backtests per configuration; a 9-ETF cross-sectional strategy costs 9–11. Prefer named pairs unless the universe is the hypothesis.

**One symbol NETS.** TradingView nets simultaneous long and short on one symbol — combining multiple strategies' books inside one Pine strategy corrupts both legs (R26 ruling). [AUDITED] Measure portfolios by exporting each frozen strategy's trades and combining offline.

**Rules conditioned on the true session open or intrabar event order.** Pine acts at bar close: "place order at 09:30" is live from 09:35 — for an opening-range system that is a *different strategy*, not a conservative one. Fix where possible: **arm on the last pre-RTH bar of an ETH chart** [VERIFIED for LIT-03/16]. A rule that needs the true open before the opening bar's intrabar path completes (Williams Oops), or breach-then-reclaim ordering inside one bar, **cannot be tested on TradingView at all** — a close-time proxy both adds false trades and drops true ones. Rename such implementations `-PROXY` and never cite them as tests of the source rule. Same class: "last/first session of month" needs a session calendar — `dayofmonth` is only a proxy near weekends/holidays.

---

## 7. Reading the Strategy Tester without being misled

- **The displayed Profit Factor is net of commission per trade; the Profit-structure chart's gross figures are pre-commission.** [VERIFIED] They will not agree, and that is not a read error. Record which one you are quoting, consistently. Reconcile: `net = grossProfit − grossLoss − (round-turn commission × trades)` — valid only after the List of Trades proves a constant round-turn charge per trade; partial exits/pyramiding need the summed actual commissions.
- **Side composition must be read from the All/Long/Short columns or a FULL scroll of the trade list — never from the visible page.** [VERIFIED failure] Sampling the first screen once produced a confident "all trades are long" claim that was wrong (208 long / 19 short), which changed the comparator and therefore the verdict.
- Report **largest single winner as a share of gross profit**. A cell whose profit factor rests on one outsized trade is not a robust result.
- **Know how big a PF difference has to be before it means anything:** `SE(log PF) ≈ √(4.5/n)` on this desk's trade P&L — ±0.25 PF at n≈118, ±0.13 at n≈300; ranking exit cells 0.15 apart needs ~800 trades/cell. A cluster of PF≈1.1 at n≈300 is what a *null* looks like. [AUDITED — R35 calibration]

---

## 8. Browser automation — the failures that look like dead charts

**The blank-canvas "dead layout" is a hidden-tab bug, not WebGL and not corruption.** [VERIFIED, root-caused on this macOS Chrome automation stack, 2026-08]
Signature (diagnose it before applying the fix): legend shows `∅`, plot area white, **every `<canvas>` backing store stuck at 300×150** while its CSS box is correctly sized, **zero console errors**, tab title still ticking a live price.
Cause: an automation-created tab is never the *active* tab, so `document.visibilityState === "hidden"` and TradingView never fires the path that sizes its canvases.
**Six fixes that do NOT work:** CDP click (sets `hasFocus()` but not `document.hidden`), `resize_window`, synthetic `window.dispatchEvent(new Event('resize'))`, hard reload, a new tab, a fresh layout. Hardware acceleration is irrelevant *to this signature*, and a full Chrome quit-and-relaunch does not fix it.
**The fix** is external — make the chart tab the active tab. Minimal one-shot (activates the **newest** matching tab):
```bash
osascript -e 'tell application "Google Chrome"
  set w to window 1
  set t to 0
  repeat with i from 1 to count of tabs of w
    if URL of tab i of w contains "tradingview.com/chart" then set t to i
  end repeat
  if t > 0 then set active tab index of w to t
end tell'
```
For a session, run the maintained watchdog `.claude/skills/tradingview-backtesting/tv-tab-watchdog.sh` (~4s loop, all windows: closes stale chart tabs, activates the newest, does not steal app focus). Do **not** use first-match/window-1 logic — that was the v1 watchdog, and with a stale chart tab present it activates the wrong tab and keeps the operator's tab hidden [VERIFIED failure]. Corollary: **only one chart tab can be live per window** — run multi-instrument work sequentially in one tab.
**Implication:** layouts previously declared "permanently dead" were probably hidden-tab victims. Retry before asking for a replacement.

**A JS visibility override fixes the dead-canvas bug when tab activation is impossible.** [VERIFIED — R68, after the watchdog silently stalled ~3h and `osascript activate` could not reach the real foreground in a sandboxed session] Overriding `document.hidden` / `document.visibilityState` via injected JS made TradingView repaint correctly. This is a **seventh fix, and the first in-band one** — the §8 list of six that do not work stands, and external activation remains preferred, but when no tool can activate the tab this one works. **Also check the watchdog is still alive** (compare its last log line to now) before concluding the chart is broken; a stalled watchdog presents exactly like a dead layout.

**Deep Backtesting may not be disableable at all.** [REPORTED — R68, one account/session, checked exhaustively: date-range menu, Script execution, Bar detalization, Settings/Properties, the "…" context menu; the DEEP badge persisted even at "Last 7 days"] If this generalises, **every technique in this document that depends on a non-Deep read is unavailable** — including the only stated method for reading a diagnostic funnel (§4: "funnels are only readable on a non-Deep backtest over a recent window"). Re-probe before relying on a non-Deep read.
**The replacement technique, which works under Deep and is better anyway: make the funnel out of TRADES, not counters.** Ship one diagnostic arm per funnel stage, each entering a trade when that stage is reached, and read the stage counts off the Strategy Tester's trade count. Trade counts are always visible under Deep Backtesting; `plot()` and the Data Window never are. Costs one read per stage and answers "where does the funnel collapse" exactly.

**A blank screenshot is NOT a dead chart.** Screenshots can capture WebGL canvases blank on a healthy chart. Discriminate on the DOM: legend showing a live price → chart is fine; read everything as DOM text. [VERIFIED]

**Operator tab discipline.** Never create a new tab mid-round; never switch tabs; reach another layout by **navigating the same active tab** (navigation preserves active status). No MCP tool can activate a tab — an operator seeing `document.hidden === true` must stop and report, not self-fix.

**Clipboard paste can silently leave a STALE script in the editor with no error.** [VERIFIED] You then backtest the previous strategy and get perfectly plausible numbers for the wrong thing. **Verify line count and the header line after every paste**, and confirm the Strategy Tester header shows the expected script name. Paste via clipboard only — never keystroke-type the script; editor auto-indent corrupts the multi-line `strategy()` declaration. If `Cmd+V` will not take, dispatch a synthetic `ClipboardEvent('paste')` at Monaco's `textarea.inputarea`. Click *into* the editor first — pasting onto the chart canvas creates a stray drawing.

**Other operator rules.** Verify the symbol **by price** on every read as a secondary check (bands dated 2026-08: NQ ≈ 23–29k, ES ≈ 6.5–7.6k — verify the ticker itself; bands go stale). Pasting alone does not swap the active strategy: use the compile/update control and confirm the header. Re-verify the date range after every recompile (it resets). **The session setting silently reverts to extended hours after a script reload** — re-verify RTH/ETH after every reload, like the date range. Never drag panel dividers. **Never Cmd+S** — it saves to the user's TradingView library. The "All" range button changes chart *resolution*, not just the visible range.

---

## 9. Batch discipline

- **≤6 reads per operator dispatch** (desk workflow convention, not a platform limit — longer sessions correlate with identical-result episodes and operator drift).
- **Save each result to disk immediately after taking it**, never at batch end — platform limits and browser failures cost nothing if completed reads are already persisted.
- Pre-state, per read: symbol, timeframe, session (RTH vs extended), date range, every input that differs, and the expected trade count if known.
- **Trade count is the cheapest integrity check — in an engine built for it.** Where entries are independent of exits (day-slot consumed at entry, no re-entry — the design used for exit surfaces here [VERIFIED at 118/123 per cell]), a stop/target grid must return an **identical** trade count in every cell; a difference means exits are feeding back into entries and the surface is invalid. **If the strategy can re-enter, or an open position blocks later signals, the invariant does not hold** — build the slot discipline first, or compare entry-event IDs instead of counts.
- **In-era validation does not buy out-of-era durability.** [VERIFIED twice] Adjacent-years (R34) and interleaved-checkerboard (R35) partitions were both passed while the sealed out-of-time window failed (0.831; 0.492). No partition of the data you can see substitutes for time you have not seen — reserve a sealed window in the protocol.

---

## 10. Techniques worth reusing

**Win% as a measurement instrument.** With TP at one barrier and SL at the other, the Strategy Tester's **win% *is* the first-touch probability** — a clean way to measure "which side breaks first" claims. Caveat: with no stop and an end-of-day exit, win% becomes an **upper bound** on the touch rate (non-touching days that close profitably score as wins).

**Serve multiple experimental windows from ONE backtest range.** TradingView takes a single contiguous range, so put the window calendar *inside the engine* as a `blockRole ∈ {all, select, validate}` input that gates entries by date. One deep-backtest range then serves selection and validation. **Verify the gate**: `select` count ~half of `all`, and `select` a strict subset *by trade dates/IDs*, not just count. [VERIFIED at exactly 0.500 on one engine] Simulate the role formula over the actual eligible session calendar first — a calendar-day formula left some month-role cells empty.

**A matched placebo is stronger than a clock control.** Keep the strategy's own signal dates and sides, shift only the entry time (e.g. +90 min). Then the null holds date, side and frequency constant and varies only *when* the trade is taken. **Check the placebo's trade count matches the real run** — if a shifted entry can fall past a session cutoff, the day is silently *dropped* rather than delayed, and the control is no longer clean (observed: 2–2.5% count shortfall).

---

## 11. Pine v6 compile/runtime hazards seen repeatedly

All [VERIFIED] observed failures except where tagged. A clean compile does not clear this list — one item is a runtime error.

- **Bools can never be `na` in v6** — neither assign `na` to a bool nor call `na()` on one (CE10123). Do not "wrap it in a ternary with `na()`" — that is the same illegal construct. Restructure: initialise with a definite value, or gate first-bar logic on `barstate.isfirst`.
- **Explicit `by -1` throws a *runtime* error after a clean compile.** Descending loops themselves are fine — write `for i = hi to lo` and let Pine infer the direction; never write a negative `by`.
- **Float division assigned to an `int`** — a compile blocker that survives review easily.
- Inline `input.*` inside the `strategy()` declaration (see §1). [REPORTED]
- `max_bars_back` needs the function form when dynamic historical offsets are large. [REPORTED — lore, no recorded failure]
- **★ `int / int` RETURNS A FLOAT IN PINE v6 — SETTLED EMPIRICALLY, and it cost this desk a whole round.** [VERIFIED — throwaway `indicator()` on a live NQ1! 5m chart, values read from the Data Window, 2026-08-03]
  ```pine
  int hm = 930
  plot(hm / 100)                              // → 9.30      NOT 9
  plot(hm / 100 * 60 + hm % 100)              // → 588.00    NOT 570
  plot(math.floor(hm / 100) * 60 + hm % 100)  // → 570.00    ← the safe form
  ```
  **Always write `math.floor(hm / 100) * 60 + hm % 100`.** Two independent auditors disagreed on this and it was settled by a one-read probe, not by argument — when reviewers contradict each other on platform semantics, **measure it; it is almost always cheaper than the debate.**
  **Why it matters more than it looks:** an `int` declaration whose right-hand side contains `/` will still compile (the float is accepted/truncated at assignment), so **the type annotation is not a guard**. In `IB-ENGINE-v1…v5` this silently made a "09:30–10:30" Initial Balance actually **09:48–10:48**, the 14:30 cutoff **14:48**, and `flatAt=1555` → **988 min = 16:28**, past the 16:00 close, so the clock-based flatten could never fire. **All of R33's results ran on that mis-specified window**; a code comment reading `// 0930 -> 570` sat beside the defect for three rounds. **Treat any `int x = ... / ...` as suspect, and assert one clock value on-chart before trusting a session-based engine.**

---

**`input.time(defval = timestamp(...))` does NOT compile in v6 — CE10123, and dropping the timezone argument does NOT fix it.** [VERIFIED twice — R68, 5 blocking errors both times, on `strategies/aw/AW-ENGINE-v5.pine` lines 15-19] `input.time` requires a **`const int`** `defval`. **Every** form of `timestamp()` types as `simple int`, including the all-literal timezone-less form `timestamp(2024, 2, 1, 0, 0)` — the widely-copied `input.time(timestamp("01 Jan 2021"))` idiom from v5-era scripts is **not** valid here. Do not spend a second operator dispatch re-testing a `timestamp()` variant; the first CE10123 refutes the whole family.
**Two fixes that work:** a literal epoch-millisecond constant (Pine time is ms, not seconds — and note the value must encode the exchange-timezone wall clock you intend), or — preferred, because it is readable and carries no timezone or unit ambiguity — **drop `input.time` entirely and gate on a `YYYYMMDD` integer**: `int t0 = input.int(20240201, "T0 (YYYYMMDD)")`, compared against `year(time, tz) * 10000 + month(time, tz) * 100 + dayofmonth(time, tz)`. That form is const-free, makes the timezone explicit at every call, and uses only multiplication and addition, so it does not reintroduce the `int/int` float hazard.
**Method note:** this was fixed once on confident reasoning about the type system, shipped, and failed identically on the next dispatch — costing a full operator round-trip. Pine's type qualifiers are not reliably derivable by inspection. Per §11's `int/int` precedent: **probe the type in a throwaway `indicator()` before committing a fix to a 800-line engine**, or choose a construct that avoids the qualifier question altogether.

**★ `ta.*` CALLED INSIDE A SHORT-CIRCUITED BOOLEAN SILENTLY RETURNS STALE VALUES.** [VERIFIED — R68] `and`/`or` short-circuit in Pine v6, and **every textual `ta.*` call site carries its own persistent per-bar state that only advances when that site is evaluated.** So `na(x) or ta.barssince(c) > n` skips the `barssince` call entirely on bars where the first operand settles the result — and its counter stops advancing, returning a stale count later. Writing the same `ta.barssince(c)` twice in one expression creates **two independent counters**, each updated on a different subset of bars. TradingView flags this only as a non-blocking **CW10002** warning, which is easy to wave through as lint.
**The fix is to hoist:** compute `int bs = ta.barssince(c)` unconditionally once per bar, then use the local in both branches. **Treat CW10002 as a correctness finding, not a style note** — in R68 this sat inside two of the five HTF-bias confirmations, i.e. in the gate governing every trade of the primary arm, and it was found by the compiler rather than by two adversarial code reviews.

**★ FOUR REVIEW PASSES DO NOT EQUAL ONE COMPILE.** [VERIFIED — R68] The CE10123 above survived two full adversarial code reviews by a frontier model, two builder self-checks with line-by-line walkthroughs, and a verified diff — because **none of them ran the compiler**. Reviews check semantics against a spec; they do not check that the language accepts the program. **Compile the script before spending a supervision pass on it**, and treat "reviewed" and "compiles" as independent properties. The cheapest ordering is: build → compile → review → read.

**"Add to chart" can succeed on a script that never compiled.** [VERIFIED — R68] A tab appeared with the expected strategy name and the Strategy Tester said only "This report requires trade data". **The tell was Strategy Properties showing Commission = 0 Percent while the script declared `cash_per_contract 2.0`** — the `strategy()` declaration had not taken effect and TradingView had fallen back to template defaults. **Check a declared property (commission, initial capital) in Strategy Properties as proof the declaration is live**, not just the tab name; a zero-trade result is otherwise indistinguishable from a signal that never fired.

## 12. Pre-flight checklist

0. **The script COMPILES.** Build → compile → review → read; a reviewed script is not a running script (§11). Zero blocking errors, and treat CW10002 `ta.*`-in-a-short-circuit warnings as correctness findings, not lint.
1. Watchdog running (`tv-tab-watchdog.sh`) **and alive** (check its last log line against now — a stalled watchdog looks exactly like a dead layout); chart tab active (`document.hidden === false`).
2. Script pasted via clipboard; **line count and header verified**; Strategy Tester header shows the expected name; exactly one strategy instance.
3. Symbol verified (ticker + price sanity); timeframe; session (extended hours on/off) as intended — **re-verify session and date range after every reload/recompile** (both silently reset).
4. Deep Backtesting on (DEEP badge); date range set; bar detalization at the pre-registered setting.
5. **Realized round-turn cost confirmed in the List of Trades** before trusting the batch. Also confirm a declared property (commission, initial capital) in **Strategy Properties** — that, not the tab name, is proof the `strategy()` declaration took effect at all.
5b. **After EVERY input change: click "Update report" and re-open the Inputs dialog to confirm the live value** before reading a number. The panel does not auto-refresh, and a stale read is indistinguishable from a finding.
6. First/last closed-trade dates recorded on every read (truncation canary); warm-up handled by an early range start + T0 entry gate.
7. Diagnostic counters window-scoped — or read only on a non-Deep recent window where loaded bars == the range. **If Deep Backtesting cannot be disabled (§8), counters are unavailable entirely: build the funnel out of TRADES instead — one diagnostic arm per stage, each taking a trade when its stage is reached.**
8. Trade count sane against expectation; identical across exit-only cells **only if** the engine's entries are exit-independent.
