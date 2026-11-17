#!/usr/bin/env python3
"""Fair comparison of two systems, runs or versions on the same fresh episodes.

    compare.py --a NAME mapsA/ --b NAME mapsB/ [--base NAME mapsBase/]
               [--clusters DIR] [--segments DIR]
               [--train-manifest-a F] [--train-manifest-b F] [--in-sample]
               [--own-a N BASE_PASSED PASSED] [--own-b N BASE_PASSED PASSED]
               [--ledger seal-ledger.json] [--markdown]
               [--catch-a DIR --catch-b DIR] [--alarm-a DIR --alarm-b DIR] [--kinds DIR]
               [--target-catch RATE] [--target-catch-kind RATE] [--target-alarm RATE]

Each maps folder holds one pass map per comparison bank, {episode id: true/false}, named
<bank>.json, from one run of that system on that bank (log every run with
`seal.py run BANK --system NAME --purpose compare`; each is a look). --clusters and
--segments are folders with the same file names: episode -> phrasing id(s), episode ->
segment (see noise.py).

Refused (exit 2) when the systems were not run on the same banks and the same episode ids,
or when a comparison bank is named in either system's training manifest, exactly
{"system": NAME, "banks": [ledger bank names], "files": [{"path": P, "sha256": S}]}: what
that system trained on, chose on or was error-analysed on. It needs --ledger; each bank's
file hashes and writer set-up come from the ledger, so a renamed copy is caught. Unknown
banks, files that do not hash as given, other shapes, another system's name or an empty
manifest are refused. --in-sample overrides: such banks are printed as "in-sample,
not comparable" and left out of the pooled result.
Without both manifests the sentence says freshness was not checked. --ledger is loaded
through seal.py and refused without $SEAL_MIRROR outside the repository, when its chain
or mirror does not check out, unless all compared runs share one non-empty evaluator
fingerprint, or unless each
system (matched by --system, or by --version when no system was given) has exactly one run
per bank that is ok with exit 0, purpose compare, not forced, not dirty, and whose
--output hashes include this map file's sha256. --clusters must cover every episode and
slot, and every episode needs a segment, or the command stops. "Reliable" comes from the
pooled cluster test; it is kept only when the difference points the same way on 3 distinct
writer set-ups (from the ledger's manifests, else --writers {bank: writer set-up}, printed
as not verified). That agreement is described, never tested.

Prints, per bank and pooled: both scores, B (passed only by A), C (passed only by B), the
net (B minus A), the cluster-aware p and interval, a verdict; the per-segment table; the
baseline row (--base, the common ancestor) with a check that the banks are equally hard
for it; the transfer table (gain over the baseline on each system's own holdouts, from
--own-*, against its gain on these fresh banks); and one sentence ready to paste.

Safety results (when the system has a safety-critical class, give these: a level pass
count can hide a reliable safety loss). --catch-a/--catch-b are folders of risk-catch maps,
<bank>.json = {episode: true when the high-risk case was caught}, over the high-risk
episodes only. --alarm-a/--alarm-b are folders of false-alarm maps, {episode: true when
there was NO false alarm}, over the non-risk episodes only. In every map true is the good
outcome. Both systems must cover the same episodes, all of them in the pass maps, and no
episode may be in both kinds of map; a bank without such episodes has no file. With
--ledger each of these files must also be an --output of that system's one run on the bank.
--kinds is a folder episode -> risk kind for the high-risk episodes. Printed: counts and a
paired cluster test for caught risk and for false alarms, and caught risk per kind (raw
and Holm p). A reliable safety gain must agree on 3 writer set-ups like any gain; a
reliable safety loss is printed as a loss whatever the writers say.

Targets from FRAME.md: --target-catch RATE (overall catch rate), --target-catch-kind RATE
(every kind, needs --kinds), --target-alarm RATE (the false-alarm rate may be at most
RATE). Each system is checked with the 95% Wilson interval: "met" only when the whole
interval is on the right side of the target; "not shown" when the count is but the
interval is not; "below target" (for alarms "above target") otherwise.

The per-segment p values are printed raw and Holm-corrected; the segment verdict uses the
Holm p, except that a loss with raw p < 0.05 that Holm does not keep is printed
"possible loss (raw p)", for segments and risk kinds. The sentence carries the risk-catch, false-alarm and target results when given.

Standard library only, Python 3.10+. Imports noise.py from the same folder.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import noise  # noqa: E402


def refuse(msg: str) -> None:
    print(f"compare.py: refused: {msg}", file=sys.stderr)
    raise SystemExit(2)


def load_dir(d: str) -> dict[str, dict[str, bool]]:
    p = Path(d)
    if not p.is_dir():
        refuse(f"{d} is not a folder of <bank>.json pass maps")
    files = sorted(p.glob("*.json"))
    if not files:
        refuse(f"{d}: no .json pass maps")
    return {f.stem: noise.read_map_file(f) for f in files}


def manifest_banks(path: str | None, system: str, ledger: dict | None) -> set[str]:
    """What a system trained, chose or was error-analysed on, as marks (bank names, file
    sha256s, writer set-ups), from its provenance manifest
    {"system": NAME, "banks": [ledger bank names], "files": [{"path": P, "sha256": S}]}.
    Every bank must be in the verified ledger (its hashes and writer set-up come from
    there); every file must exist and hash as given. Anything else is refused."""
    if not path:
        return set()
    if ledger is None:
        refuse(f"training manifest {path} needs --ledger: its banks are checked against it")
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        refuse(f"cannot read training manifest {path}: {e}")
    if not isinstance(data, dict) or set(data) != {"system", "banks", "files"}:
        refuse(f'training manifest {path}: expected exactly {{"system": NAME, "banks": [...], '
               '"files": [{"path": P, "sha256": S}]}')
    if data["system"] != system:
        refuse(f"training manifest {path} is for another system, not {system!r}")
    banks, files = data["banks"], data["files"]
    if not isinstance(banks, list) or not isinstance(files, list) or not (banks or files):
        refuse(f"training manifest {path}: banks and files are lists, not both empty")
    marks: set[str] = set()
    for b in banks:
        if not isinstance(b, str) or b not in ledger["banks"]:
            refuse(f"training manifest {path}: a bank that is not in the ledger "
                   "(seal TRAIN banks into the ledger too)")
        marks |= bank_marks(ledger, b)
    for f in files:
        ok = (isinstance(f, dict) and set(f) == {"path", "sha256"} and isinstance(f["path"], str)
              and Path(f["path"]).is_file())
        if not ok or noise_sha(Path(f["path"])) != f["sha256"]:
            refuse(f"training manifest {path}: a files entry that is missing or does not hash "
                   "as given")
        marks.add(f["sha256"])
    return marks


def noise_sha(p: Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_ledger(path: str) -> dict:
    """The ledger, loaded through seal.py, with its hash chain (and mirror, if set) verified."""
    import seal
    lp = Path(path).resolve()
    if not lp.is_file():
        refuse(f"no ledger at {path}")
    ledger = seal.load(lp)
    bad, _ = seal.chain_problems(lp, ledger)
    why = seal.mirror_problem(lp)
    if why:
        bad.append(f"no mirror protects it ({why})")
    if bad:
        refuse("the ledger does not check out: " + "; ".join(bad))
    return ledger


def bank_marks(ledger: dict | None, bank: str) -> set[str]:
    """What a training manifest may name for a bank: its name, its files' sha256, its writer set-up."""
    marks = {bank}
    b = (ledger or {}).get("banks", {}).get(bank)
    if b:
        marks |= {f["sha256"] for f in b["files"]}
        ws = (b.get("manifest") or {}).get("writer_setup")
        if ws:
            marks.add(ws)
    return marks


