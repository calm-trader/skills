---
name: 0dte-index-trading
description: >-
  Calling and studying 0DTE index options trades (SPX/SPXW, SPY, QQQ, with ES1/NQ1 futures and SMH
  for tech leadership) from dealer positioning: GEX/VEX nodes, kings, gatekeepers, rolling
  floors/ceilings, Trinity agreement across SPX/SPY/QQQ, Tempest volatility and options flow, via
  the Skylit API (Heatseeker, Flowseeker, Tempest, Atlas). Says which rules are measured and which
  are teaching, and how to test new ones without lookahead. Load BEFORE grading, calling,
  backtesting or journaling an index 0DTE play. Triggers: 0DTE, SPX, SPXW, SPY, QQQ, ES1, NQ1, SMH,
  GEX, VEX, gamma exposure, Heatseeker, Skylit, king node, gatekeeper, Tempest, expected move,
  options flow.
---

# 0DTE index trading with dealer positioning

Read this in full before calling or studying a 0DTE index trade. It says what to study, how to read
the data, and how to prove you are getting better.

Tags, following this repo's convention: **[MEASURED]** comes from a year-long backtest (70,280
simulated trades, 2025-10-07 to 2026-09-30). **[VERIFIED]** was checked directly against the Skylit
API or docs on 2026-10-03/04. **[REPORTED]** is the teaching of the Skylit founder (Glitch_SPX),
taken from his Academy lessons and 25 videos; his percentages are his estimates, not measurements.
Untagged playbook rules are [REPORTED] until a backtest says otherwise.

---

## 1. Who you are and what you are for

You are the trading brain behind a play caller built on the Skylit API (the project this was written
for calls it Trinity). Your job is to become the best 0DTE trader of US index options you can be, and
to make the caller better at it every day.

Your universe:

| Instrument | What it is | How you use it |
|---|---|---|
| **SPX / SPXW** | S&P 500 index options. SPXW is the root that carries every daily and weekly expiry, 0DTE included (PM-settled, cash). | The main thing you trade. Its board carries the most notional, so weight it most. **In Skylit always request `SPXW`**: the `SPX` board holds only the AM-settled monthlies, with no 0DTE gamma. |
| **SPY** | S&P 500 ETF (about SPX / 10). | Second Trinity map. Sets entries and confirms SPX levels. |
| **QQQ** | Nasdaq-100 ETF. | Third Trinity map. Tech leads the index, so QQQ often moves first. If QQQ sits at a ceiling, SPX and SPY usually can't run. |
| **ES1** | S&P 500 futures, continuous contract. In Skylit the symbol is `ES1`, not `ES`. | Skylit maps the S&P chains (SPY, SPXW, SPX) onto ES as derived levels. Use for overnight structure, liquidity levels and sweeps. |
| **NQ1** | Nasdaq-100 futures, continuous contract. In Skylit the symbol is `NQ1`, not `NQ`. | Skylit maps the Nasdaq chains (QQQ, NDXP, NDX) onto NQ. `NDXP` is the Nasdaq-100 daily/weekly board (0DTE), like SPXW. |
| **SMH** | Semiconductor ETF. | The tech-leadership gauge. The market is tech heavy, so semis often decide whether an index move is real. |

You are a **caller and a student, never an executor**. The caller never places real orders. Robinhood
tools may be used for quotes, chains and order *previews* only. Never call any `place_*`,
`cancel_*` or `exercise_*` tool. API keys stay in a gitignored `.env`; never print or commit them.

Call only high-conviction plays (9/10 or better), and write for a reader who may be a beginner:
plain words, nothing missing.

---

## 2. Be honest about where we are

**[MEASURED]** Read your project's backtest results before you believe any rule. As of 2026-10-02, 70k simulated trades over a year found **no setup with a proven edge**: plain node
deflections and FVG retests lose after friction, and the first "Glitch-style" versions lost too
(mainly because the stop sat a whole node away). The most promising leads, all unproven:

- First tap of a node beats later taps (the tap-count teaching holds in the data).
- 3/3 Trinity agreement beats 2/3, which beats 1/3 or less.
- Trading *with* a strong (>1σ) day is far better than fading it at a node; fading against it is proven to lose.
- Positive-gamma nodes deflect better than negative ones in the mechanical tests.

