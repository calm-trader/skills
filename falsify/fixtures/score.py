#!/usr/bin/env python3
"""Score a falsify report against the fixture's answer key.

  score.py REPORT.md [--key answer-key.json] [--json] [--no-gate]

Exit 1 without scoring when ../scripts/check_report.py rejects the report: a report that has not
finished, or whose last line disagrees with its body, is not a run, whatever it found. That is the
gate the FALSIFY: line exists for. Otherwise prints one line per defect (found / missed), the
false positives on decoys, and the totals. Exit 0.

--no-gate scores the report anyway and prints what check_report found as a separate compliance
line. Use it for an arm that has no FALSIFY: line to give (readers without the skill, the floor
the fixture README asks for); count compliance per arm, never mix it into the score.

Credit is textual on purpose: a defect is found when one paragraph of the report names one of
its files and one of its keywords. It is a floor, not a judge; read the misses by hand before believing them.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import check_report  # noqa: E402


def blocks(text):
    """Paragraphs: a finding is a heading or bullet and the lines under it up to the next blank line."""
    return [b.lower() for b in text.split("\n\n") if b.strip()]


def names_file(block, f):
    """A paragraph names a file by path (`hedge.py`) or as a module (`adapter.SIDE`, `positions.signed_qty`)."""
    f = f.lower()
    if f in block:
        return True
    stem = f[:-3] if f.endswith(".py") else None
    return bool(stem) and re.search(r"\b" + re.escape(stem) + r"\.\w", block) is not None


def mentions(text, files, keywords):
    """True when one paragraph names one of the files and one of the keywords."""
    return any(any(names_file(b, f) for f in files) and any(k.lower() in b for k in keywords) for b in blocks(text))


def score(text, key):
    out = {"defects": {}, "false_positives": []}
    for did, d in key["defects"].items():
        out["defects"][did] = {"row": d["row"], "control": d.get("control", False),
                               "found": mentions(text, d["files"], d["keywords"])}
    for xid, x in key["decoys"].items():
        if any(any(names_file(b, f) for f in x["files"]) and any(k.lower() in b for k in x["keywords"])
               and not any(u.lower() in b for u in x["unless"]) for b in blocks(text)):
            out["false_positives"].append(xid)
    scored = {k: v for k, v in out["defects"].items() if not v["control"]}
    out["found"] = sum(v["found"] for v in scored.values())
    out["of"] = len(scored)
    out["control_found"] = sum(v["found"] for v in out["defects"].values() if v["control"])
    return out


def main(argv):
    as_json = "--json" in argv
    gate = "--no-gate" not in argv
    args = [a for a in argv if a not in ("--json", "--no-gate")]
    keyp = os.path.join(HERE, "answer-key.json")
    if "--key" in args:
        i = args.index("--key"); keyp = args[i + 1]; del args[i:i + 2]
    if len(args) != 1:
        print(__doc__); return 2
    text = open(args[0], encoding="utf-8").read()
    findings, *_ = check_report.check(text)
    if findings and gate:
        print("not scored: check_report rejects the report", file=sys.stderr)
        for n, d in findings:
            print(f"  {n:<18} {d}", file=sys.stderr)
        return 1
    key = json.load(open(keyp, encoding="utf-8"))
    out = score(text, key)
    out["compliance"] = sorted({n for n, _ in findings})
    if as_json:
        print(json.dumps(out, indent=1)); return 0
    for did, v in out["defects"].items():
        tag = "control" if v["control"] else f"row {v['row']}"
        print(f"  {'found ' if v['found'] else 'MISSED'}  {did}  ({tag})  {key['defects'][did]['what'][:90]}")
    for xid in out["false_positives"]:
        print(f"  FALSE+  {xid}  {key['decoys'][xid]['what'][:90]}")
    if not gate:
        print(f"  compliance: {', '.join(out['compliance']) or 'ok'} (not gated)")
    print(f"  {out['found']}/{out['of']} planted rows 2–6 defects · control {out['control_found']}/1 · {len(out['false_positives'])} false positive(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
