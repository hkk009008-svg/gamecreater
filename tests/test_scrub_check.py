import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import scrub_check as sc


class TestLoadTerms(unittest.TestCase):
    def test_literals_and_regexes(self):
        pats = sc.load_terms(["# comment\nsecretword\nre:tok_[0-9]+\n"])
        self.assertEqual(len(pats), 2)

    def test_empty_input_loads_nothing(self):
        self.assertEqual(sc.load_terms([]), [])
        self.assertEqual(sc.load_terms(["# only comments\n"]), [])


class TestScanText(unittest.TestCase):
    def setUp(self):
        self.pats = sc.load_terms(["projectnoun\nre:[a-z0-9.]+@[a-z]+\\.com\n"])

    def test_hit_reports_file_line_term(self):
        hits = sc.scan_text("doc.md", "clean\nhas ProjectNoun here\n",
                            self.pats)
        self.assertEqual(len(hits), 1)
        self.assertIn("doc.md:2", hits[0])

    def test_regex_hits(self):
        # Assembled at runtime so the literal address never appears in the
        # tree — the scrub scans this file too, and caught it once.
        addr = "someone" + chr(64) + "example.com"
        hits = sc.scan_text("a.txt", f"mail me: {addr}", self.pats)
        self.assertEqual(len(hits), 1)

    def test_clean_text_no_hits(self):
        self.assertEqual(
            sc.scan_text("a.txt", "nothing to see", self.pats), [])

    def test_case_insensitive_literal(self):
        hits = sc.scan_text("a.txt", "PROJECTNOUN", self.pats)
        self.assertEqual(len(hits), 1)


