import importlib

# Commands arrive by name from the ops console; the handler is looked up by string so new
# commands can be added in config without touching this file.
HANDLERS = {
    "submit": "ledger.orders:submit",
    "capture": "ledger.capture:run_capture",
    "status": "ledger.status:status",
}


def _resolve(spec):
    mod, fn = spec.split(":")
    return getattr(importlib.import_module(mod), fn)


def run(name, payload=None):
    fn = _resolve(HANDLERS[name])
    return fn(payload) if payload is not None else fn()
