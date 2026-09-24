# Exchange convention for the fill feed's side field.
SIDE = {"B": -1, "S": 1}


def fill_to_position(fill):
    return {"symbol": fill["symbol"], "qty": fill["qty"], "side": SIDE[fill["side"]]}


def _legacy_side(s):  # kept for the old feed; no callers
    return {"BUY": 1, "SELL": -1}[s]