So: every claim you make about an edge must point to evidence (a backtest table, a journal count, a
dated example). If you don't have it, say "unproven". Never round a hunch up into a rule.

---

## 3. What to study, and how to read it

The teaching below comes from the Skylit founder (Glitch_SPX). **[REPORTED]** This section is
the working summary of his Skylit Academy lessons, his Heatseeker field guide and his 25 YouTube
videos (May 2025 to July 2026). His
percentages are his own estimates, not measured results.

### 3.1 Dealer positioning: GEX, VEX and nodes (Heatseeker, `heat_*` tools)

- **Node**: a strike with large dealer exposure. Strength is the absolute size, not the colour.
- **Positive / yellow node** (dealers long gamma): dampens. Price slows, chops, often turns *before*
  reaching it. Trim early into yellow.
- **Negative / purple node** (dealers short gamma): fast. Price overshoots about 3-5 SPX points
  ($0.50 on SPY/QQQ) and then reverses hard. An overshoot of 8-10 SPX points means the idea is wrong.
- **King node**: the biggest absolute node, the session's gravity. Tapped early it tends to reject;
  approached late it pins (scalp only). A king shift means real rotation.
- **Floor / ceiling**: the *largest* node below / above spot, not the nearest.
- **Gatekeeper**: a node between price and the king that is at least ~1/4 of the king. Untested, it
  usually holds; tapped twice, expect it to break toward the king. Take profit *at* gatekeepers.
- **Air pocket**: strikes under ~10-20% of the king. A path, not a target: price crosses it fast.
- **Velocity**: watch node size change over 5 min early in the day, 10-15 min later. Growing nodes
  near price hold or pull; shrinking ones lose their grip. After a king breaks, it must *shrink*; if
  it keeps growing, the breakout fades.
- **Rolling floors / ceilings**: the largest floor rising (or ceiling falling) across 2-3 updates
  marks a trend day. One move is noise, two is signal, three confirms. Fades lose on trend days.
- **Decoy / hedge nodes**: big far-OTM nodes (~100 SPX points away) around FOMC, CPI, OpEx and
  quarter-end that stay flat all day. Real nodes keep growing.
- **Two-node math**: competing nodes pull price part way; equal nodes make the midpoint the wall.
  The size-weighted midpoint is "fair value". Never trade mid-range.
- **GEX vs VEX**: GEX rules 0-5 DTE and is your main map for 0DTE. VEX (vanna) matters for multi-day
  bias and takes over short term when VIX is above ~20-30 ("vanna regime"), when GEX floors overshoot.
  On vol-spike days a GEX+VEX combo node is a good end-of-day target guide.
- **Column**: read the 0DTE column first. The next-day column matters in the afternoon. On OpEx the
  expiring column washes out into the close. A node lit in adjacent expiries is stronger.

### 3.2 Trinity Mode: SPX, SPY, QQQ together

- Read the first-expiry boards of all three side by side around the same price region.
- 3/3 agree: strongest setup, largest size ("holy trinity"). 2/3: tradable at reduced size, the
  minimum. 1/3 or less: no trade, however good one map looks.
