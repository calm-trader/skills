# Operator runbook — TradingView reads at the lowest token cost

Load this file, not the whole skill. It carries the operator rules from SKILL.md §4, §8, §9 and §12. The design and judgment material lives in SKILL.md and costs you tokens on every turn without changing what you do.

**Why it is written this way:** one desk measured ~66k tokens and ~45 browser tool calls per read, and extracting the numbers was under 1% of that. Every tool call re-sends your context, so cost grows with call count. Target about a dozen calls per read. Use DOM text, one script call per check group, and a screenshot only when the DOM cannot answer.

## Guardrails
Backtesting only: never Paper Trading, broker panels, order buttons, account or subscription settings. **Never Cmd+S** (it saves to the user's library). Never create or switch tabs mid-round; reach another layout by navigating the same tab. If a login wall appears, stop and report.

## Once per session
1. The tab watchdog (`../tv-tab-watchdog.sh`) is running **and alive**: its last log line is recent.
2. Inject the kit: paste `../scripts/tvkit.js` into one JavaScript tool call. It installs `window.__tvkit` and returns the page state. Re-inject after any navigation or reload.

## Per read (≤ 6 reads per dispatch; save each result as soon as it is taken)
1. **Load the script without reading it.** `pbcopy < strategies/x.pine`, then `wc -l` and `head -1` on the file. Do not open the file into your context. Click into the editor, select all, Cmd+V (if it will not take: synthetic `ClipboardEvent('paste')` at Monaco's `textarea.inputarea`). Confirm the editor's line count equals `wc -l`. Compile with the update control.
2. **One state call:** `JSON.stringify(__tvkit.state())`. Required before any number is read:

| Field | Must be | If not |
|---|---|---|
| `title` | expected ticker, price in the expected band | wrong symbol: fix, re-check |
| `hidden` / `canvases_stuck_300x150` | `false` / `0` | hidden-tab dead canvas (SKILL.md §8): check the watchdog; if no tool can activate the tab, apply the JS visibility override; else stop and report |
| `compiler_codes` | empty, or warnings you report (treat CW10002 as a finding) | report the exact error text and line: that is a valid result |
| `requires_trade_data` | `false` | the declaration may not have taken: check Strategy Properties |
| `strategy_title_guess`, `date_range`, `session_badge`, `deep_badge`, `detalization` | as the brief says | set them; session and range reset after every reload/recompile |
| `update_report_visible` | `false` | click Update report, call `state()` again |

3. **Once per script load:** open Strategy Properties and record commission type/value, slippage, quantity, initial capital. A zero commission on a script that declares one means the declaration did not take (SKILL.md §11).
4. **After every input change:** click Update report, confirm `update_report_visible` is `false`, and confirm the live value in the Inputs dialog. A stale report is indistinguishable from a finding.
5. **One report call:** `JSON.stringify(__tvkit.report())`. Accept it only if `missing` and `checks_failed` are both empty. Otherwise capture the report's page text to a file and flag the read for extraction fallback; do not hand-copy numbers from screenshots.
6. **Export the List of Trades CSV** and run `../scripts/split_trades.py TRADES.csv --per-year` (add `--window NAME:FROM:TO` when the brief names windows). It gives first/last entry, per-year counts, legs vs entries, legs open at export and legs exiting on a later date. Never read side mix or dates off the visible page: the list is lazy-rendered.
7. **Write the result JSON** with the fields below and run `../scripts/validate_result.py result.json`. A failing record is reported as failing, never silently fixed.

## Result record fields
`script`, `symbol`, `timeframe`, `session`, `detalization`, `deep_backtesting`, `tester_date_range`, `actual_first_trade_entry`, `actual_last_trade_entry`, `net_profit_usd`, `net_profit_pct`, `gross_profit_usd`, `gross_loss_usd`, `profit_factor`, `max_drawdown_usd`, `max_drawdown_pct`, `closed_trades`, `win_rate_pct`, `winners`, `losers`, `breakevens`, `pnl_by_side_usd`, `largest_winning_trade_usd`, `largest_losing_trade_usd`, `average_trade_usd`, `commission_type`, `commission_value`, `slippage_ticks`, `qty`, `initial_capital`, `trades_exiting_on_later_date`, `open_position_at_range_end`, `per_year`, `inputs`, `report_updated_after_input_change`, `compile_error`, `trades_csv`, `timestamp`. Add `multi_session_expected: true` only when the brief says the engine holds overnight.

## Cheaper-model hooks
Two steps are selection over captured text, not browser work, and a select-only classifier handles them at a fraction of a generative model's cost (one benchmark: 14 metrics × 12 runs, 168/168 correct, about a fifth of the cost and a tenth of the latency):
- **Extraction fallback** when `report()` returns `missing` or `checks_failed` after a UI change: candidates are the numbers in the captured text, one choice per field.
- **Page-state triage** when `state()` returns something the table above does not cover: choose among healthy, hidden-tab dead canvas, stale report, compile error, template-default declaration, login wall, dialog open.
Driving the browser stays on a tool-using model.
