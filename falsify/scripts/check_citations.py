#!/usr/bin/env python3
"""Check that every cited file exists and, where a number is attributed to it, that the number
occurs in the cited file.

falsify §5 asks whether a pipeline's claimed output ever appeared; a cited file is the same claim
in miniature. This script scans prose/evidence files (.md, .txt, .log) under a directory for
path-like tokens that look like citations (results/r03.csv, a bare round-2.md) and checks two
things: does the path resolve, and if the citing line also carries a number, does that number
occur in the cited file. A cited file itself can be of any type (a .py, .json, .csv, whatever
the target names): only the files scanned *for* citations are restricted to prose, so a source
file's own string literals ("fills.csv" inside an `os.path.join(...)` call) are not misread as
citations.

  check_citations.py DIR        exit 0: clean · 1: findings below · 2: usage
  check_citations.py --json DIR machine-readable

Findings:
  missing            the cited path does not resolve, relative to the citing file's directory,
                      each ancestor directory up to DIR, or DIR itself
  number-not-found    the citing line names a number and that exact number does not occur in the
                      cited file at a number boundary (not embedded in a longer number)
"""
import json
import os
import re
import sys

# debt: scanning is restricted to prose/evidence extensions to keep source code's own path-shaped
# string literals out of the citation count (see the module docstring). This still leaks on a
# prose file that quotes code verbatim (a .md with a fenced ```python block containing
# os.path.join("data", "fills.csv")` reads as a citation), and it misses a genuine citation
# written inside a scanned file's own comments if that file's extension isn't in this set.
# Upgrade: parse fenced code blocks out of prose before scanning, and let a caller extend the set.
SCAN_EXT = {".md", ".txt", ".log"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
URL_RE = re.compile(r"https?://\S+")
# debt: a token counts as a citation only with a slash, or a bare name ending in one of the
# extensions below (broader than SCAN_EXT, since a prose file can cite a .py or .json as
# evidence even though .py/.json files are not themselves scanned). Misses a citation to a file
# of some other extension, and still mistakes a dotted module path ending in one of these
# extensions for a file (bench.metrics.py reads as a citation to metrics.py). Upgrade: resolve
# against a real file index of the repo first, and only then decide a token was a citation.
TOKEN_RE = re.compile(
    r"(?<![\w./-])(\.{0,2}/?(?:[\w.-]+/)+[\w.-]+\.\w{1,5}|[\w-]+\.(?:md|txt|py|log|json|ya?ml|csv))(?![\w/-])"
)
# debt: real-repo noise this script cannot tell from a false "missing", measured against this
# repo's own docs: a conventional filename used as a category rather than a literal path
# ("the repo's own CLAUDE.md, CONTRIBUTING.md"); a bare filename that names a sibling skill's own
# file, correct in context but not on the citing file's ancestor chain ("SKILL.md" in the repo
# README meaning each skill's own, not one at the repo root); a placeholder path in generic
# documentation describing a file that will exist in a user's own project, not this repo
# (`x.pine`, `TRADES.csv`); and the slash-token alternative above accepting any extension, not
# just the bare-token whitelist, so a git remote like `owner/repo.git` also reads as a citation.
# Upgrade: score these by confidence rather than a flat missing/not-missing, using surrounding
# words ("your", "a", "the repo's own") as a hedge signal.
# debt: numbers are scoped to "the rest of the line", not to the nearest citation, so a second
# citation's number on the same line can produce a false match or a false miss. Bare integers are
# excluded entirely (too noisy: line counts, dates, list sizes). An attributed count like
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
    """Try the citing file's directory, then each ancestor up to and including root."""
    root_abs = os.path.abspath(root)
    d = os.path.abspath(citing_dir)
    while True:
        cand = os.path.normpath(os.path.join(d, token))
        if os.path.isfile(cand):
            return cand
        if d == root_abs:
            return None
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def number_in(n, text):
    """True if n occurs in text at a number boundary, not embedded in a longer number."""
    pat = re.compile(r"(?<![\d.])" + re.escape(n) + r"(?!\d)")
    return pat.search(text) is not None


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
                bad = [n for n in nums if not number_in(n, body)]
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
