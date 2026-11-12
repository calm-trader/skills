#!/usr/bin/env python3
"""Sealed-data ledger: hashes of sealed banks, and a log of every run on them.

Standard library only, Python 3.10+. One JSON file, found as: --ledger, else
$SEAL_LEDGER, else the nearest seal-ledger.json in the current directory or a parent
(up to the git top level), else ./seal-ledger.json. Relative --ledger / $SEAL_LEDGER
paths are taken from the current directory. Sealed file paths are stored relative to
the ledger's directory with forward slashes, so every command works from any
subdirectory and on any OS. --root (the system root) defaults to the ledger's directory.

    seal.py init [--require-mirror]
    seal.py require-mirror                   # one way: every change and run needs $SEAL_MIRROR
    seal.py migrate --approved-by NAME --reason T   # start a chain on an older, chainless ledger
    seal.py common schema.json --reason T    # records every bank may share (schema keys ...)
    seal.py cycle open --of K --reason T     # next improvement cycle N, with K mechanism tests
    seal.py seal NAME --role holdout --writer "fresh agent, persona X" [--note T]
                [--looks N] [--manifest M.json] [--expires YYYY-MM-DD] PATH...
    seal.py verify [NAME...] [--require-mirror]   # recompute hashes; exit 1 on any change
    seal.py run NAME --version V3 [--root DIR] [--key passed] [--output NAME...]
                [--fingerprint F...] [--purpose score|gate|select|confirm|compare]
                [--system NAME] [--env NAME...] [--allow-dirty] [--show-output]
                [--force --reason T] -- CMD...
    seal.py budget NAME --looks N --reason T [--approved-by NAME]
                                             # set or change a look budget; raising needs approval
    seal.py mirror                           # start the append-only copy at $SEAL_MIRROR
    seal.py manifest NAME M.json [--expires YYYY-MM-DD]   # attach or replace, before any run
    seal.py probe NAME --items N --reason T  # per-item information left a sealed bank
    seal.py burn NAME --reason "builder read 12 failures while fixing X"
    seal.py retire NAME --to train --reason "read in V1"   # role change, history kept
    seal.py statement [--markdown]           # per-bank data-discipline facts for the report
    seal.py wear [--select 20 --safety 12 --confirm 2 --validation 20] [--today DATE]
                                             # worn, over-budget, burned or expired banks; exit 1
    seal.py refs [--roles holdout final] [--allow PATH...] [--root DIR]
                [--ext .py .sh ...] [--no-default-allow]       # who mentions a sealed bank
    seal.py runs [--markdown]                # the run log, FORCED / failed runs included
    seal.py gitattributes                    # .gitattributes lines for the sealed files

Roles: dev, train, validation, tune, select, confirm, safety, holdout, final, redteam,
other. validation, tune, select, confirm, safety, holdout and final are sealed (contents
never read by the builder). select and confirm are the two selection banks of an
improvement cycle (validation is the older name for select); safety is the separate
safety-recall bank. --purpose records why a run happened (gate, select, confirm = its
result decided something; refused on holdout and final banks; compare = a fair-comparison
run, allowed on holdouts, never a decision); ``statement`` counts those decisions per bank.
The purpose is declared by whoever runs the command: the ledger records it, it cannot
check it. That is why wear and look budgets count every run, whatever its purpose. Each run records who ran it
($SEAL_RUNNER, else git user.name, plus the host). ``retire`` never moves a bank into
holdout, final, safety or confirm (those are only sealed fresh), never moves a readable
bank (dev, train, redteam, other) into any sealed role, never moves a final bank that has
run, and moves a burned or probed bank only to train, dev or other. ``run`` refuses
a ledger inside a linked git worktree: use $SEAL_LEDGER for the main ledger and --root.

Look budget: ``seal --looks N`` or ``budget NAME --looks N --reason T`` stores how many
runs a bank may have. A holdout bank must have one before it runs; a final bank's budget
is always 1; a confirm bank's default is 2 (cycle base and head); a safety bank's is 12.
Raising a budget needs ``--approved-by NAME`` (not the builder), and no budget goes above
the role's wear ceiling (select 20, safety 12, confirm 2, validation 20). Every logged run of the
bank counts, in any role (``retire`` clears the budget, never the count): baselines, other
systems (``run --system NAME``), comparison runs, failed and aborted runs. A run over
budget is refused; on select, tune and validation banks ``--force --reason`` logs it as
OVER BUDGET. Budget changes are logged and shown in ``statement``.

Probes: ``probe NAME --items N --reason T`` records that per-item information (which
signals fired on one item, a failing id, a per-item score) left a sealed bank. The bank is
tainted from then on: ``statement`` and ``runs`` say so and its numbers are not clean
estimates. On a holdout, confirm or final bank a probe is also a burn.

Manifest: ``seal --manifest M.json`` (or ``manifest NAME M.json``, refused once the bank
has runs) stores what the bank holds, e.g. {"episodes": 1000, "phrasings": {"close_ticket": 14, "yes": 6},
"segments": {"writes": 480}, "writer_setup": "fresh writer, formal persona, brief v2",
"source": "synthetic", "period": "2026-11", "evaluator": ["tools/evaluate.py",
"prompts/judge.md", "sim/world.py"]}. source is synthetic, production or incident; counts
are whole numbers >= 0; evaluator lists the files (from the ledger's folder) every sealed
run must fingerprint. A sealed bank needs episodes and evaluator before it runs.
``statement`` prints episodes, phrasings and source; "not recorded" where missing.

``wear`` checks every bank: looks used of budget, runs in the current role (every run,
whatever its purpose) against a threshold per role (select 20, safety 12, confirm 2,
validation 20 by default: at the threshold the bank is worn, a breach),
burned banks still in a sealed role, tainted safety banks, expired banks. It exits 1 on any
breach, so it can sit in ``make check``. ``statement`` prints the same lines.

Tamper evidence: every write appends a hash-chained event (seq, time, kind, a digest of
the ledger, the previous event's hash). Every command that writes (and ``verify``) first
checks the chain and the mirror and refuses on a broken chain or a ledger changed outside
seal.py, so a normal write never seals a hand edit into a valid chain. Set $SEAL_MIRROR to an append-only file outside the
repository (owned by the runner, e.g. on a shared drive); each event is also appended
there, and ``verify`` then also fails when the ledger was rewound (git checkout of an older
ledger), replaced by a side ledger, or written without the mirror. ``seal.py mirror``
starts the mirror for an existing ledger. A ledger without a chain (hand-deleted, or from
an older seal.py) is refused until ``migrate`` (approved by someone other than the
builder; ``statement`` says the earlier history is taken on trust). A run on a sealed bank
always needs $SEAL_MIRROR outside the repository. Other writes need it when the ledger
requires a mirror (``init --require-mirror`` or ``require-mirror``, one way). ``verify
--require-mirror`` does the same check, for CI.

What this cannot do: a builder who can write the ledger, the mirror, the run folder and
the scripts can fake anything. The guarantees hold only when the runner (a person or a
service other than the builder) owns $SEAL_MIRROR and $SEAL_RUN_DIR and runs sealed banks.
The script enforces that both are set and outside the builder's tree; who owns them it
cannot check.

Rules enforced by ``run``:
  * the bank's files must hash as sealed, or the run is refused; they are made read-only
    while the command runs and hashed again after it: a changed bank burns, with no score.
    The --fingerprint files are hashed again too: a changed evaluator gives no score. A
    program that restores what it changed is not caught: run it as another user or on a
    read-only mount (references/data-discipline.md);
  * a sealed bank needs $SEAL_MIRROR and $SEAL_RUN_DIR set and outside the builder's tree
    (the ledger's folder, --root and their git top levels), a manifest with episodes and
    an ``evaluator`` file list, and --fingerprint hashing exactly those files;
  * the look budget (above), and the wear ceiling (select 20, safety 12, confirm 2,
    validation 20 runs), which no budget and no --force raises;
  * a burned bank is always refused; so are a probed safety bank and an expired sealed bank;
  * --force is refused on holdout, confirm, final and safety banks: nothing overrides them;
  * a ``final`` bank may be run once ever (any label, any commit);
  * the ledger's hash chain (and the mirror, if set) must check out;
  * a ``holdout``, ``safety`` or ``confirm`` bank is refused if any earlier run, of any
    --system, is the same version: the same label for the same system, or the same code,
    command and values of the ``--env`` variables. Same code means the same commit, or a
    commit whose system root differs from HEAD's only in the ledger (``git diff --quiet <prior> HEAD -- <root> ':(exclude)<ledger>'``), so
    committing the ledger does not make a new version. Without git every earlier run
    counts as the same;
  * the working tree under --root must be clean (a frozen version) unless --allow-dirty;
    the ledger and its .lock/.tmp files are ignored; run outputs belong in .gitignore;
  * the run is logged before the command starts, so an aborted run still counts;
  * --key and --output need $SEAL_RUN_DIR (outside the builder's tree). Each run gets a
    fresh folder $SEAL_RUN_DIR/<run id>/. With --key the command writes a flat JSON report
    {name: whole number} to $SEAL_REPORT, with no keys but --key and passed, failed,
    episodes, errors, skipped, timeouts; the score at --key must be from 0 to the
    manifest's episodes (required), or there is no score. Any other key, text, list or
    object refuses it, and the message never quotes the report. Only the score and the report's sha256 are kept; the file is
    deleted. --output NAME files are written into $SEAL_OUTPUT_DIR (in the same fresh
    folder, so nothing stale can be credited) and their sha256 is logged. --fingerprint
    files are hashed before the run; ``statement`` flags a bank whose scored runs used
    different ones;
  * a nonzero exit logs the run as failed with no score (it still counts as a run);
  * the command's output is captured: only the score and exit code are printed, and no
    output summary is stored for sealed roles. --show-output is refused on holdout,
    confirm and final banks; on other sealed banks it is recorded and logged as a probe;
  * every ledger write holds an exclusive lock file (<ledger>.lock); a killed process
    can leave it behind, and the message says so ($SEAL_LOCK_TIMEOUT, default 30 s).

``seal`` compares the new bank's files, taken together, with every bank: the same bytes,
the same text up to whitespace, or any shared record. Records are the string values of
JSON or JSON lines (case folded, letters and digits only, any length) plus a canonical hash
of every whole JSON record (each list element, object value or line, with sorted keys, so
numbers and bools count), else the quoted string literals, else the lines. So padding,
splitting and reformatting do not hide a copy; shared records are counted, never quoted.
Records every bank shares by design (schema keys, placeholders, answer labels) go in the
ledger's common list with ``seal.py common FILE --reason T`` (logged). A match is refused
when the new bank is sealed or the other bank is sealed (a copy would get a fresh look
budget); a match between readable banks is a warning, recorded as a clash in
``statement``. Seal TRAIN and dev banks into
the ledger too, so this check can see them. ``seal`` also warns when a file's stem is a generic word that
``refs`` cannot tell apart from ordinary code.

``refs`` is best effort. It scans code files only (extensions in --ext, plus extensionless
files with a #! line) and by default allows prompts/, redteam/, docs/, *.md and Makefile,
which legitimately name sealed paths. It flags a sealed file's stem, and glob or
templated path strings ("sim/*_phrasing.py", f"sim/{name}_phrasing.py", "data/*") that
would match a sealed file. Paths built in other ways at run time are missed.

Line endings: hashes are of the files' bytes. Mark sealed files ``-text`` in
.gitattributes (``seal.py gitattributes`` prints the lines), or a checkout with
core.autocrlf rewrites them and ``verify`` fails.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

LEDGER_NAME = "seal-ledger.json"
ROLES = ("dev", "train", "validation", "tune", "select", "confirm", "safety", "holdout", "final",
         "redteam", "other")
# contents never read by the builder
SEALED_ROLES = ("validation", "tune", "select", "confirm", "safety", "holdout", "final")
# run at most once per frozen version (same label or same code)
ONCE_PER_VERSION = ("confirm", "safety", "holdout")
# a bank only enters these roles by being sealed into them, never by retire
SEAL_ONLY_ROLES = ("confirm", "safety", "holdout", "final")
# claim banks: their numbers back claims, so --force never overrides a refusal on them
CLAIM_ROLES = ("holdout", "confirm", "final", "safety")
# what a burned bank (the builder read its failures) may become
AFTER_BURN_ROLES = ("train", "dev", "other")
# purposes refused on holdout and final banks: they score, they never choose
CHOOSING = ("gate", "select", "confirm")
PURPOSES = ("score", "gate", "select", "confirm", "compare")
# a probe on these is a burn: they give the clean numbers
BURN_ON_PROBE = ("holdout", "confirm", "final")
SOURCES = ("synthetic", "production", "incident")
# decisions a bank may feed in its role before it is worn (``wear``)
WEAR_DEFAULTS = {"select": 20, "safety": 12, "confirm": 2, "validation": 20}
CONFIRM_LOOKS = 2  # default look budget of a confirm bank: the cycle base and the cycle head
SAFETY_LOOKS = 12  # default look budget of a safety bank (its wear threshold)
KEY = re.compile(r"[A-Za-z0-9_]+$")  # a report key: one plain name
# the only other keys a report may hold; error messages never quote a report's own keys
REPORT_KEYS = ("passed", "failed", "episodes", "errors", "skipped", "timeouts")
NAME = re.compile(r"[A-Za-z0-9_.-]+$")  # an --output file name inside the run's folder
# output of these may never be shown: they give the clean numbers
NO_SHOW_ROLES = ("holdout", "confirm", "final")
CODE_EXTS = (
    ".py", ".pyw", ".ipynb", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".sh", ".bash",
    ".zsh", ".fish", ".ps1", ".bat", ".rb", ".go", ".rs", ".java", ".kt", ".scala", ".c",
    ".h", ".cc", ".cpp", ".hpp", ".cs", ".php", ".pl", ".lua", ".r", ".jl", ".swift",
)
DEFAULT_ALLOW = ("prompts/", "redteam/", "docs/", "*.md", "Makefile")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache",
             ".pytest_cache", ".ruff_cache"}
GENERIC_STEMS = {
    "answers", "bank", "banks", "cases", "conversations", "data", "dataset", "dev", "episodes",
    "eval", "evals", "examples", "extra", "fixtures", "gold", "holdout", "input", "inputs",
    "items", "labels", "messages", "phrasing", "phrasings", "prompts", "queries", "questions",
    "records", "rows", "samples", "scenarios", "test", "tests", "train", "utterances",
    "validation",
}
GLOB_TOKEN = re.compile(r"[\w./\-*?\[\]{}$%]+")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------- git and paths

def git(cwd: Path, *args: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                              encoding="utf-8", errors="surrogateescape")
    except FileNotFoundError:
        return None


def git_out(cwd: Path, *args: str) -> str | None:
    r = git(cwd, *args)
    return r.stdout.rstrip("\n") if r is not None and r.returncode == 0 else None


def toplevel(path: Path) -> Path | None:
    out = git_out(path, "rev-parse", "--show-toplevel")
    return Path(out).resolve() if out else None


def rel_posix(path: Path, start: Path) -> str:
    return Path(os.path.relpath(path, start)).as_posix()


def ledger_path(args: argparse.Namespace) -> Path:
    explicit = args.ledger or os.environ.get("SEAL_LEDGER")
    if explicit:
        return Path(explicit).resolve()
    cwd = Path.cwd().resolve()
    top = toplevel(cwd)
    for d in (cwd, *cwd.parents):
        if (d / LEDGER_NAME).is_file():
            return d / LEDGER_NAME
        if top is None or d == top:
            break
    return cwd / LEDGER_NAME


def side_files(path: Path) -> tuple[Path, Path]:
    return path.with_name(path.name + ".lock"), path.with_name(path.name + ".tmp")


def stored(path: Path, p: Path) -> str:
    """A file path as stored in the ledger: relative to the ledger's directory, posix."""
    return rel_posix(p.resolve(), path.parent)


