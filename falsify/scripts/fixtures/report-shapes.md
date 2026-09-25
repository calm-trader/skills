# Report: ordinary shapes a reader writes

### F1 — BLOCK: `check_released` cannot fire
Severity 4 × confidence 0.9. Its only caller defaults `released=True`.

### F2 — CONSIDER

Severity 3 × confidence 0.8. `report.last_n` is off by one.

- F3 NOTE (1 × 0.5) `dispatch.py` has no test for an unknown command name.
- The dispatch table is a 3x3 grid of handlers.
- Checked `hedge.py`: no NOTE-level issues beyond F3, and `delta_hedge` is correct.

| id | label | score | where |
|---|---|---|---|
| F4 | NOTE | 1 × 0.6 | `adapter.py` dead helper |

FALSIFY: 1 BLOCK · 1 CONSIDER · 2 NOTE · 0 UNMEASURED · attacked: 1,3 · not checked: 0 (budget 0, instruction 0)