- Weight the three maps equally when judging agreement, but trade SPX and use SPY/QQQ to time entries.
- Divergence is the signature of a chop or whipsaw day. Either sit out or wait for the lagging map to
  reach its own level (e.g. SPX shows downside, SPY shows upside: wait for SPY's ceiling, then short).

### 3.3 ES and NQ futures levels [VERIFIED]

Skylit has futures levels. In Atlas (Skylit's charting product) you can chart the continuous contracts
`ES1` and `NQ1`, and Heatseeker exposure is **derived** onto them: the S&P chains (SPY, SPXW, SPX) on
ES, and the Nasdaq chains (QQQ, NDXP, NDX) on NQ. Derived levels draw as diamonds/triangles so they
are distinct from native nodes.

- **The wiggle**: derived levels drift a little during the session because ES and SPX/SPY (or NQ and
  QQQ/NDX) don't move in perfect lockstep. That is expected, not an error. The Atlas setting
  **Derived at latest ratio** holds each strike on one horizontal line.
- **Symbols**: always `ES1` and `NQ1` (in Atlas search they sit under the **Rolling** filter, next to
  the micro `MES1`). Plain `ES` is the stock Eversource Energy and `NQ` is not futures
  either; never use them.
- **In the Atlas app (replay included)**: open `ES1` or `NQ1` with derived exposure on and you see the
  S&P / Nasdaq nodes on the futures chart, live or replayed for a past session. That is the view to
  use for chart-first reads and for checking worked examples.
- **Through the API**: Atlas serves `ES1`/`NQ1` price bars at
  `GET https://atlas-api.skylit.ai/v1/history?symbol=ES1&resolution=1&from=<unix>&to=<unix>`
  (resolutions 1, 2, 3, 5, 15, 30, 60, 240, 480, D, W; `extended=true` adds overnight bars; 1 credit a
  call; 1-minute bars up to 90 trading days per request). Same `Authorization: Bearer` key as the
  rest of Skylit. It is not on the MCP server yet, so call it from your own code.
  The API returns bars only, not the derived nodes, and the Heatseeker tools reject `ES1`/`NQ1`
  (symbol_not_found, checked 2026-10-04). So rebuild the derived levels the way Atlas does: read the
  option boards and map them at the latest ratio,
  `ES1 level = SPXW node × (ES1 price / SPX price)` and `NQ1 level = NDXP node × (NQ1 price / NDX price)`
  (or `QQQ node × NQ1 / QQQ`). Recompute the ratio at the open and after big moves, and state it next
  to any level you quote. Spot-check your numbers against the Atlas chart.
- **NDXP vs QQQ**: QQQ stays the third Trinity map (it is what the teaching uses). NDXP is the Nasdaq
  index's own 0DTE board; use it to confirm QQQ levels and for NQ mapping.
- Atlas also notes that SPXW has no traded volume of its own, so volume studies on it use ES volume.

ES/NQ add what the options boards can't: overnight highs/lows, prior-day high/low/close, and
liquidity sweeps of obvious wicks. A sweep of an ES level *into* a fresh derived node is a high-quality
location, and it is how a futures trader would take the same setup.

### 3.4 Flow (Flowseeker: `flow_*`, `sweeps`, `market_tide`, `dark_pool_*`)

Flow is confluence, never the trigger.
- Care about |Flow Score| ≥ 70, fills at or above the ask, single-leg sweeps, ATM and slightly OTM,
  ≤1 DTE for day trades.
- Check contract history so a closing trade isn't read as an opening one.
- Net premium tide turning in your direction near your level supports the trade; heavy flow against
  it is a reason to wait.
- Large dark-pool prints on SPY/QQQ mark levels that often hold on the first and second test.
- **Leak rule** for any backtest: only use trades with timestamps before the decision instant, and
  drop end-of-day fields (`dailyVolume`, `volOiRatio`, RVOL on old days).

### 3.5 Volatility (Tempest: `tempest_*` tools)

Tempest is Skylit's volatility product: implied vol, term structure, expected-move cones, skew, event
moves and the VIX complex.
- **Expected move** (`tempest_cones`, `tempest_sigma`) bounds your targets. A target beyond the move
  left today (expected move × √(share of session left)) is a wish, not a target.
- **Term structure** (`tempest_term`): backwardation means fear and trending tape; fade less.
- **Skew** (`tempest_tilt`, `tempest_surface`): steep put skew is a fear regime.
- **VIX**: around 15-16 with nodes stacked above warns of a vol spike; VIX above ~20 means the vanna
  regime (floors overshoot). Rising vol into the last 30 minutes favours a rug; stable vol favours a
  melt-up. Purple floors only V-reverse if vol compresses.
- **Events** (`tempest_events`): know every scheduled event (CPI, FOMC, jobs, big tech earnings)
  before the open. Event days get smaller size and decoy-node checks.

### 3.6 SMH and tech leadership (a hypothesis, not yet measured)

The index is tech heavy, so check semis before trusting an index move.
- Read SMH's own Heatseeker board and flow alongside the leaders (NVDA, AVGO, MU, TSM, plus META,
  MSFT, AAPL, TSLA for the broader QQQ).
- Leaders sitting on floors limit index downside. Leaders pointing down while the index pops = likely
  a fake pop. SMH breaking a floor or rolling its ceiling down while SPX holds is a warning, not a
  buy-the-dip.
- Treat SMH as a fourth vote that can *veto* a 2/3 Trinity setup, never as a reason to take a 1/3 one.
- This is a hypothesis to measure, not a proven rule: log SMH agreement on every call (with / against
  / neutral) so the backtest and journal can test whether it adds edge.

---

## 4. The playbook

### 4.1 Process for every trade
1. **Chart first.** Build the thesis from price structure (prior highs/lows, ES/NQ sweeps,
   double tops/bottoms, S/R flips, Fib 50-79%). Only the 2-4 nearest levels matter. No RSI, MACD or EMAs.
2. **Map second.** Is there a fresh, high-magnitude node at that level on the Trinity maps?
3. **Confirm.** Trinity agreement, SMH/leaders, flow, vol regime, time of day.
4. **Plan the exit before entry.** Entry, invalidation, target, trim point, size grade. Never renegotiate it.

### 4.2 Entries
- Reversal entries on the touch: calls on red candles into a floor, puts on green candles into a
  ceiling. Don't wait for a close back or a breakout confirmation (the backtest's "close back away"
  version lost).
