#!/usr/bin/env python3
"""Hash-keyed verdict cache for LLM judges, so runs replay deterministically.

Key = sha256(sha256(prompt text) | kind | canonical JSON payload). Before hashing, the
prompt text has "\\r\\n" turned into "\\n" and is NFC-normalised, so a checkout's line
endings or an editor's Unicode form do not change keys. Changing a prompt changes every
key, so old verdicts can never leak into a new prompt. Verdict files hold only
{key, verdict}: no input text is stored beside a verdict.

    verdict_cache.py chunk reqs.jsonl --size 150 --prefix out/part      # batches for cheap judges
    verdict_cache.py merge out/part-*-verdicts.jsonl --into verdicts.json --labels yes no abstain
                [--prefer "escalate,review,none"]                      # order of care, most careful first
    verdict_cache.py missing reqs.jsonl --verdicts verdicts.json          # keys still unjudged, and counts
                [--show-payloads]
    verdict_cache.py overlap shipped.json sealed-reqs.jsonl [more.jsonl ...]
                                                                       # exit 1 if the shipped cache
                                                                       # holds any sealed-bank key

merge: --labels is required and case-insensitive. A verdict is lowercased and stripped of
surrounding whitespace, quotes and punctuation ("Escalate." -> "escalate"); a word
outside --labels is dropped (an abstention, never a guess). When two verdicts for one key
disagree (in the files, or with the cache), the key becomes an abstention: it is removed
and reported, unless --prefer gives an order of care covering both labels, in which case
the more careful (earlier) label wins. Malformed lines are skipped and counted.

missing prints only keys (and counts on stderr). --show-payloads prints the whole request
lines instead. NEVER use --show-payloads on requests built from sealed banks (validation,
holdout, final): the payloads are the sealed text.

overlap is for `make check`: the cache that ships with the agent must hold no verdict
for a sealed bank's request (holdout, safety, confirm, final), or the score measures a judge
that has seen the test. It prints counts only, never keys or payloads.

Library use (import from your system's judge module):

    from verdict_cache import key, Cache
    cache = Cache("judge_verdicts.json")
    v = cache.lookup(key(prompt_text, "safety", {"message": scrubbed}))   # None = abstain

A request line is {"key": K, "kind": KIND, "payload": {...}}; a verdict line is
{"key": K, "verdict": "word"}. Standard library only, Python 3.10+.
"""

from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import os
import string
import sys
import unicodedata
from pathlib import Path

STRIP = string.whitespace + string.punctuation + "“”‘’«»…"


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def normalise_prompt(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n"))


def key(prompt_text: str, kind: str, payload: dict) -> str:
    p = hashlib.sha256(normalise_prompt(prompt_text).encode()).hexdigest()
    return hashlib.sha256(f"{p}|{kind}|{canonical(payload)}".encode()).hexdigest()


def clean_label(v) -> str:
    return str(v).strip(STRIP).lower()


class Cache:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data: dict[str, str] = json.loads(self.path.read_text()) if self.path.exists() else {}

    def lookup(self, k: str) -> str | None:
        return self.data.get(k)

    def put(self, k: str, verdict: str) -> None:
        self.data[k] = verdict

    def save(self) -> None:
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(self.data, indent=0, sort_keys=True) + "\n")
        os.replace(tmp, self.path)


def read_jsonl(path: str | Path, need: tuple[str, ...] = ("key",)) -> tuple[list[dict], int]:
    """Rows that parse as JSON objects with the needed string fields, and a count of the rest."""
    rows, bad = [], 0
    for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if not ln.strip():
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            bad += 1
            continue
        if not isinstance(r, dict) or any(not isinstance(r.get(f), str) or not r.get(f) for f in need):
            bad += 1
            continue
        rows.append(r)
    return rows, bad


def warn_bad(bad: int, what: str) -> None:
    if bad:
        print(f"# skipped {bad} malformed line(s) in {what}", file=sys.stderr)


def positive(s: str) -> int:
    try:
        v = int(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {s!r}") from None
    if v < 1:
        raise argparse.ArgumentTypeError("--size must be at least 1")
    return v


def cmd_chunk(a: argparse.Namespace) -> None:
    rows, bad = read_jsonl(a.reqs)
    warn_bad(bad, a.reqs)
    paths = []
    for i in range(0, len(rows), a.size):
        p = Path(f"{a.prefix}-{i // a.size:03d}.jsonl")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows[i:i + a.size]))
        paths.append(str(p))
    print("\n".join(paths))


