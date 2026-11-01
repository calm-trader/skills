## Review of ledger

**Side representation.** `adapter.py` stores side as integers (`B` is -1) while `report.py` compares strings; pick one representation.

**Missing test.** No test drives `dispatch.run("submit", ...)` with released=False.

**Sign convention.** `adapter.SIDE` maps a buy to -1 and nothing documents which is long, so no reading of `positions.net_exposure` can be wrong.
