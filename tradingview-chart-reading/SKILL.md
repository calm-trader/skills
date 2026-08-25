---
name: tradingview-chart-reading
description: >-
  Reading a live TradingView chart in a browser — indicator values, OHLC and study inventory off a
  saved layout — without being misled. Covers the hidden-tab bug that makes a healthy chart look
  dead, why the Data Window and not the legend is the source of values, which studies cannot be read
  at all, and what must never be touched on an account with a broker panel. Load BEFORE dispatching
  any agent to read a TradingView chart. Triggers: TradingView, chart read, indicator values, Data
  Window, object tree, saved layout, EMA/Bollinger/ATR values, "read my chart", "what is on the
  chart".
---

# Reading a TradingView chart without being misled

For **reading a live chart**. For writing Pine strategies and running the Strategy Tester, see the
sibling `tradingview-backtesting` skill — its lesson applies here too: **TradingView will nearly
always give you a plausible number.** It rarely errors. It silently returns a believable, wrong one.

Tags: **[VERIFIED]** — observed directly. **[AUDITED]** — reasoned from code or docs. **[REPORTED]**
— asserted, not reproduced.

---

## 1. Prove the chart is alive before reading anything

**A blank chart is almost never a broken chart. It is a hidden-tab bug.** [VERIFIED — root-caused on
a macOS Chrome automation stack, 2026-08]

Signature, which you must diagnose before applying any fix: legend shows `∅`, plot area white,
**every `<canvas>` backing store stuck at 300×150** while its CSS box is sized correctly, **zero
console errors**, and the tab title still ticking a live price.

Cause: a tab created by browser automation is never the *active* tab, so
`document.visibilityState === "hidden"` and TradingView never runs the path that sizes its canvases.

**Six fixes that do NOT work:** CDP click (sets `hasFocus()` but not `document.hidden`),
`resize_window`, a synthetic `window.dispatchEvent(new Event('resize'))`, hard reload, a new tab, a
fresh layout. Hardware acceleration is irrelevant *to this signature*, and quitting Chrome entirely
does not help.

**The fix is external — make the tab active.** Run `tv-tab-watchdog.sh` (shipped beside this file)
for the session: a ~4s loop across all windows that closes stale chart tabs, activates the newest,
and does not steal application focus. Stop it when you finish — **it closes the operator's own chart
tabs while it runs.**

Do not use first-match or window-1 logic. That was the v1 watchdog, and with a stale chart tab
present it activates the wrong tab and leaves the operator's hidden. [VERIFIED failure]

Corollary: **one live chart tab per window.** Run multi-instrument work sequentially in one tab, and
never run two chart-reading agents at once — they share one Chrome, and each one's watchdog treats
the other's tab as stale.

**Not every site behaves this way.** On one vendor's canvas-heavy page, `visibilityState` stayed
`hidden` with canvases at 300×150 and *taking a screenshot forced it to paint*, after which the data
loaded correctly. [VERIFIED, once] So `hidden` alone is not proof of an unloaded page. **Judge
readiness on the data**: canvases off 300×150, values present, price ticking.

**A blank screenshot is not a dead chart.** Screenshots capture WebGL canvases blank on perfectly
healthy charts. Discriminate on the DOM, never on the image. [VERIFIED]

---

## 2. Read values from the Data Window, not the legend

[VERIFIED] On the account this was established against, the chart legend renders **only the price
source** — `O/H/L/C` and the day change — even with four studies loaded and the legend expanded.
Every attempt to enumerate studies from `[data-name="legend-source-item"]` returned an empty array
while four studies were live on the chart.

The working path is the right-hand panel: **Object tree** for the inventory, **Data window** for the
values.

```js
document.querySelector('.layout__area--right').innerText
// "Object tree | Data window | META · NASDAQ, 3 | Vol | FVG+iFVG+BPR | BB | TEMA | TEMA"
```

**The Data Window is cursor-anchored.** It reports values *at the hovered bar*; with no hover it
reports the last bar. Its `Date`/`Time` header is therefore **part of the reading** — capture it, or
you cannot tell a live read from a stale one, nor a last-bar read from an accidental mid-chart hover.

**During market hours the last bar is the FORMING one.** [VERIFIED] With the cursor off the chart,
the Data Window defaults to today's incomplete candle. If you want a closed session, hover the
*previous* candle deliberately and record which bar you took. An indicator computed on a partial bar
flips and un-flips as the bar fills, with nothing marking it provisional.

