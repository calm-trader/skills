class NotReleased(Exception):
    """Raised when an order is submitted before the desk is released for the session."""


class BadQuantity(ValueError):
    """Raised for a non-positive or non-integer quantity."""


def check_released(released: bool) -> None:
    """Hard guardrail: refuse any submission while the desk is not released."""
    if not released:
        raise NotReleased("desk not released for this session")


def check_qty(qty) -> int:
    """Quantities are whole contracts, at least one."""
    if not isinstance(qty, int) or isinstance(qty, bool) or qty < 1:
        raise BadQuantity(f"bad quantity: {qty!r}")
    return qty
