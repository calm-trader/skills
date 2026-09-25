# Report: a §6 category BLOCK below the arithmetic threshold

### F1 — BLOCK (3 × 0.8). `ledger/orders.py:6` `check_released` is decorative: a decorative guard on the order (money) path, so BLOCK under §6 whatever the number.

### F2 — BLOCK (2 × 0.9). `ledger/capture.py:20` every fill is dropped: confirmed reachable data loss.

### F3 — NOTE (1 × 0.5). Dead helper in `ledger/adapter.py`.

FALSIFY: 2 BLOCK · 0 CONSIDER · 1 NOTE · 0 UNMEASURED · attacked: 3,5 · not checked: 0 (budget 0, instruction 0)
