import contextlib
import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import scrub_check as sc

# NUL-bearing bytes with no text BOM: the shape the binary skip is FOR.
BINARY = b"\x89PNG\r\n\x1a\n\x00\x00\x00 not text"


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
        hits, _ = sc.scan_text("doc.md", "clean\nhas ProjectNoun here\n",
                               self.pats)
        self.assertEqual(len(hits), 1)
        self.assertIn("doc.md:2", hits[0])

    def test_regex_hits(self):
        # Assembled at runtime so the literal address never appears in the
        # tree — the scrub scans this file too, and caught it once.
        addr = "someone" + chr(64) + "example.com"
        hits, _ = sc.scan_text("a.txt", f"mail me: {addr}", self.pats)
        self.assertEqual(len(hits), 1)

    def test_clean_text_no_hits(self):
        self.assertEqual(
            sc.scan_text("a.txt", "nothing to see", self.pats), ([], 0))

    def test_case_insensitive_literal(self):
        hits, _ = sc.scan_text("a.txt", "PROJECTNOUN", self.pats)
        self.assertEqual(len(hits), 1)


class TestMainVerdicts(unittest.TestCase):
    """Regression pins for the vacuous-green defects (2026-08-13 audit):
    a green verdict must carry its denominators, and main() must refuse
    when any of them collapses instead of reporting clean over nothing."""

    def setUp(self):
        self._root = sc.ROOT
        self._term_files = sc.TERM_FILES
        self._env = {k: os.environ.pop(k, None)
                     for k in ("SCRUB_REQUIRE_LOCAL_TERMS",
                               "SCRUB_REQUIRE_TOTAL_SCAN")}
        self._td = tempfile.TemporaryDirectory()
        self.dir = Path(self._td.name)

    def tearDown(self):
        sc.ROOT = self._root
        sc.TERM_FILES = self._term_files
        for k, v in self._env.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
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

    def test_strict_env_zero_means_off(self):
        # "0" is the documented off-value; a polarity slip here bricks
        # the gate to exit 2 on a clean tree (mutation-audit hole M4).
        absent = self.dir / "scrub_terms.local.txt"
        sc.TERM_FILES = (self._terms(), absent)
        sc.ROOT = self._git_repo(("doc.txt", b"clean\n"))
        os.environ["SCRUB_REQUIRE_LOCAL_TERMS"] = "0"
        rc, out = self._run_main()
        self.assertEqual(rc, 0)
        self.assertIn("WARNING", out)

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
        # True binaries (NUL bytes, no text BOM) are skipped — and the
        # summary must say so. UTF-16 no longer lands here: since the
        # 2026-08-13 fix it is decoded and scanned (tests below).
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo(("doc.txt", b"clean\n"),
                                 ("blob.bin", BINARY))
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
        sc.ROOT = self._git_repo(("blob.bin", BINARY))
        rc, out = self._run_main()
        self.assertEqual(rc, 2)
        self.assertIn("0 of 1", out)
        self.assertIn("1 skipped", out)

    def test_utf16le_secret_is_decoded_and_caught(self):
        # Pre-fix the NUL heuristic skipped UTF-16 wholesale: a planted
        # secret exited 0 "clean" while its ASCII twin was caught in the
        # same run (2026-08-13 adversarial pass).
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo(
            ("u16.txt",
             b"\xff\xfe" + "has secretword inside\n".encode("utf-16-le")))
        rc, out = self._run_main()
        self.assertEqual(rc, 1)
        self.assertIn("u16.txt:1", out)

    def test_utf16be_secret_is_decoded_and_caught(self):
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo(
            ("u16.txt",
             b"\xfe\xff" + "has secretword inside\n".encode("utf-16-be")))
        rc, out = self._run_main()
        self.assertEqual(rc, 1)
        self.assertIn("u16.txt:1", out)

    def test_utf32le_secret_is_decoded_and_caught(self):
        # A UTF-32-LE BOM begins with the UTF-16-LE BOM bytes: decoded
        # as UTF-16 the text is NUL-riddled and the term cannot match,
        # so the UTF-32 check must run first.
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo(
            ("u32.txt",
             b"\xff\xfe\x00\x00"
             + "has secretword inside\n".encode("utf-32-le")))
        rc, out = self._run_main()
        self.assertEqual(rc, 1)
        self.assertIn("u32.txt:1", out)

    def test_utf32be_secret_is_decoded_and_caught(self):
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo(
            ("u32.txt",
             b"\x00\x00\xfe\xff"
             + "has secretword inside\n".encode("utf-32-be")))
        rc, out = self._run_main()
        self.assertEqual(rc, 1)
        self.assertIn("u32.txt:1", out)

    def test_total_scan_env_refuses_on_a_skipped_file(self):
        # A skip tally in the output is not a skip tally at an
        # exit-code-only consumer: strict mode turns skipped>0 into a
        # refusal, and names what was skipped.
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo(("doc.txt", b"clean\n"),
                                 ("blob.bin", BINARY))
        os.environ["SCRUB_REQUIRE_TOTAL_SCAN"] = "1"
        rc, out = self._run_main()
        self.assertEqual(rc, 2)
        self.assertIn("SCRUB_REQUIRE_TOTAL_SCAN", out)
        self.assertIn("blob.bin", out)
        self.assertNotIn("scrub clean", out)

    def test_total_scan_env_zero_means_off(self):
        # "0" is the documented off-value, same convention as
        # SCRUB_REQUIRE_LOCAL_TERMS (mutation-audit hole M4).
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo(("doc.txt", b"clean\n"),
                                 ("blob.bin", BINARY))
        os.environ["SCRUB_REQUIRE_TOTAL_SCAN"] = "0"
        rc, out = self._run_main()
        self.assertEqual(rc, 0)
        self.assertIn("1 skipped", out)

    def test_total_scan_env_passes_on_a_full_scan(self):
        # Positive control: the flag alone must not brick a clean tree.
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo(("doc.txt", b"clean\n"))
        os.environ["SCRUB_REQUIRE_TOTAL_SCAN"] = "1"
        rc, out = self._run_main()
        self.assertEqual(rc, 0)
        self.assertIn("scrub clean", out)

    def test_hits_still_win_over_a_total_scan_refusal(self):
        # Exit 1 (hits) is the more specific verdict; either code blocks
        # a strict consumer.
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo(("dirty.txt", b"has secretword\n"),
                                 ("blob.bin", BINARY))
        os.environ["SCRUB_REQUIRE_TOTAL_SCAN"] = "1"
        rc, out = self._run_main()
        self.assertEqual(rc, 1)
        self.assertIn("SCRUB FAILED", out)

    def test_long_line_head_is_still_scanned(self):
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo(
            ("big.txt", ("secretword " + "x" * 6000 + "\n").encode()))
        rc, out = self._run_main()
        self.assertEqual(rc, 1)
        self.assertIn("big.txt:1", out)

    def test_long_line_truncation_is_noted(self):
        # The tail past the cap is NOT scanned; the note is what keeps
        # that narrowing honest (line too long, truncated-scan).
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo(
            ("big.txt", ("x" * 6000 + "\n").encode()))
        rc, out = self._run_main()
        self.assertEqual(rc, 0)
        self.assertIn("truncated-scan", out)
        self.assertIn("big.txt", out)

    def test_total_scan_env_refuses_on_a_truncated_line(self):
        # A term hidden past the cap is unscanned — strict mode must
        # refuse rather than report clean over a partial line.
        sc.TERM_FILES = (self._terms(),)
        sc.ROOT = self._git_repo(
            ("big.txt", ("x" * 6000 + " secretword\n").encode()))
        os.environ["SCRUB_REQUIRE_TOTAL_SCAN"] = "1"
        rc, out = self._run_main()
        self.assertEqual(rc, 2)
        self.assertIn("truncated", out)


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
        (root / "scripts" / "gitignored_config.py").write_bytes(
            (Path(sc.__file__).resolve().parent
             / "gitignored_config.py").read_bytes())
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
        self.env.pop("SCRUB_REQUIRE_TOTAL_SCAN", None)

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

    def test_strict_env_zero_means_off_at_real_entry(self):
        proc = self._run(SCRUB_REQUIRE_LOCAL_TERMS="0")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("WARNING", proc.stdout)

    def test_verdict_text_is_ascii_with_no_escape_artifacts(self):
        # backslashreplace is a last-resort backstop, not a license: a
        # non-ASCII char regrowing in a message degrades to literal
        # \uXXXX sequences on this console instead of crashing. Pin the
        # messages themselves ASCII (mutation-audit hole M8).
        proc = self._run()
        self.assertTrue(proc.stdout.isascii(), proc.stdout)
        self.assertNotIn("\\u", proc.stdout)

    def test_non_ascii_matched_text_still_reports_the_hit(self):
        # The reconfigure guard is what keeps non-cp949 MATCHED CONTENT
        # from crashing the report mid-verdict and losing the hit detail
        # (mutation-audit hole M9).
        (self.root / "scripts" / "scrub_terms.txt").write_text(
            "re:secretword.\n", encoding="utf-8")
        (self.root / "dirty.txt").write_bytes(
            "has secretword—here\n".encode("utf-8"))
        subprocess.run(["git", "add", "dirty.txt"], cwd=self.root,
                       check=True, capture_output=True)
        proc = self._run()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("dirty.txt:1", proc.stdout)
        self.assertNotIn("Traceback", proc.stderr)

    def test_utf16_secret_is_caught_at_the_real_entry(self):
        # The 2026-08-13 adversarial pass planted the same secret twice:
        # the ASCII twin was caught (rc 1) while the UTF-16 carrier was
        # skipped as binary — an exit-code consumer saw rc 1 only
        # because the twin existed. Both carriers must report.
        (self.root / "ascii.txt").write_bytes(b"has secretword inside\n")
        (self.root / "u16.txt").write_bytes(
            b"\xff\xfe" + "has secretword inside\n".encode("utf-16-le"))
        subprocess.run(["git", "add", "ascii.txt", "u16.txt"],
                       cwd=self.root, check=True, capture_output=True)
        proc = self._run()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("ascii.txt:1", proc.stdout)
        self.assertIn("u16.txt:1", proc.stdout)

    def test_total_scan_strict_refuses_on_a_partial_scan(self):
        # One skipped binary and one truncated line: strict mode refuses
        # with exit 2, names both, and the whole verdict survives the
        # machine codepage (the ASCII pin must cover the new messages).
        (self.root / "blob.bin").write_bytes(BINARY)
        (self.root / "big.txt").write_bytes(("x" * 6000 + "\n").encode())
        subprocess.run(["git", "add", "blob.bin", "big.txt"],
                       cwd=self.root, check=True, capture_output=True)
        proc = self._run(SCRUB_REQUIRE_TOTAL_SCAN="1")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("SCRUB_REQUIRE_TOTAL_SCAN", proc.stdout)
        self.assertIn("blob.bin", proc.stdout)
        self.assertIn("truncated-scan", proc.stdout)
        self.assertTrue(proc.stdout.isascii(), proc.stdout)

    def test_total_scan_zero_means_off_at_the_real_entry(self):
        (self.root / "blob.bin").write_bytes(BINARY)
        subprocess.run(["git", "add", "blob.bin"], cwd=self.root,
                       check=True, capture_output=True)
        proc = self._run(SCRUB_REQUIRE_TOTAL_SCAN="0")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class TestCommittedTerms(unittest.TestCase):
    """Pins on scripts/scrub_terms.txt as committed: the instrument is
    the pattern file plus the code that loads it, and the ReDoS route
    lived in the file (2026-08-13: a 20 KB @-less line took 2.2 s, 80 KB
    took 35.5 s — one minified tracked file degraded the gate to
    no-verdict)."""

    @classmethod
    def setUpClass(cls):
        terms = (Path(sc.__file__).resolve().parent
                 / "scrub_terms.txt").read_text(encoding="utf-8")
        cls.email = [p for p in sc.load_terms([terms])
                     if "@" in p.pattern]

    def test_exactly_one_email_pattern(self):
        # Premise check for the tests below: they time and match "the"
        # email pattern, so there must be exactly one.
        self.assertEqual(len(self.email), 1)

    def test_email_pattern_still_matches_addresses(self):
        addr = "someone" + chr(64) + "example.com"
        m = self.email[0].search(f"mail me: {addr}")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(0), addr)
        self.assertIsNotNone(self.email[0].search(addr))

    def test_email_pattern_is_linear_on_an_atless_line(self):
        # The run-start lookbehind makes an @-less token run one failed
        # attempt instead of one per offset. Pre-fix measured 9.0 s at
        # 40 KB; 1.0 s is generous margin for a slow machine, not a
        # tight bound.
        line = "a" * 40_000
        t0 = time.perf_counter()
        self.assertIsNone(self.email[0].search(line))
        self.assertLess(time.perf_counter() - t0, 1.0)

    def test_sk_key_pattern_matches_anthropic_and_openai_keys(self):
        terms = (Path(sc.__file__).resolve().parent
                 / "scrub_terms.txt").read_text(encoding="utf-8")
        sk_pats = [p for p in sc.load_terms([terms])
                   if "sk-" in p.pattern]
        self.assertEqual(len(sk_pats), 1)
        pat = sk_pats[0]
        # Dynamically constructed to avoid tripping the real tree scrub
        openai_key = "sk-" + "a" * 25
        anthropic_key = "sk-ant-api03-" + "b" * 30
        self.assertIsNotNone(pat.search(openai_key))
        self.assertIsNotNone(pat.search(anthropic_key))

    def test_expanded_secret_patterns_match_credentials(self):
        terms = (Path(sc.__file__).resolve().parent
                 / "scrub_terms.txt").read_text(encoding="utf-8")
        pats = sc.load_terms([terms])
        google_ai_pat = [p for p in pats if "AIzaSy" in p.pattern][0]
        aws_sts_pat = [p for p in pats if "ASIA" in p.pattern][0]
        gh_app_pat = [p for p in pats if "gh[ousr]" in p.pattern][0]

        # Dynamically constructed
        google_key = "AIzaSy" + "A" * 33
        aws_sts = "ASIA" + "B" * 16
        gh_token = "gho_" + "C" * 25

        self.assertIsNotNone(google_ai_pat.search(google_key))
        self.assertIsNotNone(aws_sts_pat.search(aws_sts))
        self.assertIsNotNone(gh_app_pat.search(gh_token))


class TestPublishFlowDoc(unittest.TestCase):
    def test_documented_scrub_step_is_strict(self):
        # docs/lessons-pipeline.md is the publish flow's spec; if its
        # scrub step drops the strict flags, "clean" at publish time
        # stops meaning the project-noun tier ran. Grep-level pin: it
        # cannot prove an operator exports the env, only that the
        # documented command does.
        doc = (Path(sc.__file__).resolve().parent.parent / "docs"
               / "lessons-pipeline.md").read_text(encoding="utf-8")
        self.assertIn("SCRUB_REQUIRE_LOCAL_TERMS=1", doc)
        self.assertIn("SCRUB_REQUIRE_TOTAL_SCAN=1", doc)
        self.assertIn("scrub_check.py", doc)


if __name__ == "__main__":
    unittest.main()