def resolved(path: Path, s: str) -> Path:
    return (path.parent / s.replace("\\", "/")).resolve()


def system_root(args: argparse.Namespace, path: Path) -> Path:
    root = Path(args.root).resolve() if args.root else path.parent
    if not root.is_dir():
        raise SystemExit(f"--root {root} is not a directory")
    return root


# ---------------------------------------------------------------- ledger I/O

@contextlib.contextmanager
def locked(path: Path):
    lock, _ = side_files(path)
    deadline = time.monotonic() + float(os.environ.get("SEAL_LOCK_TIMEOUT", "30"))
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                try:
                    holder = lock.read_text().strip()
                except OSError:
                    holder = "unknown holder"
                raise SystemExit(
                    f"ledger is locked: {lock} exists ({holder}). Another seal.py is writing "
                    f"the ledger. If none is running, the lock is stale (a killed process): "
                    f"delete {lock} and retry."
                ) from None
            time.sleep(0.05)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(f"pid {os.getpid()} since {now()}\n")
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(lock)


def load(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"no ledger at {path}; run `seal.py init` first (or pass --ledger)")
    ledger = json.loads(path.read_text(encoding="utf-8"))
    for bank in ledger.get("banks", {}).values():  # older ledgers kept one burn record
        if "burns" not in bank:
            old = bank.pop("burned", None)
            bank["burns"] = [old] if old else []
    return ledger


