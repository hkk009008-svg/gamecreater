"""The lessons inbox is append-only, and the mechanisms that enforce it.

Two mechanisms, two failure modes:
- `check_lessons_inbox.append_only_verdict` DETECTS a rewrite after the
  fact, against the inbox's committed HEAD. Its own trap is newline
  normalization: this repo's git converts LF to CRLF on touch, so a naive
  byte compare would score every checkout as a violation.
- `hook_pretooluse.INBOX_TRUNCATE_RE` PREVENTS the one shell shape that
  loses everything at once: a truncating redirect or cmdlet aimed at
  LESSONS.md. `>>` must stay legal or the inbox cannot do its job.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_lessons_inbox as cli  # noqa: E402
import hook_pretooluse as hook  # noqa: E402


def make_repo(tmp: Path, content: str) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp)], check=True)
    inbox = tmp / "LESSONS.md"
    inbox.write_text(content, encoding="utf-8")
    env_ok = subprocess.run(
        ["git", "-C", str(tmp), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--no-verify", "-am", "seed"],
        capture_output=True)
    if env_ok.returncode != 0:
        subprocess.run(["git", "-C", str(tmp), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(tmp), "-c", "user.email=t@t",
             "-c", "user.name=t", "commit", "-q", "--no-verify",
             "-m", "seed"], check=True)
    return inbox


SEED = ("# inbox\n"
        "- 2026-08-01 — first lesson, paid for.\n"
        "- 2026-08-02 — second lesson.\n")


class TestAppendOnlyDetector(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.inbox = make_repo(self.root, SEED)

    def tearDown(self):
        self._tmp.cleanup()

    def verdict(self):
        return cli.check_one(self.root, self.inbox)

    def test_pure_append_is_ok_and_counts_new_entries(self):
        self.inbox.write_text(SEED + "- 2026-08-15 — third.\n",
                              encoding="utf-8")
        verdict, detail, n = self.verdict()
        self.assertEqual(verdict, "OK")
        self.assertIn("+1 entry", detail)
        self.assertEqual(n, 3)

    def test_editing_a_committed_lesson_is_a_violation_naming_the_line(self):
        self.inbox.write_text(SEED.replace("first lesson", "REWRITTEN"),
                              encoding="utf-8")
        verdict, detail, _ = self.verdict()
        self.assertEqual(verdict, "VIOLATION")
        self.assertIn("line 2", detail)

    def test_deleting_the_tail_is_a_violation_not_a_short_ok(self):
        self.inbox.write_text(SEED.rsplit("- 2026-08-02", 1)[0],
                              encoding="utf-8")
        verdict, detail, _ = self.verdict()
        self.assertEqual(verdict, "VIOLATION")
        self.assertIn("SHORTER", detail)

    def test_crlf_conversion_alone_is_not_a_violation(self):
        # The repo's own gitattributes behavior: same text, CRLF on disk.
        self.inbox.write_bytes(
            (SEED + "- 2026-08-15 — third.\n")
            .replace("\n", "\r\n").encode("utf-8"))
        verdict, _, _ = self.verdict()
        self.assertEqual(verdict, "OK")

    def test_uncommitted_inbox_reports_no_baseline_not_violation(self):
        fresh = self.root / "NEW_LESSONS.md"
        fresh.write_text("- 2026-08-15 — unborn inbox.\n", encoding="utf-8")
        verdict, _, _ = cli.check_one(self.root, fresh)
        self.assertEqual(verdict, "NO_BASELINE")

    def test_identical_file_is_ok_with_zero_added(self):
        verdict, detail, _ = self.verdict()
        self.assertEqual(verdict, "OK")
        self.assertIn("+0", detail)


class TestTruncationGuard(unittest.TestCase):
    """dispatch() returns 2 (block) or 0 (allow); the regex is the rule."""

    BLOCKED = [
        'echo oops > memory/LESSONS.md',
        'python x.py > D:/Unreal/game/kurogane/LESSONS.md',
        'Set-Content memory/LESSONS.md "gone"',
        'Get-Content a.md | Out-File memory/LESSONS.md',
        'run | tee memory/LESSONS.md',
        'cmd 2> memory/LESSONS.md',
    ]
    ALLOWED = [
        'cat >> memory/LESSONS.md <<EOF\n- lesson\nEOF',
        'echo more >> D:/Unreal/game/kurogane/LESSONS.md',
        'run | tee -a memory/LESSONS.md',
        'Get-Content a.md | Out-File -Append memory/LESSONS.md',
        'echo fine > other/NOTES.md',
        'git log --oneline -- memory/LESSONS.md',
        'grep -n lesson memory/LESSONS.md',
    ]

    def test_truncating_shapes_are_blocked(self):
        for cmd in self.BLOCKED:
            with self.subTest(cmd=cmd):
                self.assertEqual(hook.dispatch(cmd), 2, cmd)

    def test_appends_and_reads_stay_legal(self):
        for cmd in self.ALLOWED:
            with self.subTest(cmd=cmd):
                self.assertEqual(hook.dispatch(cmd), 0, cmd)


if __name__ == "__main__":
    unittest.main()