class TestMainVerdicts(unittest.TestCase):
    """Regression pins for the vacuous-green defects (2026-08-13 audit):
    a green verdict must carry its denominators, and main() must refuse
    when any of them collapses instead of reporting clean over nothing."""

    def setUp(self):
        self._root = sc.ROOT
        self._term_files = sc.TERM_FILES
        self._env = os.environ.pop("SCRUB_REQUIRE_LOCAL_TERMS", None)
        self._td = tempfile.TemporaryDirectory()
        self.dir = Path(self._td.name)

    def tearDown(self):
        sc.ROOT = self._root
        sc.TERM_FILES = self._term_files
        os.environ.pop("SCRUB_REQUIRE_LOCAL_TERMS", None)
        if self._env is not None:
            os.environ["SCRUB_REQUIRE_LOCAL_TERMS"] = self._env
        self._td.cleanup()

    def _terms(self, body="secretword\n", name="terms.txt"):
        f = self.dir / name
        f.write_text(body, encoding="utf-8")
        return f

    def _git_repo(self, *files):
        repo = self.dir / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True,
                       capture_output=True)
        for name, body in files:
            (repo / name).write_bytes(body)
            subprocess.run(["git", "add", name], cwd=repo, check=True,
                           capture_output=True)
        return repo

    def _run_main(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = sc.main([])
        return rc, buf.getvalue()

    def test_enumerator_failure_is_a_distinct_failure(self):
        # git ls-files fails outside a repo; pre-fix this printed
        # "scrub clean: 0 tracked text files" and exited 0.
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self.dir / "notarepo"
        sc.ROOT.mkdir()
        rc, out = self._run_main()
        self.assertEqual(rc, 2)
        self.assertIn("ls-files failed", out)
        self.assertNotIn("scrub clean", out)

    def test_zero_files_enumerated_is_a_distinct_failure(self):
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo()  # valid repo, nothing tracked
        rc, out = self._run_main()
        self.assertEqual(rc, 2)
        self.assertIn("0 of 0", out)
        self.assertNotIn("scrub clean", out)

    def test_missing_local_terms_warns_naming_the_tier(self):
        absent = self.dir / "scrub_terms.local.txt"  # never created
        sc.TERM_FILES = (self._terms(), absent)
        sc.ROOT = self._git_repo(("doc.txt", b"clean\n"))
        rc, out = self._run_main()
        self.assertEqual(rc, 0)
        self.assertIn("WARNING", out)
        self.assertIn("scrub_terms.local.txt", out)

    def test_strict_env_hard_fails_on_missing_local_terms(self):
        absent = self.dir / "scrub_terms.local.txt"
        sc.TERM_FILES = (self._terms(), absent)
        sc.ROOT = self._git_repo(("doc.txt", b"clean\n"))
        os.environ["SCRUB_REQUIRE_LOCAL_TERMS"] = "1"
        rc, out = self._run_main()
        self.assertEqual(rc, 2)
        self.assertIn("SCRUB_REQUIRE_LOCAL_TERMS", out)

    def test_strict_env_passes_when_local_terms_present(self):
        local = self._terms("localnoun\n", name="scrub_terms.local.txt")
        sc.TERM_FILES = (self._terms(), local)
        sc.ROOT = self._git_repo(("doc.txt", b"clean\n"))
        os.environ["SCRUB_REQUIRE_LOCAL_TERMS"] = "1"
        rc, out = self._run_main()
        self.assertEqual(rc, 0)
        self.assertNotIn("WARNING", out)

    def test_no_patterns_refuses_as_instrument_failure(self):
        sc.TERM_FILES = (self._terms("# only comments\n"),)
        sc.ROOT = self._git_repo(("doc.txt", b"clean\n"))
        rc, out = self._run_main()
        self.assertEqual(rc, 2)
        self.assertIn("no terms loaded", out)

    def test_nul_file_skip_is_counted_in_summary(self):
        # UTF-16 text (common from Windows tooling) has NULs in its first
        # bytes and is skipped as binary — the summary must say so.
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo(("doc.txt", b"clean\n"),
                                 ("utf16.txt", "clean\n".encode("utf-16")))
        rc, out = self._run_main()
        self.assertEqual(rc, 0)
        self.assertIn("1 tracked text files", out)
        self.assertIn("1 skipped", out)

    def test_unreadable_file_skip_is_counted_in_summary(self):
        sc.TERM_FILES = (self._terms(),)
        repo = self._git_repo(("doc.txt", b"clean\n"),
                              ("gone.txt", b"tracked then deleted\n"))
        (repo / "gone.txt").unlink()  # still in the index -> enumerated
        sc.ROOT = repo
        rc, out = self._run_main()
        self.assertEqual(rc, 0)
        self.assertIn("1 skipped", out)

    def test_all_files_skipped_refuses(self):
        # Enumeration succeeded but nothing was scannable: still vacuous.
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo(("utf16.txt", "clean\n".encode("utf-16")))
        rc, out = self._run_main()
        self.assertEqual(rc, 2)
        self.assertIn("0 of 1", out)
        self.assertIn("1 skipped", out)


class TestRealEntry(unittest.TestCase):
    """The consumer's entry is `python scripts/scrub_check.py` on a console
    that encodes with the machine codepage (cp949 on this machine), not an
    in-process call with a StringIO stdout. The exit contract (0 clean /
    1 dirty / 2 broken instrument) must hold there, which also means every
    printed message must survive that encoding."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        root = Path(self._td.name) / "proj"
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "scrub_check.py").write_bytes(
            Path(sc.__file__).read_bytes())
        (root / "scripts" / "scrub_terms.txt").write_text(
            "secretword\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True,
                       capture_output=True)
        (root / "doc.txt").write_bytes(b"clean\n")
        # Track only the content file: the fixture's own term list holds a
        # literal that would (correctly) self-match if it were scanned.
        subprocess.run(["git", "add", "doc.txt"], cwd=root, check=True,
                       capture_output=True)
        self.root = root
        # Strip PYTHON* so PYTHONIOENCODING/PYTHONUTF8 cannot mask the
        # console codepage the real gate runs under.
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith("PYTHON")}
        self.env.pop("SCRUB_REQUIRE_LOCAL_TERMS", None)

    def tearDown(self):
        self._td.cleanup()

    def _run(self, **env):
        return subprocess.run(
            [sys.executable, str(self.root / "scripts" / "scrub_check.py")],
            capture_output=True, text=True, errors="replace",
            env={**self.env, **env})

    def test_missing_local_tier_warns_and_exits_zero(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("WARNING", proc.stdout)

    def test_strict_refuses_with_exit_2(self):
        proc = self._run(SCRUB_REQUIRE_LOCAL_TERMS="1")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("SCRUB_REQUIRE_LOCAL_TERMS", proc.stdout)

    def test_git_binary_unavailable_is_instrument_failure(self):
        # An empty PATH makes the git subprocess unlaunchable; the gate
        # must refuse as a broken instrument (exit 2), not crash into the
        # exit code that means "hits found".
        proc = self._run(PATH="")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("cannot enumerate", proc.stdout)

    def test_dirty_tree_exits_one_with_hits(self):
        (self.root / "dirty.txt").write_bytes(b"has secretword inside\n")
        subprocess.run(["git", "add", "dirty.txt"], cwd=self.root,
                       check=True, capture_output=True)
        proc = self._run()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("SCRUB FAILED", proc.stdout)


if __name__ == "__main__":
    unittest.main()