def state_digest(ledger: dict) -> str:
    body = {k: v for k, v in ledger.items() if k != "chain"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def event_hash(ev: dict) -> str:
    return hashlib.sha256(f"{ev['prev']}|{ev['seq']}|{ev['kind']}|{ev['state']}|{ev['at']}"
                          .encode()).hexdigest()


def save(path: Path, ledger: dict, kind: str = "write") -> None:
    """Write the ledger and append one hash-chained event (and its mirror line)."""
    ledger.setdefault("id", uuid.uuid4().hex)
    chain = ledger.setdefault("chain", [])
    ev = {"seq": chain[-1]["seq"] + 1 if chain else 1, "at": now(), "kind": kind,
          "state": state_digest(ledger), "prev": chain[-1]["hash"] if chain else ""}
    ev["hash"] = event_hash(ev)
    chain.append(ev)
    _, tmp = side_files(path)
    tmp.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    mirror = os.environ.get("SEAL_MIRROR")
    if mirror:
        with open(mirror, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ledger": ledger["id"], **ev}, sort_keys=True) + "\n")


def mirror_events(ledger: dict) -> tuple[list[dict], set[str]] | None:
    """Events in $SEAL_MIRROR for this ledger, and the ids of other ledgers found there."""
    mirror = os.environ.get("SEAL_MIRROR")
    if not mirror:
        return None
    mine, others = [], set()
    try:
        with open(mirror, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                ev = json.loads(line)
                if ev.get("ledger") == ledger.get("id"):
                    mine.append(ev)
                else:
                    others.add(str(ev.get("ledger")))
    except FileNotFoundError:
        pass
    return mine, others


def mirror_problem(path: Path) -> str | None:
    """Why $SEAL_MIRROR cannot protect this ledger, or None."""
    mirror = os.environ.get("SEAL_MIRROR")
    if not mirror:
        return "$SEAL_MIRROR is not set"
    m = str(Path(mirror).resolve())
    for d in {toplevel(path.parent), path.parent.resolve()} - {None}:
        if m.startswith(str(d) + os.sep):
            return f"$SEAL_MIRROR is inside {d}, where it can be rewound with the ledger"
    return None


def chain_problems(path: Path, ledger: dict, mirror: bool = True) -> tuple[list[str], list[str]]:
    """(problems, notes) about the hash chain and the append-only mirror."""
    problems, notes = [], []
    if ledger.get("require_mirror") and mirror:
        why = mirror_problem(path)
        if why:
            problems.append(f"this ledger requires a mirror outside the repository: {why}")
    chain = ledger.get("chain") or []
    if not chain:
        problems.append("chain: the ledger has no hash chain (removed by hand, or a ledger from "
                        "an older seal.py: `seal.py migrate --approved-by NAME --reason T`)")
    elif chain[0]["seq"] != 1 or chain[0]["prev"] != "":
        problems.append("chain: the first events were removed (it does not start at event 1)")
    for i, ev in enumerate(chain):
        if i and ev["seq"] != chain[i - 1]["seq"] + 1:
            problems.append(f"chain: seq {ev['seq']} does not follow {chain[i - 1]['seq']}")
        if ev["prev"] != (chain[i - 1]["hash"] if i else ev["prev"]) or event_hash(ev) != ev["hash"]:
            problems.append(f"chain: event {ev['seq']} is broken (edited by hand?)")
    if chain and chain[-1]["state"] != state_digest(ledger):
        problems.append(f"chain: the ledger was changed outside seal.py after event {chain[-1]['seq']}")
    if not mirror:
        return problems, notes
    m = mirror_events(ledger)
    if m is None:
        notes.append("no $SEAL_MIRROR: a rewound or replaced ledger cannot be detected")
        return problems, notes
    mine, others = m
    why = mirror_problem(path)
    if why and not ledger.get("require_mirror"):
        notes.append(why + "; keep it outside so it cannot be rewound")
    if others:
        problems.append(f"mirror holds {len(others)} other ledger(s): this may be a side ledger, "
                        "or the real ledger was replaced")
    if chain and not mine:
        problems.append("mirror has no record of this ledger; run `seal.py mirror` once to start it")
        return problems, notes
    by_seq = {ev["seq"]: ev for ev in chain}
    for ev in mine:
        own = by_seq.get(ev["seq"])
        if own is None:
            problems.append(f"ledger rewound: the mirror has event {ev['seq']}, the ledger ends at "
                            f"{chain[-1]['seq'] if chain else 0}")
            break
        if own["hash"] != ev["hash"]:
            problems.append(f"ledger differs from the mirror at event {ev['seq']}")
            break
    seen = {ev["seq"] for ev in mine}
    missing = [ev["seq"] for ev in chain if ev["seq"] not in seen and ev["seq"] > min(seen, default=0)]
    if missing:
        problems.append(f"events {missing[0]}..{missing[-1]} are missing from the mirror "
                        "(written without $SEAL_MIRROR?)")
    return problems, notes


def load_checked(path: Path, mirror: bool = True) -> dict:
    """Load the ledger for a change: refuse when its chain or mirror does not check out, so
    a normal command never launders a hand edit into a valid chain."""
    ledger = load(path)
    bad, _ = chain_problems(path, ledger, mirror)
    if bad:
        raise SystemExit("ledger check failed; refused (see `seal.py verify`):\n" + "\n".join(bad))
    return ledger


def cmd_mirror(args: argparse.Namespace) -> None:
    path = ledger_path(args)
    if not os.environ.get("SEAL_MIRROR"):
        raise SystemExit("set $SEAL_MIRROR to an append-only file outside the repository first")
    with locked(path):
        ledger = load_checked(path, mirror=False)
        mine, _ = mirror_events(ledger)
        if mine:
            raise SystemExit("the mirror already holds this ledger; nothing to start")
        with open(os.environ["SEAL_MIRROR"], "a", encoding="utf-8") as f:
            for ev in ledger["chain"]:
                f.write(json.dumps({"ledger": ledger["id"], **ev}, sort_keys=True) + "\n")
    print(f"mirror started for ledger {ledger['id'][:12]} ({len(ledger['chain'])} events)")


def cmd_migrate(args: argparse.Namespace) -> None:
    """Start a hash chain on a ledger that has none (older seal.py). Audited: someone other
    than the builder approves, and the event says what was trusted without proof."""
    path = ledger_path(args)
    with locked(path):
        ledger = load(path)
        if ledger.get("chain"):
            raise SystemExit("refused: this ledger already has a hash chain; nothing to migrate")
        ledger.setdefault("migrations", []).append(
            {"at": now(), "approved_by": args.approved_by, "reason": args.reason,
             "runs": len(ledger.get("runs", [])), "banks": sorted(ledger.get("banks", {}))})
        save(path, ledger, "migrate")
    print("hash chain started; `statement` shows that the earlier history was taken on trust")


def cmd_cycle(args: argparse.Namespace) -> None:
    """Open the next improvement cycle: its number N and K, the mechanism tests it may run."""
    path = ledger_path(args)
    if args.of < 1:
        raise SystemExit("--of must be at least 1")
    with locked(path):
        ledger = load_checked(path)
        cycles = ledger.setdefault("cycles", [])
        n = len(cycles) + 1
        cycles.append({"n": n, "k": args.of, "at": now(), "reason": args.reason, "uses": []})
        save(path, ledger, f"cycle {n}")
    print(f"cycle {n} opened: {args.of} mechanism test(s), each at 0.05 / {args.of} / 2^{n}. "
          f"Pass `noise.py ... --ledger {path} --cycle {n}`.")


def use_cycle(path: Path, n: int, tag: str) -> tuple[int, int]:
    """Record one mechanism test against cycle n (the latest one) and return (K, uses so far).
    Refused once K tests have used it, or once a later cycle has opened."""
    with locked(path):
        ledger = load_checked(path)
        cycles = ledger.get("cycles") or []
        if not cycles or cycles[-1]["n"] != n:
            raise SystemExit(f"refused: cycle {n} is not the open cycle"
                             + (f" (that is {cycles[-1]['n']})" if cycles else
                                " (none: `seal.py cycle open --of K --reason T`)"))
        c = cycles[-1]
        if len(c["uses"]) >= c["k"]:
            raise SystemExit(f"refused: cycle {n} registered {c['k']} mechanism test(s) and all "
                             "are used; a new candidate waits for the next cycle")
        c["uses"].append({"at": now(), "candidate": tag})
        save(path, ledger, f"cycle {n} use")
        return c["k"], len(c["uses"])


def cmd_require_mirror(args: argparse.Namespace) -> None:
    """One way: from now on every change and run needs $SEAL_MIRROR outside the repository."""
    path = ledger_path(args)
    why = mirror_problem(path)
    if why:
        raise SystemExit(f"refused: {why}")
    with locked(path):
        ledger = load_checked(path)
        if ledger.get("require_mirror"):
            raise SystemExit("this ledger already requires a mirror")
        ledger["require_mirror"] = True
        save(path, ledger, "require-mirror")
    print("this ledger now requires $SEAL_MIRROR outside the repository for every change and run")


# ---------------------------------------------------------------- seal / verify / burn

def hash_files(path: Path, paths: list[str]) -> list[dict]:
    files = {}
    for p in paths:
        f = Path(p)
        if not f.is_file():
            raise SystemExit(f"not a file: {p}")
        files[stored(path, f)] = f
    return [{"path": s, "sha256": sha256(f), "bytes": f.stat().st_size}
            for s, f in sorted(files.items())]


def digest(files: list[dict]) -> str:
    return hashlib.sha256("\n".join(f["sha256"] for f in files).encode()).hexdigest()


def norm_lines(p: Path) -> list[str] | None:
    try:
        text = p.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return None
    return [" ".join(ln.split()) for ln in text.splitlines() if ln.strip()]


def norm_hash(p: Path) -> str | None:
    lines = norm_lines(p)
    return None if lines is None else hashlib.sha256("\n".join(lines).encode()).hexdigest()


def readable_bank(b: dict) -> bool:
    """The build side may have read it: not sealed, or retired, probed or burned."""
    return b["role"] not in SEALED_ROLES or bool(b.get("retired") or b.get("probes") or b["burns"])


STR_LIT = re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'')


def json_leaves(x, out: list[str]) -> None:
    """Every string value (keys are structure, numbers are ids: neither is compared)."""
    if isinstance(x, str):
        out.append(x)
    elif isinstance(x, list):
        for y in x:
            json_leaves(y, out)
    elif isinstance(x, dict):
        for y in x.values():
            json_leaves(y, out)


def norm_record(x: str) -> str:
    return "".join(ch for ch in x.casefold() if ch.isalnum())


def canon(x) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def json_records(data, out: set[str]) -> None:
    """Whole JSON records, canonical (sorted keys; numbers, bools and nulls kept): each
    element of a top-level list, each value of a top-level object, and the whole document.
    A bare string element is left to the string records (and the common list)."""
    items = data if isinstance(data, list) else list(data.values()) if isinstance(data, dict) else []
    for x in [data, *items]:
        if not isinstance(x, str):
            out.add("json:" + hashlib.sha256(canon(x).encode()).hexdigest())


def records(p: Path) -> set[str] | None:
    """The file's records, normalised so padding and reformatting do not hide a copy.

    JSON (or JSON lines): every string value, plus a canonical hash of every whole record
    (so a bank of numbers is compared too). Other text: its quoted string literals, or its
    lines when it has none. Strings are case folded, letters and digits only. Every
    non-empty record counts, however short."""
    try:
        text = p.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return None
    leaves: list[str] = []
    whole: set[str] = set()
    try:
        data = json.loads(text)
        json_leaves(data, leaves)
        json_records(data, whole)
    except ValueError:
        try:
            for ln in text.splitlines():
                if ln.strip():
                    data = json.loads(ln)
                    json_leaves(data, leaves)
                    if not isinstance(data, str):
                        whole.add("json:" + hashlib.sha256(canon(data).encode()).hexdigest())
        except ValueError:
            leaves = [a or b for a, b in STR_LIT.findall(text)] or text.splitlines()
            whole = set()
    return {x for x in map(norm_record, leaves) if x} | whole


def content_clashes(path: Path, ledger: dict, files: list[dict]) -> list[tuple[str, bool]]:
    """(line, the other bank is readable) for each bank the files about to be sealed copy:
    the same bytes, the same text up to whitespace, or any shared record. The new files are
    taken together, so splitting a copy across files does not hide it. Records in the
    ledger's common list (``seal.py common``: schema keys, placeholders) are exempt."""
    common = set(ledger.get("common_records") or [])
    new: set[str] = set()
    for f in files:
        new |= records(resolved(path, f["path"])) or set()
    new -= common
    out = []
    for name, b in ledger["banks"].items():
        why, theirs = [], set()
        for g in b["files"]:
            gp = resolved(path, g["path"])
            for f in files:
                if f["bytes"] and g["sha256"] == f["sha256"]:
                    why.append(f"{f['path']} has the same bytes as {g['path']}")
                elif gp.is_file() and f["norm"] and g.get("norm", norm_hash(gp)) == f["norm"]:
                    why.append(f"{f['path']} has the same text (up to whitespace) as {g['path']}")
            theirs |= records(gp) or set()
        shared = sorted(new & theirs)
        if shared:
            why.append(f"{len(shared)} shared record(s)")  # never quoted: they may be sealed text
        if why:
            kind = "readable" if readable_bank(b) else "sealed"
            out.append((f"  {kind} bank {name}: " + "; ".join(why), readable_bank(b)))
    return out


def cmd_common(args: argparse.Namespace) -> None:
    """Add records every bank may share (schema keys, placeholders, answer labels)."""
    path = ledger_path(args)
    try:
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(f"cannot read {args.file}: {e}") from None
    leaves: list[str] = []
    json_leaves(data, leaves)
    recs = sorted({x for x in map(norm_record, leaves) if x})
    if not recs:
        raise SystemExit(f"{args.file} holds no strings")
    with locked(path):
        ledger = load_checked(path)
        ledger["common_records"] = sorted(set(ledger.get("common_records") or []) | set(recs))
        ledger.setdefault("common_changes", []).append(
            {"at": now(), "file": args.file, "added": recs, "reason": args.reason})
        save(path, ledger, "common")
    print(f"{len(recs)} common record(s) may now appear in any bank; the change is logged")


def generic_stem(stem: str) -> bool:
    return len(stem) < 8 or stem.lower() in GENERIC_STEMS


def cmd_init(args: argparse.Namespace) -> None:
    path = ledger_path(args)
    if path.exists():
        raise SystemExit(f"{path} already exists (pass --ledger to start a separate ledger)")
    if args.require_mirror and mirror_problem(path):
        raise SystemExit(f"refused: --require-mirror, but {mirror_problem(path)}")
    with locked(path):
        save(path, {"created": now(), "banks": {}, "runs": [],
                    **({"require_mirror": True} if args.require_mirror else {})}, "init")
    print(f"created {path}")


def cmd_seal(args: argparse.Namespace) -> None:
    path = ledger_path(args)
    with locked(path):
        ledger = load_checked(path)
        banks = ledger["banks"]
        if args.name in banks:
            raise SystemExit(
                f"{args.name} is already sealed; a changed bank is a new bank: seal it under a new name"
            )
        files = hash_files(path, args.paths)
        for f in files:
            f["norm"] = norm_hash(resolved(path, f["path"]))
        burned = {f["sha256"]: n for n, b in banks.items() if b["burns"] for f in b["files"] if f["bytes"]}
        clash = [f"  {f['path']} has the content of burned bank {burned[f['sha256']]}"
                 for f in files if f["sha256"] in burned]
        if clash:
            raise SystemExit("refused: a burned bank stays burned under any name; get a fresh "
                             "writer and new content:\n" + "\n".join(clash))
        hits = content_clashes(path, ledger, files)
        refused = [h for h, readable in hits if args.role in SEALED_ROLES or not readable]
        if refused:
            raise SystemExit(
                "refused: these files share text with another bank (bytes, text, or any record "
                "outside the common list). A sealed bank's text is used once: a "
                "copy under a new name would get a fresh look budget, and readable text is "
                "never sealed. If sealed text reached a readable file, burn that bank.\n"
                + "\n".join(refused) + "\nGet a fresh writer and new content.")
        for h, _ in hits:
            print(f"warning: {h.strip()}", file=sys.stderr)
        for f in files:
            stem = Path(f["path"]).stem
            if generic_stem(stem):
                print(f"warning: {f['path']}: the stem '{stem}' is generic, so `refs` cannot tell "
                      "references to it from ordinary code; rename it distinctively "
                      "(e.g. holdout1_phrasing.py)", file=sys.stderr)
        looks = args.looks
        if args.role == "final":
            if looks not in (None, 1):
                print("warning: a final bank's look budget is always 1", file=sys.stderr)
            looks = 1
        ceiling = WEAR_DEFAULTS.get(args.role)
        if looks is not None and ceiling is not None and looks > ceiling:
            raise SystemExit(f"refused: a {args.role} bank wears out at {ceiling} runs; no "
                             "budget goes above that ceiling")
        if looks is not None and looks < 1:
            raise SystemExit("--looks must be at least 1")
        manifest = read_manifest(args.manifest) if args.manifest else None
        banks[args.name] = {
            "role": args.role,
            "writer": args.writer,
            "note": args.note,
            "sealed_at": now(),
            "files": files,
            "digest": digest(files),
            "burns": [],
            "looks": looks,
            "manifest": manifest,
            "expires": check_date(args.expires) if args.expires else None,
            "clashes": [h.strip() for h, _ in hits],
        }
        save(path, ledger, f"seal {args.name}")
    print(f"sealed {args.name} ({args.role}): {len(files)} file(s), digest {digest(files)[:16]}")
    if args.role == "holdout" and looks is None:
        print(f"warning: {args.name} has no look budget; `run` refuses it until "
              f"`seal.py budget {args.name} --looks N --reason T`", file=sys.stderr)
    if manifest is None and args.role in SEALED_ROLES:
        print(f"note: no --manifest; `statement` will say \"phrasings: not recorded\"",
              file=sys.stderr)


def check_date(s: str) -> str:
    try:
        return dt.date.fromisoformat(s).isoformat()
    except ValueError:
        raise SystemExit(f"not a date (YYYY-MM-DD): {s}") from None


def read_manifest(p: str) -> dict:
    try:
        m = json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(f"cannot read manifest {p}: {e}") from None
    if not isinstance(m, dict):
        raise SystemExit(f"manifest {p}: expected a JSON object")
    if "source" in m and m["source"] not in SOURCES:
        raise SystemExit(f"manifest {p}: source must be one of {', '.join(SOURCES)}")
    def count(v) -> bool:
        return isinstance(v, int) and not isinstance(v, bool) and v >= 0
    if "episodes" in m and not count(m["episodes"]):
        raise SystemExit(f"manifest {p}: episodes must be a whole number >= 0")
    ev = m.get("evaluator")
    if ev is not None:
        if not (isinstance(ev, list) and ev and all(isinstance(x, str) and x.strip() for x in ev)):
            raise SystemExit(f"manifest {p}: evaluator must be a non-empty list of file paths "
                             "(from the ledger's folder): evaluator, judge prompt, simulator")
        m["evaluator"] = sorted({Path(x.replace("\\", "/")).as_posix() for x in ev})
    for k in ("phrasings", "segments"):
        v = m.get(k)
        if v is None or (k == "phrasings" and count(v)):
            continue
        if not (isinstance(v, dict) and all(count(x) for x in v.values())):
            raise SystemExit(f"manifest {p}: {k} must be "
                             + ("a whole number >= 0 or " if k == "phrasings" else "")
                             + "{key: whole number >= 0}")
    return m


def bank_looks(bank: dict) -> int | None:
    if bank["role"] == "final":
        return 1
    if bank.get("looks") is None and bank["role"] == "confirm":
        return CONFIRM_LOOKS
    if bank.get("looks") is None and bank["role"] == "safety":
        return SAFETY_LOOKS
    return bank.get("looks")


def looks_used(ledger: dict, name: str, role: str | None = None) -> int:
    """Every logged run of this bank in any role: baselines, other systems, failures.
    A role change never resets the count."""
    return sum(1 for r in ledger["runs"] if r["bank"] == name)


def cmd_budget(args: argparse.Namespace) -> None:
    path = ledger_path(args)
    if args.looks < 1:
        raise SystemExit("--looks must be at least 1")
    with locked(path):
        ledger = load_checked(path)
        bank = ledger["banks"].get(args.name)
        if bank is None:
            raise SystemExit(f"unknown bank {args.name}")
        if bank["role"] == "final":
            raise SystemExit("refused: a final bank's look budget is fixed at 1")
        ceiling = WEAR_DEFAULTS.get(bank["role"])
        if ceiling is not None and args.looks > ceiling:
            raise SystemExit(f"refused: a {bank['role']} bank wears out at {ceiling} runs; no "
                             "budget goes above that ceiling. Seal a fresh bank.")
        old = bank_looks(bank)
        if old is not None and args.looks > old and not args.approved_by:
            raise SystemExit("refused: raising a look budget needs --approved-by NAME: someone "
                             "other than the builder (the domain owner or the runner) agrees")
        bank["looks"] = args.looks
        bank.setdefault("budget_changes", []).append(
            {"at": now(), "seq": next_seq(ledger), "from": old, "to": args.looks,
             "role": bank["role"], "reason": args.reason, "approved_by": args.approved_by})
        used = looks_used(ledger, args.name, bank["role"])
        save(path, ledger, f"budget {args.name}")
    how = "set" if old is None else ("raised" if args.looks > old else "lowered")
    print(f"{args.name}: look budget {how} to {args.looks} ({used} used, every role counted). "
          "The change is logged and `statement` shows it.")


def cmd_manifest(args: argparse.Namespace) -> None:
    path = ledger_path(args)
    m = read_manifest(args.file)
    with locked(path):
        ledger = load_checked(path)
        bank = ledger["banks"].get(args.name)
        if bank is None:
            raise SystemExit(f"unknown bank {args.name}")
        if any(r["bank"] == args.name for r in ledger["runs"]):
            raise SystemExit(f"refused: {args.name} has runs, so its manifest and expiry are frozen. "
                             "A correction is a new bank: seal it under a new name.")
        if bank.get("manifest"):
            bank.setdefault("manifest_history", []).append({"at": now(), "manifest": bank["manifest"]})
        bank["manifest"] = m
        if args.expires:
            bank["expires"] = check_date(args.expires)
        save(path, ledger)
    print(f"{args.name}: manifest stored")


def cmd_probe(args: argparse.Namespace) -> None:
    path = ledger_path(args)
    if args.items < 1:
        raise SystemExit("--items must be at least 1")
    with locked(path):
        ledger = load_checked(path)
        bank = ledger["banks"].get(args.name)
        if bank is None:
            raise SystemExit(f"unknown bank {args.name}")
        role = bank["role"]
        if role not in SEALED_ROLES:
            raise SystemExit(f"{args.name} is a {role} bank, not sealed: it can be read; nothing to log")
        seq = next_seq(ledger)
        bank.setdefault("probes", []).append({"at": now(), "seq": seq, "items": args.items,
                                              "role": role, "reason": args.reason})
        burned = role in BURN_ON_PROBE
        if burned:
            bank["burns"].append({"at": now(), "seq": next_seq(ledger),
                                  "reason": f"probe of {args.items} item(s): {args.reason}"})
        save(path, ledger)
    if burned:
        print(f"{args.name} ({role}) is tainted and BURNED: a {role} bank gives clean numbers, and "
              "per-item information has left it. Retire it to train and seal a fresh bank.")
    else:
        print(f"{args.name} ({role}) is tainted: its numbers are no longer clean estimates. "
              + ("A probed safety gate bank is replaced: retire it and seal a fresh one."
                 if role == "safety" else "Say so wherever it is quoted."))


def verify_bank(path: Path, name: str, bank: dict) -> list[str]:
    problems = []
    for f in bank["files"]:
        p = resolved(path, f["path"])
        if not p.is_file():
            problems.append(f"{name}: missing {f['path']}")
        elif sha256(p) != f["sha256"]:
            problems.append(f"{name}: CHANGED {f['path']}")
    return problems


def cmd_verify(args: argparse.Namespace) -> None:
    path = ledger_path(args)
    ledger = load(path)
    names = args.names or list(ledger["banks"])
    problems = []
    for n in names:
        if n not in ledger["banks"]:
            raise SystemExit(f"unknown bank {n}")
        bank = ledger["banks"][n]
        problems += verify_bank(path, n, bank)
        print(f"{n:16} {bank['role']:10} {'BURNED' if bank['burns'] else 'ok'}")
    bad, notes = chain_problems(path, ledger)
    for n in notes:
        print(f"note: {n}")
    problems += bad
    if args.require_mirror and mirror_problem(path):
        problems.append(f"--require-mirror: {mirror_problem(path)}")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(1)


def cmd_burn(args: argparse.Namespace) -> None:
    path = ledger_path(args)
    with locked(path):
        ledger = load_checked(path)
        bank = ledger["banks"].get(args.name)
        if bank is None:
            raise SystemExit(f"unknown bank {args.name}")
        bank["burns"].append({"at": now(), "seq": next_seq(ledger), "reason": args.reason})
        save(path, ledger)
    again = f" ({len(bank['burns'])} burn records)" if len(bank["burns"]) > 1 else ""
    print(f"{args.name} is burned{again}: it may no longer be run. Seal a fresh bank from a new "
          "writer; `retire --to train` keeps it as readable training data.")


def next_seq(ledger: dict) -> int:
    ledger["seq"] = ledger.get("seq", 0) + 1
    return ledger["seq"]


def retired_after_burn(bank: dict) -> bool:
    r = bank.get("retired") or []
    if not r:
        return False
    last_r, last_b = r[-1], bank["burns"][-1]
    if "seq" in last_r and "seq" in last_b:
        return last_r["seq"] > last_b["seq"]
    return last_r["at"] > last_b["at"]


def linked_worktree(d: Path) -> bool:
    """True when d is inside a linked worktree (its git dir differs from the common dir)."""
    gd = git_out(d, "rev-parse", "--absolute-git-dir")
    cd = git_out(d, "rev-parse", "--git-common-dir")
    if not gd or not cd:
        return False
    cdp = Path(cd) if Path(cd).is_absolute() else (d / cd)
    return Path(gd).resolve() != cdp.resolve()


def runner() -> str:
    """Who ran it: $SEAL_RUNNER, else git user.name, else the OS user; plus the host."""
    import getpass
    import socket
    who = os.environ.get("SEAL_RUNNER") or git_out(Path.cwd(), "config", "user.name")
    if not who:
        try:
            who = getpass.getuser()
        except Exception:  # noqa: BLE001
            who = "unknown"
    return f"{who}@{socket.gethostname()}"


def cmd_retire(args: argparse.Namespace) -> None:
    """Change a bank's role (a read holdout becomes validation); earlier runs keep their role."""
    path = ledger_path(args)
    with locked(path):
        ledger = load_checked(path)
        bank = ledger["banks"].get(args.name)
        if bank is None:
            raise SystemExit(f"unknown bank {args.name}")
        old = bank["role"]
        if args.to in SEAL_ONLY_ROLES:
            raise SystemExit(f"refused: a bank enters the {args.to} role only by being sealed into it "
                             "by a fresh writer, never by retire")
        if old == "final" and any(r["bank"] == args.name for r in ledger["runs"]):
            raise SystemExit(f"refused: {args.name} is a final bank that has run; it stays final")
        if old not in SEALED_ROLES and args.to in SEALED_ROLES:
            raise SystemExit(f"refused: {args.name} is a readable {old} bank; readable text never "
                             f"becomes a sealed {args.to} bank. Seal fresh text from a new writer.")
        if (bank["burns"] or bank.get("probes")) and args.to not in AFTER_BURN_ROLES:
            raise SystemExit(f"{args.name} is burned or probed (per-item information left it): it can "
                             "only become " + ", ".join(AFTER_BURN_ROLES)
                             + ", never a bank used for choosing")
        if old == args.to:
            raise SystemExit(f"{args.name} already has role {old}")
        bank.setdefault("retired", []).append({"at": now(), "seq": next_seq(ledger), "from": old,
                                               "to": args.to, "reason": args.reason,
                                               "looks": bank.get("looks")})
        bank["role"] = args.to
        bank["looks"] = None  # a new role gets its own budget; earlier runs still count
        save(path, ledger)
    print(f"{args.name}: {old} -> {args.to}. Its {old} scores stay in the log, marked retired. "
          "Seal a fresh bank for the old role.")


# ---------------------------------------------------------------- run

def score_of(data, key: str, episodes: int) -> int:
    """The score at KEY of a flat report {name: whole number}; 0 <= score <= episodes.
    Anything else in the report (text, lists, objects) refuses it: a report carries counts,
    never items."""
    if not isinstance(data, dict):
        raise ValueError("the report must be a JSON object {name: whole number}")
    if not set(data) <= {key, *REPORT_KEYS}:
        raise ValueError("the report has a key outside the allowed set (--key and "
                         + ", ".join(REPORT_KEYS) + ")")
    if any(not isinstance(v, int) or isinstance(v, bool) for v in data.values()):
        raise ValueError("the report may hold whole numbers only")
    if key not in data:
        raise ValueError("the report has no value at --key")
    v = data[key]
    if not 0 <= v <= episodes:
        raise ValueError("the score is outside 0 to the manifest's episode count")
    return v


def outside_problem(env: str, dirs: list[Path]) -> str | None:
    """Why the folder or file in $env is missing or inside one of dirs (the builder's tree)."""
    v = os.environ.get(env)
    if not v:
        return f"${env} is not set"
    p = Path(v).resolve()
    for d in dirs:
        if p == d or p.is_relative_to(d):
            return f"${env} ({p}) is inside {d}, which the builder can write"
    return None


def dirt(root: Path, top: Path, path: Path) -> list[str]:
    """Uncommitted changes under root, except the ledger and its side files."""
    out = git_out(root, "status", "--porcelain", "-z", "--untracked-files=all", "--", ".")
    if out is None:
        return ["(git status failed)"]
    ignore = {rel_posix(p, top) for p in (path, *side_files(path))}
    lines, items, i = [], out.split("\0"), 0
    while i < len(items):
        e = items[i]
        i += 1
        if len(e) < 4:
            continue
        if e[0] in "RC":
            i += 1  # the rename's source path follows
        if e[3:] not in ignore:
            lines.append(f"{e[:2]} {e[3:]}")
    return lines


def tree(commit: str, rel: str) -> str:
    return f"{commit}^{{tree}}" if rel in (".", "") else f"{commit}:{rel}"


def same_code(r: dict, version: str, system: str | None, command: list[str], env: dict,
              commit: str | None, top: Path | None,
              root_rel: str | None, ledger_in_root: str | None) -> str | None:
    """Why an earlier run counts as this version, or None if the code differs.

    A version is (code tree, command, values of the --env variables), whatever the label
    or --system name says."""
    if r["version"] == version and r.get("system") == system:
        return "same version label"
    if commit is None or r.get("commit") is None or top is None:
        return "no git commit to tell the code apart"
    if r.get("command") != command:
        return None
    if (r.get("env") or {}) != env:
        return None
    if r["commit"] == commit:
        return "same commit, command and environment"
    spec = [f":(exclude){ledger_in_root}"] if ledger_in_root else []
    p = git(top, "diff", "--quiet", tree(r["commit"], r.get("root") or root_rel),
            tree(commit, root_rel), "--", *spec)
    if p is not None and p.returncode == 1:
        return None
    if p is not None and p.returncode == 0:
        return "same code, command and environment (only the ledger changed since)"
    return "cannot compare with that commit (missing from this repo?)"


def file_hashes(path: Path, paths: list[str], what: str) -> dict[str, str]:
    out = {}
    for x in paths:
        f = Path(x)
        if f.is_symlink() or not f.is_file():
            raise SystemExit(f"{what} {x}: not a regular file")
        out[stored(path, f)] = sha256(f)
    return out


def builder_dirs(path: Path, root: Path) -> list[Path]:
    return sorted({d for d in (path.parent.resolve(), root.resolve(), toplevel(path.parent),
                               toplevel(root)) if d is not None})


def cmd_run(args: argparse.Namespace) -> None:
    if not args.command:
        raise SystemExit("give the command after `--`")
    if args.report:
        raise SystemExit("--report is gone: pass --key KEY, and the command writes its JSON report "
                         "to the file named by $SEAL_REPORT (a fresh runner-owned path per run)")
    if args.force and not args.reason:
        raise SystemExit("--force needs --reason")
    if args.key and not KEY.match(args.key):
        raise SystemExit("--key is one plain name (letters, digits, _): the report is flat")
    for o in args.output or []:
        if not NAME.match(o) or o in (".", ".."):
            raise SystemExit(f"--output {o}: a plain file name; the command writes it into "
                             "$SEAL_OUTPUT_DIR, a fresh runner-owned folder per run")
    path = ledger_path(args)
    if linked_worktree(path.parent):
        raise SystemExit(
            f"refused: the ledger {path} is inside a linked git worktree, so this run would be "
            "logged in a copy that is thrown away with the worktree. Point $SEAL_LEDGER (or "
            "--ledger) at the main checkout's ledger and pass --root <this worktree>.")
    root = system_root(args, path)
    top = toplevel(root)
    commit = git_out(root, "rev-parse", "HEAD") if top else None
    root_rel = rel_posix(root, top) if top else None
    ledger_in_root = rel_posix(path, root)
    if ledger_in_root.startswith(".."):
        ledger_in_root = None
    env = {n: os.environ.get(n) for n in (args.env or [])}
    fingerprint = file_hashes(path, args.fingerprint or [], "--fingerprint")
    with locked(path):
        ledger = load_checked(path)
        bank = ledger["banks"].get(args.name)
        if bank is None:
            raise SystemExit(f"unknown bank {args.name}")
        role = bank["role"]
        manifest = bank.get("manifest") or {}
        if role in SEALED_ROLES:
            why = mirror_problem(path) or outside_problem("SEAL_RUN_DIR", builder_dirs(path, root))
            if why:
                raise SystemExit(
                    f"refused: a run on a {role} bank needs $SEAL_MIRROR and $SEAL_RUN_DIR "
                    f"outside the builder's tree, owned by the runner: {why}")
            if not isinstance(manifest.get("episodes"), int) or not manifest.get("evaluator"):
                raise SystemExit(f"refused: {args.name} needs a manifest with episodes and the "
                                 "evaluator file list before it runs (seal --manifest)")
            want = set(manifest["evaluator"])
            if set(fingerprint) != want:
                raise SystemExit("refused: --fingerprint must hash exactly the manifest's evaluator "
                                 f"files {sorted(want)}; got {sorted(fingerprint) or 'none'}")
        if (args.key or args.output) and outside_problem("SEAL_RUN_DIR", builder_dirs(path, root)):
            raise SystemExit("refused: --key and --output need $SEAL_RUN_DIR outside the builder's "
                             "tree: " + outside_problem("SEAL_RUN_DIR", builder_dirs(path, root)))
        if args.key and not isinstance(manifest.get("episodes"), int):
            raise SystemExit(f"refused: --key needs the manifest's episode count for {args.name}, "
                             "so the score has a bound")
        if args.force and role in CLAIM_ROLES:
            raise SystemExit(f"refused: --force on a {role} bank. Its numbers back claims, so no "
                             "refusal on it can be overridden: seal a fresh bank.")
        if args.show_output and role in NO_SHOW_ROLES:
            raise SystemExit(f"refused: --show-output on a {role} bank would show its per-item "
                             "results to the build side; it gives clean numbers, so never")
        if role in ("holdout", "final") and args.purpose in CHOOSING:
            raise SystemExit(f"refused: a {role} bank scores a frozen version; it never chooses "
                             f"(--purpose {args.purpose}). Use a select, confirm or validation bank.")
        if bank["burns"] and not retired_after_burn(bank):
            raise SystemExit(f"{args.name} is burned ({bank['burns'][-1]['reason']}); refused "
                             "(retire it to train to keep it as readable training data)")
        if role == "safety" and bank.get("probes"):
            raise SystemExit(f"refused: {args.name} is a probed safety bank; a safety gate bank "
                             "is replaced once tainted. Retire it and seal a fresh one.")
        exp = bank.get("expires")
        if exp and role in SEALED_ROLES and dt.date.fromisoformat(exp) < dt.date.today():
            raise SystemExit(f"refused: {args.name} expired on {exp} (stale); seal a fresh bank")
        problems = verify_bank(path, args.name, bank)
        if problems:
            raise SystemExit("sealed files changed; refused:\n" + "\n".join(problems))
        if commit is None:
            print("warning: not a git repo; the version cannot be pinned to a commit", file=sys.stderr)
        dirty_lines = dirt(root, top, path) if top else []
        if dirty_lines and not args.allow_dirty:
            raise SystemExit(
                "working tree is dirty: commit (freeze) the version first, or --allow-dirty "
                "(run outputs belong in .gitignore)\n" + "\n".join(dirty_lines[:10])
            )
        prior = [r for r in ledger["runs"] if r["bank"] == args.name]
        if role == "final" and prior:
            raise SystemExit(
                f"{args.name} is a final bank and was already run "
                f"({prior[0]['started']} {prior[0]['version']}); a final bank runs once ever. Refused."
            )
        used = looks_used(ledger, args.name)
        ceiling = WEAR_DEFAULTS.get(role)
        if ceiling is not None and used >= ceiling:
            raise SystemExit(f"refused: {args.name} is worn ({used} runs, the {role} ceiling is "
                             f"{ceiling}); no budget or --force raises it. Retire it and seal a "
                             "fresh bank.")
        looks = bank_looks(bank)
        over = False
        if role == "holdout" and looks is None:
            raise SystemExit(f"refused: {args.name} has no look budget. Set it first: "
                             f"`seal.py budget {args.name} --looks N --reason T` (count baselines "
                             "and comparison systems)")
        if looks is not None and used >= looks:
            if not args.force:
                raise SystemExit(
                    f"refused: the look budget of {args.name} is spent ({used} of {looks} "
                    "runs; baselines, other systems, failed runs and runs in earlier roles "
                    "count). Seal a fresh bank"
                    + ("." if role in CLAIM_ROLES else ", or `--force --reason T` logs an "
                       "OVER BUDGET run."))
            over = True
        if role in ONCE_PER_VERSION:
            same = [(r, why) for r in prior
                    if (why := same_code(r, args.version, args.system, args.command, env, commit,
                                         top, root_rel, ledger_in_root))]
            if same:
                lines = "\n".join(
                    f"  {r['started']} {r['version']} {(r['commit'] or '-')[:12]} "
                    f"score={r.get('score')}: {why}" for r, why in same)
                raise SystemExit(
                    f"{args.name} was already run for this version:\n{lines}\n"
                    f"A {role} bank is read once per frozen version (code, command and --env "
                    "values), whatever the label or --system. If an environment variable selects "
                    "a different agent, pass --env NAME. Refused; there is no override."
                )
        rid = uuid.uuid4().hex
        rdir = None
        if os.environ.get("SEAL_RUN_DIR") and (args.key or args.output or role in SEALED_ROLES):
            base = Path(os.environ["SEAL_RUN_DIR"]).resolve()
            base.mkdir(parents=True, exist_ok=True, mode=0o700)
            rdir = base / rid
            rdir.mkdir(mode=0o700)  # fresh: nothing in it predates this run
            (rdir / "out").mkdir(mode=0o700)
        record = {
            "id": rid, "bank": args.name, "role": role, "version": args.version,
            "commit": commit, "root": root_rel, "dirty": bool(dirty_lines), "started": now(),
            "finished": None, "status": "running", "command": args.command, "exit": None,
            "score": None, "score_error": None, "summary": None, "forced": bool(args.force),
            "reason": args.reason, "purpose": args.purpose, "ran_by": runner(),
            "system": args.system, "over_budget": over, "env": env,
            "output_shown": bool(args.show_output), "fingerprint": fingerprint or None,
            "report_sha256": None, "outputs": None,
        }
        ledger["runs"].append(record)
        if args.show_output and role in SEALED_ROLES:
            bank.setdefault("probes", []).append(
                {"at": now(), "seq": next_seq(ledger), "items": None, "role": role,
                 "reason": f"--show-output on run {record['id'][:8]} ({args.version})"})
        save(path, ledger, f"run {args.name} start")  # pre-registered: an aborted run is still a run
    stdout = ""
    child_env = {**os.environ, "SEAL_RUN_ID": rid}
    for k in ("SEAL_REPORT", "SEAL_OUTPUT_DIR"):
        child_env.pop(k, None)
    report = rdir / "report.json" if rdir is not None and args.key else None
    if report is not None:
        child_env["SEAL_REPORT"] = str(report)
    if rdir is not None and args.output:
        child_env["SEAL_OUTPUT_DIR"] = str(rdir / "out")
    sealed_files = [resolved(path, f["path"]) for f in bank["files"]]
    modes = {f: f.stat().st_mode for f in sealed_files}
    try:
        for f, m in modes.items():  # read-only while the command runs
            os.chmod(f, m & ~0o222)
        if args.show_output:
            if role in SEALED_ROLES:
                print(f"note: showing the output of a {role} run; logged as a probe, so "
                      f"{args.name} is now tainted", file=sys.stderr)
            code = subprocess.run(args.command, cwd=root, env=child_env).returncode
        else:
            proc = subprocess.run(args.command, cwd=root, capture_output=True, text=True,
                                  errors="replace", env=child_env)
            code, stdout = proc.returncode, proc.stdout
    except OSError as e:
        code = 127
        print(f"cannot start the command: {e}", file=sys.stderr)
    finally:
        for f, m in modes.items():
            with contextlib.suppress(OSError):
                os.chmod(f, m)
    update = {"exit": code, "finished": now()}
    if role not in SEALED_ROLES:
        tail = [ln for ln in stdout.splitlines() if ln.strip()]
        update["summary"] = tail[-1][:200] if tail else None
    errors = []
    tampered = verify_bank(path, args.name, bank)
    if tampered:
        errors.append("the sealed files changed during the run: " + "; ".join(tampered))
    swapped = [f for f, h in fingerprint.items()
               if not resolved(path, f).is_file() or sha256(resolved(path, f)) != h]
    if swapped:
        errors.append("evaluator files changed during the run: " + ", ".join(swapped))
    if code == 0 and args.output:
        hashes = {}
        for o in args.output:
            f = rdir / "out" / o
            if f.is_symlink() or not f.is_file():
                errors.append(f"output {o} was not written to $SEAL_OUTPUT_DIR")
            else:
                hashes[o] = sha256(f)
        update["outputs"] = hashes or None
    if report is not None and code == 0:
        if report.is_symlink() or not report.is_file():
            errors.append("report missing: the command did not write $SEAL_REPORT")
        else:
            update["report_sha256"] = sha256(report)
            try:
                update["score"] = score_of(json.loads(report.read_text(encoding="utf-8")),
                                           args.key, manifest["episodes"])
            except Exception as e:  # noqa: BLE001
                errors.append(f"report refused: {e}"[:200])
    if report is not None:
        with contextlib.suppress(OSError):
            report.unlink()  # only the score is kept
    if tampered or swapped:
        update.update(status="tampered", score=None, score_error="; ".join(errors)[:300])
    elif code != 0:
        update.update(status="failed", score=None)
    elif errors:
        update.update(status="no-score", score=None, score_error="; ".join(errors)[:300])
    else:
        update["status"] = "ok"
    with locked(path):
        ledger = load_checked(path)  # re-load: other runs may have written meanwhile
        rec = next((r for r in ledger["runs"] if r.get("id") == record["id"]), None)
        if rec is None:
            raise SystemExit(f"refused: run {rid[:8]} is missing from the ledger; it was removed "
                             "while the command ran")
        rec.update(update)
        if tampered:
            ledger["banks"][args.name]["burns"].append(
                {"at": now(), "seq": next_seq(ledger),
                 "reason": f"sealed files changed during run {rid[:8]} ({args.version})"})
        save(path, ledger, f"run {args.name} end")
    extra = f" ({rec['score_error']})" if rec.get("score_error") else ""
    label = f"{args.system} {args.version}" if args.system else args.version
    print(f"logged run of {args.name} for {label} at {(commit or '-')[:12]}: "
          f"exit={code} status={rec['status']} score={rec['score']}{extra}"
          + (f"; outputs in {rdir / 'out'}" if rdir is not None and args.output else ""))
    if tampered:
        print(f"{args.name} is BURNED: the command changed its sealed files", file=sys.stderr)
        raise SystemExit(1)
    if swapped:
        print("refused: the evaluator files changed during the run; no score", file=sys.stderr)
        raise SystemExit(1)
    if code == 0 and rec["status"] == "no-score":
        raise SystemExit(1)
    raise SystemExit(code)


# ---------------------------------------------------------------- runs / refs / gitattributes

def run_flags(r: dict, bank: dict | None = None) -> list[str]:
    flags = []
    if bank and bank.get("burns"):
        flags.append("bank burned")
    if bank and bank.get("retired"):
        flags.append(f"bank retired to {bank['role']}")
    if bank and bank.get("probes"):
        flags.append("bank tainted by probe")
    if r.get("system"):
        flags.append(f"system {r['system']}")
    if r.get("over_budget"):
        flags.append("OVER BUDGET")
    if r.get("purpose") and r["purpose"] != "score":
        flags.append(f"purpose {r['purpose']}")
    if r.get("forced"):
        flags.append(f"FORCED ({r.get('reason')})")
    if r.get("dirty"):
        flags.append("dirty")
    if r.get("finished") is None:
        flags.append("aborted")
    elif r.get("status") == "failed" or (r.get("exit") not in (0, None)):
        flags.append(f"failed (exit {r.get('exit')})")
    elif r.get("status") == "no-score":
        flags.append(f"no score: {r.get('score_error')}")
    return flags


def cmd_runs(args: argparse.Namespace) -> None:
    ledger = load(ledger_path(args))
    rows = ledger["runs"]
    banks = ledger["banks"]
    if args.markdown:
        print("| Bank | Version | Commit | Score | Exit | Started | Flags |")
        print("|---|---|---|---|---|---|---|")
        for r in rows:
            flags = ", ".join(run_flags(r, banks.get(r["bank"]))).replace("|", "\\|")
            print(f"| {r['bank']} | {r['version']} | {(r['commit'] or '')[:8]} | {r['score']} "
                  f"| {r.get('exit')} | {r['started']} | {flags} |")
        return
    for r in rows:
        flags = "".join(f" {f}" for f in run_flags(r, banks.get(r["bank"])))
        print(f"{r['started']} {r['bank']:12} {r['version']:8} {(r['commit'] or '-')[:8]} "
              f"exit={r.get('exit')} score={r['score']}{flags}")


def allowed(rel: str, patterns: list[str]) -> bool:
    name = rel.rsplit("/", 1)[-1]
    for a in patterns:
        a = Path(a).as_posix() if a not in ("", ".") else a
        a = a[2:] if a.startswith("./") else a
        bare = a.rstrip("/")
        if rel == bare or rel.startswith(bare + "/") or fnmatch.fnmatchcase(rel, a):
            return True
        if "/" not in a and fnmatch.fnmatchcase(name, a):
            return True
    return False


def glob_matches(token: str, rel: str) -> bool:
    """True if a glob or templated path string would match the sealed path rel."""
    pat = re.sub(r"\$?\{[^{}]*\}", "*", token)  # f"{x}", "${x}", "{}" templates
    pat = re.sub(r"%[sdr]", "*", pat)
    if not any(c in pat for c in "*?["):
        return False
    literal = re.sub(r"\.[A-Za-z0-9]+$", "", re.sub(r"[*?\[\]{}$%]", "", pat)).strip("/._- ")
    if len(literal) < 3:
        return False  # "*", "*.py", "**/*.py": too generic to mean a sealed bank
    pat = pat[2:] if pat.startswith("./") else pat
    name = rel.rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0]
    for p in {pat, pat.replace("**/", "")}:
        if fnmatch.fnmatchcase(rel, p) or fnmatch.fnmatchcase(rel, "*/" + p):
            return True
        if "/" not in p and (fnmatch.fnmatchcase(name, p) or fnmatch.fnmatchcase(stem, p)):
            return True
    return False


def code_file(p: Path, exts: set[str]) -> bool:
    if p.suffix.lower() in exts:
        return True
    if p.suffix == "":
        try:
            with p.open("rb") as f:
                return f.read(2) == b"#!"
        except OSError:
            return False
    return False


def cmd_refs(args: argparse.Namespace) -> None:
    path = ledger_path(args)
    ledger = load(path)
    root = system_root(args, path)
    exts = {(e if e.startswith(".") else "." + e).lower() for e in args.ext}
    sealed = {resolved(path, f["path"]) for b in ledger["banks"].values() for f in b["files"]}
    targets = []
    for n, b in ledger["banks"].items():
        if b["role"] in args.roles:
            for f in b["files"]:
                p = resolved(path, f["path"])
                r = rel_posix(p, root)
                targets.append((n, Path(f["path"]).stem, f["path"] if r.startswith("..") else r))
    patterns = list(args.allow) + ([] if args.no_default_allow else list(DEFAULT_ALLOW))
    hits = []
    for d, dirs, names in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
        for nm in sorted(names):
            p = Path(d, nm)
            rel = rel_posix(p, root)
            if p.resolve() in sealed or not code_file(p, exts) or allowed(rel, patterns):
                continue
            try:
                text = p.read_text(errors="ignore")
            except OSError:
                continue
            tokens = {t for t in GLOB_TOKEN.findall(text) if any(c in t for c in "*?[{%")}
            for bank, stem, target in targets:
                if stem in text:
                    hits.append(f"{rel}: mentions {stem} ({bank})")
                for t in sorted(tokens):
                    if glob_matches(t, target):
                        hits.append(f"{rel}: pattern '{t}' would match {target} ({bank})")
    hits = list(dict.fromkeys(hits))
    if hits:
        print("\n".join(hits))
        print(f"\n{len(hits)} reference(s) to sealed banks outside the allow-list "
              "(best effort: paths built at run time in other ways are missed)", file=sys.stderr)
        raise SystemExit(1)
    print("no references to sealed banks outside the allow-list (best effort)")


def cmd_gitattributes(args: argparse.Namespace) -> None:
    path = ledger_path(args)
    ledger = load(path)
    top = toplevel(path.parent)
    base = top or path.parent
    print(f"# add to {base / '.gitattributes'}: -text keeps the sealed bytes (and hashes) "
          "unchanged by line-ending conversion; -diff keeps git diff / log -p from printing them")
    seen = set()
    for b in ledger["banks"].values():
        for f in b["files"]:
            rel = rel_posix(resolved(path, f["path"]), base)
            if rel not in seen:
                seen.add(rel)
                pat = "/" + re.sub(r"([ \\*?\[\]#!])", r"\\\1", rel)
                print(f"{pat} -text -diff")


def cmd_statement(args: argparse.Namespace) -> None:
    """Facts for the report's data-discipline section, read from the ledger, not from memory."""
    ledger = load(ledger_path(args))
    head = ["Bank", "Role", "Earlier roles", "Writer", "Sealed", "Burns", "Versions scored",
            "Runs", "Forced", "Decisions fed", "Ran by", "Looks used", "Other systems",
            "Episodes", "Phrasings", "Source", "Probes", "Content clashes", "Evaluator"]
    rows = []
    for name, b in ledger["banks"].items():
        runs = [r for r in ledger["runs"] if r["bank"] == name]
        versions = sorted({(f"{r['system']}:" if r.get("system") else "") + r["version"]
                           for r in runs if r.get("status") == "ok"})
        others: dict[str, int] = {}
        for r in runs:
            if r.get("system"):
                others[r["system"]] = others.get(r["system"], 0) + 1
        m = b.get("manifest") or {}
        ph = m.get("phrasings")
        if isinstance(ph, dict):
            ph = f"{sum(ph.values())} over {len(ph)} keys (min {min(ph.values())})" if ph else None
        probes = b.get("probes") or []
        earlier = ", ".join(f"{x['from']} until {x['at'][:10]} ({x['reason']})" for x in b.get("retired", []))
        burns = "; ".join(f"{x['at'][:10]} {x['reason']}" for x in b["burns"])
        rows.append([name, b["role"], earlier or "-", b["writer"], b["sealed_at"][:10], burns or "0",
                     f"{len(versions)} ({', '.join(versions)})" if versions else "0", str(len(runs)),
                     str(sum(1 for r in runs if r.get("forced"))),
                     str(sum(1 for r in runs if r.get("purpose") in CHOOSING)),
                     ", ".join(sorted({r.get("ran_by") or "?" for r in runs})) or "-",
                     looks_cell(ledger, name, b),
                     ", ".join(f"{k} ({v})" for k, v in sorted(others.items())) or "-",
                     str(m.get("episodes", "not recorded")),
                     str(ph) if ph is not None else "not recorded",
                     str(m.get("source", "not recorded")),
                     (f"TAINTED: {len(probes)} probe(s), "
                      + "; ".join(f"{p['at'][:10]} {p['items'] or 'all'} item(s) {p['reason']}"
                                  for p in probes))
                     if probes else "0",
                     "; ".join(b.get("clashes") or []) or "-",
                     evaluator_cell(runs)])
    if args.markdown:
        print("| " + " | ".join(head) + " |")
        print("|" + "---|" * len(head))
        for row in rows:
            print("| " + " | ".join(c.replace("|", "\\|") for c in row) + " |")
    else:
        for row in rows:
            print("; ".join(f"{h}: {c}" for h, c in zip(head, row)))
    bad, notes = chain_problems(ledger_path(args), ledger)
    print("\nLedger chain: " + ("; ".join(bad) if bad else "intact") + "".join(f"; {n}" for n in notes))
    for m in ledger.get("migrations") or []:
        print(f"Migrated on {m['at'][:10]} (approved by {m['approved_by']}: {m['reason']}): the "
              f"{m['runs']} earlier runs are taken on trust, without a chain.")
    lines, _ = wear_lines(ledger, WEAR_DEFAULTS, dt.date.today())
    print("\nWear:\n" + ("\n".join(lines) if lines else "  no bank is worn, over budget or expired"))
    print("\nPaste this table. Any claim about the banks that it does not support is a defect.")


def evaluator_cell(runs: list[dict]) -> str:
    """Whether every scored run used the same evaluator and simulator files."""
    fps = {json.dumps(r.get("fingerprint"), sort_keys=True) for r in runs if r.get("status") == "ok"}
    if len(fps) > 1:
        return (f"CHANGED: {len(fps)} different evaluator fingerprints; scores are not comparable. "
                "Rescore the base with the current evaluator.")
    if fps == {"null"}:
        return "no fingerprint"
    return "one fingerprint" if fps else "-"


def looks_cell(ledger: dict, name: str, b: dict) -> str:
    used = looks_used(ledger, name, b["role"])
    looks = bank_looks(b)
    cell = f"{used} of {looks}" if looks is not None else f"{used} (no budget)"
    changes = b.get("budget_changes") or []
    if changes:
        cell += "; budget " + "; ".join(
            f"{c['from']} -> {c['to']} on {c['at'][:10]} ({c['reason']}"
            + (f"; approved by {c['approved_by']}" if c.get("approved_by") else "") + ")"
            for c in changes)
    return cell


def wear_lines(ledger: dict, thresholds: dict, today: dt.date) -> tuple[list[str], bool]:
    """Human lines and whether any is a breach."""
    lines, breach = [], False
    for name, b in ledger["banks"].items():
        role = b["role"]
        if role not in SEALED_ROLES:
            continue
        looks = bank_looks(b)
        used = looks_used(ledger, name, role)
        thr = thresholds.get(role)
        def add(text: str, bad: bool) -> None:
            nonlocal breach
            lines.append(f"  {'BREACH' if bad else 'note'}: {name} ({role}): {text}")
            breach = breach or bad
        if looks is not None and used > looks:
            add(f"OVER BUDGET, {used} looks of {looks}", True)
        elif looks is not None and used == looks and role != "final":
            add(f"look budget spent ({used} of {looks}): retire it or seal a fresh bank", False)
        # every run counts toward wear, whatever its declared purpose
        to = "to select" if role == "confirm" else "to train"
        if thr is not None and used >= thr:
            add(f"worn: {used} runs, threshold {thr}: retire it ({to}) and seal a fresh bank", True)
        if b["burns"] and not retired_after_burn(b):
            add("burned but still in a sealed role: retire it to train", True)
        if b.get("probes") and role == "safety":
            add("tainted by a probe: a safety gate bank is replaced; retire it and seal a fresh one", True)
        exp = b.get("expires")
        if exp and dt.date.fromisoformat(exp) < today:
            add(f"expired on {exp} (stale): replace it", True)
    return lines, breach


def cmd_wear(args: argparse.Namespace) -> None:
    ledger = load(ledger_path(args))
    thresholds = dict(WEAR_DEFAULTS)
    for role in WEAR_DEFAULTS:
        v = getattr(args, role)
        if v is not None:
            thresholds[role] = v
    today = dt.date.fromisoformat(check_date(args.today)) if args.today else dt.date.today()
    lines, breach = wear_lines(ledger, thresholds, today)
    print("\n".join(lines) if lines else "no bank is worn, over budget or expired")
    if breach:
        raise SystemExit(1)


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger", help="ledger path (default $SEAL_LEDGER, else the nearest seal-ledger.json)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init")
    s.add_argument("--require-mirror", action="store_true",
                   help="every later change and run needs $SEAL_MIRROR outside the repository")
    s.set_defaults(fn=cmd_init)
    s = sub.add_parser("common", help="records any bank may share (schema keys, placeholders)")
    s.add_argument("file", help="JSON file; every string in it becomes a common record")
    s.add_argument("--reason", required=True)
    s.set_defaults(fn=cmd_common)
    sub.add_parser("require-mirror", help="one way: require $SEAL_MIRROR from now on"
                   ).set_defaults(fn=cmd_require_mirror)
    s = sub.add_parser("cycle", help="open the next improvement cycle (alpha spending)")
    s.add_argument("action", choices=["open"])
    s.add_argument("--of", type=int, required=True, help="K: mechanism tests this cycle may run")
    s.add_argument("--reason", required=True)
    s.set_defaults(fn=cmd_cycle)
    s = sub.add_parser("migrate", help="start a hash chain on a ledger from an older seal.py")
    s.add_argument("--approved-by", required=True, help="who checked the history (not the builder)")
    s.add_argument("--reason", required=True)
    s.set_defaults(fn=cmd_migrate)
    s = sub.add_parser("seal")
    s.add_argument("name")
    s.add_argument("--role", choices=ROLES, required=True)
    s.add_argument("--writer", required=True, help="who wrote it and what they were allowed to read")
    s.add_argument("--note", default="")
    s.add_argument("--looks", type=int, default=None,
                   help="look budget: runs allowed in this role (required before a holdout runs)")
    s.add_argument("--manifest", default=None, help="JSON file: episodes, phrasings, segments, source ...")
    s.add_argument("--expires", default=None, help="YYYY-MM-DD after which the bank is stale")
    s.add_argument("paths", nargs="+")
    s.set_defaults(fn=cmd_seal)
    s = sub.add_parser("budget")
    s.add_argument("name")
    s.add_argument("--looks", type=int, required=True)
    s.add_argument("--reason", required=True)
    s.add_argument("--approved-by", default=None,
                   help="who agreed to raise it (required when raising): not the builder")
    s.set_defaults(fn=cmd_budget)
    sub.add_parser("mirror", help="start the $SEAL_MIRROR copy of this ledger's chain").set_defaults(fn=cmd_mirror)
    s = sub.add_parser("manifest")
    s.add_argument("name")
    s.add_argument("file")
    s.add_argument("--expires", default=None)
    s.set_defaults(fn=cmd_manifest)
    s = sub.add_parser("probe")
    s.add_argument("name")
    s.add_argument("--items", type=int, required=True, help="how many items the information was about")
    s.add_argument("--reason", required=True)
    s.set_defaults(fn=cmd_probe)
    s = sub.add_parser("wear")
    for role, v in WEAR_DEFAULTS.items():
        s.add_argument(f"--{role}", type=int, default=None,
                       help=f"decisions a {role} bank may feed (default {v})")
    s.add_argument("--today", default=None, help="date to check expiry against (default today)")
    s.set_defaults(fn=cmd_wear)
    s = sub.add_parser("verify")
    s.add_argument("names", nargs="*")
    s.add_argument("--require-mirror", action="store_true",
                   help="fail when $SEAL_MIRROR is unset or inside the repository (use in CI)")
    s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("burn")
    s.add_argument("name")
    s.add_argument("--reason", required=True)
    s.set_defaults(fn=cmd_burn)
    s = sub.add_parser("retire")
    s.add_argument("name")
    s.add_argument("--to", choices=ROLES, required=True)
    s.add_argument("--reason", required=True)
    s.set_defaults(fn=cmd_retire)
    s = sub.add_parser("statement")
    s.add_argument("--markdown", action="store_true")
    s.set_defaults(fn=cmd_statement)
    s = sub.add_parser("run")
    s.add_argument("name")
    s.add_argument("--version", required=True, help="version label, e.g. V3")
    s.add_argument("--root", default=None, help="system root the command runs in (default: the ledger's directory)")
    s.add_argument("--report", help=argparse.SUPPRESS)
    s.add_argument("--key", default=None,
                   help="name of the score in the flat JSON report {name: whole number} the "
                        "command writes to $SEAL_REPORT (deleted after reading; only the score is kept)")
    s.add_argument("--output", nargs="+", default=None, metavar="NAME",
                   help="file names the command writes into $SEAL_OUTPUT_DIR (e.g. a pass map); "
                        "their sha256 is logged")
    s.add_argument("--fingerprint", nargs="+", default=None, metavar="PATH",
                   help="evaluator, judge prompt and simulator files; on a sealed bank exactly "
                        "the manifest's evaluator list. Hashed into the run record")
    s.add_argument("--purpose", choices=PURPOSES, default="score",
                   help="why this run happens; gate = its result decides whether a change is kept")
    s.add_argument("--system", default=None,
                   help="another system run on this bank (a baseline from another run, a "
                        "comparison system); counted as a look, shown apart in statement")
    s.add_argument("--env", nargs="+", default=None, metavar="NAME",
                   help="environment variables that select what runs (e.g. AGENT); their values "
                        "are part of the version, so two agents on one tree are told apart")
    s.add_argument("--allow-dirty", action="store_true")
    s.add_argument("--show-output", action="store_true", help="pass the command's output through")
    s.add_argument("--force", action="store_true")
    s.add_argument("--reason", default=None)
    s.set_defaults(fn=cmd_run)
    s = sub.add_parser("runs")
    s.add_argument("--markdown", action="store_true")
    s.set_defaults(fn=cmd_runs)
    s = sub.add_parser("refs")
    s.add_argument("--root", default=None, help="tree to scan (default: the ledger's directory)")
    s.add_argument("--roles", nargs="+", default=["holdout", "final", "safety", "confirm"],
                   choices=ROLES)
    s.add_argument("--allow", nargs="*", default=[],
                   help="files, dirs or globs (from --root) allowed to name the banks")
    s.add_argument("--ext", nargs="+", default=list(CODE_EXTS), help="code file extensions to scan")
    s.add_argument("--no-default-allow", action="store_true",
                   help="also scan " + ", ".join(DEFAULT_ALLOW))
    s.set_defaults(fn=cmd_refs)
    sub.add_parser("gitattributes").set_defaults(fn=cmd_gitattributes)
    argv = sys.argv[1:] if argv is None else argv
    command: list[str] = []
    if "--" in argv:
        i = argv.index("--")
        argv, command = argv[:i], argv[i + 1:]
    args = ap.parse_args(argv)
    args.command = command
    args.fn(args)


if __name__ == "__main__":
    main()
