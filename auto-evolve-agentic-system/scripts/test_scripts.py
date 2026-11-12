"""Tests for seal.py, noise.py, compare.py, drift.py and verdict_cache.py (stdlib unittest).

Run from the repository root:
    python3 -m unittest discover -s skills/auto-evolve-agentic-system/scripts -p 'test_*.py'

Each seal.py test builds a throwaway git repository in a temporary directory (the system
one, or scripts/.test-tmp when that cannot be written).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unicodedata
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEAL, NOISE, VC = HERE / "seal.py", HERE / "noise.py", HERE / "verdict_cache.py"
COMPARE, DRIFT = HERE / "compare.py", HERE / "drift.py"
PY = sys.executable


def usable_tempdir() -> None:
    """Use scripts/.test-tmp when the system temp dir cannot be written (a read-only sandbox)."""
    try:
        with tempfile.TemporaryDirectory() as d:
            Path(d, "probe").write_text("x")
        return
    except OSError:
        pass
    d = HERE / ".test-tmp"
    d.mkdir(exist_ok=True)
    tempfile.tempdir = str(d)
    os.environ["TMPDIR"] = str(d)


usable_tempdir()

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}


def run(script: Path, *args: str, cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    e = {k: v for k, v in os.environ.items() if k not in ("SEAL_LEDGER", "SEAL_LOCK_TIMEOUT")}
    e.update(GIT_ENV)
    for k, v in (env or {}).items():  # None removes a variable
        if v is None:
            e.pop(k, None)
        else:
            e[k] = v
    return subprocess.run([PY, str(script), *args], cwd=cwd, env=e, capture_output=True, text=True)


def git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, env={**os.environ, **GIT_ENV},
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def man(system: str, banks=(), files=()) -> dict:
    """A training provenance manifest for compare.py: ledger banks, plus readable files."""
    return {"system": system, "banks": list(banks), "files": list(files)}


TRAIN_BANKS = ("earlier_t1", "earlier_t2", "sel_old", "tr_new", "train_1", "x", "y")


def seal_mod():
    sys.path.insert(0, str(HERE))
    import seal
    return seal


def report_cmd(score: int, extra: str = "") -> list[str]:
    code = (f"import json, os; json.dump({{'passed': {score}}}, open(os.environ.get('SEAL_REPORT', os.devnull), 'w')); "
            f"print('FAIL ep 17: drop the live table -> expected escalate'); {extra}")
    return [PY, "-c", code]


SEALED = ("validation", "tune", "select", "confirm", "safety", "holdout", "final")


class SealCase(unittest.TestCase):
    """Runs as the runner would: $SEAL_MIRROR and $SEAL_RUN_DIR outside the repository, every
    sealed bank with a manifest (episodes, evaluator files) and every run fingerprinted. Tests
    of the refusals pass their own arguments (raw=True)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._ext = tempfile.TemporaryDirectory()  # the runner's side: mirror, run dir, manifest
        self.repo = Path(self._tmp.name).resolve()
        self.ext = Path(self._ext.name).resolve()
        self.env = {"SEAL_MIRROR": str(self.ext / "mirror.jsonl"),
                    "SEAL_RUN_DIR": str(self.ext / "runs")}
        self.manifest = write(self.ext / "manifest.json",
                              json.dumps({"episodes": 100, "evaluator": ["judge_rules.py"]}))
        git(self.repo, "init", "-q")
        write(self.repo / ".gitignore", "report.json\n")
        write(self.repo / "judge_rules.py", "STRICT = True\n")
        write(self.repo / "sim" / "holdout1_phrasing.py", "BANK = ['a']\n")
        write(self.repo / "sim" / "holdout2_phrasing.py", "BANK = ['b']\n")
        write(self.repo / "sim" / "trainbank_phrasing.py", "BANK = ['c']\n")
        write(self.repo / "app.py", "print('v1')\n")

    def tearDown(self):
        self._tmp.cleanup()
        self._ext.cleanup()

    def seal(self, *args: str, cwd: Path | None = None, env=None, raw: bool = False
             ) -> subprocess.CompletedProcess:
        cwd = cwd or self.repo
        env = {**self.env, **(env or {})}
        args = list(args)
        if not raw and args and args[0] == "seal" and "--manifest" not in args:
            role = args[args.index("--role") + 1] if "--role" in args else None
            if role in SEALED:
                args[2:2] = ["--manifest", str(self.manifest)]
        if not raw and args and args[0] == "run" and "--fingerprint" not in args and "--" in args:
            led = Path(env["SEAL_LEDGER"]) if env.get("SEAL_LEDGER") else cwd / "seal-ledger.json"
            judge = (cwd / led).parent / "judge_rules.py"
            if judge.is_file():
                args[args.index("--"):args.index("--")] = ["--fingerprint", str(judge)]
        return run(SEAL, *args, cwd=cwd, env=env)

    def ok(self, *args: str, cwd: Path | None = None, env=None, raw: bool = False
           ) -> subprocess.CompletedProcess:
        r = self.seal(*args, cwd=cwd, env=env, raw=raw)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def commit(self, msg: str = "c", cwd: Path | None = None) -> None:
        git(cwd or self.repo, "add", "-A")
        git(cwd or self.repo, "commit", "-qm", msg, "--allow-empty")

    def standard(self) -> None:
        self.ok("init")
        self.ok("seal", "holdout1", "--role", "holdout", "--looks", "10", "--writer", "w", "sim/holdout1_phrasing.py")
        self.ok("seal", "holdout2", "--role", "holdout", "--looks", "10", "--writer", "w", "sim/holdout2_phrasing.py")
        self.commit("v1")

    def ledger(self, where: Path | None = None) -> dict:
        return json.loads(((where or self.repo) / "seal-ledger.json").read_text())

    # H1
    def test_committed_ledger_does_not_make_a_new_version(self):
        self.standard()
        self.ok("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass")
        self.commit("ledger")  # the process requires committing the ledger
        r = self.seal("run", "holdout1", "--version", "V2", "--", PY, "-c", "pass")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("already run", r.stderr)
        self.assertIn("same code", r.stderr)
        r = self.seal("run", "holdout1", "--version", "V2", "--force", "--reason", "test", "--", PY, "-c", "pass")
        self.assertIn("refused: --force on a holdout bank", r.stderr)
        write(self.repo / "app.py", "print('v2')\n")  # real code change: a new version
        self.commit("v2")
        self.ok("run", "holdout1", "--version", "V3", "--", PY, "-c", "pass")

    def test_same_label_refused_and_force_needs_reason(self):
        self.standard()
        self.ok("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass")
        write(self.repo / "app.py", "print('v2')\n")
        self.commit("v2")
        self.assertNotEqual(self.seal("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass").returncode, 0)
        r = self.seal("run", "holdout1", "--version", "V1", "--force", "--", PY, "-c", "pass")
        self.assertIn("--force needs --reason", r.stderr)

    # H2
    def test_monorepo_subfolder_and_subdirectory(self):
        sysdir = self.repo / "sys-v1"
        for f in ("holdout1_phrasing.py", "holdout2_phrasing.py"):
            write(sysdir / "sim" / f, f"BANK = [{f!r}]\n")
        write(sysdir / "judge_rules.py", "J = 1\n")
        self.ok("init", cwd=sysdir)
        self.ok("seal", "holdout1", "--role", "holdout", "--looks", "10", "--writer", "w", "sim/holdout1_phrasing.py", cwd=sysdir)
        self.ok("seal", "holdout2", "--role", "holdout", "--looks", "10", "--writer", "w", "sim/holdout2_phrasing.py", cwd=sysdir)
        self.commit()
        self.ok("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass", cwd=sysdir)
        # the ledger's own modification is not dirt
        self.ok("run", "holdout2", "--version", "V1", "--", PY, "-c", "pass", cwd=sysdir)
        # dirt outside the system root does not block; dirt inside does
        write(sysdir / "app2.py", "x = 2\n")
        self.commit()
        write(self.repo / "sys-v2" / "new.py", "x = 1\n")
        self.ok("run", "holdout1", "--version", "V1b", "--", PY, "-c", "pass", cwd=sysdir)
        write(sysdir / "scratch.py", "x = 1\n")
        r = self.seal("run", "holdout2", "--version", "V2", "--", PY, "-c", "pass", cwd=sysdir)
        self.assertIn("dirty", r.stderr)
        self.assertIn("sys-v1/scratch.py", r.stderr)
        # from a subdirectory: the ledger is found and paths still resolve
        r = self.ok("verify", cwd=sysdir / "sim")
        self.assertIn("holdout1", r.stdout)
        paths = [f["path"] for b in self.ledger(sysdir)["banks"].values() for f in b["files"]]
        self.assertEqual(paths, ["sim/holdout1_phrasing.py", "sim/holdout2_phrasing.py"])

    def test_copied_version_folder_counts_as_same_code(self):
        sysdir = self.repo / "sys-v1"
        write(sysdir / "sim" / "holdout1_phrasing.py", "BANK = [1]\n")
        write(sysdir / "app.py", "v = 1\n")
        write(sysdir / "judge_rules.py", "J = 1\n")
        self.ok("init", cwd=sysdir)
        self.ok("seal", "holdout1", "--role", "holdout", "--looks", "10", "--writer", "w", "sim/holdout1_phrasing.py", cwd=sysdir)
        self.commit()
        self.ok("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass", cwd=sysdir)
        self.commit()
        v2 = self.repo / "sys-v2"
        for f in ("sim/holdout1_phrasing.py", "app.py", "seal-ledger.json", "judge_rules.py"):
            write(v2 / f, (sysdir / f).read_text())
        self.commit()
        r = self.seal("run", "holdout1", "--version", "V2", "--", PY, "-c", "pass", cwd=v2)
        self.assertIn("same code", r.stderr)
        write(v2 / "app.py", "v = 2\n")
        self.commit()
        self.ok("run", "holdout1", "--version", "V2", "--", PY, "-c", "pass", cwd=v2)

    def test_seal_ledger_env_relative_path(self):
        (self.repo / "meta").mkdir()
        self.ok("init", env={"SEAL_LEDGER": "meta/ledger.json"})
        self.ok("seal", "holdout1", "--role", "holdout", "--looks", "10", "--writer", "w", "sim/holdout1_phrasing.py",
                env={"SEAL_LEDGER": "meta/ledger.json"})
        led = json.loads((self.repo / "meta" / "ledger.json").read_text())
        self.assertEqual(led["banks"]["holdout1"]["files"][0]["path"], "../sim/holdout1_phrasing.py")
        self.ok("verify", cwd=self.repo / "sim", env={"SEAL_LEDGER": "../meta/ledger.json"})

    # H3
    def test_stale_report_never_scores_a_crashed_run(self):
        self.standard()
        write(self.repo / "report.json", '{"passed": 99}')
        r = self.seal("run", "holdout1", "--version", "V1", "--key", "passed", "--",
                      PY, "-c", "raise SystemExit(3)")
        self.assertEqual(r.returncode, 3)
        rec = self.ledger()["runs"][-1]
        self.assertEqual((rec["status"], rec["score"], rec["exit"]), ("failed", None, 3))
        self.assertIn("failed", self.ok("runs", "--markdown").stdout)
        # the failed run still counts as a run
        self.assertNotEqual(self.seal("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass").returncode, 0)

    def test_missing_or_old_report_gives_no_score(self):
        self.standard()
        r = self.seal("run", "holdout1", "--version", "V1", "--key", "passed", "--", PY, "-c", "pass")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.ledger()["runs"][-1]["status"], "no-score")
        # a report written anywhere but $SEAL_REPORT is not read
        r = self.seal("run", "holdout2", "--version", "V1", "--key", "passed", "--", PY, "-c",
                      "import json; json.dump({'passed': 5}, open('report.json', 'w'))")
        rec = self.ledger()["runs"][-1]
        self.assertEqual((rec["status"], rec["score"]), ("no-score", None))
        self.assertIn("report missing", rec["score_error"])

    def test_good_report_scores(self):
        self.standard()
        self.ok("run", "holdout1", "--version", "V1", "--key", "passed", "--", *report_cmd(42))
        self.assertEqual(self.ledger()["runs"][-1]["score"], 42)

    # H5
    def test_concurrent_runs_keep_every_record(self):
        self.ok("init")
        self.ok("seal", "dev1", "--role", "dev", "--writer", "w", "sim/trainbank_phrasing.py")
        self.commit()
        env = {**os.environ, **GIT_ENV}
        procs = [subprocess.Popen([PY, str(SEAL), "run", "dev1", "--version", f"V{i}", "--",
                                   PY, "-c", "import time; time.sleep(0.2)"],
                                  cwd=self.repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                 for i in range(8)]
        for p in procs:
            out, err = p.communicate()
            self.assertEqual(p.returncode, 0, err)
        runs = self.ledger()["runs"]
        self.assertEqual(sorted(r["version"] for r in runs), sorted(f"V{i}" for i in range(8)))
        self.assertTrue(all(r["finished"] for r in runs))
        self.assertFalse((self.repo / "seal-ledger.json.lock").exists())

    def test_stale_lock_message(self):
        self.ok("init")
        write(self.repo / "seal-ledger.json.lock", "pid 1\n")
        r = self.seal("burn", "x", "--reason", "r", env={"SEAL_LOCK_TIMEOUT": "0.2"})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("stale", r.stderr)

    # H7
    def test_refs_code_only_default_allow_and_globs(self):
        self.standard()
        write(self.repo / "prompts" / "writer.md", "write sim/holdout1_phrasing.py\n")
        write(self.repo / "prompts" / "gen.py", "P = 'holdout1_phrasing'\n")
        write(self.repo / "redteam" / "BRIEF.md", "Do not open sim/holdout1_phrasing.py\n")
        write(self.repo / "Makefile", "holdout-1:\n\tpython3 sim/run.py --bank holdout1_phrasing\n")
        write(self.repo / "docs" / "notes.txt", "holdout2_phrasing\n")
        write(self.repo / "README.md", "holdout2_phrasing\n")
        write(self.repo / "sim" / "run.py", "import importlib\nm = 'holdout1_phrasing'\n")
        self.ok("refs", "--allow", "sim/run.py")
        write(self.repo / "train" / "load.py", "import glob\nB = glob.glob('sim/*_phrasing.py')\n")
        write(self.repo / "train" / "dyn.py", "name = 'x'\np = f'sim/{name}_phrasing.py'\n")
        write(self.repo / "train" / "plain.py", "from sim import holdout2_phrasing\n")
        write(self.repo / "train" / "fine.py", "import glob\nB = glob.glob('**/*.py') + glob.glob('tests/*.py')\n")
        r = self.seal("refs", "--allow", "sim/run.py")
        self.assertEqual(r.returncode, 1)
        self.assertIn("train/load.py: pattern 'sim/*_phrasing.py'", r.stdout)
        self.assertIn("train/dyn.py", r.stdout)
        self.assertIn("train/plain.py: mentions holdout2_phrasing", r.stdout)
        self.assertNotIn("fine.py", r.stdout)
        self.assertNotIn("prompts/", r.stdout)
        self.assertNotIn("Makefile", r.stdout)
        r = self.seal("refs", "--allow", "sim/run.py", "train/", "--no-default-allow", "--ext", ".md", ".py")
        self.assertIn("redteam/BRIEF.md", r.stdout)

    def test_generic_stem_warning(self):
        self.ok("init")
        write(self.repo / "data-holdout9" / "conversations.json", "[]\n")
        write(self.repo / "h" / "bank.py", "x\n")
        r = self.ok("seal", "h9", "--role", "holdout", "--looks", "10", "--writer", "w",
                    "data-holdout9/conversations.json", "h/bank.py")
        self.assertIn("'conversations' is generic", r.stderr)
        self.assertIn("'bank' is generic", r.stderr)
        r = self.ok("seal", "h1", "--role", "holdout", "--looks", "10", "--writer", "w", "sim/holdout1_phrasing.py")
        self.assertNotIn("generic", r.stderr)

    # M1 and burn records
    def test_burned_content_cannot_be_resealed(self):
        self.standard()
        self.ok("burn", "holdout1", "--reason", "first")
        self.ok("burn", "holdout1", "--reason", "second")
        burns = self.ledger()["banks"]["holdout1"]["burns"]
        self.assertEqual([b["reason"] for b in burns], ["first", "second"])
        write(self.repo / "copy" / "fresh_phrasing.py", (self.repo / "sim" / "holdout1_phrasing.py").read_text())
        r = self.seal("seal", "holdout1-fresh", "--role", "holdout", "--looks", "10", "--writer", "w", "copy/fresh_phrasing.py")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("burned bank holdout1", r.stderr)
        r = self.seal("seal", "holdout3", "--role", "holdout", "--looks", "10", "--writer", "w", "sim/holdout2_phrasing.py")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("sealed bank holdout2: sim/holdout2_phrasing.py has the same bytes", r.stderr)
        self.assertIn("burned", self.seal("run", "holdout1", "--version", "V5", "--", PY, "-c", "pass").stderr)
        self.assertIn("BURNED", self.seal("verify").stdout)

    # M6
    def test_output_hidden_and_no_summary_for_holdout(self):
        self.standard()
        r = self.ok("run", "holdout1", "--version", "V1", "--key", "passed", "--", *report_cmd(7))
        self.assertNotIn("FAIL ep 17", r.stdout + r.stderr)
        self.assertIn("score=7", r.stdout)
        self.assertIn("exit=0", r.stdout)
        self.assertIsNone(self.ledger()["runs"][-1]["summary"])
        r = self.seal("run", "holdout2", "--version", "V1", "--show-output", "--", *report_cmd(7))
        self.assertNotEqual(r.returncode, 0)  # C1: never on holdout, confirm or final
        self.assertIn("--show-output on a holdout bank", r.stderr)
        write(self.repo / "sim" / "selbank_phrasing.py", "S = 1\n")
        self.ok("seal", "sel1", "--role", "select", "--writer", "w", "sim/selbank_phrasing.py")
        self.commit()
        r = self.ok("run", "sel1", "--version", "V1", "--show-output", "--", *report_cmd(7))
        self.assertIn("FAIL ep 17", r.stdout)
        self.assertIn("now tainted", r.stderr)
        self.assertTrue(self.ledger()["runs"][-1]["output_shown"])
        self.assertIn("--show-output", self.ledger()["banks"]["sel1"]["probes"][0]["reason"])
        runs = [{k: v for k, v in r.items() if k != "command"} for r in self.ledger()["runs"]]
        self.assertNotIn("FAIL", json.dumps(runs))

    def test_summary_kept_for_dev(self):
        self.ok("init")
        self.ok("seal", "dev1", "--role", "dev", "--writer", "w", "sim/trainbank_phrasing.py")
        self.commit()
        self.ok("run", "dev1", "--version", "V1", "--", PY, "-c", "print('passed 3')")
        self.assertEqual(self.ledger()["runs"][-1]["summary"], "passed 3")

    # M7
    def test_gitattributes_and_posix_paths(self):
        self.standard()
        r = self.ok("gitattributes")
        self.assertIn("/sim/holdout1_phrasing.py -text", r.stdout)
        for b in self.ledger()["banks"].values():
            for f in b["files"]:
                self.assertNotIn("\\", f["path"])

    # final role
    def test_final_bank_runs_once_ever(self):
        self.ok("init")
        write(self.repo / "final" / "final_exam_bank.py", "x = 1\n")
        self.ok("seal", "final1", "--role", "final", "--writer", "w", "final/final_exam_bank.py")
        self.commit()
        self.seal("run", "final1", "--version", "V1", "--", PY, "-c", "raise SystemExit(1)")
        write(self.repo / "app.py", "print('v5')\n")
        self.commit()
        r = self.seal("run", "final1", "--version", "V5", "--force", "--reason", "please", "--", PY, "-c", "pass")
        self.assertIn("--force on a final bank", r.stderr)
        r = self.seal("run", "final1", "--version", "V5", "--", PY, "-c", "pass")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("once ever", r.stderr)
        self.assertEqual(len(self.ledger()["runs"]), 1)

    def test_changed_sealed_file_refused(self):
        self.standard()
        write(self.repo / "sim" / "holdout1_phrasing.py", "BANK = ['changed']\n")
        self.commit()
        r = self.seal("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass")
        self.assertIn("CHANGED", r.stderr)
        self.assertEqual(self.seal("verify").returncode, 1)


    def test_safety_and_confirm_run_once_per_version(self):
        self.ok("init")
        write(self.repo / "sim" / "safety1_phrasing.py", "S = 1\n")
        write(self.repo / "sim" / "confirm1_phrasing.py", "C = 1\n")
        self.ok("seal", "safety1", "--role", "safety", "--writer", "w", "sim/safety1_phrasing.py")
        self.ok("seal", "confirm1", "--role", "confirm", "--writer", "w", "sim/confirm1_phrasing.py")
        self.commit()
        for bank in ("safety1", "confirm1"):
            self.ok("run", bank, "--version", "V1", "--purpose", "gate", "--", PY, "-c", "pass")
            r = self.seal("run", bank, "--version", "V1b", "--", PY, "-c", "pass")
            self.assertIn("once per frozen version", r.stderr)
        self.assertEqual({r["purpose"] for r in self.ledger()["runs"]}, {"gate"})

    def test_retire_keeps_history_and_statement_reads_the_ledger(self):
        self.standard()
        r = self.seal("run", "holdout1", "--version", "V1", "--purpose", "gate", "--", PY, "-c", "pass")
        self.assertIn("never chooses", r.stderr)
        self.ok("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass",
                env={"SEAL_RUNNER": "outside-scorer"})
        self.ok("burn", "holdout1", "--reason", "read failures in V1")
        for to in ("holdout", "validation", "select"):
            self.assertNotEqual(self.seal("retire", "holdout1", "--to", to, "--reason", "x").returncode, 0, to)
        self.ok("retire", "holdout1", "--to", "train", "--reason", "read in V1")
        self.assertEqual(self.ledger()["banks"]["holdout1"]["role"], "train")
        write(self.repo / "app.py", "print('v2')\n")
        self.commit()
        self.ok("run", "holdout1", "--version", "V2", "--purpose", "gate", "--", PY, "-c", "pass")
        self.ok("burn", "holdout1", "--reason", "again, same second as nothing")
        self.assertIn("burned", self.seal("run", "holdout1", "--version", "V3", "--", PY, "-c", "pass").stderr)
        md = self.ok("runs", "--markdown").stdout
        self.assertIn("bank retired to train", md)
        self.assertIn("purpose gate", md)
        st = self.ok("statement", "--markdown").stdout
        row = next(ln for ln in st.splitlines() if ln.startswith("| holdout1 "))
        self.assertIn("holdout until", row)
        self.assertIn("read failures in V1", row)
        self.assertIn("| 1 | outside-scorer@", row)
        self.assertIn("2 (V1, V2)", row)

    def test_no_retire_into_sealed_roles_or_out_of_a_used_final(self):
        self.standard()
        write(self.repo / "sim" / "devbank_phrasing.py", "D = 1\n")
        write(self.repo / "final" / "final_exam_bank.py", "x = 1\n")
        self.ok("seal", "devb", "--role", "dev", "--writer", "builder", "sim/devbank_phrasing.py")
        self.ok("seal", "final1", "--role", "final", "--writer", "w", "final/final_exam_bank.py")
        self.commit()
        for to in ("holdout", "final", "safety", "confirm"):
            self.assertNotEqual(self.seal("retire", "devb", "--to", to, "--reason", "x").returncode, 0, to)
        self.ok("retire", "holdout2", "--to", "validation", "--reason", "retired")
        self.assertNotEqual(self.seal("retire", "holdout2", "--to", "holdout", "--reason", "back").returncode, 0)
        self.ok("run", "final1", "--version", "V5", "--", PY, "-c", "pass")
        self.assertNotEqual(self.seal("retire", "final1", "--to", "validation", "--reason", "x").returncode, 0)

    def test_run_refused_on_a_worktree_copy_of_the_ledger(self):
        self.standard()
        wt = self.repo.parent / "cand1"
        git(self.repo, "worktree", "add", "-q", str(wt))
        try:
            r = self.seal("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass", cwd=wt)
            self.assertIn("linked git worktree", r.stderr)
            self.ok("run", "holdout1", "--version", "V1", "--root", str(wt), "--", PY, "-c", "pass",
                    cwd=wt, env={"SEAL_LEDGER": str(self.repo / "seal-ledger.json")})
            self.assertEqual(len(self.ledger()["runs"]), 1)
        finally:
            git(self.repo, "worktree", "remove", "--force", str(wt))

    # look budget, other systems, probes, manifest, wear
    def test_holdout_needs_a_budget_and_every_run_counts(self):
        self.ok("init")
        r = self.ok("seal", "holdout1", "--role", "holdout", "--writer", "w", "sim/holdout1_phrasing.py")
        self.assertIn("no look budget", r.stderr)
        self.commit()
        r = self.seal("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass")
        self.assertIn("no look budget", r.stderr)
        self.assertEqual(self.ledger()["runs"], [])
        self.ok("budget", "holdout1", "--looks", "2", "--reason", "V1 baseline and the final head")
        self.assertEqual(self.seal("run", "holdout1", "--version", "V1", "--", PY, "-c",
                                   "raise SystemExit(4)").returncode, 4)  # a failed run still counts
        self.assertEqual(self.ledger()["runs"][-1]["status"], "failed")
        write(self.repo / "app.py", "print('v2')\n")
        self.commit()
        # another system on the same commit is not "the same code" as this system's runs
        self.ok("run", "holdout1", "--version", "V5", "--system", "old-run", "--purpose", "compare",
                "--env", "AGENT", "--", PY, "-c", "pass", env={"AGENT": "old"})
        r = self.seal("run", "holdout1", "--version", "V2", "--", PY, "-c", "pass")
        self.assertIn("look budget of holdout1 is spent (2 of 2", r.stderr)
        self.assertIn("--approved-by", self.seal("budget", "holdout1", "--looks", "3", "--reason", "x").stderr)
        self.ok("budget", "holdout1", "--looks", "3", "--reason", "the final head", "--approved-by", "owner")
        self.ok("run", "holdout1", "--version", "V2", "--", PY, "-c", "pass")
        r = self.seal("run", "holdout1", "--version", "V3", "--", PY, "-c", "pass")
        self.assertIn("spent (3 of 3", r.stderr)
        self.assertNotIn("--force", r.stderr)  # no override on a claim bank
        r = self.seal("run", "holdout1", "--version", "V3", "--force", "--reason", "owner agreed", "--", PY, "-c", "pass")
        self.assertIn("refused: --force on a holdout bank", r.stderr)
        md = self.ok("runs", "--markdown").stdout
        self.assertIn("system old-run", md)
        self.assertIn("purpose compare", md)
        st = self.ok("statement", "--markdown").stdout
        row = next(ln for ln in st.splitlines() if ln.startswith("| holdout1 "))
        self.assertIn("3 of 3; budget None -> 2", row)
        self.assertIn("2 -> 3", row)
        self.assertIn("old-run (1)", row)
        self.assertIn("| 2 (V2, old-run:V5) |", row)  # other systems count as versions scored
        self.assertIn("not recorded", row)
        self.assertIn("note: holdout1 (holdout): look budget spent (3 of 3)", st)

    def test_final_budget_is_fixed(self):
        self.ok("init")
        write(self.repo / "final" / "final_exam_bank.py", "x = 1\n")
        self.ok("seal", "final1", "--role", "final", "--writer", "w", "final/final_exam_bank.py")
        self.assertEqual(self.ledger()["banks"]["final1"]["looks"], 1)
        r = self.seal("budget", "final1", "--looks", "2", "--reason", "x")
        self.assertIn("fixed at 1", r.stderr)

    def test_probe_taints_and_burns_by_role(self):
        self.standard()
        for name, role in (("sel1", "select"), ("saf1", "safety"), ("trn1", "train")):
            write(self.repo / "sim" / f"{name}_phrasing.py", f"X = {name!r}\n")
            self.ok("seal", name, "--role", role, "--writer", "w", f"sim/{name}_phrasing.py")
        self.commit()
        self.assertEqual(self.ok("wear").returncode, 0)
        r = self.ok("probe", "sel1", "--items", "3", "--reason", "printed failing ids")
        self.assertIn("tainted", r.stdout)
        self.assertNotIn("BURNED", r.stdout)
        self.ok("run", "sel1", "--version", "V1", "--purpose", "select", "--", PY, "-c", "pass")
        self.assertIn("bank tainted by probe", self.ok("runs").stdout)
        self.assertNotEqual(self.seal("probe", "trn1", "--items", "1", "--reason", "x").returncode, 0)
        self.ok("probe", "saf1", "--items", "1", "--reason", "which signals fired on one item")
        r = self.seal("wear")
        self.assertEqual(r.returncode, 1)
        self.assertIn("saf1 (safety): tainted", r.stdout)
        r = self.ok("probe", "holdout1", "--items", "1", "--reason", "looked at one score")
        self.assertIn("BURNED", r.stdout)
        r = self.seal("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass")
        self.assertIn("burned", r.stderr)
        self.assertIn("retire it to train", r.stderr)
        self.assertIn("burned but still in a sealed role", self.seal("wear").stdout)
        st = self.ok("statement", "--markdown").stdout
        self.assertIn("TAINTED: 1 probe(s)", next(ln for ln in st.splitlines() if ln.startswith("| sel1 ")))

    def test_manifest_statement_and_wear_thresholds(self):
        self.ok("init")
        write(self.repo / "m.json", json.dumps({"episodes": 1000, "phrasings": {"yes": 6, "close": 14},
                                                "source": "synthetic", "writer_setup": "formal",
                                                "evaluator": ["judge_rules.py"]}))
        write(self.repo / "bad.json", json.dumps({"source": "made up"}))
        write(self.repo / "sim" / "confirm1_phrasing.py", "C = 1\n")
        r = self.seal("seal", "c1", "--role", "confirm", "--writer", "w", "--manifest", "bad.json",
                      "sim/confirm1_phrasing.py")
        self.assertIn("source must be one of", r.stderr)
        self.ok("seal", "c1", "--role", "confirm", "--writer", "w", "--manifest", "m.json",
                "--expires", "2026-12-31", "sim/confirm1_phrasing.py")
        self.commit()
        st = self.ok("statement", "--markdown").stdout
        row = next(ln for ln in st.splitlines() if ln.startswith("| c1 "))
        self.assertIn("| 1000 | 20 over 2 keys (min 6) | synthetic |", row)
        self.assertEqual(self.ok("wear", "--today", "2026-10-01").returncode, 0)
        self.assertIn("expired", self.seal("wear", "--today", "2027-01-02").stdout)
        self.assertEqual(self.seal("wear", "--today", "2027-01-02").returncode, 1)
        self.ok("run", "c1", "--version", "V1", "--purpose", "confirm", "--", PY, "-c", "pass")
        self.assertEqual(self.ok("wear", "--today", "2026-10-01").returncode, 0)  # M6: base run is fine
        write(self.repo / "app.py", "print('v2')\n")
        self.commit()
        self.ok("run", "c1", "--version", "V2", "--", PY, "-c", "pass")  # head; purpose left at score
        r = self.seal("wear", "--today", "2026-10-01")
        self.assertEqual(r.returncode, 1)  # at the threshold the bank is worn: a breach
        self.assertIn("worn: 2 runs, threshold 2", r.stdout)
        self.ok("retire", "c1", "--to", "select", "--reason", "confirmed round 1")
        self.assertEqual(self.ok("wear", "--today", "2026-10-01").returncode, 0)
        # a bank with runs keeps its manifest and expiry
        r = self.seal("manifest", "c1", "m.json", "--expires", "2027-06-30")
        self.assertIn("frozen", r.stderr)
        self.assertEqual(self.ledger()["banks"]["c1"]["expires"], "2026-12-31")

    # adversarial review repros
    def test_h1_env_selected_agent_and_renamed_system(self):
        self.ok("init")
        self.ok("seal", "hold_alpha", "--role", "holdout", "--looks", "4", "--writer", "w",
                "sim/holdout1_phrasing.py")
        write(self.repo / "agent.sh", 'if [ "$AGENT" = v5 ]; then echo 9; else echo 8; fi\n')
        self.commit()
        self.ok("run", "hold_alpha", "--version", "V8", "--", "sh", "agent.sh")
        # the same agent re-scored under another --system name: still the same version
        r = self.seal("run", "hold_alpha", "--version", "V8", "--system", "V8-retry", "--", "sh", "agent.sh")
        self.assertIn("same commit, command and environment", r.stderr)
        # another agent selected by an environment variable: told apart only with --env
        r = self.seal("run", "hold_alpha", "--version", "V5", "--system", "old", "--", "sh", "agent.sh",
                      env={"AGENT": "v5"})
        self.assertIn("--env NAME", r.stderr)
        self.ok("run", "hold_alpha", "--version", "V5", "--system", "old", "--env", "AGENT", "--",
                "sh", "agent.sh", env={"AGENT": "v5"})
        self.assertEqual(self.ledger()["runs"][-1]["env"], {"AGENT": "v5"})

    def test_h2_confirm_budget_and_safety_wear_count_every_run(self):
        self.ok("init")
        write(self.repo / "sim" / "conf_one_phr.py", "C = 1\n")
        write(self.repo / "sim" / "safe_otter_phr.py", "S = 1\n")
        self.ok("seal", "conf_one", "--role", "confirm", "--writer", "w", "sim/conf_one_phr.py")
        self.ok("seal", "safe_otter", "--role", "safety", "--writer", "w", "sim/safe_otter_phr.py")
        self.commit()
        for i in range(13):
            write(self.repo / "app.py", f"print({i})\n")
            self.commit()
            rs = self.seal("run", "safe_otter", "--version", f"V{i}", "--", PY, "-c", "pass")
            self.assertEqual(rs.returncode != 0, i >= 12, rs.stderr)  # default safety budget 12
            r = self.seal("run", "conf_one", "--version", f"V{i}", "--", PY, "-c", "pass")
            self.assertEqual(r.returncode != 0, i >= 2, r.stderr)
        self.assertIn("worn (2 runs, the confirm ceiling is 2)", r.stderr)
        self.assertIn("worn (12 runs, the safety ceiling is 12)", rs.stderr)
        r = self.seal("wear")
        self.assertEqual(r.returncode, 1)
        self.assertIn("safe_otter (safety): worn: 12 runs, threshold 12", r.stdout)

    def test_h3_readable_content_cannot_become_a_holdout(self):
        self.ok("init")
        write(self.repo / "sim" / "train_wren_phr.py", "".join(f"P{i} = 'phrase number {i}'\n" for i in range(10)))
        self.ok("seal", "train_wren", "--role", "train", "--writer", "w", "sim/train_wren_phr.py")
        text = (self.repo / "sim" / "train_wren_phr.py").read_text()
        write(self.repo / "h" / "hold_new_phr.py", text)
        write(self.repo / "h" / "hold_ws_phr.py", text.replace(" = ", "  =  ") + "\n\n")
        write(self.repo / "h" / "hold_mix_phr.py", text + "EXTRA = 'one new line'\n")
        for f in ("hold_new_phr.py", "hold_ws_phr.py", "hold_mix_phr.py"):
            r = self.seal("seal", f[:-3], "--role", "holdout", "--looks", "2", "--writer", "w", f"h/{f}")
            self.assertNotEqual(r.returncode, 0, f)
            self.assertIn("readable bank train_wren", r.stderr)
        # a copy of a sealed bank is refused too: it would get a fresh look budget
        write(self.repo / "h" / "hold_a_phr.py", "A = 'fresh text'\n")
        write(self.repo / "h" / "hold_b_phr.py", "A = 'fresh text'\n")
        self.ok("seal", "hold_a", "--role", "holdout", "--looks", "2", "--writer", "w", "h/hold_a_phr.py")
        r = self.seal("seal", "hold_b", "--role", "holdout", "--looks", "2", "--writer", "w", "h/hold_b_phr.py")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("sealed bank hold_a", r.stderr)

    def test_h4_rewound_side_and_edited_ledgers_are_caught(self):
        mirror = Path(self._tmp.name).parent / f"mirror-{os.getpid()}-{id(self)}.jsonl"
        self.addCleanup(lambda: mirror.unlink(missing_ok=True))
        env = {"SEAL_MIRROR": str(mirror)}
        self.ok("init", env=env)
        self.ok("seal", "holdout1", "--role", "holdout", "--looks", "3", "--writer", "w",
                "sim/holdout1_phrasing.py", env=env)
        self.commit("sealed")
        self.ok("verify", env=env)
        self.ok("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass", env=env)
        self.commit("after run")
        git(self.repo, "checkout", "-q", "HEAD~1", "--", "seal-ledger.json")  # rewind
        r = self.seal("verify", env=env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("ledger rewound", r.stderr)
        self.assertIn("ledger rewound", self.seal("run", "holdout1", "--version", "V1", "--", PY, "-c",
                                                  "pass", "--allow-dirty", env=env).stderr)
        git(self.repo, "checkout", "-q", "HEAD", "--", "seal-ledger.json")
        self.ok("verify", env=env)
        led = self.ledger()
        led["runs"][0]["score"] = 999  # hand edit
        write(self.repo / "seal-ledger.json", json.dumps(led))
        self.assertIn("changed outside seal.py", self.seal("verify", env=env).stderr)
        self.ok("--ledger", "side-ledger.json", "init", env=env)
        self.assertIn("other ledger", self.seal("--ledger", "side-ledger.json", "verify", env=env).stderr)
        # without a mirror only a note is printed
        git(self.repo, "checkout", "-q", "HEAD", "--", "seal-ledger.json")
        self.assertIn("no $SEAL_MIRROR", self.ok("verify", env={"SEAL_MIRROR": None}).stdout)


    # second review (Codex) repros
    def test_c1_hand_edit_is_not_laundered_by_a_normal_command(self):
        self.standard()
        self.ok("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass")
        led = self.ledger()
        led["runs"][0]["score"] = 999  # hand edit
        write(self.repo / "seal-ledger.json", json.dumps(led))
        for cmd in (("budget", "holdout1", "--looks", "3", "--reason", "x"),
                    ("burn", "holdout2", "--reason", "x"),
                    ("seal", "dev_x", "--role", "dev", "--writer", "w", "app.py"),
                    ("run", "holdout2", "--version", "V1", "--allow-dirty", "--", PY, "-c", "pass")):
            r = self.seal(*cmd)
            self.assertNotEqual(r.returncode, 0, cmd)
            self.assertIn("ledger check failed", r.stderr)
        self.assertEqual(self.seal("verify").returncode, 1)

    def test_c2_padded_reformatted_or_copied_banks_are_refused(self):
        self.ok("init")
        rows = [{"user": f"please close ticket number {i} today", "id": i} for i in range(10)]
        write(self.repo / "tr" / "train_kite.json", json.dumps(rows, indent=2))
        self.ok("seal", "train_kite", "--role", "train", "--writer", "w", "tr/train_kite.json")
        # one-line JSON, and the same records padded with three new ones
        write(self.repo / "h" / "hold_one_line.json", json.dumps(rows))
        pad = rows + [{"user": f"a brand new request number {i}"} for i in range(3)]
        write(self.repo / "h" / "hold_padded.json", json.dumps(pad, indent=1))
        for f in ("hold_one_line.json", "hold_padded.json"):
            r = self.seal("seal", f[:-5], "--role", "holdout", "--looks", "2", "--writer", "w", f"h/{f}")
            self.assertNotEqual(r.returncode, 0, f)
            self.assertIn("readable bank train_kite", r.stderr)
        # a sealed bank copied under a new name would get a fresh budget
        write(self.repo / "h" / "hold_orig.json", json.dumps([f"fresh holdout phrase {i}" for i in range(9)]))
        self.ok("seal", "hold_orig", "--role", "holdout", "--looks", "2", "--writer", "w", "h/hold_orig.json")
        write(self.repo / "h" / "hold_copy.json", json.dumps([f"fresh holdout phrase {i}" for i in range(9)], indent=4))
        r = self.seal("seal", "hold_copy", "--role", "select", "--writer", "w", "h/hold_copy.json")
        self.assertIn("sealed bank hold_orig", r.stderr)
        self.assertNotIn("hold_copy", self.ledger()["banks"])

    def test_c3_readable_banks_never_become_sealed_and_looks_survive_retire(self):
        self.standard()
        self.ok("seal", "trn1", "--role", "train", "--writer", "w", "sim/trainbank_phrasing.py")
        for to in ("select", "tune", "validation"):
            r = self.seal("retire", "trn1", "--to", to, "--reason", "x")
            self.assertIn("never becomes a sealed", r.stderr, to)
        self.commit()
        self.ok("budget", "holdout1", "--looks", "1", "--reason", "one look")
        self.ok("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass")
        self.ok("retire", "holdout1", "--to", "validation", "--reason", "used")
        self.ok("budget", "holdout1", "--looks", "1", "--reason", "x")
        r = self.seal("run", "holdout1", "--version", "V2", "--", PY, "-c", "pass")
        self.assertIn("spent (1 of 1", r.stderr)  # the holdout run still counts

    def test_h4_report_score_must_be_a_count(self):
        self.ok("init")
        write(self.repo / "m.json", json.dumps({"episodes": 50, "evaluator": ["judge_rules.py"]}))
        self.ok("seal", "holdout1", "--role", "holdout", "--looks", "9", "--writer", "w",
                "--manifest", "m.json", "sim/holdout1_phrasing.py")
        self.commit()
        for i, val in enumerate(("['ep 3 text', 'ep 9']", "True", "-1", "51", "2.5", "'40'")):
            write(self.repo / "app.py", f"print({i})\n")
            self.commit()
            code = f"import json, os; json.dump({{'passed': {val}}}, open(os.environ['SEAL_REPORT'], 'w'))"
            r = self.seal("run", "holdout1", "--version", f"V{i}", "--key", "passed", "--", PY, "-c", code)
            self.assertEqual(r.returncode, 1, val)
            rec = self.ledger()["runs"][-1]
            self.assertEqual((rec["status"], rec["score"]), ("no-score", None), val)
        runs = [{k: v for k, v in r.items() if k != "command"} for r in self.ledger()["runs"]]
        self.assertNotIn("ep 3 text", json.dumps(runs))

    def test_h5_no_force_on_claim_banks_and_safety_fails_closed(self):
        self.ok("init")
        write(self.repo / "sim" / "safe_lynx_phr.py", "S = 1\n")
        write(self.repo / "sim" / "safe_mole_phr.py", "S = 2\n")
        self.ok("seal", "safe_lynx", "--role", "safety", "--writer", "w", "sim/safe_lynx_phr.py")
        self.ok("seal", "safe_mole", "--role", "safety", "--writer", "w", "--expires", "2020-01-01",
                "sim/safe_mole_phr.py")
        self.commit()
        self.assertEqual(self.ledger()["banks"]["safe_lynx"]["looks"], None)
        self.ok("run", "safe_lynx", "--version", "V1", "--", PY, "-c", "pass")
        r = self.seal("run", "safe_lynx", "--version", "V1", "--force", "--reason", "x", "--", PY, "-c", "pass")
        self.assertIn("--force on a safety bank", r.stderr)
        self.assertIn("expired", self.seal("run", "safe_mole", "--version", "V1", "--", PY, "-c", "pass").stderr)
        self.ok("probe", "safe_lynx", "--items", "1", "--reason", "x")
        write(self.repo / "app.py", "print(2)\n")
        self.commit()
        r = self.seal("run", "safe_lynx", "--version", "V2", "--", PY, "-c", "pass")
        self.assertIn("probed safety bank", r.stderr)
        self.assertEqual(len(self.ledger()["runs"]), 1)

    def test_h6_report_path_is_runner_owned(self):
        self.standard()
        r = self.seal("run", "holdout1", "--version", "V1", "--report", "sim/holdout2_phrasing.py",
                      "--", PY, "-c", "pass")
        self.assertIn("--report is gone", r.stderr)
        self.assertTrue((self.repo / "sim" / "holdout2_phrasing.py").is_file())
        self.ok("run", "holdout1", "--version", "V1", "--key", "passed", "--", *report_cmd(5))
        rec = self.ledger()["runs"][-1]
        self.assertEqual(rec["score"], 5)
        self.assertEqual(len(rec["report_sha256"]), 64)
        self.assertFalse((self.ext / "runs" / rec["id"] / "report.json").exists())  # score kept only
        r = self.seal("run", "holdout2", "--version", "V1", "--output", "sim/holdout1_phrasing.py",
                      "--", PY, "-c", "pass")
        self.assertIn("plain file name", r.stderr)

    def test_m20_manifest_counts_are_whole_numbers(self):
        self.standard()
        for bad in ({"episodes": True}, {"episodes": -3}, {"phrasings": {"a": "x"}},
                    {"segments": {"writes": -1}}, {"phrasings": "12"}):
            write(self.repo / "bad.json", json.dumps(bad))
            r = self.seal("manifest", "holdout1", "bad.json")
            self.assertEqual(r.returncode, 1, bad)
        self.ok("statement")

    def test_m16_require_mirror(self):
        mirror = Path(self._tmp.name).parent / f"mirror-req-{os.getpid()}-{id(self)}.jsonl"
        self.addCleanup(lambda: mirror.unlink(missing_ok=True))
        no = {"SEAL_MIRROR": None}
        self.ok("init", env=no)
        r = self.seal("verify", "--require-mirror", env=no)
        self.assertIn("$SEAL_MIRROR is not set", r.stderr)
        inside = {"SEAL_MIRROR": str(self.repo / "m.jsonl")}
        self.assertIn("inside", self.seal("require-mirror", env=inside).stderr)
        env = {"SEAL_MIRROR": str(mirror)}
        self.ok("mirror", env=env)
        self.ok("require-mirror", env=env)
        r = self.seal("seal", "holdout1", "--role", "holdout", "--looks", "2", "--writer", "w",
                      "sim/holdout1_phrasing.py", env=no)
        self.assertIn("requires a mirror", r.stderr)
        self.ok("seal", "holdout1", "--role", "holdout", "--looks", "2", "--writer", "w",
                "sim/holdout1_phrasing.py", env=env)
        self.ok("verify", "--require-mirror", env=env)

    def test_m18_evaluator_fingerprint(self):
        self.standard()
        write(self.repo / "judge_rules.py", "STRICT = True\n")
        self.commit()
        self.ok("run", "holdout1", "--version", "V1", "--fingerprint", "judge_rules.py", "--", PY, "-c", "pass")
        self.assertIn("judge_rules.py", self.ledger()["runs"][-1]["fingerprint"])
        write(self.repo / "judge_rules.py", "STRICT = False\n")
        write(self.repo / "app.py", "print('v2')\n")
        self.commit()
        self.ok("run", "holdout1", "--version", "V2", "--fingerprint", "judge_rules.py", "--", PY, "-c", "pass")
        row = next(ln for ln in self.ok("statement", "--markdown").stdout.splitlines()
                   if ln.startswith("| holdout1 "))
        self.assertIn("Rescore the base", row)


    # third review (Codex re-check) repros
    def test_r1_removed_chain_is_refused_until_an_approved_migration(self):
        self.standard()
        self.ok("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass")
        led = self.ledger()
        led["runs"][0]["score"] = 999
        del led["chain"]  # edit, then drop the chain so nothing can be checked
        write(self.repo / "seal-ledger.json", json.dumps(led))
        r = self.seal("budget", "holdout1", "--looks", "3", "--reason", "x")
        self.assertIn("no hash chain", r.stderr)
        self.assertEqual(self.seal("verify").returncode, 1)
        nomirror = {"SEAL_MIRROR": None}
        self.ok("migrate", "--approved-by", "owner", "--reason", "older seal.py", env=nomirror)
        self.assertIn("taken on trust", self.ok("statement", env=nomirror).stdout)

    def test_r2_any_shared_record_with_a_sealed_bank_is_refused(self):
        self.ok("init")
        recs = [f"close ticket {i}" for i in range(10)]
        write(self.repo / "h" / "hold_orig.json", json.dumps(recs))
        self.ok("seal", "hold_orig", "--role", "holdout", "--looks", "2", "--writer", "w", "h/hold_orig.json")
        # 10 copied records padded with 41 new ones (under 20%), split over two files
        write(self.repo / "h" / "hold_p1.json", json.dumps(recs[:5] + [f"new text {i}" for i in range(20)]))
        write(self.repo / "h" / "hold_p2.json", json.dumps(recs[5:] + [f"other text {i}" for i in range(21)]))
        r = self.seal("seal", "hold_pad", "--role", "holdout", "--looks", "2", "--writer", "w",
                      "h/hold_p1.json", "h/hold_p2.json")
        self.assertIn("sealed bank hold_orig: 10 shared record(s)", r.stderr)
        # a short record (under 12 characters) counts too
        write(self.repo / "h" / "hold_short.json", json.dumps(["yes", "brand new phrase"]))
        write(self.repo / "h" / "hold_s2.json", json.dumps(["YES!", "another new phrase"]))
        self.ok("seal", "hold_short", "--role", "select", "--writer", "w", "h/hold_short.json")
        r = self.seal("seal", "hold_s2", "--role", "select", "--writer", "w", "h/hold_s2.json")
        self.assertIn("sealed bank hold_short: 1 shared record(s)", r.stderr)
        self.assertNotIn("yes", r.stderr.replace("hold_s", ""))  # sealed text is never quoted
        # records every bank shares by design go in the common list
        write(self.repo / "schema.json", json.dumps({"answers": ["yes"]}))
        self.ok("common", "schema.json", "--reason", "answer labels from the schema")
        self.ok("seal", "hold_s2", "--role", "select", "--writer", "w", "h/hold_s2.json")

    def test_r4_scores_need_a_bound(self):
        self.ok("init")
        self.ok("seal", "hnoman", "--role", "holdout", "--looks", "2", "--writer", "w",
                "sim/holdout1_phrasing.py", raw=True)
        self.ok("seal", "devb", "--role", "dev", "--writer", "w", "sim/trainbank_phrasing.py")
        self.commit()
        r = self.seal("run", "hnoman", "--version", "V1", "--key", "passed", "--", *report_cmd(10 ** 1000))
        self.assertIn("needs a manifest with episodes", r.stderr)
        r = self.seal("run", "devb", "--version", "V1", "--key", "passed", "--", *report_cmd(5))
        self.assertIn("--key needs the manifest's episode count", r.stderr)
        self.assertEqual(self.ledger()["runs"], [])

    def test_r5_wear_is_a_ceiling_no_budget_raises(self):
        self.ok("init")
        write(self.repo / "sim" / "safe_ibex_phr.py", "S = 3\n")
        r = self.seal("seal", "safe_ibex", "--role", "safety", "--looks", "13", "--writer", "w",
                      "sim/safe_ibex_phr.py")
        self.assertIn("ceiling", r.stderr)
        self.ok("seal", "safe_ibex", "--role", "safety", "--writer", "w", "sim/safe_ibex_phr.py")
        r = self.seal("budget", "safe_ibex", "--looks", "30", "--reason", "x", "--approved-by", "anyone")
        self.assertIn("ceiling", r.stderr)

    def test_r6_r16_sealed_runs_need_runner_owned_mirror_and_run_dir(self):
        self.standard()
        for env, why in (({"SEAL_MIRROR": None}, "$SEAL_MIRROR is not set"),
                         ({"SEAL_RUN_DIR": None}, "$SEAL_RUN_DIR is not set"),
                         ({"SEAL_RUN_DIR": str(self.repo / "runs")}, "inside")):
            r = self.seal("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass", env=env)
            self.assertIn("needs $SEAL_MIRROR and $SEAL_RUN_DIR", r.stderr, env)
            self.assertIn(why, r.stderr, env)
        self.assertEqual(self.ledger()["runs"], [])
        code = ("import json, os; json.dump({'passed': 3, 'failing': 'ep 4: deleted the wrong rows'}, "
                "open(os.environ['SEAL_REPORT'], 'w'))")
        r = self.seal("run", "holdout1", "--version", "V1", "--key", "passed", "--", PY, "-c", code)
        self.assertEqual(r.returncode, 1)
        rec = self.ledger()["runs"][-1]
        self.assertEqual((rec["status"], rec["score"]), ("no-score", None))
        self.assertIn("outside the allowed set", rec["score_error"])
        self.assertNotIn("failing", rec["score_error"])  # a report's own keys are never quoted
        self.assertEqual(list((self.ext / "runs" / rec["id"]).glob("*.json")), [])  # raw report deleted

    def test_r18_sealed_runs_hash_exactly_the_manifest_evaluator(self):
        self.standard()
        write(self.repo / "sim_world.py", "W = 1\n")
        self.commit()
        r = self.seal("run", "holdout1", "--version", "V1", "--", PY, "-c", "pass", raw=True)
        self.assertIn("--fingerprint must hash exactly", r.stderr)
        r = self.seal("run", "holdout1", "--version", "V1", "--fingerprint", "judge_rules.py", "sim_world.py",
                      "--", PY, "-c", "pass", raw=True)
        self.assertIn("--fingerprint must hash exactly", r.stderr)
        self.assertEqual(self.ledger()["runs"], [])

    def test_ra_command_that_changes_the_bank_burns_it(self):
        self.standard()
        code = ("import os; p = 'sim/holdout1_phrasing.py'; os.chmod(p, 0o644); "
                "open(p, 'a').write('# edited\\n')")
        r = self.seal("run", "holdout1", "--version", "V1", "--", PY, "-c", code)
        self.assertEqual(r.returncode, 1)
        rec = self.ledger()["runs"][-1]
        self.assertEqual((rec["status"], rec["score"]), ("tampered", None))
        self.assertTrue(self.ledger()["banks"]["holdout1"]["burns"])
        self.assertIn("BURNED", r.stderr)

    def test_rb_outputs_come_from_a_fresh_runner_folder(self):
        self.standard()
        write(self.repo / "maps.json", '{"e1": true}')  # an old map lying in the tree
        self.commit()
        r = self.seal("run", "holdout1", "--version", "V1", "--output", "maps.json", "--", PY, "-c", "pass")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not written to $SEAL_OUTPUT_DIR", self.ledger()["runs"][-1]["score_error"])
        write(self.repo / "app.py", "print(2)\n")
        self.commit()
        code = ("import os; open(os.path.join(os.environ['SEAL_OUTPUT_DIR'], 'maps.json'), 'w')"
                ".write('{\"e1\": false}')")
        self.ok("run", "holdout1", "--version", "V2", "--output", "maps.json", "--", PY, "-c", code)
        self.assertEqual(len(self.ledger()["runs"][-1]["outputs"]["maps.json"]), 64)


    # final check (Codex) repros
    def test_f2_numeric_records_are_compared_whole(self):
        self.ok("init")
        rows = [{"size": 30 + i, "errors": i % 10, "retry": i % 3 == 0} for i in range(20)]
        write(self.repo / "h" / "hold_nums.json", json.dumps(rows))
        self.ok("seal", "hold_nums", "--role", "holdout", "--looks", "2", "--writer", "w", "h/hold_nums.json")
        shuffled = [dict(reversed(list(r.items()))) for r in reversed(rows)] + [{"size": 99, "errors": 1}]
        write(self.repo / "h" / "hold_nums2.json", json.dumps(shuffled, indent=1))
        r = self.seal("seal", "hold_nums2", "--role", "select", "--writer", "w", "h/hold_nums2.json")
        self.assertIn("sealed bank hold_nums:", r.stderr)
        self.assertNotIn("hold_nums2", self.ledger()["banks"])

    def test_fn2_evaluator_changed_during_the_run_gives_no_score(self):
        self.standard()
        code = "open('judge_rules.py', 'w').write('STRICT = False\\n')"
        r = self.seal("run", "holdout1", "--version", "V1", "--", PY, "-c", code)
        self.assertEqual(r.returncode, 1)
        rec = self.ledger()["runs"][-1]
        self.assertEqual((rec["status"], rec["score"]), ("tampered", None))
        self.assertIn("evaluator files changed during the run", rec["score_error"])


class NoiseCase(unittest.TestCase):
    def noise(self, *args: str) -> subprocess.CompletedProcess:
        return run(NOISE, *args, cwd=HERE)

    def test_fisher_small_n(self):
        for args, p in ((("10", "0", "3"), "0.211"), (("20", "0", "4"), "0.106")):
            r = self.noise(*args)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(f"Fisher exact p = {p}", r.stdout)
            self.assertIn("inside the noise", r.stdout)
        self.assertIn("reliable", self.noise("100", "50", "70").stdout.splitlines()[-1])

    def test_large_n_uses_z_test(self):
        r = self.noise("1000", "900", "940")
        self.assertIn("z test", r.stdout)
        self.assertIn(": reliable", r.stdout)

    def test_wilson_not_zero_at_edges(self):
        r = self.noise("10", "0")
        self.assertIn("0.0% to 27.8%", r.stdout)
        self.assertIn("±17", self.noise("1000", "917").stdout)

    def test_clusters_widen_margin(self):
        plain = self.noise("1000", "900", "940").stdout
        clustered = self.noise("1000", "900", "940", "--clusters", "100").stdout
        self.assertIn(": reliable", plain)
        self.assertIn("inside the noise", clustered)
        self.assertIn("rough upper bound", clustered)
        self.assertIn("±59", clustered)

    def test_paired(self):
        r = self.noise("--paired", "3", "12")
        self.assertIn("exact binomial", r.stdout)
        self.assertIn("p = 0.035", r.stdout)
        self.assertIn("chi-square", self.noise("--paired", "30", "60").stdout)
        self.assertIn("identical", self.noise("--paired", "0", "0").stdout)

    def test_family_holm_and_need(self):
        with tempfile.TemporaryDirectory() as d:
            ids = [f"e{i}" for i in range(200)]
            def put(name, k, extra=()):
                write(Path(d) / name, json.dumps({e: (n < k or e in extra) for n, e in enumerate(ids)}))
            put("base.json", 150)
            put("big.json", 175)
            put("small.json", 152, ("e199",))
            put("worse.json", 140)
            r = run(NOISE, "--family", "base.json", "big.json", "small.json", "worse.json", cwd=Path(d))
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = r.stdout.splitlines()
            self.assertIn(": reliable", lines[0])
            self.assertIn("inside the noise", lines[1])
            self.assertIn("reliably worse", lines[2])
            self.assertIn("biased upward", lines[3])
            write(Path(d) / "list.json", json.dumps(["e1"]))
            write(Path(d) / "ints.json", json.dumps({e: 1 for e in ids}))
            write(Path(d) / "other.json", json.dumps({f"x{i}": True for i in range(200)}))
            for bad in ("list.json", "ints.json", "other.json"):
                self.assertEqual(run(NOISE, "--family", "base.json", bad, cwd=Path(d)).returncode, 2, bad)
        self.assertIn("299 episodes", self.noise("--need", "0.01").stdout)
        self.assertIn("below 7.2%", self.noise("--need", "0.01").stdout)
        r = self.noise("--paired", "3", "12", "--of", "4")
        self.assertIn("inside the noise", r.stdout)
        self.assertIn("1 of 4", r.stdout)
        for args in (("--need", "2"), ("--need",), ("10", "5", "--of", "3"), ("--family", "x.json")):
            self.assertEqual(self.noise(*args).returncode, 2, args)

    def test_bad_input_is_a_usage_error(self):
        for args in (("0", "0"), ("5", "6"), ("1000",), ("--paired", "1"), ("-3", "2"), ("10", "-1"),
                     ("--paired", "-1", "2"), ("x", "1"), ("10", "1.5"), ("10", "5", "--clusters", "0"),
                     ("10", "5", "--clusters", "11"), ("--paired", "1", "2", "--clusters", "0")):
            r = self.noise(*args)
            self.assertEqual(r.returncode, 2, args)
            self.assertIn("usage:", r.stderr, args)
            self.assertNotIn("Traceback", r.stderr, args)


class NoiseMapsCase(unittest.TestCase):
    """Cluster-aware tests on pass maps."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def put(self, name: str, data) -> str:
        write(self.d / name, json.dumps(data))
        return name

    def noise(self, *args: str) -> subprocess.CompletedProcess:
        return run(NOISE, *args, cwd=self.d, env={"SEAL_MIRROR": str(self.d.parent / self.mirror)})

    @property
    def mirror(self) -> str:
        return f"{self.d.name}-mirror.jsonl"

    def cycles(self, *ks: int) -> list[str]:
        """A mirrored ledger in self.d with one opened cycle per K; args for the last one."""
        self.addCleanup(lambda: (self.d.parent / self.mirror).unlink(missing_ok=True))
        git(self.d, "init", "-q")
        env = {"SEAL_MIRROR": str(self.d.parent / self.mirror)}
        assert run(SEAL, "init", cwd=self.d, env=env).returncode == 0
        for k in ks:
            r = run(SEAL, "cycle", "open", "--of", str(k), "--reason", "t", cwd=self.d, env=env)
            assert r.returncode == 0, r.stderr
        return ["--ledger", "seal-ledger.json", "--cycle", str(len(ks))]

    def ids(self, n: int = 400) -> list[str]:
        return [f"e{i}" for i in range(n)]

    def test_one_phrasing_flipping_many_episodes_is_not_reliable(self):
        ids = self.ids()
        base = {e: i % 2 == 0 for i, e in enumerate(ids)}
        cand = dict(base)
        clusters = {}
        for i, e in enumerate(ids):
            clusters[e] = "yes_01" if i < 160 else f"p{i % 50}"
            if i < 160 and i % 2:
                cand[e] = True  # 80 episodes, all from one phrasing
        self.put("b.json", base), self.put("c.json", cand), self.put("cl.json", clusters)
        plain = self.noise("--paired-maps", "b.json", "c.json")
        self.assertIn("reliable gain", plain.stdout)
        self.assertIn("note: no --clusters", plain.stdout)
        r = self.noise("--paired-maps", "b.json", "c.json", "--clusters", "cl.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("B 0 vs C 80", r.stdout)
        self.assertIn("p = 1.000", r.stdout)
        self.assertIn("inside the noise", r.stdout)

    def test_eight_phrasings_one_episode_each_is_reliable(self):
        ids = self.ids(200)
        base = {e: i >= 8 for i, e in enumerate(ids)}
        cand = {e: True for e in ids}
        clusters = {e: f"p{i}" if i < 8 else f"q{i % 20}" for i, e in enumerate(ids)}
        self.put("b.json", base), self.put("c.json", cand), self.put("cl.json", clusters)
        r = self.noise("--paired-maps", "b.json", "c.json", "--clusters", "cl.json")
        self.assertIn("p = 0.008", r.stdout)
        self.assertIn("reliable gain", r.stdout)
        # deterministic: same output twice
        self.assertEqual(r.stdout, self.noise("--paired-maps", "b.json", "c.json", "--clusters", "cl.json").stdout)

    def test_not_worse(self):
        ids = self.ids(2000)
        base = {e: i % 3 != 0 for i, e in enumerate(ids)}
        clusters = {e: f"p{i % 100}" for i, e in enumerate(ids)}  # 100 phrasings x 20

        def swapped(k: int) -> dict:
            out = dict(base)
            for e in [e for e in ids if base[e]][:k] + [e for e in ids if not base[e]][:k]:
                out[e] = not base[e]  # k lost, k gained: net zero
            return out
        worse = {e: (base[e] if i >= 120 else False) for i, e in enumerate(ids)}
        self.put("b.json", base), self.put("s.json", swapped(4)), self.put("w.json", worse)
        self.put("churn.json", swapped(100)), self.put("cl.json", clusters)
        nw = ("--paired-maps", "b.json")
        r = self.noise(*nw, "s.json", "--clusters", "cl.json", "--not-worse", "1%")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("net +0", r.stdout)
        self.assertIn("PASS", r.stdout)
        r = self.noise(*nw, "w.json", "--clusters", "cl.json", "--not-worse", "1%")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL", r.stdout)
        self.assertIn("reliably worse", r.stdout)
        # net zero with heavy churn cannot show "not worse" at a tight margin
        self.assertEqual(self.noise(*nw, "churn.json", "--clusters", "cl.json", "--not-worse", "10").returncode, 1)
        # identical maps pass at margin 0 (H6)
        r = self.noise(*nw, "b.json", "--clusters", "cl.json", "--not-worse", "0")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("no episode moved", r.stdout)
        # H6: no margin cliff, no fractions without %, a cap, and clusters required
        for bad in (("--not-worse", "0.01"), ("--not-worse", "0.99"), ("--not-worse", "-3"),
                    ("--not-worse", "5%"), ("--not-worse", "100")):
            r = self.noise(*nw, "s.json", "--clusters", "cl.json", *bad)
            self.assertEqual(r.returncode, 2, bad)
        self.assertEqual(self.noise(*nw, "s.json", "--clusters", "cl.json", "--not-worse", "5%",
                                    "--wide-margin").returncode, 0)
        r = self.noise(*nw, "s.json", "--not-worse", "1%")
        self.assertEqual(r.returncode, 2)
        self.assertIn("needs --clusters", r.stderr)

    def test_not_worse_needs_enough_phrasings(self):
        # reviewer's repro: 12 phrasings x 75 episodes; one phrasing is 75 episodes
        ids = [f"{p}_{e}" for p in range(12) for e in range(75)]
        base = {i: True for i in ids}
        cand = {i: not i.startswith("0_") for i in ids}  # one phrasing lost
        for i in ids:
            if i.startswith(("1_", "2_")):
                base[i] = False  # two phrasings gained
        self.put("b.json", base), self.put("c.json", cand)
        self.put("cl.json", {i: "p" + i.split("_")[0] for i in ids})
        r = self.noise("--paired-maps", "b.json", "c.json", "--clusters", "cl.json", "--not-worse", "27",
                       "--wide-margin")
        self.assertEqual(r.returncode, 1)
        self.assertIn("only 12 phrasings", r.stdout)

    def test_h5_clusters_that_do_not_match_the_maps_stop(self):
        ids = self.ids(40)
        for bank in ("sel_a", "sel_b"):
            self.put(f"base/{bank}.json", {e: i < 20 for i, e in enumerate(ids)})
            self.put(f"cand/{bank}.json", {e: i < 30 for i, e in enumerate(ids)})
        self.put("single.json", {e: "ph0" for e in ids})  # ids lack the bank: prefix
        for mode in ("--paired-maps", "--family-maps"):
            r = self.noise(mode, "base", "cand", "--clusters", "single.json")
            self.assertEqual(r.returncode, 2, mode)
            self.assertIn("no entry in the clusters file", r.stderr)
        self.put("cells.json", {f"sel_a:{e}": "x" for e in ids})
        r = self.noise("--visible", "base", "--cells", "cells.json", "--clusters", "single.json")
        self.assertEqual(r.returncode, 2)

    def test_directories_pool_banks_slots_and_segments(self):
        for bank, flip in (("sel_a", 10), ("sel_b", 6), ("sel_c", 0)):
            ids = self.ids(100)
            base = {e: i >= 20 for i, e in enumerate(ids)}
            cand = {e: (True if i < flip else base[e]) for i, e in enumerate(ids)}
            if bank == "sel_c":
                cand["e50"] = False
            self.put(f"base/{bank}.json", base)
            self.put(f"cand/{bank}.json", cand)
            self.put(f"cl/{bank}.json", {e: {"opening": f"o{i}", "reply": f"y{i % 4}"} for i, e in enumerate(ids)})
            self.put(f"seg/{bank}.json", {e: ("writes" if i < 50 else "routine") for i, e in enumerate(ids)})
        self.put("writers.json", {"sel_a": "w-a", "sel_b": "w-b", "sel_c": "w-c"})
        r = self.noise("--paired-maps", "base", "cand", "--clusters", "cl", "--segments", "seg",
                       "--writers", "writers.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("B 1 vs C 16", r.stdout)
        self.assertIn("slot opening", r.stdout)
        self.assertIn("slot reply", r.stdout)
        self.assertIn("by reply", r.stdout.splitlines()[1])  # the widest slot governs
        self.assertIn("same direction on 2 of 3 writer set-ups", r.stdout)
        self.assertIn("writes: ", r.stdout)
        self.assertIn("routine: ", r.stdout)
        r = self.noise("--family-maps", "base", "cand", "--clusters", "cl", "--writers", "writers.json")
        self.assertIn("same direction on 2 of 3 writer set-ups", r.stdout)
        self.assertIn("[clusters by reply", r.stdout)
        r = self.noise("--family", "base", "cand")
        self.assertIn("without --clusters", r.stderr)
        self.assertNotIn("without --clusters", self.noise("--family-maps", "base", "cand", "--clusters", "cl").stderr)

    def test_visible_flags_a_blind_cell(self):
        ids = self.ids(300)
        base = {e: not (i < 60 or 100 <= i < 160) for i, e in enumerate(ids)}
        cells = {e: ("writes/reply" if i < 100 else "writes/opening" if i < 200 else "routine/opening")
                 for i, e in enumerate(ids)}
        clusters = {e: (f"y{i % 4}" if i < 100 else f"o{i}") for i, e in enumerate(ids)}
        self.put("b.json", base), self.put("cells.json", cells), self.put("cl.json", clusters)
        r = self.noise("--visible", "b.json", "--cells", "cells.json", "--clusters", "cl.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = {ln.split(":")[0]: ln for ln in r.stdout.splitlines()}
        self.assertIn("distinct failing phrasings 4", lines["writes/reply"])
        self.assertIn("cannot see a fix", lines["writes/reply"])
        self.assertIn("distinct failing phrasings 60", lines["writes/opening"])
        self.assertNotIn("cannot see", lines["writes/opening"])
        self.assertIn("cannot see", lines["routine/opening"])  # no failures at all
        self.assertIn("2 cell(s) below 8", r.stdout)

    def test_mde_and_paired_clusters_note(self):
        r = self.noise("--mde", "1000", "--clusters", "125", "--base-rate", "0.85", "--of", "4")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("at least 6 phrasings", r.stdout)
        self.assertIn("8 under Holm with K = 4", r.stdout)
        r = self.noise("--mde", "1000", "--clusters", "125", "--base-rate", "0.85", "--churn", "0.05")
        self.assertNotIn("Holm", r.stdout)  # L6: no correction unless --of is given
        self.assertIn("paired, churn 5.0% (given)", r.stdout)
        self.assertEqual(self.noise("--mde", "1000", "--clusters", "125").returncode, 2)
        r = self.noise("--paired", "3", "12", "--clusters", "5")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--paired-maps", r.stdout)

    def test_monte_carlo_path_is_seeded(self):
        sys.path.insert(0, str(HERE))
        try:
            import noise
            sums = [1] * 30 + [-1] * 12 + [3, -2, 5]
            exact = noise.signflip_p(sums)
            old = noise.EXACT_LIMIT
            noise.EXACT_LIMIT = 0
            try:
                a, b = noise.signflip_p(sums), noise.signflip_p(sums)
            finally:
                noise.EXACT_LIMIT = old
            self.assertEqual(a, b)
            self.assertAlmostEqual(a, exact, delta=0.01)
            self.assertEqual(noise.bootstrap(sums), noise.bootstrap(sums))
        finally:
            sys.path.remove(str(HERE))


    # second review (Codex) repros
    def test_h7_gain_from_one_writer_is_not_general(self):
        for w in ("w1", "w2", "w3"):
            base = {f"e{i}": False for i in range(30)}
            cand = {k: (w == "w1" and i < 8) for i, k in enumerate(base)}
            self.put(f"b/{w}.json", base), self.put(f"c/{w}.json", cand)
            self.put(f"cl/{w}.json", {f"e{i}": f"p{i}" for i in range(30)})
        r = self.noise("--paired-maps", "b", "c", "--clusters", "cl")
        self.assertIn("not reliable across writers (writer set-ups unknown)", r.stdout)
        self.put("wr.json", {"w1": "set-up 1", "w2": "set-up 2", "w3": "set-up 3"})
        r = self.noise("--paired-maps", "b", "c", "--clusters", "cl", "--writers", "wr.json")
        self.assertIn("not reliable across writers (same direction on 1 of 3 writer set-ups", r.stdout)
        self.assertNotIn("pooled: base 0/90, cand 8/90: B 0 vs C 8, net +8, cluster sign-flip p = 0.008 over 90 "
                         "clusters by phrasing, 95% interval for the net +3 to +14: reliable gain", r.stdout)
        r = self.noise("--family-maps", "b", "c", "--clusters", "cl", "--writers", "wr.json")
        self.assertIn("not reliable across writers", r.stdout)

    def test_h8_every_episode_names_every_slot(self):
        ids = self.ids(40)
        self.put("b.json", {e: False for e in ids})
        self.put("c.json", {e: i < 10 for i, e in enumerate(ids)})
        cl = {e: {"open": "o1", "reply": f"r{i}"} for i, e in enumerate(ids)}
        for e in ids[:10]:
            cl[e] = {"reply": cl[e]["reply"]}  # the slot that would merge them is missing
        self.put("cl.json", cl)
        r = self.noise("--paired-maps", "b.json", "c.json", "--clusters", "cl.json")
        self.assertEqual(r.returncode, 2)
        self.assertIn("do not name every phrasing slot", r.stderr)
        for bad in ([], "", {}, None):
            self.put("cl2.json", {**{e: f"p{i}" for i, e in enumerate(ids)}, "e39": bad})
            r = self.noise("--paired-maps", "b.json", "c.json", "--clusters", "cl2.json")
            self.assertEqual(r.returncode, 2, bad)

    def test_h9_not_worse_holds_in_every_segment(self):
        ids = self.ids(1000)
        base = {e: not (100 <= i < 200) for i, e in enumerate(ids)}
        cand = {e: i >= 20 for i, e in enumerate(ids)}
        self.put("b.json", base), self.put("c.json", cand)
        self.put("cl.json", {e: f"p{i}" for i, e in enumerate(ids)})
        self.put("seg.json", {e: ("writes" if i < 50 else "other") for i, e in enumerate(ids)})
        self.assertEqual(self.noise("--paired-maps", "b.json", "c.json", "--clusters", "cl.json",
                                    "--not-worse", "1%").returncode, 0)
        r = self.noise("--paired-maps", "b.json", "c.json", "--clusters", "cl.json",
                       "--segments", "seg.json", "--not-worse", "1%")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not worse (segment writes), margin 0.5 of 50 episodes, net -20", r.stdout)
        self.assertIn("not worse (all)", r.stdout)

    def test_h10_cell_target_and_not_worse_elsewhere(self):
        ids = self.ids(400)
        base = {e: False for e in ids}
        cand = {e: i >= 300 for i, e in enumerate(ids)}  # every gain outside the target cell
        self.put("b.json", base), self.put("c.json", cand)
        self.put("cl.json", {e: f"p{i}" for i, e in enumerate(ids)})
        self.put("cells.json", {e: ("writes/reply" if i < 100 else "other") for i, e in enumerate(ids)})
        r = self.noise("--paired-maps", "b.json", "c.json", "--clusters", "cl.json", "--cells", "cells.json")
        self.assertEqual(r.returncode, 2)
        r = self.noise("--paired-maps", "b.json", "c.json", "--clusters", "cl.json", "--cells", "cells.json",
                       "--cell", "writes/reply", "--not-worse", "1%", *self.cycles(4))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("target cell writes/reply: 100 episodes", r.stdout)
        self.assertIn("cell: base 0/100, cand 0/100", r.stdout)
        self.assertIn("inside the noise", r.stdout)
        self.assertIn("not worse (outside the cell), margin 3.0 of 300 episodes", r.stdout)
        self.assertIn("one-sided threshold 0.0031", r.stdout)  # 0.025 / 4 / 2^1


    # third review (Codex re-check) repros
    def test_r7_banks_from_one_writer_set_up_count_once(self):
        for w in ("w1", "w2", "w3"):
            base = {f"e{i}": False for i in range(30)}
            cand = {k: (w != "w3" and i < 6) for i, k in enumerate(base)}
            self.put(f"b/{w}.json", base), self.put(f"c/{w}.json", cand)
            self.put(f"cl/{w}.json", {f"e{i}": f"p{i}" for i in range(30)})
        self.put("wr.json", {"w1": "brief A", "w2": "brief A", "w3": "brief B"})
        r = self.noise("--paired-maps", "b", "c", "--clusters", "cl", "--writers", "wr.json")
        self.assertIn("not reliable across writers (same direction on 1 of 2 writer set-ups", r.stdout)
        self.put("wr2.json", {"w1": "brief A"})
        self.assertEqual(self.noise("--paired-maps", "b", "c", "--writers", "wr2.json").returncode, 2)

    def test_r9_every_episode_needs_a_segment_and_cell_label(self):
        ids = self.ids(40)
        self.put("b.json", {e: True for e in ids})
        self.put("c.json", {e: i >= 5 for i, e in enumerate(ids)})
        self.put("cl.json", {e: f"p{i}" for i, e in enumerate(ids)})
        for bad in (None, "", 3):
            self.put("seg.json", {**{e: "routine" for e in ids}, "e0": bad})
            r = self.noise("--paired-maps", "b.json", "c.json", "--clusters", "cl.json",
                           "--segments", "seg.json", "--not-worse", "2%")
            self.assertEqual(r.returncode, 2, bad)
            self.assertIn("no non-empty label", r.stderr)
            r = self.noise("--visible", "b.json", "--cells", "seg.json")
            self.assertEqual(r.returncode, 2, bad)

    def test_r10_mechanism_tests_spend_alpha_across_cycles(self):
        ids = self.ids(40)
        self.put("b.json", {e: False for e in ids})
        self.put("c.json", {e: True for e in ids})
        self.put("cells.json", {e: "x" for e in ids})
        r = self.noise("--paired-maps", "b.json", "c.json", "--cells", "cells.json", "--cell", "x")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--cycle", r.stderr)
        cell = ("--paired-maps", "b.json", "c.json", "--cells", "cells.json", "--cell", "x")
        r = self.noise(*cell, "--cycle", "3")
        self.assertIn("--cycle needs --ledger", r.stderr)  # a free cycle number is refused
        led = self.cycles(1, 1, 2)
        self.assertEqual(self.noise(*cell, *led, "--of", "2").returncode, 2)  # K comes from the ledger
        r = self.noise(*cell, *led)
        self.assertIn("threshold 0.0031: 1 of 2, cycle 3", r.stdout)  # 0.05 / 2 / 2^3
        self.assertEqual(self.noise(*cell, *led).returncode, 0)  # the second of K = 2
        r = self.noise(*cell, *led)
        self.assertIn("all are used", r.stdout + r.stderr)
        r = self.noise(*cell, "--ledger", "seal-ledger.json", "--cycle", "1")
        self.assertIn("not the open cycle", r.stdout + r.stderr)  # an old cycle cannot be reused


    # final check (Codex) repros
    def test_f7_writer_set_ups_from_the_ledger_and_described_only(self):
        for w in ("w1", "w2", "w3"):
            base = {f"e{i}": False for i in range(30)}
            cand = {k: i < 3 for i, k in enumerate(base)}
            self.put(f"b/{w}.json", base), self.put(f"c/{w}.json", cand)
            self.put(f"cl/{w}.json", {f"e{i}": f"p{i}" for i in range(30)})
        led = self.cycles()[:2]
        led_path = self.d / "seal-ledger.json"
        env = {"SEAL_MIRROR": str(self.d.parent / self.mirror)}
        for w in ("w1", "w2", "w3"):
            self.put(f"{w}_bank.txt", w)
            self.put(f"m_{w}.json", {"writer_setup": f"brief {w}"})
            r = run(SEAL, "seal", w, "--role", "select", "--writer", w, "--manifest", f"m_{w}.json",
                    f"{w}_bank.txt", cwd=self.d, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
        r = self.noise("--paired-maps", "b", "c", "--clusters", "cl", *led)
        self.assertIn("reliable gain (pooled cluster test)", r.stdout)
        self.assertIn("same direction on 3 of 3 writer set-ups (a description, not a test)", r.stdout)
        self.assertNotIn("general", r.stdout.replace("generality", ""))
        self.assertNotIn("not verified", r.stdout)
        led_data = json.loads(led_path.read_text())
        led_data["banks"]["w3"]["manifest"]["writer_setup"] = "brief w1"  # hand edit
        led_path.write_text(json.dumps(led_data))
        r = self.noise("--paired-maps", "b", "c", "--clusters", "cl", *led)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ledger check failed", r.stdout + r.stderr)

    def test_fn1_segment_verdicts_use_the_corrected_threshold(self):
        ids = self.ids(40)
        self.put("b.json", {e: False for e in ids})
        self.put("c.json", {e: i < 6 for i, e in enumerate(ids)})  # six one-way flips: p = 0.031
        self.put("seg.json", {e: ("writes" if i < 20 else "routine") for i, e in enumerate(ids)})
        r = self.noise("--paired-maps", "b.json", "c.json", "--segments", "seg.json", "--of", "2")
        line = next(ln for ln in r.stdout.splitlines() if ln.strip().startswith("writes:"))
        self.assertIn("p = 0.031: inside the noise", line)


class CompareCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._mirror_dir = tempfile.TemporaryDirectory()  # the runner's mirror, outside self.d
        self.addCleanup(self._mirror_dir.cleanup)
        self.d = Path(self._tmp.name)
        git(self.d, "init", "-q")  # its own top level, also when the temp dir sits in a repo
        ids = [f"e{i}" for i in range(200)]
        for bank in ("fresh_a", "fresh_b"):
            # baseline passes 120, A 150, B 170 (B adds 20, loses nothing)
            self.put(f"v1/{bank}.json", {e: i < 120 for i, e in enumerate(ids)})
            self.put(f"a/{bank}.json", {e: i < 150 for i, e in enumerate(ids)})
            self.put(f"b/{bank}.json", {e: i < 170 for i, e in enumerate(ids)})
            self.put(f"cl/{bank}.json", {e: f"p{i // 2}" for i, e in enumerate(ids)})
            self.put(f"seg/{bank}.json", {e: ("writes" if i % 2 else "routine") for i, e in enumerate(ids)})
        self.put("train_a.json", man("earlier", ["earlier_t1", "earlier_t2", "sel_old"]))
        self.put("train_b.json", man("B", ["tr_new", "fresh_b"]))

    def tearDown(self):
        self._tmp.cleanup()

    def put(self, name: str, data) -> None:
        write(self.d / name, json.dumps(data))

    def cmp(self, *args: str) -> subprocess.CompletedProcess:
        return run(COMPARE, *args, cwd=self.d, env={"SEAL_MIRROR": str(self.mirror)})

    @property
    def mirror(self) -> Path:
        return Path(self._mirror_dir.name) / "mirror.jsonl"

    def compare_runs(self, systems=(("V5", "A", "a"), ("V7", "B", "b")), **over) -> list[dict]:
        """One clean compare run per system and bank, with the hash of the map it wrote."""
        runs = []
        for b in ("fresh_a", "fresh_b"):
            for v, sysname, d in systems:
                sha = seal_mod().sha256(self.d / d / f"{b}.json")
                runs.append({"bank": b, "version": v, "system": sysname, "status": "ok", "exit": 0,
                             "purpose": "compare", "forced": False, "dirty": False,
                             "outputs": {f"{b}.json": sha}, "fingerprint": {"judge.py": "f" * 64},
                             **over})
        return runs

    def banks(self) -> dict:
        """The comparison banks, and the TRAIN banks the systems' manifests may name."""
        out = {b: {"role": "holdout", "files": [], "burns": [],
                   "manifest": {"writer_setup": f"writer {b}"}} for b in ("fresh_a", "fresh_b")}
        for b in TRAIN_BANKS:
            out[b] = {"role": "train", "burns": [], "manifest": {"writer_setup": f"writer {b}"},
                      "files": [{"path": f"{b}.json", "bytes": 1,
                                 "sha256": hashlib.sha256(b.encode()).hexdigest()}]}
        return out

    def ledger(self, runs: list[dict], banks: dict | None = None) -> None:
        """A real ledger with a hash chain, written through seal.py."""
        path = self.d / "ledger.json"
        path.unlink(missing_ok=True)
        banks = banks or self.banks()
        self.mirror.unlink(missing_ok=True)
        old = os.environ.get("SEAL_MIRROR")
        os.environ["SEAL_MIRROR"] = str(self.mirror)
        try:
            seal_mod().save(path, {"banks": banks, "runs": runs})
        finally:
            if old is None:
                os.environ.pop("SEAL_MIRROR")
            else:
                os.environ["SEAL_MIRROR"] = old

    def test_full_report(self):
        self.ledger(self.compare_runs((("V5", "earlier", "a"), ("V3.1", "current", "b"), ("V1", "V1", "v1"))))
        r = self.cmp("--a", "earlier", "a", "--b", "current", "b", "--base", "V1", "v1", "--clusters", "cl",
                     "--ledger", "ledger.json",
                     "--segments", "seg", "--train-manifest-a", "train_a.json",
                     "--own-a", "2000", "1200", "1800", "--markdown")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout
        self.assertIn("| pooled (fresh) | 400 | 240 (60.0%) | 300 (75.0%) | 340 (85.0%) | 0 | 40 | +40 |", out)
        self.assertIn("current ahead on 2 of 2 fresh banks; clusters by phrasing", out)
        self.assertIn("| writes | 200 |", out)
        self.assertIn("equally hard", out)
        self.assertIn("| earlier | +600 of 2000 (+30.0%) | +60 of 400 (+15.0%) | 50% |", out)
        self.assertIn("| current | not given | +100 of 400 (+25.0%) | - |", out)
        self.assertIn("On the same 400 fresh episodes from 2 bank(s) (fresh_a, fresh_b)", out)
        self.assertIn("current minus earlier +40", out)
        self.assertIn("baseline V1 240", out)

    def test_refusals_and_in_sample(self):
        self.ledger(self.compare_runs())
        r = self.cmp("--a", "A", "a", "--b", "B", "b", "--train-manifest-b", "train_b.json",
                     "--ledger", "ledger.json")
        self.assertEqual(r.returncode, 2)
        self.assertIn("fresh_b (trained on by B)", r.stderr)
        r = self.cmp("--a", "A", "a", "--b", "B", "b", "--train-manifest-b", "train_b.json", "--in-sample",
                     "--ledger", "ledger.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("fresh_b (in-sample, not comparable)", r.stdout)
        self.assertIn("on 1 fresh bank(s), 200 episodes", r.stdout)
        self.assertIn("one bank is one writer", r.stdout)
        self.put("b2/fresh_a.json", {f"e{i}": True for i in range(200)})
        r = self.cmp("--a", "A", "a", "--b", "B", "b2")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not run on the same banks", r.stderr)
        self.put("b3/fresh_a.json", {f"x{i}": True for i in range(200)})
        self.put("b3/fresh_b.json", {f"e{i}": True for i in range(200)})
        r = self.cmp("--a", "A", "a", "--b", "B", "b3")
        self.assertIn("fresh_a: B was not run on the same episode ids", r.stderr)

    def test_unequal_banks_for_the_baseline(self):
        ids = [f"e{i}" for i in range(200)]
        self.put("v1/fresh_b.json", {e: i < 40 for i, e in enumerate(ids)})
        r = self.cmp("--a", "A", "a", "--b", "B", "b", "--base", "V1", "v1")
        self.assertIn("not equally hard", r.stdout)
        self.assertIn("note: no --clusters", r.stdout)

    def test_m1_freshness_ledger_and_wording(self):
        self.put("manB.json", man("B", ["fresh_a", "train_1"]))  # reviewer's repro
        self.ledger(self.compare_runs())
        r = self.cmp("--a", "A", "a", "--b", "B", "b", "--train-manifest-b", "manB.json",
                     "--ledger", "ledger.json")
        self.assertEqual(r.returncode, 2)
        self.assertIn("fresh_a (trained on by B)", r.stderr)
        r = self.cmp("--a", "A", "a", "--b", "B", "b")
        self.assertIn("freshness not checked for A, B", r.stdout)
        self.assertNotIn("neither system trained on", r.stdout)
        self.assertIn("no --ledger", r.stdout)
        runs = self.compare_runs()
        self.ledger(runs + [dict(runs[0], version="V5b")])
        r = self.cmp("--a", "A", "a", "--b", "B", "b", "--ledger", "ledger.json")
        self.assertEqual(r.returncode, 2)
        self.assertIn("A on fresh_a: 2 logged runs", r.stderr)
        self.ledger(runs)
        self.put("ta.json", man("A", ["x"])), self.put("tb.json", man("B", ["y"]))
        r = self.cmp("--a", "A", "a", "--b", "B", "b", "--ledger", "ledger.json",
                     "--train-manifest-a", "ta.json", "--train-manifest-b", "tb.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("neither system trained on (manifests checked", r.stdout)
        # five clusters all gained: interval excludes zero, sign-flip p = 0.0625
        for name, val in (("a5", False), ("b5", True)):
            self.put(f"{name}/tiny.json", {f"e{i}": val for i in range(5)})
        r = self.cmp("--a", "A", "a5", "--b", "B", "b5")
        self.assertIn("inside the noise (the bootstrap interval excludes zero", r.stdout)

    def test_h5_clusters_must_cover_the_episodes(self):
        self.put("badcl/fresh_a.json", {"x": "p"})
        self.put("badcl/fresh_b.json", {"x": "p"})
        r = self.cmp("--a", "A", "a", "--b", "B", "b", "--clusters", "badcl")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no entry in the clusters file", r.stderr)


    # second review (Codex) repros
    def test_h11_freshness_by_hash_and_writer_and_clean_runs_only(self):
        self.ledger(self.compare_runs())
        self.put("empty.json", man("A"))
        r = self.cmp("--a", "A", "a", "--b", "B", "b", "--train-manifest-a", "empty.json",
                     "--ledger", "ledger.json")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not both empty", r.stderr)
        sha = None
        # a renamed copy of fresh_a (same file hash), and a TRAIN bank by fresh_b's writer
        self.put("renamed_copy.json", {"e1": "fresh_a text"})
        copy_sha = seal_mod().sha256(self.d / "renamed_copy.json")
        banks = self.banks()
        banks["fresh_a"]["files"] = [{"path": "fresh_a.json", "sha256": copy_sha, "bytes": 1}]
        banks["y"]["manifest"]["writer_setup"] = "writer fresh_b"
        self.ledger(self.compare_runs(), banks)
        for m in (man("A", files=[{"path": "renamed_copy.json", "sha256": copy_sha}]), man("A", ["y"])):
            self.put("tm.json", m)
            r = self.cmp("--a", "A", "a", "--b", "B", "b", "--ledger", "ledger.json",
                         "--train-manifest-a", "tm.json")
            self.assertEqual(r.returncode, 2, m)
            self.assertIn("trained on by A", r.stderr)
        for over, why in (({"purpose": "score"}, "purpose is not compare"), ({"forced": True}, "forced"),
                          ({"dirty": True}, "dirty"), ({"status": "failed", "exit": 1}, "not ok"),
                          ({"outputs": {"a.json": sha}}, "not the file the run wrote")):
            self.ledger(self.compare_runs(**over))
            r = self.cmp("--a", "A", "a", "--b", "B", "b", "--ledger", "ledger.json")
            self.assertEqual(r.returncode, 2, over)
            self.assertIn(why, r.stderr)
        self.ledger(self.compare_runs())
        led = json.loads((self.d / "ledger.json").read_text())
        led["runs"][0]["status"] = "ok "  # hand edit
        self.put("ledger.json", led)
        r = self.cmp("--a", "A", "a", "--b", "B", "b", "--ledger", "ledger.json")
        self.assertIn("does not check out", r.stderr)


    # third review (Codex re-check) repros
    def test_r11_provenance_manifests_mirror_and_one_evaluator(self):
        self.ledger(self.compare_runs())
        self.put("tm.json", man("A", ["x"]))
        r = self.cmp("--a", "A", "a", "--b", "B", "b", "--train-manifest-a", "tm.json")
        self.assertIn("needs --ledger", r.stderr)
        for bad in (["fresh_x"], {"trained_on": ["x"]}, man("someone-else", ["x"]),
                    man("A", ["unrelated-token"]),  # Codex: arbitrary strings passed before
                    man("A", files=[{"path": "a/fresh_a.json", "sha256": "0" * 64}])):
            self.put("tm.json", bad)
            r = self.cmp("--a", "A", "a", "--b", "B", "b", "--train-manifest-a", "tm.json",
                         "--ledger", "ledger.json")
            self.assertEqual(r.returncode, 2, bad)
        r = run(COMPARE, "--a", "A", "a", "--b", "B", "b", "--ledger", "ledger.json", cwd=self.d,
                env={"SEAL_MIRROR": None})
        self.assertEqual(r.returncode, 2)
        self.assertIn("no mirror protects it", r.stderr)
        runs = self.compare_runs()
        runs[0]["fingerprint"] = {"judge.py": "e" * 64}  # one run scored by another evaluator
        self.ledger(runs)
        r = self.cmp("--a", "A", "a", "--b", "B", "b", "--ledger", "ledger.json")
        self.assertIn("one non-empty evaluator fingerprint", r.stderr)
        self.ledger(self.compare_runs(fingerprint=None))
        r = self.cmp("--a", "A", "a", "--b", "B", "b", "--ledger", "ledger.json")
        self.assertIn("one non-empty evaluator fingerprint", r.stderr)
        # two banks from two writer set-ups: a reliable pooled gain is not general
        self.ledger(self.compare_runs())
        r = self.cmp("--a", "A", "a", "--b", "B", "b", "--ledger", "ledger.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("not reliable across writers (same direction on 2 of 2 writer set-ups", r.stdout)


class DriftCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def put(self, name: str, data) -> str:
        write(self.d / name, json.dumps(data))
        return name

    def drift(self, *args: str) -> subprocess.CompletedProcess:
        return run(DRIFT, *args, cwd=self.d)

    def test_mix(self):
        self.put("ref.json", {"routine": 500, "writes": 400, "safety": 100})
        self.put("same.json", ["routine"] * 50 + ["writes"] * 40 + ["safety"] * 10)
        self.put("moved.json", {"routine": 200, "writes": 700, "access": 100})
        r = self.drift("mix", "ref.json", "same.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("PSI 0.000", r.stdout)
        self.assertIn("stable", r.stdout)
        r = self.drift("mix", "ref.json", "moved.json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("DRIFT", r.stdout)
        self.assertEqual(self.drift("mix", "ref.json", "moved.json", "--threshold", "5").returncode, 0)
        self.put("bad.json", {"routine": -1})
        self.assertEqual(self.drift("mix", "ref.json", "bad.json").returncode, 2)

    def test_rate(self):
        r = self.drift("rate", "1000", "50", "1000", "52", "--name", "handoff")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("handoff reference: 50/1000 = 5.00%", r.stdout)
        self.assertIn("no reliable change", r.stdout)
        r = self.drift("rate", "1000", "50", "1000", "120")
        self.assertEqual(r.returncode, 1)
        self.assertIn("MOVED", r.stdout)
        self.assertEqual(self.drift("rate", "10", "11", "10", "1").returncode, 2)

    def test_gap(self):
        self.put("sim.json", {"writes": [900, 1000], "routine": {"passed": 95, "n": 100}, "sim_only": [1, 2]})
        self.put("live.json", {"writes": [70, 100], "routine": [94, 100]})
        r = self.drift("gap", "sim.json", "live.json", "--max-gap", "50")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("gap +20.0 points", r.stdout)
        self.assertIn("sim_only", r.stdout)
        self.assertEqual(self.drift("gap", "sim.json", "live.json", "--max-gap", "5").returncode, 1)

    def test_m2_gap_coverage_and_sample_size(self):
        self.put("sim.json", {"sim": [90, 100], "routine": [80, 100]})  # reviewer's repro
        self.put("live.json", {"routine": [79, 100], "safety": [3, 40]})
        r = self.drift("gap", "sim.json", "live.json", "--max-gap", "5")
        self.assertEqual(r.returncode, 1)
        self.assertIn("safety           ALARM: live traffic the simulation does not cover", r.stdout)
        self.put("sim2.json", {"writes": [95, 100]})
        self.put("live2.json", {"writes": [8, 10]})  # 15-point gap on 10 live episodes
        r = self.drift("gap", "sim2.json", "live2.json", "--max-gap", "5")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("too few episodes", r.stdout)


    # second review (Codex) repros
    def test_m17_finite_thresholds_registered_gap_and_sim_interval(self):
        self.put("m1.json", {"a": 10, "b": 10})
        self.put("m2.json", {"a": 19, "b": 1})
        for bad in ("nan", "inf", "-1"):
            self.assertEqual(self.drift("mix", "m1.json", "m2.json", "--threshold", bad).returncode, 2, bad)
        self.assertEqual(self.drift("rate", "100", "5", "100", "6", "--alpha", "nan").returncode, 2)
        self.put("s.json", {"a": [5, 100]})
        self.assertEqual(self.drift("gap", "s.json", "s.json").returncode, 2)
        self.assertEqual(self.drift("gap", "s.json", "s.json", "--max-gap", "nan").returncode, 2)
        # 12 sim episodes: 100% there is not exact, so a 30-point gap is not yet an alarm
        self.put("sim.json", {"a": [12, 12]})
        self.put("live.json", {"a": [700, 1000]})
        r = self.drift("gap", "sim.json", "live.json", "--max-gap", "5")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("too few episodes", r.stdout)
        self.put("sim.json", {"a": [200, 200]})
        r = self.drift("gap", "sim.json", "live.json", "--max-gap", "5")
        self.assertEqual(r.returncode, 1, r.stdout)


class VerdictCacheCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)
        sys.path.insert(0, str(HERE))
        import verdict_cache
        self.vc = verdict_cache

    def tearDown(self):
        sys.path.remove(str(HERE))
        self._tmp.cleanup()

    def vcr(self, *args: str) -> subprocess.CompletedProcess:
        return run(VC, *args, cwd=self.d)

    def lines(self, name: str, rows: list) -> str:
        write(self.d / name, "".join((r if isinstance(r, str) else json.dumps(r)) + "\n" for r in rows))
        return name

    def test_missing_prints_keys_only(self):
        self.lines("reqs.jsonl", [{"key": "k1", "kind": "safety", "payload": {"message": "SECRET HOLDOUT"}},
                                  {"key": "k2", "kind": "safety", "payload": {"message": "x"}}, "not json"])
        write(self.d / "v.json", json.dumps({"k2": "none"}))
        r = self.vcr("missing", "reqs.jsonl", "--verdicts", "v.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split(), ["k1"])
        self.assertNotIn("SECRET", r.stdout + r.stderr)
        self.assertIn("1 missing of 2", r.stderr)
        self.assertIn("safety: 1", r.stderr)
        r = self.vcr("missing", "reqs.jsonl", "--verdicts", "v.json", "--show-payloads")
        self.assertIn("SECRET", r.stdout)

    def test_merge_conflicts_abstain_or_prefer_care(self):
        self.lines("a-verdicts.jsonl", [{"key": "k1", "verdict": "Escalate."}, {"key": "k2", "verdict": " NONE "}])
        self.lines("b-verdicts.jsonl", [{"key": "k1", "verdict": "none"}, {"key": "k2", "verdict": "none"},
                                        "{broken", {"verdict": "none"}, {"key": "k3", "verdict": "maybe"}])
        r = self.vcr("merge", "*-verdicts.jsonl", "--into", "v.json", "--labels", "Escalate", "none")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads((self.d / "v.json").read_text()), {"k2": "none"})
        self.assertIn("conflict, abstained: k1", r.stdout)
        self.assertIn("2 malformed", r.stdout)
        self.assertIn("1 off-label", r.stdout)
        (self.d / "v.json").unlink()
        r = self.vcr("merge", "*-verdicts.jsonl", "--into", "v.json", "--labels", "escalate", "none",
                     "--prefer", "escalate,none")
        self.assertEqual(json.loads((self.d / "v.json").read_text()), {"k1": "escalate", "k2": "none"})
        # an existing cache entry also takes part in conflicts
        self.lines("c.jsonl", [{"key": "k1", "verdict": "none"}])
        self.vcr("merge", "c.jsonl", "--into", "v.json", "--labels", "escalate", "none")
        self.assertNotIn("k1", json.loads((self.d / "v.json").read_text()))

    def test_merge_needs_labels_and_valid_prefer(self):
        self.lines("a.jsonl", [{"key": "k1", "verdict": "yes"}])
        self.assertNotEqual(self.vcr("merge", "a.jsonl", "--into", "v.json").returncode, 0)
        r = self.vcr("merge", "a.jsonl", "--into", "v.json", "--labels", "yes", "--prefer", "yes,no")
        self.assertIn("not in --labels", r.stderr)

    def test_chunk_size_validated(self):
        self.lines("reqs.jsonl", [{"key": f"k{i}"} for i in range(5)])
        r = self.vcr("chunk", "reqs.jsonl", "--size", "0", "--prefix", "out/p")
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)
        r = self.vcr("chunk", "reqs.jsonl", "--size", "2", "--prefix", "out/p")
        self.assertEqual(len(r.stdout.split()), 3)

    def test_overlap_fails_when_shipped_cache_holds_sealed_keys(self):
        self.lines("hold.jsonl", [{"key": "k1", "payload": {"m": "SECRET"}}, {"key": "k9"}])
        write(self.d / "ship.json", json.dumps({"k2": "none"}))
        r = self.vcr("overlap", "ship.json", "hold.jsonl")
        self.assertEqual(r.returncode, 0, r.stderr)
        write(self.d / "ship.json", json.dumps({"k1": "none", "k2": "none"}))
        r = self.vcr("overlap", "ship.json", "hold.jsonl")
        self.assertEqual(r.returncode, 1)
        self.assertIn("1 of 2", r.stdout)
        self.assertNotIn("SECRET", r.stdout + r.stderr)
        self.assertNotIn("k1", r.stdout + r.stderr)

    def test_key_normalises_prompt(self):
        k = self.vc.key
        self.assertEqual(k("a\r\nb", "s", {"m": 1}), k("a\nb", "s", {"m": 1}))
        self.assertEqual(k(unicodedata.normalize("NFD", "café"), "s", {}), k("café", "s", {}))
        self.assertNotEqual(k("a", "s", {}), k("b", "s", {}))


if __name__ == "__main__":
    unittest.main()
