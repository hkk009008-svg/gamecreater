import io
import json
import os
import shutil
import subprocess
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import hook_pretooluse as hook

ROOT = Path(__file__).resolve().parent.parent


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
        self.assertTrue(hook.PUSH_RE.search("git.exe push origin main"))
        self.assertTrue(hook.PUSH_RE.search("git --no-pager push"))
        self.assertTrue(hook.PUSH_RE.search('git -C "/path with spaces" push'))

    def test_non_push_git_does_not(self):
        self.assertFalse(hook.PUSH_RE.search("git status"))
        self.assertFalse(hook.PUSH_RE.search("git pushd-like-nothing"))
        self.assertFalse(hook.PUSH_RE.search("echo push; git status"))
        self.assertFalse(hook.PUSH_RE.search("git stash push -m wip"))
        self.assertFalse(hook.PUSH_RE.search('git commit -m "ready to push"'))
        self.assertFalse(hook.PUSH_RE.search("git log --grep=push"))


class TestPushTargetDir(unittest.TestCase):
    def test_git_c_wins(self):
        self.assertEqual(hook.push_target_dir("git -C D:/repo push"),
                         "D:/repo")

    def test_last_cd_wins(self):
        cmd = "cd /d/a && ls && cd /d/b && git push"
        self.assertEqual(hook.push_target_dir(cmd), "D:/b")

    def test_msys_drive_paths_normalize_for_windows(self):
        # Git-Bash '-C /d/somerepo' must reach the preflight as
        # 'D:/somerepo': Windows Python cannot cwd into '/d/...', gh never
        # ran, and the guard fail-close blocked an authorized push
        # (2026-08-13).
        self.assertEqual(
            hook.push_target_dir("git -C /d/somerepo push origin main"),
            "D:/somerepo")
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


class TestDispatch(unittest.TestCase):
    """The consumer is hook.main() over stdin, with reasons on stderr.

    Tests that only drive PUSH_RE / push_target_dir never prove the
    dispatcher calls the guards, copies their verdict to stderr, or
    fail-closes on a crash (Trap 1 / 2026-08-13 wiring class).
    """

    def _run(self, command: str) -> tuple[int, str]:
        payload = json.dumps({"tool_name": "Bash",
                              "tool_input": {"command": command}})
        err = io.StringIO()
        with patch.object(sys, "stdin", io.StringIO(payload)), \
                redirect_stderr(err):
            rc = hook.main()
        return rc, err.getvalue()

    def test_push_block_reason_is_on_stderr(self):
        def fake(argv):
            print("PUSH BLOCKED: me/repo is PUBLIC")
            return 1

        with patch.object(hook.preflight_push, "main", side_effect=fake):
            rc, err = self._run("git push")
        self.assertEqual(rc, 2)
        self.assertIn("PUSH BLOCKED", err)
        self.assertIn("PUBLIC", err)

    def test_msys_path_reaches_preflight_on_the_allow_path(self):
        seen = []

        def fake(argv):
            seen.append(argv)
            print("push allowed: me/repo is PRIVATE")
            return 0

        with patch.object(hook.preflight_push, "main", side_effect=fake):
            rc, err = self._run("git -C /d/somerepo push origin main")
        self.assertEqual(rc, 0)
        self.assertEqual(seen, [["preflight_push", "D:/somerepo"]])
        self.assertIn("PRIVATE", err)

    def test_stash_push_does_not_invoke_preflight(self):
        with patch.object(hook.preflight_push, "main") as mocked:
            rc, _ = self._run("git stash push -m wip")
        mocked.assert_not_called()
        self.assertEqual(rc, 0)

    def test_commit_message_containing_push_does_not_invoke_preflight(self):
        with patch.object(hook.preflight_push, "main") as mocked:
            rc, _ = self._run('git commit -m "ready to push"')
        mocked.assert_not_called()
        self.assertEqual(rc, 0)

    def test_preflight_exception_fails_closed(self):
        with patch.object(hook.preflight_push, "main",
                          side_effect=OSError("gh missing")):
            rc, err = self._run("git push origin main")
        self.assertEqual(rc, 2)
        self.assertIn("failed closed", err)

    def test_editor_block_reason_is_on_stderr(self):
        def fake(argv):
            print("LAUNCH BLOCKED: editor process(es) running: UnrealEditor.exe")
            return 1

        with patch.object(hook.check_editor_clear, "main", side_effect=fake):
            rc, err = self._run("UnrealEditor-Cmd.exe proj.uproject")
        self.assertEqual(rc, 2)
        self.assertIn("LAUNCH BLOCKED", err)
        self.assertIn("UnrealEditor.exe", err)

    def test_unrelated_command_does_not_invoke_guards(self):
        with patch.object(hook.preflight_push, "main") as push, \
                patch.object(hook.check_editor_clear, "main") as editor:
            rc, _ = self._run("echo hello")
        push.assert_not_called()
        editor.assert_not_called()
        self.assertEqual(rc, 0)


class TestHookWiring(unittest.TestCase):
    def test_settings_invokes_the_posix_wrapper(self):
        settings = json.loads(
            (ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        cmd = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        self.assertIn("run_pretooluse.sh", cmd)
        self.assertNotIn("hook_pretooluse.py", cmd)

    def test_wrapper_execs_and_does_not_or_chain_interpreters(self):
        text = (ROOT / "scripts" / "run_pretooluse.sh").read_text(
            encoding="utf-8")
        self.assertIn("exec", text)
        self.assertNotIn("||", text)

    def test_wrapper_allow_path_at_real_entry(self):
        payload = json.dumps({"tool_input": {"command": "echo hi"}})
        proc = subprocess.run(
            ["sh", str(ROOT / "scripts" / "run_pretooluse.sh")],
            input=payload, capture_output=True, text=True,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT)})
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_wrapper_fails_closed_without_python(self):
        payload = json.dumps({"tool_input": {"command": "git push"}})
        sh_bin = shutil.which("sh")
        self.assertIsNotNone(sh_bin)
        proc = subprocess.run(
            [sh_bin, str(ROOT / "scripts" / "run_pretooluse.sh")],
            input=payload, capture_output=True, text=True,
            env={**os.environ, "PATH": "/no-such-bin",
                 "CLAUDE_PROJECT_DIR": str(ROOT)})
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("failed closed", proc.stderr)


if __name__ == "__main__":
    unittest.main()
