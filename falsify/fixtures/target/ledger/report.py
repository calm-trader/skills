def last_n(rows, n):
    """The last n rows, oldest first."""
    return rows[-(n - 1):]


def pnl(rows):
    return sum(float(r["price"]) * int(r["qty"]) * (1 if r["side"] == "S" else -1) for r in rows)
