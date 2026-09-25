#!/usr/bin/env python3
"""Check a falsify report against its own last line.

falsify §7 says a report ends with exactly one line of the form

  FALSIFY: <n> BLOCK · <n> CONSIDER · <n> NOTE · <n> UNMEASURED · attacked: <kinds> · not checked: <n> (budget <n>, instruction <n>)

and §6 says how a finding's label follows from severity × confidence. Nothing enforced either
until this script. It reads a report (a file, or stdin) and reports every way the line and the
body disagree. It is the consumer the line needed: the harness in ../fixtures scores a run only
if this passes, and a verifier can run it on a supervisor-evals transcript.

  check_report.py REPORT.md        exit 0: consistent · 1: findings below · 2: usage
  check_report.py --json REPORT.md machine-readable

Findings it can raise (name — meaning):
  no-verdict-line     the last non-empty line is not a FALSIFY: line; the report has not finished
  verdict-not-last    a FALSIFY: line exists but something follows it
  duplicate-verdict   FALSIFY: appears more than once (a template echoed above a real verdict)
  partial-in-final    FALSIFY_PARTIAL: in a finished report
  gap-arithmetic      budget + instruction ≠ not checked
  mislabel            a finding's label disagrees with §6 applied to its own severity × confidence,
                      the finding does not say `override:`, and it is not a BLOCK that names one of
                      §6's categories (security, authz, data loss, destructive, a decorative guard)
  two-labels          a finding carries two labels (CONSIDER→BLOCK); write one, and `override:` if
                      it differs from the arithmetic
  straddles           a severity or confidence range crosses a §6 threshold, so the bucket is
                      undecided
  unscored            a labelled finding carries no severity × confidence
  count-mismatch      the line's count for a bucket differs from the body, recomputed from
                      severity × confidence (label counts are reported alongside)
  nothing-scored      the line claims findings but no line in the body carries severity × confidence
"""
import json
import re
import sys

SEP = r"\s*[·•|]\s*"
LINE_RE = re.compile(
    r"^FALSIFY:\s*(?P<block>\d+)\s*BLOCK" + SEP + r"(?P<consider>\d+)\s*CONSIDER" + SEP
    + r"(?P<note>\d+)\s*NOTE" + SEP + r"(?P<unmeasured>\d+)\s*UNMEASURED" + SEP
    + r"attacked:\s*(?P<attacked>.*?)" + SEP
    + r"not checked:\s*(?P<nc>\d+)\s*\(\s*budget\s*(?P<budget>\d+)\s*,\s*instruction\s*(?P<instr>\d+)\s*\)\s*$"
)
LABELS = ("BLOCK", "CONSIDER", "NOTE", "UNMEASURED")
NUM = r"(?:[0-5](?:\.\d+)?|\.\d+)"
RANGE = r"(?:\s*[–-]\s*(" + NUM + r"))?"
SXC_RE = re.compile(r"(?<![\w.])(" + NUM + r")" + RANGE + r"\s*[×x*]\s*(" + NUM + r")" + RANGE + r"(?![\w.])")
SEVCONF_RE = re.compile(r"severity\s*[:=]?\s*(" + NUM + r")\D{0,40}?confidence\s*[:=]?\s*(" + NUM + r")", re.I)


def bucket(risk):
    if risk >= 3.5:
        return "BLOCK"
    if risk >= 2.0:
        return "CONSIDER"
    return "NOTE"


def parse_score(text):
    """Return (sev_lo, sev_hi, conf_lo, conf_hi) or None. Severity is the 1–5 number, confidence 0–1.

    Only a pair whose confidence is at most 1 counts, so "a 3x3 grid" or "2 × 4 contracts" in a
    finding's prose is not read as a score."""
    for m in SXC_RE.finditer(text):
        s1, s2, c1, c2 = (float(x) if x else None for x in m.groups())
        s2, c2 = s2 or s1, c2 or c1
        if 0 < s1 <= 5 and 0 < s2 <= 5 and c1 <= 1 and c2 <= 1:
            return (s1, s2, c1, c2)
    for m in SEVCONF_RE.finditer(text):
        s, c = float(m.group(1)), float(m.group(2))
        if 0 < s <= 5 and c <= 1:
            return (s, s, c, c)
    return None


