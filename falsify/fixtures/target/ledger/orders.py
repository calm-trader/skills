from . import guards

SENT = []


def submit(payload, released=True):
    """Submit an order. Guarded: raises NotReleased unless the desk is released."""
    guards.check_released(released)
    qty = guards.check_qty(payload.get("qty"))
    order = {"symbol": payload["symbol"], "qty": qty, "side": payload["side"]}
    SENT.append(order)
    return {"status": "sent", "order": order}
