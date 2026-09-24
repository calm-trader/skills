# ledger

A small fills ledger: fills arrive from the exchange feed, get captured to `data/fills.csv`, and
orders go out through a released-only submission path.

- `ledger/dispatch.py` — command router; every external command comes through `run(name, payload)`.
- `ledger/orders.py` — order submission, guarded by `guards.check_released` so nothing is sent
  before the desk is released for the session.
- `ledger/guards.py` — the guards.
- `ledger/capture.py` — the capture pipeline; `run_capture()` runs every 5 minutes from cron and
  logs to `logs/capture.log`.
- `ledger/status.py` — health for the ops page.
- `ledger/hedge.py` — hedge sizing.
- `ledger/positions.py`, `ledger/adapter.py` — signed positions from feed fills.
- `ledger/report.py` — reporting helpers.

Tests: `python3 -m unittest discover -s tests -t .` — all green.