def pooled_word(total: dict, pa, pb, clusters, fresh_ids, writers) -> str:
    """The pooled verdict; a reliable difference must also point the same way on
    noise.MIN_WRITERS distinct writer set-ups (from the ledger's manifests or --writers)."""
    w = noise.word(total)
    if w == "inside the noise":
        return w
    if writers is None:
        return "not reliable across writers (writer set-ups unknown: give --ledger or --writers)"
    sign = 1 if total["net"] > 0 else -1
    groups = noise.by_group(fresh_ids, lambda i: writers[i.split(":", 1)[0]])
    same = sum(1 for g in groups.values()
               if noise.paired(pa, pb, clusters, g, interval=False)["net"] * sign > 0)
    ok, rule = noise.writer_rule(same, len(groups))
    return f"{w} (pooled cluster test)" if ok else f"not reliable across writers ({rule})"


def load_extra(d: str, flag: str, passes: dict[str, dict[str, bool]]) -> dict[str, dict[str, bool]]:
    """A folder of risk-catch or false-alarm maps: <bank>.json over a subset of that bank's
    episodes. A bank with no such episodes has no file."""
    out = load_dir(d)
    for bank, m in out.items():
        if bank not in passes:
            refuse(f"{flag} {d}: {bank}.json is not one of the comparison banks")
        extra = set(m) - set(passes[bank])
        if extra:
            refuse(f"{flag} {d}: {bank}.json has {len(extra)} episode ids that are not in the "
                   f"pass map (e.g. {sorted(extra)[0]!r})")
    return out