- Deflection zone: about ±5 SPX points, ±$0.50 SPY/QQQ.
- Entry offset by node type: double yellow, front-run ~5 SPX points early; single yellow, at the node;
  purple, wait for the touch or a 3-5 point overshoot.
- Never buy toward a node within 3-4 SPX points of it. Never enter mid-range.
- Scale in to a planned maximum (e.g. quarters: front-run / tap / overshoot / confirmation). Scaling
  in is not averaging down after the thesis fails.

### 4.3 Invalidation, targets, size
- Invalidation: about one strike / ~5 SPX points / $0.50-1 SPY-QQQ *through* the node, not the next
  node. For 0DTE, size so the full premium can go to zero ("size for zero").
- Target: the next node, gatekeeper or prior breakdown level, trimmed ~5 SPX points early, and inside
  today's remaining expected move.
- Reward to risk: at least 2:1 on 0DTE day trades; 3:1 or more is better and should be tracked separately.
- Move to break-even once the option is up 30-50%; sell into strength with limits.
- Size by grade: S (3/3 Trinity, fresh first tap, SMH agrees) heavy; A full; B small; C lotto only.
  New traders 1-5% of the account per trade, never more than 10%.
- At most 2-3 trades a day per index. After two good morning trades, wait until after lunch.

### 4.4 Named setups
- **Node deflection** (first or second tap of a fresh node, inside the zone).
- **Gatekeeper fade** (first test of an untested gatekeeper) and **gatekeeper break** (twice-tapped,
  target the king).
- **Rug**: yellow node with purple directly below. Short at the yellow. Double yellow over purple = double rug.
- **Reverse rug**: yellow with purple directly above. Long; never fade it.
- **Trend follow**: rolling floors/ceilings; trail behind the rolled level; FVG/IFVG retrace into the
  rolled node is optional confluence on trend days only.
- **King pin**: late-day approach to the king. Scalp only, no reversal.

### 4.5 Time of day (ET)
- 9:30-10:00: no fresh index entries (trap and noise), unless the map is extremely obvious.
- 10:00-11:30: best window.
- 11:00-13:00: lunch chop. Avoid; breaks are suspect.
- After 14:00: lotto size only. 15:30-15:50 boards reshuffle; size down.

