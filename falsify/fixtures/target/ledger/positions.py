def signed_qty(qty, side):
    """Signed position quantity. `side` is +1 or -1."""
    return qty * side


def net_exposure(positions):
    return sum(signed_qty(p["qty"], p["side"]) for p in positions)