# A finding starts at a heading, bullet, numbered item, table row, bold lead or F<n> id.
START_RE = re.compile(r"^\s*(#+\s|[-*+]\s|\|\s*\S|\d+[.)]\s|\*\*|F\d+\b)")
# Its label is the first word after the marker and an optional id ("### F1 — BLOCK", "- **NOTE**",
# "| F4 | NOTE |"), or a label written straight before its score ("… — BLOCK (4 × 0.9)").
# "no NOTE-level issues" is neither, so it is not a finding.
_L = r"(BLOCK|CONSIDER|NOTE|UNMEASURED)"
LEAD_RE = re.compile(r"^\s*(?:#+|[-*+]|\d+[.)]|\|)?\s*(?:\*\*)?\s*(?:F\d+|\d+[.)]?)?\s*[—–:.|*-]*\s*(?:\*\*)?\s*"
                     + _L + r"\b(?:\*\*)?(\s*(?:→|->)\s*" + _L + r"\b)?")
INLINE_RE = re.compile(r"\b" + _L + r"\b(\s*(?:→|->)\s*" + _L + r"\b)?\**\s*\(")
# §6 makes these BLOCK whatever the arithmetic says. Matching them is textual, so it is a floor:
# a finding that names one of them is not second-guessed.
# debt: keyword match, not a judgement; a BLOCK that merely mentions "auth" passes. Upgrade path is a
# required `§6:` tag on the finding once readers are shown to write it.
CATEGORY_RE = re.compile(r"secur|\bauth|data[- ]loss|destructive|decorative\b[^.\n]{0,80}\b(guard|check)|"
                         r"\b(guard|check)\b[^.\n]{0,80}\bdecorative", re.I)


def finding_blocks(lines):
    """Group body lines into findings: (first line index, text). A heading's finding runs to the next
    start line, blank lines included, so a score written under the heading belongs to it; any other
    finding ends at a blank line or the next start line."""
    blocks, cur, start, heading = [], [], None, False
    for i, l in enumerate(lines):
        if START_RE.match(l) or (not l.strip() and not heading):
            if cur:
                blocks.append((start, "\n".join(cur)))
            cur, start, heading = [], None, False
            if not l.strip():
                continue
            heading = l.lstrip().startswith("#")
        if not l.strip():
            continue
        if start is None:
            start = i
        cur.append(l)
    if cur:
        blocks.append((start, "\n".join(cur)))
    return blocks