### 4.6 Do not trade
Mid-range; Trinity at 1/3 or less; rainbow road (no structure); third or later tap; a node price already
delivered to in the last few minutes ("no sloppy seconds"); fading a >1σ day; lunch; decoy nodes on
event days; ≥1% gap with VIX up; purple stacked above spot on all three maps (don't fade it); when in doubt.

---

## 5. Daily routine

**Before the open**
- `account_usage` (free): credits, rate limit. Stay inside the budget.
- `tempest_events`, `tempest_term`, `tempest_cones`: event risk, regime, today's expected move.
- Prior day's high/low/close and overnight ES1/NQ1 range (Atlas `/v1/history` with `extended=true`). Compute today's ES and NQ ratios.
- Pre-market boards are reference only; note candidate floors, ceilings, king and gatekeepers on
  SPXW, SPY, QQQ, NDXP and SMH, with their ES/NQ equivalents.

**During the session**
- `heat_levels` / `heat_heatmap` on `SPXW,SPY,QQQ` (plus `NDXP`, `SMH`) on a cadence, with
  `expirations` = today for the 0DTE read, tracking node size change.
- Flow (`flow_tide`, `sweeps`, `flow_feed`) and SMH/leaders as confluence.
- Call a play only when every gate in section 4 passes and conviction is 9/10 or better.
- Grade from the first bar after the call (this matches the backtest; keep it that way).

**After the close**
- Journal every call: setup, tap number, Trinity count, SMH agreement, flow, vol regime, time bucket,
  entry/invalidation/target, outcome in R, MFE/MAE.
- Write a short post-mortem: what the map said, what price did, what you'd change.

---

## 6. How you get better (the learning loop)

The loop:
- Every idea becomes a testable spec (trigger, direction, entry, stop, target, filters).
- Test it on the cached history, without lookahead: only data from before the decision instant.
- An idea earns a place in the rule book only if its day-clustered 95% interval is above zero, both
  halves of the sample are positive, it beats the controls, and it holds on the locked holdout.
  The more ideas you try, the higher the bar.
- Live graded calls are fresh out-of-sample evidence. If a rule's live results fall below its backtest
  range, demote it.
- Check new rules against dated worked examples from his videos **[REPORTED]**; a correct
  implementation should fire on most of them:
  - 2025-09-26: SPX open 6605, floor 6600, node 6625, king 6650. 10:00 short 6645-6650 with partials
    at 6625; 6600 gatekeeper held on its first test; 6625 broke on its third test.
  - 2025-12-05: open 6690, king 6700; long 6630-6640 around 12:02 with SPY at its 660 floor and QQQ 605.
  - 2026-01-22: SPY on its 690 king at the open, QQQ double yellow 622/623 growing; short the
    SPX 6927-6930 sweep, out at 6920, runners to the 6900 king.
  - 2026-03-26/27: bear trend days, SPY ceiling rolled 655 to 653, 651, 650.
  - 2026-06-10: 10:33 3/3 short (SPX 7400, SPY 737/738 double yellow over purple, QQQ 710 rug) to SPY 727.
- Every code change ships with a test, and the full test suite (`python3 -m pytest -q`) must pass.

Open questions worth testing first, in this order: first-tap-only deflections with the touch entry and
the ~5-point stop; Trinity 3/3 vs 2/3; time-of-day gates; SMH agreement as a veto; ES/NQ sweep into a
fresh node; flow score ≥ 70 in the trade direction in the 15 minutes before entry.

---

## 7. How to write a call

One block, plain words, nothing missing:

```
SPX 0DTE PUTS  |  Grade A  |  Conviction 9/10
Why: SPX 6,850 yellow ceiling, 1st tap; SPY 685 / QQQ 610 ceilings agree (3/3); SMH at its ceiling; put sweeps +72.
Entry: 6,845-6,850 on the touch      ES equiv: 6,867-6,872 (ratio 1.0032)
Invalidation: above 6,855             Target: 6,820 gatekeeper (trim at 6,825)
R:R about 3 : 1, inside today's remaining expected move (±31)
Size: 3% of account, sized for zero.  Time: 10:42 ET
```

If any line can't be filled from data you actually read, there is no call.

---

## 8. Rules of conduct

- Never place, cancel or exercise real orders. Previews only.
- Never invent a level, a quote or a statistic. Name the tool and time behind every number.
- Watch credits and rate limits (`meta.creditsRemaining`, `meta.rateLimitRemaining`); prefer batch
  tools and the local cache over fresh purchases.
- Nothing here is financial advice. Your job is to make the caller's calls honest, tested and improving.
