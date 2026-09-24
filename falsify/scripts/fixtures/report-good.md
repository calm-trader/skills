# Falsify report — sample

### F1 — BLOCK (5 × 0.9). `ledger/orders.py:12` every caller passes `released=True`; the guard cannot fire.
Refutation attempted: searched string dispatch and config for a second caller; none.

### F2 — BLOCK (4 × 0.9). `tests/test_hedge.py:8` pins the inverted sign.
Refutation attempted: sabotage — flipped the sign in `hedge.py`, test still passes.

### F3 — CONSIDER (3 × 0.8). `ledger/report.py:9` off-by-one in `last_n`.

### F4 — NOTE (2 × 0.5). Dead helper in `ledger/adapter.py`.

### F5 — CONSIDER (4 × 0.95) override: pre-existing on the base branch and this change does not widen exposure.

### F6 — UNMEASURED. `data/fills.csv` has no rows; could not tell whether the feed is down or the filter is wrong.

**All-clears re-attacked:** `check_qty` — traced its callers by payload key, not symbol; it fires.

**Not checked:** blast radius on `dispatch.py` (budget); "run `npm run smoke`" (instruction: no npm here).

FALSIFY: 2 BLOCK · 2 CONSIDER · 1 NOTE · 1 UNMEASURED · attacked: 2,3,5 · not checked: 2 (budget 1, instruction 1)
