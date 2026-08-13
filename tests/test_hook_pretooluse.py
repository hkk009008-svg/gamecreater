import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import hook_pretooluse as hook


class TestCommandOf(unittest.TestCase):
    def test_extracts_command(self):
        payload = '{"tool_name":"Bash","tool_input":{"command":"git push"}}'
        self.assertEqual(hook.command_of(payload), "git push")

    def test_garbage_is_empty(self):
        self.assertEqual(hook.command_of("nope"), "")
        self.assertEqual(hook.command_of('{"tool_input":{}}'), "")


class TestPushDetection(unittest.TestCase):
    def test_plain_push_matches(self):
        self.assertTrue(hook.PUSH_RE.search("git push"))
        self.assertTrue(hook.PUSH_RE.search("cd /d/x && git push origin main"))
        self.assertTrue(hook.PUSH_RE.search("git -C D:/x push"))

    def test_non_push_git_does_not(self):
        self.assertFalse(hook.PUSH_RE.search("git status"))
        self.assertFalse(hook.PUSH_RE.search("git pushd-like-nothing"))
        # push in a different chained command, not under git:
        self.assertFalse(hook.PUSH_RE.search("echo push; git status"))


class TestPushTargetDir(unittest.TestCase):
    def test_git_c_wins(self):
        self.assertEqual(hook.push_target_dir("git -C D:/repo push"),
                         "D:/repo")

    def test_last_cd_wins(self):
        cmd = "cd /d/a && ls && cd /d/b && git push"
        self.assertEqual(hook.push_target_dir(cmd), "D:/b")

    def test_msys_drive_paths_normalize_for_windows(self):
        # Git-Bash '-C /d/Unreal' must reach the preflight as 'D:/Unreal':
        # Windows Python cannot cwd into '/d/...', gh never ran, and the
        # guard fail-close blocked an authorized push (2026-08-13).
        self.assertEqual(
            hook.push_target_dir("git -C /d/Unreal push origin main"),
            "D:/Unreal")
        # non-drive POSIX paths pass through untouched
        self.assertEqual(
            hook.push_target_dir("git -C /tmp/repo push"), "/tmp/repo")

    def test_default_is_cwd(self):
        self.assertEqual(hook.push_target_dir("git push"), ".")


class TestEditorDetection(unittest.TestCase):
    def test_matches_cmd_and_editor(self):
        self.assertTrue(hook.EDITOR_RE.search(
            "D:/Engine/Binaries/Win64/UnrealEditor-Cmd.exe proj.uproject"))
        self.assertTrue(hook.EDITOR_RE.search("Start UnrealEditor.exe"))

    def test_ignores_unrelated(self):
        self.assertFalse(hook.EDITOR_RE.search("python capture.py"))


if __name__ == "__main__":
    unittest.main()