def cmd_merge(a: argparse.Namespace) -> None:
    labels = {clean_label(x) for x in a.labels} - {""}
    if not labels:
        raise SystemExit("--labels must name at least one verdict word")
    care = [clean_label(x) for x in a.prefer.split(",")] if a.prefer else []
    care = [x for x in care if x]
    unknown = [x for x in care if x not in labels]
    if unknown:
        raise SystemExit(f"--prefer names labels not in --labels: {', '.join(unknown)}")
    rank = {x: i for i, x in enumerate(care)}
    cache = Cache(a.into)
    votes: dict[str, set[str]] = collections.defaultdict(set)
    for k, v in cache.data.items():
        votes[k].add(v)
    n = off = bad = 0
    files = sorted({f for pattern in a.files for f in glob.glob(pattern)})
    if not files:
        raise SystemExit("no verdict files match " + " ".join(a.files))
    for f in files:
        rows, b = read_jsonl(f, need=("key",))
        bad += b
        for r in rows:
            v = clean_label(r.get("verdict", ""))
            if v not in labels:
                off += 1
                continue  # an unknown word is an abstention, never a guess
            votes[r["key"]].add(v)
            n += 1
    abstained, resolved = [], 0
    for k, vs in votes.items():
        if len(vs) == 1:
            cache.data[k] = next(iter(vs))
        elif all(v in rank for v in vs):
            cache.data[k] = min(vs, key=rank.__getitem__)
            resolved += 1
        else:
            cache.data.pop(k, None)
            abstained.append(k)
    cache.save()
    print(f"merged {n} verdicts from {len(files)} file(s) into {a.into}; {off} off-label dropped; "
          f"{bad} malformed line(s) skipped; {resolved} conflict(s) resolved by --prefer; "
          f"{len(abstained)} conflicting key(s) removed (abstain)")
    for k in sorted(abstained):
        print(f"conflict, abstained: {k}")


def cmd_missing(a: argparse.Namespace) -> None:
    cache = Cache(a.verdicts)
    rows, bad = read_jsonl(a.reqs)
    warn_bad(bad, a.reqs)
    missing = [r for r in rows if r["key"] not in cache.data]
    if a.show_payloads:
        print("# --show-payloads: never on requests from sealed banks", file=sys.stderr)
    for r in missing:
        print(json.dumps(r, ensure_ascii=False) if a.show_payloads else r["key"])
    kinds = collections.Counter(str(r.get("kind", "?")) for r in missing)
    by_kind = ", ".join(f"{k}: {c}" for k, c in sorted(kinds.items()))
    print(f"# {len(missing)} missing of {len(rows)} request(s)" + (f" ({by_kind})" if by_kind else ""),
          file=sys.stderr)


def cmd_overlap(a: argparse.Namespace) -> None:
    cache = Cache(a.shipped)
    total = hits = 0
    for path in a.reqs:
        rows, bad = read_jsonl(path)
        warn_bad(bad, path)
        n = sum(1 for r in rows if r["key"] in cache.data)
        total, hits = total + len(rows), hits + n
        print(f"{path}: {n} of {len(rows)} request key(s) are in {a.shipped}")
    if hits:
        print(f"FAIL: the shipped cache holds {hits} verdict(s) for sealed requests; keep sealed "
              "verdicts in a per-run cache outside the shipped code", file=sys.stderr)
        raise SystemExit(1)
    print(f"ok: no overlap ({total} sealed request(s) checked)")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("chunk")
    s.add_argument("reqs")
    s.add_argument("--size", type=positive, default=150)
    s.add_argument("--prefix", required=True)
    s.set_defaults(fn=cmd_chunk)
    s = sub.add_parser("merge")
    s.add_argument("files", nargs="+")
    s.add_argument("--into", required=True)
    s.add_argument("--labels", nargs="+", required=True, help="allowed verdict words (case-insensitive)")
    s.add_argument("--prefer", help='order of care, most careful first, e.g. "escalate,review,none"')
    s.set_defaults(fn=cmd_merge)
    s = sub.add_parser("missing")
    s.add_argument("reqs")
    s.add_argument("--verdicts", required=True)
    s.add_argument("--show-payloads", action="store_true",
                   help="print whole request lines; NEVER on sealed banks")
    s.set_defaults(fn=cmd_missing)
    s = sub.add_parser("overlap")
    s.add_argument("shipped", help="the verdict cache that ships with the agent")
    s.add_argument("reqs", nargs="+", help="request files built from sealed banks")
    s.set_defaults(fn=cmd_overlap)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
