import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from gitignored_config import resolve_gitignored


def _git_env():
    email = "test" + chr(64) + "users.noreply.github.com"
    env = {**os.environ,
           "GIT_AUTHOR_NAME": "test",
           "GIT_AUTHOR_EMAIL": email,
           "GIT_COMMITTER_NAME": "test",
           "GIT_COMMITTER_EMAIL": email}
    return env


class TestResolveGitignored(unittest.TestCase):
    def test_present_file_is_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "public-grant.txt"
            path.write_text("me/repo\n", encoding="utf-8")
            self.assertEqual(resolve_gitignored(path), path)

    def test_absent_without_git_stays_absent(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "public-grant.txt"
            self.assertEqual(resolve_gitignored(path, cwd=Path(td)), path)
            self.assertFalse(path.is_file())

    def test_worktree_falls_back_to_primary(self):
        env = _git_env()
        with tempfile.TemporaryDirectory() as td:
            primary = Path(td) / "primary"
            primary.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=primary, check=True,
                           capture_output=True, env=env)
            (primary / "README").write_text("x\n", encoding="utf-8")
            subprocess.run(["git", "add", "README"], cwd=primary, check=True,
                           capture_output=True, env=env)
            subprocess.run(["git", "commit", "-qm", "i"], cwd=primary,
                           check=True, capture_output=True, env=env)
            grant = primary / "public-grant.txt"
            grant.write_text("me/repo\n", encoding="utf-8")
            wt = Path(td) / "wt"
            subprocess.run(["git", "worktree", "add", "-q", str(wt), "HEAD"],
                           cwd=primary, check=True, capture_output=True,
                           env=env)
            missing = wt / "public-grant.txt"
            self.assertFalse(missing.is_file())
            resolved = resolve_gitignored(missing, cwd=wt)
            self.assertEqual(resolved.resolve(), grant.resolve())
            self.assertTrue(resolved.is_file())

    def test_worktree_local_copy_wins_over_primary(self):
        env = _git_env()
        with tempfile.TemporaryDirectory() as td:
            primary = Path(td) / "primary"
            primary.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=primary, check=True,
                           capture_output=True, env=env)
            (primary / "README").write_text("x\n", encoding="utf-8")
            subprocess.run(["git", "add", "README"], cwd=primary, check=True,
                           capture_output=True, env=env)
            subprocess.run(["git", "commit", "-qm", "i"], cwd=primary,
                           check=True, capture_output=True, env=env)
            (primary / "public-grant.txt").write_text("primary/repo\n",
                                                     encoding="utf-8")
            wt = Path(td) / "wt"
            subprocess.run(["git", "worktree", "add", "-q", str(wt), "HEAD"],
                           cwd=primary, check=True, capture_output=True,
                           env=env)
            local = wt / "public-grant.txt"
            local.write_text("worktree/repo\n", encoding="utf-8")
            resolved = resolve_gitignored(local, cwd=wt)
            self.assertEqual(resolved.resolve(), local.resolve())
            self.assertEqual(resolved.read_text(encoding="utf-8"),
                             "worktree/repo\n")


if __name__ == "__main__":
    unittest.main()
