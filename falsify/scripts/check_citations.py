#!/usr/bin/env python3
"""Check that every cited file exists and, where a number is attributed to it, that the number
occurs in the cited file.

falsify §5 asks whether a pipeline's claimed output ever appeared; a cited file is the same claim
in miniature. This script scans every text file under a directory for path-like tokens that look
like citations (results/r03.csv, a bare round-2.md) and checks two things: does the path resolve,
and if the citing line also carries a number, does that number occur in the cited file.

  check_citations.py DIR        exit 0: clean · 1: findings below · 2: usage
  check_citations.py --json DIR machine-readable

Findings:
  missing            the cited path does not resolve, relative to the citing file's directory
                      or to DIR itself
  number-not-found    the citing line names a number and that exact number string is not a
                      substring of the cited file's content
"""
import json
import os
import re
import sys

SCAN_EXT = {".md", ".txt", ".py", ".log", ".json", ".yaml", ".yml", ".csv"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
URL_RE = re.compile(r"https?://\S+")
# debt: a token counts as a citation only with a slash, or a bare name ending in SCAN_EXT. Misses
# a citation to a file of some other extension, and still mistakes a dotted module path ending in
# .py or .json for a file (bench.metrics.py reads as a citation to metrics.py). Upgrade: resolve
# against a real file index of the repo first, and only then decide a token was a citation.
TOKEN_RE = re.compile(
    r"(?<![\w./-])(\.{0,2}/?(?:[\w.-]+/)+[\w.-]+\.\w{1,5}|[\w-]+\.(?:md|txt|py|log|json|ya?ml|csv))(?![\w/-])"
)
# debt: numbers are scoped to "the rest of the line", not to the nearest citation, so a second
# citation's number on the same line can produce a false match or a false miss. Bare integers are
# excluded entirely (too noisy: line counts, dates, list sizes) — an attributed count like
# "37 trades" is invisible to this check. Upgrade: pair each number to its nearest token by
# distance, and widen the pattern behind a small verb whitelist ("shows", "reports", "at").
NUM_RE = re.compile(r"-?\d+\.\d+%?|-?\d+%")


def citations(path):
    """Yield (lineno, token, rest_of_line) for each path-like token in a text file."""
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except (UnicodeDecodeError, OSError):
        return
    for i, line in enumerate(lines, 1):
        stripped = URL_RE.sub(" ", line)
        for m in TOKEN_RE.finditer(stripped):
            token = m.group(1)
            if "*" in token:
                continue
            rest = stripped[: m.start()] + stripped[m.end():]
            yield i, token, rest


def resolve(token, citing_dir, root):
    for base in (citing_dir, root):
        cand = os.path.normpath(os.path.join(base, token))
        if os.path.isfile(cand):
            return cand
    return None


def check(root):
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if os.path.splitext(name)[1] not in SCAN_EXT:
                continue
            fpath = os.path.join(dirpath, name)
            rel = os.path.relpath(fpath, root)
            for lineno, token, rest in citations(fpath):
                target = resolve(token, dirpath, root)
                if not target:
                    findings.append(("missing", rel, lineno, token, "does not resolve to a file"))
                    continue
                nums = NUM_RE.findall(rest)
                if not nums:
                    continue
                body = open(target, encoding="utf-8", errors="replace").read()
                bad = [n for n in nums if n not in body]
                if bad:
                    findings.append(("number-not-found", rel, lineno, token,
                                      f"{', '.join(bad)} not found in {os.path.relpath(target, root)}"))
    return findings


def main(argv):
    as_json = "--json" in argv
    args = [a for a in argv if a != "--json"]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(__doc__)
        return 2
    findings = check(args[0])
    if as_json:
        print(json.dumps([{"kind": k, "citing": f"{c}:{l}", "path": t, "detail": d}
                           for k, c, l, t, d in findings], ensure_ascii=False, indent=1))
    else:
        for k, c, l, t, d in findings:
            print(f"{k:<18} {c}:{l}  {t}  {d}")
        if not findings:
            print("ok: every cited path resolves and carries its attributed number")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