---

## 3. What cannot be read at all

**A study that draws boxes has no Data Window row.** [VERIFIED] A fair-value-gap study
(`FVG+iFVG+BPR`) appeared in the Object tree, was plainly visible on the chart, and contributed
**nothing** to the Data Window — because it has no `plot()` series. Reading zero rows for it is the
expected result, not a failure to report.

**Do not infer its levels from the price scale or a screenshot.** Until a verified extraction method
exists, the honest output is `null` with a stated reason. A number derived from pixel positions is a
guess wearing a decimal point.

---

## 4. Two instances of one study are indistinguishable

[VERIFIED] A layout carried two `TEMA`s. The Object tree showed `TEMA` twice with no parameters; the
Data Window showed `TEMA 559.71` twice. **Neither panel exposes the length.**

**Never label them by guessed lengths.** Reporting "TEMA(9) / TEMA(21)" when the chart says only
"TEMA" invents the most decision-relevant part of the reading. Either open each study's settings and
read the length, or report positionally (`TEMA #1`, `TEMA #2`, in Object-tree order) and say the
lengths are unresolved.

**Prefer a multi-plot study over N copies of a single one.** A built-in *Moving Average Ribbon*
configured with four EMAs reports as `MA #1`..`MA #4` — distinguishable. Four separate EMA studies
all report as an indistinguishable `EMA`. [VERIFIED] The choice of study is a choice about whether
the reading is decodable.

**Getting to a study's settings:** double-clicking an Object tree row **zooms the chart** rather than
opening settings [VERIFIED] — harmless, but it changes the visible range and a later screenshot will
not match an earlier one. The hover controls expose only Hide and Remove. **Right-click the row and
choose `Settings…`.** [VERIFIED]

---

## 5. Verify you read what you think you read

**Verify the symbol by price on every read.** The Data Window's close must agree with an
independently fetched quote for the same instrument. A mismatch means a different symbol, session, or
feed — and a reading labelled with the wrong ticker is the failure mode that otherwise looks perfect.

**The interval is part of the reading's identity.** A 3-minute Bollinger band is not a daily one, and
changing the interval changes every study value. **Record the interval with the values**, and never
present an intraday indicator inside a daily/weekly/monthly narrative.

**A page can show more than one price at once.** [VERIFIED] A chart widget read 559.09 while a table
header on the same page read 560.13, both live, both the page's own. Pick one deliberately, record
which, never average them, and never substitute your own estimate.

---

## 6. What never to touch

**Never `Cmd+S`, and never click Save.** It overwrites the operator's saved layout. Reading requires
no save. Changing a symbol or interval *without* saving is fine and is usually what you want.

**Never save, submit, or write on any site — including sites that are not the one you were sent to.**
[VERIFIED failure] An agent working a different vendor's page met a stale TradingView tab whose
"unsaved changes" dialog blocked navigation, and cleared it by **saving that layout**. Nothing
forbade it, because TradingView was not that agent's site — which is exactly why the rule must be
general. A blocking dialog on someone else's page is something to **report**, not to clear by writing
to their account.

**Never touch a broker or Trade panel.** [VERIFIED present] An account may carry
`layout__area--tradingpanel` in the DOM and a `Trade` button in the header. Never click it, never
open it, never interact with any order control. Where the calling system routes execution through a
simulator by design, a browser agent touching a real broker panel routes around every guardrail at
once.

**Never resolve an account modal.** [VERIFIED] A "Please verify your personal information"
KYC-style dialog can appear with a full-page backdrop blocking every click. Do not click Continue and
do not enter anything. Report it and let the operator dismiss it — removing the overlay node to reach
the chart beneath is a deviation that must be disclosed if you do it at all.

---

## 7. Reporting

Return the reading as data, with the facts that make it checkable: symbol, exchange, **interval**,
the Data Window's own **bar date**, OHLC, every plot with its study and plot name, and the price the
page displayed. State what you could not read and why — a study with no plots, a length you could not
resolve, a panel that would not open.

**Never report a value you did not read.** No estimates, no pixel measurements, no plausible
defaults. A fabricated indicator value is the worst possible output here, because nothing downstream
can detect it.
