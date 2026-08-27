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
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_lessons_inbox as cli  # noqa: E402
import hook_pretooluse as hook  # noqa: E402
from game_config import GameConfig  # noqa: E402


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


class TestGameInboxDiscovery(unittest.TestCase):

    def test_configured_path_with_spaces_is_discovered(self):
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            harness = temp / "harness worktree"
            harness.mkdir()
            game = temp / "game repo"
            game.mkdir()
            subprocess.run(["git", "init", "-q", str(game)], check=True)
            inbox = game / "game docs" / "LESSONS.md"
            inbox.parent.mkdir()
            inbox.write_text(SEED, encoding="utf-8")
            config = harness / "GAME.local.md"
            config.write_text(
                f"- Lessons inbox: `{inbox}`\n", encoding="utf-8")

            with patch.object(cli, "ROOT", harness):
                result = cli.game_inbox()

        self.assertEqual(result.status, "OK")
        self.assertEqual(result.repo_root, game)
        self.assertEqual(result.inbox, inbox)

    def test_loader_result_from_primary_checkout_is_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            worktree = temp / "linked worktree"
            worktree.mkdir()
            primary = temp / "primary checkout"
            primary.mkdir()
            config = primary / "GAME.local.md"
            config.write_text("local", encoding="utf-8")
            inbox = primary / "LESSONS.md"
            inbox.write_text(SEED, encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(primary)], check=True)
            loaded = GameConfig(source=config, lessons=inbox)

            with (
                patch.object(cli, "ROOT", worktree),
                patch.object(cli, "load_game_config", return_value=loaded) as load,
            ):
                result = cli.game_inbox()

        load.assert_called_once_with(worktree / "GAME.local.md")
        self.assertEqual(result.status, "OK")
        self.assertIn(str(config), result.detail)

    def test_unconfigured_missing_and_error_are_distinct(self):
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            absent_config = temp / "absent" / "GAME.local.md"
            cases = [
                (GameConfig(source=absent_config), "UNCONFIGURED"),
                (GameConfig(source=temp / "GAME.local.md",
                            lessons=temp / "missing LESSONS.md"), "MISSING"),
            ]
            (temp / "GAME.local.md").write_text("local", encoding="utf-8")
            for configured, expected in cases:
                with self.subTest(expected=expected), patch.object(
                        cli, "load_game_config", return_value=configured):
                    self.assertEqual(cli.game_inbox().status, expected)

            not_repo = temp / "outside repo" / "LESSONS.md"
            not_repo.parent.mkdir()
            not_repo.write_text(SEED, encoding="utf-8")
            configured = GameConfig(
                source=temp / "GAME.local.md", lessons=not_repo)
            with patch.object(cli, "load_game_config", return_value=configured):
                self.assertEqual(cli.game_inbox().status, "ERROR")

    def test_default_main_reports_unconfigured_game_and_fails_visible(self):
        discovery = cli.InboxDiscovery("UNCONFIGURED", "no game binding")
        stream = StringIO()
        with (
            patch.object(cli, "game_inbox", return_value=discovery),
            patch.object(cli, "check_one", return_value=("OK", "+0 entries", 0)),
            redirect_stdout(stream),
        ):
            code = cli.main(["check_lessons_inbox.py"])

        self.assertEqual(code, 1)
        self.assertIn("game: UNCONFIGURED (no game binding)", stream.getvalue())


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