def load_pair(da: str | None, db: str | None, what: str, passes) -> tuple[dict, dict] | None:
    """Both systems' maps for one safety measure, pooled to bank:episode ids, or None."""
    if not da and not db:
        return None
    if not (da and db):
        refuse(f"give both --{what}-a and --{what}-b, from the same episodes")
    ma, mb = load_extra(da, f"--{what}-a", passes), load_extra(db, f"--{what}-b", passes)
    if set(ma) != set(mb) or any(set(ma[k]) != set(mb[k]) for k in ma):
        refuse(f"--{what}-a and --{what}-b do not cover the same banks and episode ids")
    return ({f"{b}:{k}": v for b, m in ma.items() for k, v in m.items()},
            {f"{b}:{k}": v for b, m in mb.items() for k, v in m.items()})


def rate(s: str) -> float:
    try:
        v = float(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{s!r} is not a rate")
    if not 0 < v < 1:
        raise argparse.ArgumentTypeError("a target is a rate between 0 and 1, e.g. 0.95")
    return v


def holm_adjust(ps: list[float]) -> list[float]:
    """Holm-adjusted p values, in the input order (reliable when below 0.05)."""
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    out, top = [1.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        top = max(top, min(1.0, (len(ps) - rank) * ps[i]))
        out[i] = top
    return out


def holm_word(r: dict, adj: float) -> str:
    """Verdict from the Holm p. A loss the raw p shows but Holm does not is still flagged:
    correcting over many groups must not hide harm."""
    w = noise.word({"p": adj, "net": r["net"]})
    if w == "inside the noise" and r["net"] < 0 and r["p"] < noise.ALPHA:
        return f"possible loss (raw p = {r['p']:.3f})"
    return w


def target_status(k: int, n: int, target: float, at_most: bool = False) -> tuple[str, str]:
    """(status, 95% Wilson interval) of k/n against a target. "met" needs the whole interval
    on the right side; a count that is but an interval that is not is "not shown"."""
    lo, hi = noise.wilson(n, k)
    span = f"{lo:.1%} to {hi:.1%}"
    if at_most:
        if hi <= target:
            return "met", span
        return ("not shown (the interval goes above the target)" if k / n <= target
                else "above target (misses the cap)"), span
    if lo >= target:
        return "met", span
    return ("not shown (the interval goes below the target)" if k / n >= target
            else "below target"), span


def short(status: str) -> str:
    return status.split(" (", 1)[0]


def safety_word(r: dict, base, cand, clusters, ids, writers, gain: str, loss: str) -> str:
    """Verdict for a safety measure where true is good. A gain follows the writer rule; a
    reliable loss is never softened by it."""
    w = noise.word(r)
    if w == "inside the noise":
        return w
    across = pooled_word(r, base, cand, clusters, ids, writers)
    if w == "reliable gain":
        return across.replace("reliable gain", gain, 1)
    return loss + (" (pooled cluster test)" if across.startswith(w) else
                   " (pooled cluster test; " + across.split("(", 1)[1])


def pct(k: int, n: int) -> str:
    return f"{k} ({k / n:.1%})" if n else str(k)


def table(head: list[str], rows: list[list[str]], markdown: bool) -> None:
    if markdown:
        print("| " + " | ".join(head) + " |")
        print("|" + "---|" * len(head))
        for r in rows:
            print("| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |")
    else:
        widths = [max(len(str(x)) for x in col) for col in zip(head, *rows)]
        for r in [head, *rows]:
            print("  ".join(str(c).ljust(w) for c, w in zip(r, widths)).rstrip())
    print()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", nargs=2, metavar=("NAME", "DIR"), required=True)
    ap.add_argument("--b", nargs=2, metavar=("NAME", "DIR"), required=True)
    ap.add_argument("--base", nargs=2, metavar=("NAME", "DIR"))
    ap.add_argument("--clusters")
    ap.add_argument("--segments")
    ap.add_argument("--train-manifest-a")
    ap.add_argument("--train-manifest-b")
    ap.add_argument("--in-sample", action="store_true")
    ap.add_argument("--own-a", nargs=3, type=int, metavar=("N", "BASE_PASSED", "PASSED"))
    ap.add_argument("--own-b", nargs=3, type=int, metavar=("N", "BASE_PASSED", "PASSED"))
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--ledger", help="seal-ledger.json: check each system ran once per bank")
    ap.add_argument("--writers", help="{bank: writer set-up}, when there is no --ledger")
    ap.add_argument("--catch-a", metavar="DIR", help="A's risk-catch maps, {episode: caught}, "
                                                     "over the high-risk episodes")
    ap.add_argument("--catch-b", metavar="DIR")
    ap.add_argument("--alarm-a", metavar="DIR", help="A's false-alarm maps, {episode: true when "
                                                     "NO false alarm}, over the non-risk episodes")
    ap.add_argument("--alarm-b", metavar="DIR")
    ap.add_argument("--kinds", metavar="DIR", help="episode -> risk kind, for the high-risk episodes")
    ap.add_argument("--target-catch", type=rate, metavar="RATE",
                    help="FRAME target for the overall catch rate, e.g. 0.95")
    ap.add_argument("--target-catch-kind", type=rate, metavar="RATE",
                    help="FRAME target for the catch rate of every risk kind, e.g. 0.90")
    ap.add_argument("--target-alarm", type=rate, metavar="RATE",
                    help="FRAME cap on the false-alarm rate, e.g. 0.10")
    args = ap.parse_args(argv)

    (na, da), (nb, db) = args.a, args.b
    A, B = load_dir(da), load_dir(db)
    base_name, BASE = (args.base[0], load_dir(args.base[1])) if args.base else (None, None)
    if set(A) != set(B) or (BASE is not None and set(BASE) != set(A)):
        refuse("the systems were not run on the same banks: "
               + "; ".join(f"{n}: {', '.join(sorted(m))}" for n, m in
                           ((na, A), (nb, B), (base_name, BASE)) if m is not None))
    for bank in A:
        for n, m in ((nb, B), (base_name, BASE)):
            if m is not None and set(m[bank]) != set(A[bank]):
                refuse(f"{bank}: {n} was not run on the same episode ids as {na}")
    catch = load_pair(args.catch_a, args.catch_b, "catch", A)
    alarm = load_pair(args.alarm_a, args.alarm_b, "alarm", A)
    if catch and alarm and set(catch[0]) & set(alarm[0]):
        refuse("an episode is in both the risk-catch and the false-alarm maps: the first are "
               "the high-risk episodes, the second the non-risk ones")
    if (args.kinds or args.target_catch or args.target_catch_kind) and not catch:
        refuse("--kinds, --target-catch and --target-catch-kind need --catch-a and --catch-b")
    if args.target_catch_kind and not args.kinds:
        refuse("--target-catch-kind needs --kinds (episode -> risk kind)")
    if args.target_alarm and not alarm:
        refuse("--target-alarm needs --alarm-a and --alarm-b")
    ledger = read_ledger(args.ledger) if args.ledger else None
    trained = {na: manifest_banks(args.train_manifest_a, na, ledger),
               nb: manifest_banks(args.train_manifest_b, nb, ledger)}
    insample = {bank: [n for n, s in trained.items() if s & bank_marks(ledger, bank)] for bank in A}
    insample = {k: v for k, v in insample.items() if v}
    if insample and not args.in_sample:
        refuse("comparison bank(s) in a training manifest: "
               + "; ".join(f"{k} (trained on by {', '.join(v)})" for k, v in insample.items())
               + ". Use fresh banks neither system has seen, or --in-sample to print them as not comparable.")
    fresh = [b for b in sorted(A) if b not in insample]
    if not fresh:
        refuse("no fresh bank left to compare on")
    names = [na, nb] + ([base_name] if base_name else [])
    if ledger is not None:
        import seal
        dirs = {na: da, nb: db, **({base_name: args.base[1]} if args.base else {})}
        extra_dirs = {n: [(f, d) for f, d in pairs if d] for n, pairs in (
            (na, (("--catch-a", args.catch_a), ("--alarm-a", args.alarm_a))),
            (nb, (("--catch-b", args.catch_b), ("--alarm-b", args.alarm_b))))}
        bad, fps = [], set()
        for bank in sorted(A):
            if bank not in ledger["banks"]:
                bad.append(f"{bank} is not a bank in the ledger")
                continue
            for n in names:
                runs = [r for r in ledger["runs"] if r["bank"] == bank
                        and (r.get("system") == n or (not r.get("system") and r["version"] == n))]
                if len(runs) != 1:
                    bad.append(f"{n} on {bank}: {len(runs)} logged runs")
                    continue
                r = runs[0]
                sha = seal.sha256(Path(dirs[n]) / f"{bank}.json")
                why = [w for w, c in (("not ok", r.get("status") != "ok" or r.get("exit") != 0),
                                      ("purpose is not compare", r.get("purpose") != "compare"),
                                      ("forced", r.get("forced")), ("dirty", r.get("dirty")),
                                      ("its pass map is not the file the run wrote (--output)",
                                       sha not in (r.get("outputs") or {}).values())) if c]
                for flag, d in extra_dirs.get(n, ()):
                    f = Path(d) / f"{bank}.json"
                    if f.is_file() and seal.sha256(f) not in (r.get("outputs") or {}).values():
                        why.append(f"its {flag} map is not a file the run wrote (--output)")
                if why:
                    bad.append(f"{n} on {bank}: " + ", ".join(why))
                fps.add(json.dumps(r.get("fingerprint"), sort_keys=True))
        if len(fps) != 1 or fps == {"null"}:
            bad.append("the runs must share one non-empty evaluator fingerprint (seal.py run "
                       f"--fingerprint); found {len(fps)} different, missing counted as one")
        if bad:
            refuse("each system must be scored exactly once per bank through `seal.py run "
                   "--purpose compare --output <bank>.json` (--system NAME or --version NAME), "
                   "frozen and successful: " + "; ".join(bad))
    checked = [n for n, f in ((na, args.train_manifest_a), (nb, args.train_manifest_b)) if f]

    def pooled(m: dict[str, dict[str, bool]], banks) -> dict[str, bool]:
        return {f"{b}:{k}": v for b in banks for k, v in m[b].items()}

    pa, pb = pooled(A, A), pooled(B, A)
    pbase = pooled(BASE, A) if BASE is not None else None
    clusters = noise.read_clusters(args.clusters) if args.clusters else None
    noise.check_cluster_ids(pa, clusters, args.clusters or "")
    segs = noise.read_labels(args.segments, pa, "--segments") if args.segments else None
    writers = None
    if ledger is not None:
        writers = {b: (ledger["banks"][b].get("manifest") or {}).get("writer_setup") for b in A}
        if not all(isinstance(v, str) and v.strip() for v in writers.values()):
            refuse("every comparison bank needs a writer_setup in its ledger manifest")
    elif args.writers:
        print("note: writer set-ups from --writers, not verified against a ledger")
        writers = noise.read_writers(args.writers, A)
    fresh_ids = [i for i in pa if i.split(":", 1)[0] in fresh]

    print(f"Fair comparison: {na} (A) against {nb} (B) on {len(fresh)} fresh bank(s), "
          f"{len(fresh_ids)} episodes" + (f"; baseline {base_name}" if base_name else ""))
    if len(fresh) < 2:
        print("warning: one bank is one writer's idea of the users; use at least 2 banks from 2 "
              "writer set-ups")
    if clusters is None:
        print("note: no --clusters, so every episode counts as independent and the intervals "
              "are too narrow")
    if len(checked) < 2:
        print("warning: freshness checked for " + (", ".join(checked) or "neither system")
              + ": give --train-manifest-a and --train-manifest-b")
    if not args.ledger:
        print("note: no --ledger, so one logged run per system per bank and freshness were "
              "not checked")
    print()

    head = ["Bank", "Episodes"] + ([base_name] if base_name else []) + [
        na, nb, "B (only A)", "C (only B)", "Net B-A", "p", "95% interval", "Verdict"]
    rows = []
    results = {}
    for bank in sorted(A):
        ids = [f"{bank}:{k}" for k in A[bank]]
        r = noise.paired(pa, pb, clusters, ids)
        results[bank] = r
        cells = [bank + (" (in-sample, not comparable)" if bank in insample else ""), str(r["n"])]
        if pbase is not None:
            cells.append(pct(sum(pbase[i] for i in ids), r["n"]))
        cells += [pct(r["base"], r["n"]), pct(r["cand"], r["n"]), str(r["b"]), str(r["c"]),
                  f"{r['net']:+d}", f"{r['p']:.3f}", f"{r['lo']:+d} to {r['hi']:+d}", noise.word(r)]
        rows.append(cells)
    total = noise.paired(pa, pb, clusters, fresh_ids)
    cells = ["pooled (fresh)", str(total["n"])]
    if pbase is not None:
        cells.append(pct(sum(pbase[i] for i in fresh_ids), total["n"]))
    cells += [pct(total["base"], total["n"]), pct(total["cand"], total["n"]), str(total["b"]),
              str(total["c"]), f"{total['net']:+d}", f"{total['p']:.3f}",
              f"{total['lo']:+d} to {total['hi']:+d}", pooled_word(total, pa, pb, clusters, fresh_ids, writers)]
    rows.append(cells)
    table(head, rows, args.markdown)
    wins = sum(1 for b in fresh if results[b]["net"] > 0)
    print(f"{nb} ahead on {wins} of {len(fresh)} fresh banks"
          + (f"; clusters by {total['slot']}" if clusters else "") + "\n")

    seg_parts = []
    if segs is not None:
        groups = noise.by_group(fresh_ids, segs.get)
        srows = []
        tests = {name: noise.paired(pa, pb, clusters, ids, interval=False)
                 for name, ids in groups.items()}
        for (name, r), adj in zip(tests.items(), holm_adjust([r["p"] for r in tests.values()])):
            ids = groups[name]
            w = holm_word(r, adj)
            cells = [name, str(r["n"])]
            if pbase is not None:
                cells.append(pct(sum(pbase[i] for i in ids), r["n"]))
            cells += [pct(r["base"], r["n"]), pct(r["cand"], r["n"]), str(r["b"]), str(r["c"]),
                      f"{r['net']:+d}", f"{r['p']:.3f}", f"{adj:.3f}", w]
            srows.append(cells)
            seg_parts.append(f"{name} {r['net']:+d}"
                             + ("" if w == "inside the noise" else f" ({w}, Holm p = {adj:.3f})"))
        print(f"By segment (pooled fresh banks; the verdict uses the Holm p over {len(tests)} segments):")
        table(["Segment", "Episodes"] + ([base_name] if base_name else [])
              + [na, nb, "B", "C", "Net B-A", "p", "Holm p", "Verdict"], srows, args.markdown)

    safety_parts: list[str] = []
    is_fresh = lambda i: i.split(":", 1)[0] in fresh  # noqa: E731
    if catch:
        ca, cb = catch
        ids = [i for i in ca if is_fresh(i)]
        if not ids:
            refuse("no high-risk episode on a fresh bank in the risk-catch maps")
        r = noise.paired(ca, cb, clusters, ids)
        w = safety_word(r, ca, cb, clusters, ids, writers, "reliably more caught", "reliably fewer caught")
        print(f"Caught risk ({r['n']} high-risk episodes on the fresh banks):")
        rows = [["all kinds", str(r["n"]), pct(r["base"], r["n"]), pct(r["cand"], r["n"]), str(r["b"]),
                 str(r["c"]), f"{r['net']:+d}", f"{r['p']:.3f}", "-", f"{r['lo']:+d} to {r['hi']:+d}", w]]
        part = (f"caught risk {na} {r['base']} of {r['n']} ({r['base'] / r['n']:.1%}), {nb} "
                f"{r['cand']} of {r['n']} ({r['cand'] / r['n']:.1%}), {nb} minus {na} {r['net']:+d} "
                f"(95% interval {r['lo']:+d} to {r['hi']:+d}, p = {r['p']:.3f}): {w}; "
                f"{r['b']} caught by {na} were missed by {nb}, {r['c']} the other way")
        kind_groups = {}
        if args.kinds:
            kinds = noise.read_labels(args.kinds, ids, "--kinds")
            kind_groups = noise.by_group(ids, kinds.get)
            ktests = {k: noise.paired(ca, cb, clusters, g, interval=False) for k, g in kind_groups.items()}
            moved = []
            for (k, kr), adj in zip(ktests.items(), holm_adjust([x["p"] for x in ktests.values()])):
                kw = holm_word(kr, adj).replace("reliable gain", "reliably more caught").replace(
                    "reliably worse", "reliably fewer caught")
                rows.append([f"kind {k}", str(kr["n"]), pct(kr["base"], kr["n"]), pct(kr["cand"], kr["n"]),
                             str(kr["b"]), str(kr["c"]), f"{kr['net']:+d}", f"{kr['p']:.3f}",
                             f"{adj:.3f}", "-", kw])
                if kw != "inside the noise":
                    moved.append(f"{k} {kr['base']} against {kr['cand']} of {kr['n']} ({kw}, "
                                 f"Holm p = {adj:.3f})")
            if moved:
                part += "; by risk kind " + ", ".join(moved)
        table(["Risk", "Episodes", na, nb, "B (only A)", "C (only B)", "Net B-A", "p", "Holm p",
               "95% interval", "Verdict"], rows, args.markdown)
        safety_parts.append(part)
        if args.target_catch or args.target_catch_kind:
            trows, tparts = [], []
            for name, m in ((na, ca), (nb, cb)):
                if args.target_catch:
                    k = sum(m[i] for i in ids)
                    st, span = target_status(k, len(ids), args.target_catch)
                    trows.append([name, "all kinds", f"{k} of {len(ids)} ({k / len(ids):.1%})", span,
                                  f"{args.target_catch:.0%}", st])
                    tparts.append(f"{name} {short(st)} ({k / len(ids):.1%}, interval {span})")
                if args.target_catch_kind:
                    by: dict[str, list[str]] = {}
                    for kind, g in kind_groups.items():
                        k = sum(m[i] for i in g)
                        st, span = target_status(k, len(g), args.target_catch_kind)
                        trows.append([name, f"kind {kind}", f"{k} of {len(g)} ({k / len(g):.1%})", span,
                                      f"{args.target_catch_kind:.0%}", st])
                        by.setdefault(short(st), []).append(f"{kind} {k} of {len(g)}")
                    tparts.append(f"{name} per kind: " + "; ".join(
                        f"{st} on {', '.join(v)}" for st, v in sorted(by.items())))
            print("Catch-rate targets (95% Wilson interval; met only when the whole interval is "
                  "at or above the target):")
            table(["System", "Risk", "Caught", "95% interval", "Target", "Status"], trows, args.markdown)
            goal = " and ".join(x for x in (
                f"{args.target_catch:.0%} overall" if args.target_catch else "",
                f"{args.target_catch_kind:.0%} per kind" if args.target_catch_kind else "") if x)
            safety_parts.append(f"catch-rate target {goal}: " + "; ".join(tparts))
    if alarm:
        fa, fb = alarm
        ids = [i for i in fa if is_fresh(i)]
        if not ids:
            refuse("no non-risk episode on a fresh bank in the false-alarm maps")
        r = noise.paired(fa, fb, clusters, ids)
        n = r["n"]
        ka, kb = n - r["base"], n - r["cand"]
        w = safety_word(r, fa, fb, clusters, ids, writers, "reliably fewer false alarms",
                        "reliably more false alarms")
        print(f"False alarms ({n} non-risk episodes on the fresh banks; fewer is better):")
        table(["Episodes", na, nb, "Only A alarmed", "Only B alarmed", "Net B-A", "p",
               "95% interval", "Verdict"],
              [[str(n), pct(ka, n), pct(kb, n), str(r["c"]), str(r["b"]), f"{kb - ka:+d}",
                f"{r['p']:.3f}", f"{-r['hi']:+d} to {-r['lo']:+d}", w]], args.markdown)
        safety_parts.append(
            f"false alarms {na} {ka} of {n} ({ka / n:.1%}), {nb} {kb} of {n} ({kb / n:.1%}), "
            f"{nb} minus {na} {kb - ka:+d} (95% interval {-r['hi']:+d} to {-r['lo']:+d}, "
            f"p = {r['p']:.3f}): {w}")
        if args.target_alarm:
            trows, tparts = [], []
            for name, k in ((na, ka), (nb, kb)):
                st, span = target_status(k, n, args.target_alarm, at_most=True)
                trows.append([name, f"{k} of {n} ({k / n:.1%})", span, f"{args.target_alarm:.0%}", st])
                tparts.append(f"{name} {short(st)} ({k / n:.1%}, interval {span})")
            print("False-alarm target (95% Wilson interval; met only when the whole interval is "
                  "at or below the target):")
            table(["System", "False alarms", "95% interval", "At most", "Status"], trows, args.markdown)
            safety_parts.append(f"false-alarm target at most {args.target_alarm:.0%}: " + "; ".join(tparts))
    if (catch or alarm) and args.ledger is None:
        print("note: no --ledger, so the risk-catch and false-alarm maps were not checked "
              "against the logged runs\n")

    base_total = None
    if pbase is not None:
        rates = []
        for bank in fresh:
            n = len(A[bank])
            k = sum(BASE[bank].values())
            lo, hi = noise.wilson(n, k)
            rates.append((bank, k, n, lo, hi))
        overlap = max(r[3] for r in rates) <= min(r[4] for r in rates)
        spread = ", ".join(f"{b} {k / n:.1%} ({lo:.1%} to {hi:.1%})" for b, k, n, lo, hi in rates)
        print(f"Baseline {base_name} on each fresh bank: {spread}.")
        print("  The banks look equally hard to the baseline; differences belong to the systems."
              if overlap else
              "  The banks are not equally hard for the baseline: compare within a bank, not across.")
        print()
        base_total = sum(pbase[i] for i in fresh_ids)
        trows = []
        n = len(fresh_ids)
        for name, own, score in ((na, args.own_a, total["base"]), (nb, args.own_b, total["cand"])):
            fresh_gain = (score - base_total) / n
            if own:
                on, ob, op = own
                if on <= 0 or not (0 <= ob <= on and 0 <= op <= on):
                    refuse(f"--own for {name}: need N > 0 and 0 <= counts <= N")
                own_gain = (op - ob) / on
                share = f"{fresh_gain / own_gain:.0%}" if own_gain > 0 else "-"
                trows.append([name, f"{op - ob:+d} of {on} ({own_gain:+.1%})",
                              f"{score - base_total:+d} of {n} ({fresh_gain:+.1%})", share])
            else:
                trows.append([name, "not given", f"{score - base_total:+d} of {n} ({fresh_gain:+.1%})", "-"])
        print(f"Transfer: gain over {base_name} on each system's own holdouts against these fresh banks")
        table(["System", "Own holdouts", "Fresh banks", "Transfer share"], trows, args.markdown)

    clus = (f"clusters by {total['slot']}" if clusters else "episodes counted as independent")
    fresh_claim = ("written by writer set-ups neither system trained on (manifests checked "
                   "against bank names, file hashes and writer set-ups)"
                   if len(checked) == 2 else
                   "freshness not checked for " + (", ".join(n for n in (na, nb) if n not in checked)))
    verdict_word = pooled_word(total, pa, pb, clusters, fresh_ids, writers)
    if verdict_word == "inside the noise" and (total["lo"] > 0 or total["hi"] < 0):
        verdict_word += (" (the bootstrap interval excludes zero but the cluster test does not "
                         "reach 0.05: treat it as no reliable difference)")
    sentence = (f"On the same {total['n']} fresh episodes from {len(fresh)} bank(s) "
                f"({', '.join(fresh)}), {fresh_claim}: "
                f"{na} {total['base']} ({total['base'] / total['n']:.1%}), "
                f"{nb} {total['cand']} ({total['cand'] / total['n']:.1%}); paired difference "
                f"{nb} minus {na} {total['net']:+d} (95% interval {total['lo']:+d} to "
                f"{total['hi']:+d}, p = {total['p']:.3f}, {clus}): {verdict_word}")
    if base_total is not None:
        sentence += f"; baseline {base_name} {base_total}"
    if seg_parts:
        sentence += "; by segment " + ", ".join(seg_parts)
    for part in safety_parts:
        sentence += "; " + part
    missing = [w for w, m in (("risk-catch", catch), ("false-alarm", alarm)) if not m]
    if missing:
        sentence += "; " + " and ".join(missing) + " maps not given"
    print("Sentence for the report:\n" + sentence + ".")


if __name__ == "__main__":
    main()
