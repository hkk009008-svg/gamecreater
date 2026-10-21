"""Configured guard entry and shell-route wiring, without executing tool payloads.

Only the host-applicable configured commands run. On Windows that means Claude
and Codex commandWindows; the portable Codex command is checked structurally.
The sibling test_guard_posix module executes the saved portable command in Bash.
Temporary Git repositories have no remotes or hook activation. Push-looking
strings reach only the dispatcher and a mocked preflight, never a shell.
"""

from __future__ import annotations

import io
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import hook_pretooluse as hp  # noqa: E402

SAFE = json.dumps({"tool_name": "Bash", "tool_input": {
    "command": "Write-Output fixture"}})
BLOCKED = json.dumps({"tool_name": "Bash", "tool_input": {
    "command": "git push"}})


def configured_hooks() -> list[tuple[str, dict]]:
    result = []
    for label, path in (("Claude", ROOT / ".claude" / "settings.json"),
                        ("Codex", ROOT / ".codex" / "hooks.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["hooks"]["PreToolUse"]:
            for hook in entry["hooks"]:
                result.append((label, hook))
    return result


def main_payload(name: str, **tool_input) -> tuple[int, str]:
    stderr = io.StringIO()
    raw = json.dumps({"tool_name": name, "tool_input": tool_input})
    with mock.patch.object(sys, "stdin", io.StringIO(raw)), \
            redirect_stderr(stderr):
        status = hp.main()
    return status, stderr.getvalue()


class TestConfiguredGuardEntry(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="guard wiring ")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / "fixture repository"
        self.repo.mkdir()
        init = subprocess.run(
            ["git", "-c", "init.templateDir=", "init", "--quiet", str(self.repo)],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.scripts = self.repo / "scripts"
        self.scripts.mkdir()
        for source in (ROOT / "scripts").glob("*.py"):
            shutil.copy2(source, self.scripts / source.name)
        self.commands = []
        for label, hook in configured_hooks():
            key = "commandWindows" if label == "Codex" and os.name == "nt" else "command"
            self.commands.append((label, hook[key]))

    def run_configured(self, command, *, raw=SAFE, cwd=None,
                       project=None, pythonpath=None):
        env = os.environ.copy()
        for key in ("CLAUDE_PROJECT_DIR", "PYTHONPATH", "GIT_DIR", "GIT_WORK_TREE",
                    "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
            env.pop(key, None)
        if project is not None:
            env["CLAUDE_PROJECT_DIR"] = str(project)
        if pythonpath is not None:
            env["PYTHONPATH"] = str(pythonpath)
        return subprocess.run(command, shell=True, cwd=cwd or self.repo,
                              env=env, input=raw, capture_output=True,
                              text=True, timeout=20)

    def assert_status(self, result, expected):
        self.assertEqual(result.returncode, expected,
                         f"stdout={result.stdout!r}\nstderr={result.stderr!r}")

    def test_real_configured_commands_allow_and_block_payloads(self):
        for label, command in self.commands:
            for raw, expected in ((SAFE, 0), (BLOCKED, 2), ("{not-json", 2)):
                with self.subTest(entry=label, payload=raw):
                    result = self.run_configured(command, raw=raw)
                    self.assert_status(result, expected)
                    if expected == 2:
                        self.assertTrue(result.stderr, "refusal needs visible evidence")

    def test_entry_startup_faults_fail_closed(self):
        entry = self.scripts / "guard_entry.py"
        original = entry.read_bytes()
        faults = {
            "missing": None,
            "syntax": "def broken(:\n",
            "import": "import gamecreater_fixture_missing_module_94d5\n",
            "premature-exit-zero": "raise SystemExit(0)\n",
            "no-main": "main = None\n",
            "noninteger-allow": "def main():\n    return False\n",
        }
        for fault, source in faults.items():
            if source is None:
                entry.unlink()
            else:
                entry.write_text(source, encoding="utf-8")
            for label, command in self.commands:
                with self.subTest(entry=label, fault=fault):
                    self.assert_status(self.run_configured(command), 2)
            entry.write_bytes(original)

    def test_dispatcher_load_and_execution_faults_fail_closed(self):
        target = self.scripts / "hook_pretooluse.py"
        original = target.read_bytes()
        faults = {
            "missing": None,
            "syntax": "def broken(:\n",
            "import": "import gamecreater_fixture_missing_module_724d\n",
            "import-exit-zero": "raise SystemExit(0)\n",
            "main-exit-zero": "def main():\n    raise SystemExit(0)\n",
        }
        for fault, source in faults.items():
            if source is None:
                target.unlink()
            else:
                target.write_text(source, encoding="utf-8")
            for label, command in self.commands:
                with self.subTest(entry=label, fault=fault):
                    self.assert_status(self.run_configured(command), 2)
            target.write_bytes(original)

    def test_real_missing_dependency_blocks_startup(self):
        (self.scripts / "hook_shell_routes.py").unlink()
        for label, command in self.commands:
            with self.subTest(entry=label):
                self.assert_status(self.run_configured(command), 2)

    def test_stdin_reaches_adjacent_dispatcher_unchanged(self):
        (self.scripts / "hook_pretooluse.py").write_text(
            "import sys\nfrom pathlib import Path\n"
            "def main():\n"
            "    raw = sys.stdin.read()\n"
            "    Path(__file__).with_name('stdin-exact.txt').write_text(raw, encoding='utf-8')\n"
            "    return 0\n", encoding="utf-8")
        raw = ' \n{"tool_name": "Bash", "tool_input": {"command": "fixture"}}\n'
        receipt = self.scripts / "stdin-exact.txt"
        for label, command in self.commands:
            if receipt.exists():
                receipt.unlink()
            with self.subTest(entry=label):
                self.assert_status(self.run_configured(command, raw=raw), 0)
                self.assertEqual(receipt.read_text(encoding="utf-8"), raw)

    def test_nested_cwd_and_pythonpath_decoys_cannot_replace_root_guard(self):
        decoy = self.repo / "nested decoy"
        (decoy / "scripts").mkdir(parents=True)
        for parent in (decoy, decoy / "scripts"):
            for name in ("guard_entry.py", "hook_pretooluse.py"):
                (parent / name).write_text("def main():\n    return 0\n", encoding="utf-8")
        # Without interpreter isolation, a startup import can terminate with 0.
        (decoy / "pathlib.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
        for label, command in self.commands:
            for raw, expected in ((SAFE, 0), (BLOCKED, 2)):
                with self.subTest(entry=label, payload=raw):
                    self.assert_status(self.run_configured(
                        command, raw=raw, cwd=decoy, pythonpath=decoy), expected)

    def test_outside_git_is_blocked_unless_claude_has_an_explicit_valid_root(self):
        outside = self.base / "outside git"
        (outside / "scripts").mkdir(parents=True)
        for name in ("guard_entry.py", "hook_pretooluse.py"):
            (outside / "scripts" / name).write_text(
                "def main():\n    return 0\n", encoding="utf-8")
        for label, command in self.commands:
            with self.subTest(entry=label, context="unset"):
                self.assert_status(self.run_configured(command, cwd=outside), 2)
            with self.subTest(entry=label, context="explicit-valid"):
                result = self.run_configured(command, cwd=outside, project=self.repo)
                self.assert_status(result, 0 if label == "Claude" else 2)
            with self.subTest(entry=label, context="explicit-missing"):
                result = self.run_configured(command, cwd=outside,
                                             project=self.base / "missing root")
                self.assert_status(result, 2)

    def test_every_configured_shell_matcher_and_command_has_the_contract(self):
        for path in (ROOT / ".claude" / "settings.json", ROOT / ".codex" / "hooks.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            matchers = [entry["matcher"] for entry in data["hooks"]["PreToolUse"]]
            for name in ("Bash", "PowerShell", "Monitor", "exec_command",
                         "mcp__terminal__run_in_terminal"):
                with self.subTest(config=path.name, tool=name):
                    self.assertTrue(any(re.fullmatch(pattern, name) for pattern in matchers))
        for label, hook in configured_hooks():
            for key in ("command", "commandWindows"):
                if key not in hook:
                    continue
                with self.subTest(entry=label, command=key):
                    command = hook[key]
                    self.assertRegex(command, r"(?:^|\s)-I(?:\s|$)")
                    self.assertIn("guard_entry.py", command)
                    self.assertIn("BaseException", command)

    def test_host_timeout_exceeds_declared_nested_subprocess_waits(self):
        # This is a configured budget check, not a wall-clock/host guarantee.
        waits = []
        for name in ("preflight_push.py", "gitignored_config.py"):
            tree = ast.parse((ROOT / "scripts" / name).read_text(encoding="utf-8"))
            declared = [keyword.value.value for node in ast.walk(tree)
                        if isinstance(node, ast.Call) for keyword in node.keywords
                        if keyword.arg == "timeout" and isinstance(keyword.value, ast.Constant)
                        and isinstance(keyword.value.value, (int, float))]
            self.assertTrue(declared, f"{name}: declared CLI waits must be inspected")
            waits.extend(declared)
        self.assertTrue(waits, "the preflight's declared CLI waits must be inspected")
        for label, hook in configured_hooks():
            commands = [hook[key] for key in ("command", "commandWindows") if key in hook]
            root_waits = [int(value) for command in commands
                          for value in re.findall(r"timeout=(\d+)", command)]
            self.assertTrue(root_waits, f"{label}: no root-discovery bound captured")
            budget = sum(waits) + max(root_waits) + 10
            self.assertGreaterEqual(hook.get("timeout", 0), budget,
                                    f"{label}: host may terminate before guard refuses")
        agents = json.loads((ROOT / ".agents" / "hooks.json").read_text(encoding="utf-8"))
        for entry in agents["gamecreater-guards"]["PreToolUse"]:
            for hook in entry["hooks"]:
                self.assertGreaterEqual(hook.get("timeout", 0), sum(waits) + 10)


class TestShellRouteCallsites(unittest.TestCase):
    CONTRACTS = (("exec_command", "cmd", "workdir"),
                 ("mcp__terminal__run_in_terminal", "command", "cwd"))

    def test_exact_command_and_workdir_reach_dispatch(self):
        command = 'Write-Output "fixture with spaces"'
        for name, field, context in self.CONTRACTS:
            for workdir in (None, "fixture-shell-workdir"):
                tool_input = {field: command, context: workdir}
                with self.subTest(tool=name, workdir=workdir), \
                        mock.patch.object(hp, "dispatch", return_value=0) as dispatch:
                    status, stderr = main_payload(name, **tool_input)
                    self.assertEqual(status, 0, stderr)
                    if workdir is None:
                        dispatch.assert_called_once_with(command)
                    else:
                        dispatch.assert_called_once_with(
                            command, cwd=str((Path.cwd() / workdir).resolve()))

    def test_real_push_dispatch_receives_actual_tool_repository_and_remote(self):
        for name, field, context in self.CONTRACTS:
            for suffix, relative in (("", "."), ("-C nested ", "nested")):
                tool_input = {field: f"git {suffix}push origin main",
                              context: "fixture-shell-workdir"}
                expected = str((Path.cwd() / "fixture-shell-workdir" / relative).resolve())
                for verdict in (0, 1):
                    with self.subTest(tool=name, command=tool_input[field], verdict=verdict), \
                            mock.patch.object(hp.preflight_push, "main", return_value=verdict) as preflight, \
                            mock.patch.object(subprocess, "run", side_effect=AssertionError("payload executed")):
                        status, stderr = main_payload(name, **tool_input)
                        self.assertEqual(status, 0 if verdict == 0 else 2, stderr)
                        preflight.assert_called_once_with(["preflight_push", expected, "origin"])

    def test_default_workdir_still_reaches_the_real_preflight(self):
        for name, field, _ in self.CONTRACTS:
            with self.subTest(tool=name), \
                    mock.patch.object(hp.preflight_push, "main", return_value=0) as preflight:
                status, stderr = main_payload(name, **{field: "git push origin main"})
                self.assertEqual(status, 0, stderr)
                preflight.assert_called_once_with(["preflight_push", ".", "origin"])

    def test_conflicting_context_aliases_and_invalid_paths_fail_closed(self):
        for name, field, context in self.CONTRACTS:
            other = "cwd" if context == "workdir" else "workdir"
            cases = ({context: ".", other: "."}, {other: "."},
                     {"working_directory": "."}, {"workingDirectory": "."},
                     {context: ""}, {context: 7}, {context: "bad\x00path"},
                     {context: "C:"}, {context: "C:relative"},
                     {context: "\\\\server\\share"}, {context: "//server/share"})
            for extra in cases:
                with self.subTest(tool=name, extra=extra), \
                        mock.patch.object(hp, "dispatch") as dispatch:
                    status, stderr = main_payload(name, **{field: "git push origin main", **extra})
                    self.assertEqual(status, 2, stderr)
                    dispatch.assert_not_called()

    def test_drive_relative_git_selector_is_refused_before_preflight(self):
        for name, field, context in self.CONTRACTS:
            for selector in ("C:", "C:relative"):
                for workdir in (None, "fixture-shell-workdir"):
                    with self.subTest(tool=name, selector=selector, workdir=workdir), \
                            mock.patch.object(hp.preflight_push, "main") as preflight:
                        status, stderr = main_payload(name, **{
                            field: f'git -C "{selector}" push origin main',
                            context: workdir})
                        self.assertEqual(status, 2, stderr)
                        self.assertIn("drive-relative", stderr)
                        preflight.assert_not_called()

    def test_name_policy_refusal_precedes_command_dispatch(self):
        name = "mcp__terminal__run_in_terminal"
        with mock.patch.object(hp, "dispatch_tool", return_value=2) as policy, \
                mock.patch.object(hp, "dispatch") as dispatch:
            status, _ = main_payload(name, command="git push origin main")
            self.assertEqual(status, 2)
            policy.assert_called_once_with(name)
            dispatch.assert_not_called()

    def test_ordinary_mcp_command_fields_remain_opaque(self):
        with mock.patch.object(hp, "dispatch") as dispatch:
            status, stderr = main_payload("mcp__example__read", command="git push origin main")
            self.assertEqual(status, 0, stderr)
            dispatch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