def check(text):
    findings = []
    lines = text.splitlines()
    nonempty = [(i, l) for i, l in enumerate(lines) if l.strip()]
    verdict_idx = [i for i, l in nonempty if l.strip().startswith("FALSIFY:")]
    partial = [i for i, l in nonempty if "FALSIFY_PARTIAL:" in l]
    if partial:
        findings.append(("partial-in-final", f"line {partial[0] + 1}: FALSIFY_PARTIAL: belongs to a message that is not the finished report"))
    if not verdict_idx:
        findings.append(("no-verdict-line", "no line starts with FALSIFY: — the report has not finished (falsify §7)"))
        line = None
    else:
        if len(verdict_idx) > 1:
            findings.append(("duplicate-verdict", f"FALSIFY: appears {len(verdict_idx)} times (lines {', '.join(str(i + 1) for i in verdict_idx)}); a template echoed above the verdict reads as the verdict"))
        last_i = nonempty[-1][0]
        if verdict_idx[-1] != last_i:
            findings.append(("verdict-not-last", f"line {verdict_idx[-1] + 1} is the verdict but line {last_i + 1} follows it"))
        raw = lines[verdict_idx[-1]].strip()
        m = LINE_RE.match(raw)
        if not m:
            findings.append(("no-verdict-line", f"line {verdict_idx[-1] + 1} starts with FALSIFY: but does not match the §7 form: {raw[:120]}"))
            line = None
        else:
            line = {k: (int(v) if v.isdigit() else v) for k, v in m.groupdict().items()}
            if line["budget"] + line["instr"] != line["nc"]:
                findings.append(("gap-arithmetic", f"not checked: {line['nc']} but budget {line['budget']} + instruction {line['instr']} = {line['budget'] + line['instr']}"))

    # Body findings: any line (outside the verdict) carrying a label and/or a severity × confidence.
    body_end = verdict_idx[-1] if verdict_idx else len(lines)
    by_label = dict.fromkeys(LABELS, 0)
    by_risk = dict.fromkeys(LABELS, 0)
    scored_any = False
    for i, block in finding_blocks(lines[:body_end]):
        head = block.splitlines()[0]
        if head.lstrip().startswith("FALSIFY"):
            continue
        lm = LEAD_RE.match(head) or INLINE_RE.search(head)
        score = parse_score(block)
        if not lm and not score:
            continue
        override = "override:" in block.lower()
        label = lm.group(1) if lm else None
        if lm and lm.group(3):
            findings.append(("two-labels", f"line {i + 1}: {lm.group(0).strip()} — one label per finding; `override:` says why it differs from the arithmetic"))
            label = lm.group(3)
        if label:
            by_label[label] += 1
        if score:
            scored_any = True
            s_lo, s_hi, c_lo, c_hi = score
            b_lo, b_hi = bucket(s_lo * c_lo), bucket(s_hi * c_hi)
            if b_lo != b_hi:
                findings.append(("straddles", f"line {i + 1}: {s_lo}–{s_hi} × {c_lo}–{c_hi} spans {b_lo} to {b_hi}; score the finding once"))
                by_risk[label or b_hi] += 1
                continue
            categorical = label == "BLOCK" and b_hi != "BLOCK" and CATEGORY_RE.search(block)
            if label and label != b_hi and (override or categorical):
                by_risk[label] += 1  # a stated override or a §6 category is a decision; count it where it was put
            else:
                by_risk[b_hi] += 1
            if label and label != "UNMEASURED" and label != b_hi and not (override or categorical):
                findings.append(("mislabel", f"line {i + 1}: labelled {label}, but {s_hi} × {c_hi} = {s_hi * c_hi:.2f} is {b_hi} under §6 (no `override:` and no §6 BLOCK category given)"))
        elif label and label != "UNMEASURED":
            findings.append(("unscored", f"line {i + 1}: labelled {label} with no severity × confidence"))

    if line:
        claimed = sum(line[k] for k in ("block", "consider", "note", "unmeasured"))
        if claimed and not scored_any and not any(by_label.values()):
            findings.append(("nothing-scored", f"the line claims {claimed} finding(s) but no body line carries a label or severity × confidence"))
        elif scored_any or any(by_label.values()):
            for key, lab in (("block", "BLOCK"), ("consider", "CONSIDER"), ("note", "NOTE")):
                if line[key] != by_risk[lab]:
                    findings.append(("count-mismatch", f"line says {line[key]} {lab}; body has {by_risk[lab]} by severity × confidence ({by_label[lab]} by label)"))
            if line["unmeasured"] != by_label["UNMEASURED"]:
                findings.append(("count-mismatch", f"line says {line['unmeasured']} UNMEASURED; body labels {by_label['UNMEASURED']}"))
    return findings, line, by_label, by_risk


def main(argv):
    as_json = "--json" in argv
    args = [a for a in argv if a != "--json"]
    if len(args) > 1 or (args and args[0] in ("-h", "--help")):
        print(__doc__)
        return 2
    text = open(args[0], encoding="utf-8").read() if args else sys.stdin.read()
    findings, line, by_label, by_risk = check(text)
    if as_json:
        print(json.dumps({"ok": not findings, "findings": [{"name": n, "detail": d} for n, d in findings],
                          "line": line, "by_label": by_label, "by_risk": by_risk}, ensure_ascii=False, indent=1))
    else:
        for n, d in findings:
            print(f"  {n:<18} {d}")
        if findings:
            print(f"  {len(findings)} finding(s): the line and the body disagree")
        else:
            print(f"  ok: FALSIFY line consistent with the body ({by_risk['BLOCK']} BLOCK · {by_risk['CONSIDER']} CONSIDER · {by_risk['NOTE']} NOTE · {by_label['UNMEASURED']} UNMEASURED)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
