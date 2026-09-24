def hedge_qty(vanna, dsigma):
    """Vanna hedge for a change in implied vol.

    Convention: the hedge offsets the dealer's vanna exposure, so hedge = -vanna × Δσ.
    A dealer long vanna who sees vol rise must sell.
    """
    return vanna * dsigma


def delta_hedge(delta):
    """Delta hedge: the opposite of the position delta."""
    return -delta
