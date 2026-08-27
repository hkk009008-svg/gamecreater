"""Regression tests for the cold-session NOW.md handoff."""

from __future__ import annotations

import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import session_start as ss  # noqa: E402


class TestNowBlock(unittest.TestCase):

    def test_current_heading_and_opaque_register_ids_are_visible(self):
        text = f"""# NOW — Test Game

**As of:** {date.today().isoformat()}.

## Next executable action

Run the focused Standalone playtest.

## Open register

### Blocks the next slice

- **KG-A2B-PLAYTEST** — human visual acceptance.
- **KG-CONTACT-1** — swept contact observer.

## Active blockers

The user must run the visual test.
"""
        with tempfile.TemporaryDirectory() as td:
            now = Path(td) / "NOW.md"
            now.write_text(text, encoding="utf-8")
            old_lines, old_warn = ss.LINES, ss.WARN
            ss.LINES, ss.WARN = [], []
            try:
                ss.now_block({"now": str(now)})
                output = "\n".join(ss.LINES)
                warnings = "\n".join(ss.WARN)
            finally:
                ss.LINES, ss.WARN = old_lines, old_warn

        self.assertIn("Next executable action:", output)
        self.assertIn("Run the focused Standalone playtest.", output)
        self.assertIn(
            "Blocks the next slice: 2 - KG-A2B-PLAYTEST, KG-CONTACT-1",
            output,
        )
        self.assertNotIn("no register items", warnings)
        self.assertNotIn("has no 'Next executable action'", warnings)
        self.assertNotIn("has no 'Active blockers'", warnings)


class TestPerBlockDegradation(unittest.TestCase):

    def test_system_exit_in_skills_probe_does_not_kill_orientation(self):
        old_lines, old_warn = ss.LINES, ss.WARN
        ss.LINES, ss.WARN = [], []
        stream = StringIO()
        try:
            with (
                patch.object(ss, "game_binding", return_value={}),
                patch.object(ss, "now_block"),
                patch.object(ss, "inbox_block"),
                patch.object(ss, "repo_block"),
                patch.object(ss, "guard_block"),
                patch.object(ss, "engine_block"),
                patch.object(ss, "skills_block", side_effect=SystemExit(3)),
                redirect_stdout(stream),
            ):
                code = ss.main()
            output = stream.getvalue()
        finally:
            ss.LINES, ss.WARN = old_lines, old_warn

        self.assertEqual(code, 0)
        self.assertIn("skills probe exited unexpectedly (3)", output)
        self.assertIn("Authorization boundary", output)

    def test_failed_block_does_not_prevent_the_next_block(self):
        reached: list[str] = []
        old_lines, old_warn = ss.LINES, ss.WARN
        ss.LINES, ss.WARN = [], []
        try:
            ss.run_block("broken", lambda: (_ for _ in ()).throw(
                RuntimeError("boom")))
            ss.run_block("next", lambda: reached.append("next"))
            warnings = "\n".join(ss.WARN)
        finally:
            ss.LINES, ss.WARN = old_lines, old_warn

        self.assertEqual(reached, ["next"])
        self.assertIn("broken probe failed (RuntimeError: boom)", warnings)

    def test_system_exit_in_now_probe_still_reaches_inbox_probe(self):
        old_lines, old_warn = ss.LINES, ss.WARN
        ss.LINES, ss.WARN = [], []
        stream = StringIO()
        try:
            with (
                patch.object(ss, "game_binding", return_value={}),
                patch.object(ss, "now_block", side_effect=SystemExit(4)),
                patch.object(ss, "inbox_block") as inbox,
                patch.object(ss, "repo_block"),
                patch.object(ss, "guard_block"),
                patch.object(ss, "engine_block"),
                patch.object(ss, "skills_block"),
                redirect_stdout(stream),
            ):
                code = ss.main()
        finally:
            ss.LINES, ss.WARN = old_lines, old_warn

        self.assertEqual(code, 0)
        inbox.assert_called_once_with({})
        self.assertIn("NOW probe exited unexpectedly (4)", stream.getvalue())


def init_repo(path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "Test.uproject").write_text("{}", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "Test.uproject"],
                   check=True)
    subprocess.run(
        ["git", "-C", str(path), "-c", "user.email=t@t",
         "-c", "user.name=t", "commit", "-q", "-m", "seed"],
        check=True,
    )


class TestRepoBlock(unittest.TestCase):

    def test_uproject_parent_and_linked_worktree_are_detected_by_git(self):
        import subprocess

        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            primary = temp / "primary repo"
            primary.mkdir()
            init_repo(primary)
            worktree = temp / "linked worktree"
            subprocess.run(
                ["git", "-C", str(primary), "worktree", "add", "-q",
                 "-b", "test-worktree", str(worktree)], check=True)
            self.assertTrue((worktree / ".git").is_file())

            old_root, old_lines, old_warn = ss.ROOT, ss.LINES, ss.WARN
            ss.ROOT = temp / "not-a-repo"
            ss.LINES, ss.WARN = [], []
            try:
                ss.repo_block({"project": str(worktree / "Test.uproject")})
                output = "\n".join(ss.LINES)
            finally:
                ss.ROOT, ss.LINES, ss.WARN = old_root, old_lines, old_warn

        self.assertIn("linked worktree@test-worktree", output)
        self.assertIn("cleanliness clean", output)
        self.assertIn("tracking UNCONFIGURED", output)
        self.assertNotIn("clean, in sync", output)

    def test_failed_tracking_comparison_is_unknown_not_in_sync(self):
        def fake_git(args: list[str], _cwd: Path) -> tuple[bool, str]:
            command = " ".join(args)
            if command == "rev-parse --is-inside-work-tree":
                return True, "true"
            if command == "rev-parse --abbrev-ref HEAD":
                return True, "main"
            if command.startswith("status "):
                return True, ""
            if "@{upstream}" in command:
                return True, "origin/main"
            if command.startswith("rev-list "):
                return False, ""
            raise AssertionError(command)

        old_lines, old_warn = ss.LINES, ss.WARN
        ss.LINES, ss.WARN = [], []
        try:
            with patch.object(ss, "git_result", side_effect=fake_git):
                ss.repo_block({})
            output = "\n".join(ss.LINES)
            warnings = "\n".join(ss.WARN)
        finally:
            ss.LINES, ss.WARN = old_lines, old_warn

        self.assertIn("cleanliness clean", output)
        self.assertIn("tracking origin/main UNKNOWN", output)
        self.assertNotIn("in sync", output)
        self.assertIn("could not be measured", warnings)


if __name__ == "__main__":
    unittest.main()
