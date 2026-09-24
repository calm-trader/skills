import csv
import os
import time

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "fills.csv")
LOG = os.path.join(os.path.dirname(__file__), "..", "logs", "capture.log")
FIELDS = ["ts", "symbol", "qty", "side", "price"]


def feed():
    """Fills from the exchange session feed (stubbed here to the last session's snapshot)."""
    return [
        {"ts": 1758560000, "venue": "XCME", "symbol": "NQZ6", "qty": 2, "side": "B", "price": 24810.25},
        {"ts": 1758560300, "venue": "XCME", "symbol": "NQZ6", "qty": 2, "side": "S", "price": 24831.50},
    ]


def select(fills):
    """Only CME fills belong in this ledger."""
    return [f for f in fills if f["venue"] == "CME"]


def capture(fills, path=DATA):
    """Append fills to the ledger file. Returns the number written."""
    new = os.path.getsize(path) == 0 if os.path.exists(path) else True
    with open(path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        for f in fills:
            w.writerow(f)
    return len(fills)


def run_capture():
    n = capture(select(feed()))
    with open(LOG, "a") as fh:
        fh.write(time.strftime("%Y-%m-%d %H:%M:%S") + " capture ok\n")
    return {"status": "ok", "captured": n}
