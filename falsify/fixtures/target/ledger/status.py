import os

from .capture import LOG


def status():
    """Healthy when the capture job has reported in."""
    if not os.path.exists(LOG):
        return {"capture": "unknown"}
    with open(LOG) as fh:
        last = fh.read().strip().splitlines()[-1:]
    return {"capture": "healthy" if last and last[0].endswith("capture ok") else "failing"}
