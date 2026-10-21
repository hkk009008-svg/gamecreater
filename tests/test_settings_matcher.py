"""The PreToolUse matcher must name every tool that runs a shell command.

WHY THIS TEST EXISTS (2026-08-14, measured, not theorised).

The matcher read `Bash|PowerShell`. The identical command

    git -C C:/nonexistent-repo-xyz push origin main

was BLOCKED through Bash and EXECUTED through Monitor -- git ran and
answered `fatal: cannot change to 'C:/nonexistent-repo-xyz'`, which is git
speaking, not the guard. Both mechanized rules were therefore bypassable by
choosing a different tool, and nothing in the repo would have noticed.

The matcher is an ALLOWLIST OF TOOL NAMES, not a description of behaviour.
That is the whole hazard: a newly added command-running tool is unguarded by
default and silently so. This test is the tripwire -- when a tool is added to
the harness that can execute a shell string, it must be added to REQUIRED
here and to the matcher, and the two are checked against each other.

It is a config test, not a unit test, because the defect lived in config.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / ".claude" / "settings.json"
CODEX_HOOKS = ROOT / ".codex" / "hooks.json"
sys.path.insert(0, str(ROOT / "scripts"))
import hook_antigravity_pretooluse as antigravity_hook  # noqa: E402

# Every tool in this harness that can execute a shell command string.
REQUIRED = ("Bash", "PowerShell", "Monitor", "exec_command")


def matchers() -> list[str]:
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    out = []
    for entry in data.get("hooks", {}).get("PreToolUse", []):
        m = entry.get("matcher")
        if isinstance(m, str):
            out.append(m)
    return out


class TestPreToolUseMatcher(unittest.TestCase):

    def test_settings_file_exists_and_wires_pretooluse(self):
        self.assertTrue(SETTINGS.is_file(), f"missing {SETTINGS}")
        self.assertTrue(matchers(), "no PreToolUse matcher configured at all")

    def test_every_command_running_tool_is_matched(self):
        names = set()
        for m in matchers():
            names.update(part.strip() for part in m.split("|"))
        for tool in REQUIRED:
            self.assertIn(
                tool, names,
                f"{tool} runs shell commands but is not in the PreToolUse "
                f"matcher, so the push and editor guards do not see it. "
                f"Measured bypass 2026-08-14: a push blocked through Bash "
                f"executed through Monitor.")

    def test_hook_command_is_wired_for_each_matcher(self):
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
        for entry in data.get("hooks", {}).get("PreToolUse", []):
            hooks = entry.get("hooks") or []
            self.assertTrue(
                hooks, f"matcher {entry.get('matcher')!r} has no hook command")
            for h in hooks:
                self.assertEqual(h.get("type"), "command")
                self.assertIn("guard_entry.py", h.get("command", ""),
                              "the matcher must route through the fail-closed entry")


class TestCodexHooks(unittest.TestCase):
    def test_session_start_and_guard_reuse_repository_scripts(self):
        self.assertTrue(CODEX_HOOKS.is_file(), f"missing {CODEX_HOOKS}")
        data = json.loads(CODEX_HOOKS.read_text(encoding="utf-8"))
        hooks = data.get("hooks", {})
        start = hooks.get("SessionStart") or []
        pre = hooks.get("PreToolUse") or []
        self.assertTrue(start, "Codex sessions are not loading current game state")
        self.assertTrue(pre, "Codex tool calls are not reaching safety guards")
        pre_matchers = "|".join(str(e.get("matcher") or "") for e in pre)
        self.assertIn("Bash", pre_matchers)
        self.assertIn("mcp__.*", pre_matchers)
        start_commands = "\n".join(
            str(h.get("commandWindows") or h.get("command") or "")
            for entry in start for h in (entry.get("hooks") or []))
        pre_commands = "\n".join(
            str(h.get("commandWindows") or h.get("command") or "")
            for entry in pre for h in (entry.get("hooks") or []))
        self.assertIn("session_start.py", start_commands)
        self.assertIn("guard_entry.py", pre_commands)
        self.assertIn("git", start_commands.lower(),
                      "hook must resolve this checkout, not assume one path")
        self.assertIn("git", pre_commands.lower(),
                      "hook must resolve this checkout, not assume one path")

    @unittest.skipUnless(os.name == "nt", "commandWindows is a Windows entry")
    def test_windows_session_command_runs_at_real_entry(self):
        data = json.loads(CODEX_HOOKS.read_text(encoding="utf-8"))
        command = data["hooks"]["SessionStart"][0]["hooks"][0][
            "commandWindows"]
        result = subprocess.run(
            command,
            cwd=ROOT,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SESSION ORIENTATION", result.stdout)

    @unittest.skipUnless(os.name == "nt", "commandWindows is a Windows entry")
    def test_windows_guard_command_fails_closed_on_schema_drift(self):
        data = json.loads(CODEX_HOOKS.read_text(encoding="utf-8"))
        command = data["hooks"]["PreToolUse"][0]["hooks"][0][
            "commandWindows"]
        payloads = (
            "{not-json",
            json.dumps({"tool_name": "Bash", "tool_input": {}}),
            json.dumps([]),
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                result = subprocess.run(
                    command, cwd=ROOT, shell=True, input=payload,
                    capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 2,
                                 result.stdout + result.stderr)
                self.assertIn("failed closed", result.stderr)


class TestAntigravityShimPresent(unittest.TestCase):
    """The Antigravity guard failed open for 13 tool calls on 2026-08-14.

    .agents/hooks.json declares `python scripts/hook_antigravity_pretooluse.py`
    and Antigravity resolves it against .agents/, so it looked for
    .agents/scripts/... and got [Errno 2]. It logged the error and let the
    call through. The shim lives at the path it actually looks for.
    """

    def test_shim_exists_where_antigravity_looks(self):
        hooks = ROOT / ".agents" / "hooks.json"
        self.assertTrue(hooks.is_file(), f"missing {hooks}")
        data = json.loads(hooks.read_text(encoding="utf-8"))
        cmds = [
            h.get("command", "")
            for group in data.values()
            for entry in group.get("PreToolUse", [])
            for h in (entry.get("hooks") or [])
        ]
        self.assertTrue(cmds, "no Antigravity PreToolUse hook configured")
        for cmd in cmds:
            # the trailing token is the script path as Antigravity sees it
            rel = cmd.split()[-1].strip('"')
            resolved = (hooks.parent / rel).resolve()
            self.assertTrue(
                resolved.is_file(),
                f"Antigravity resolves {rel!r} against {hooks.parent} -> "
                f"{resolved}, which does not exist. That is exactly the "
                f"[Errno 2] that left the guard failing open.")

    def test_shim_real_entry_allows_safe_command_and_denies_schema_drift(self):
        shim = ROOT / ".agents" / "scripts" / "hook_antigravity_pretooluse.py"
        safe = subprocess.run(
            [sys.executable, str(shim)], cwd=ROOT,
            input=json.dumps({"toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "Write-Output safe"},
            }}), capture_output=True, text=True, timeout=10)
        self.assertEqual(safe.returncode, 0, safe.stderr)
        self.assertEqual(json.loads(safe.stdout), {"decision": "allow"})

        malformed = subprocess.run(
            [sys.executable, str(shim)], cwd=ROOT, input="{not-json",
            capture_output=True, text=True, timeout=10)
        self.assertEqual(malformed.returncode, 0, malformed.stderr)
        decision = json.loads(malformed.stdout)
        self.assertEqual(decision["decision"], "deny")
        self.assertIn("failed closed", decision["reason"])


class TestAntigravityAdapter(unittest.TestCase):
    def run_adapter(self, payload: str, dispatch_result=0,
                    dispatch_error: Exception | None = None) -> dict:
        def dispatch(_command: str) -> int:
            if dispatch_error is not None:
                raise dispatch_error
            return dispatch_result

        stdout = StringIO()
        with mock.patch.object(sys, "stdin", StringIO(payload)), \
             mock.patch.object(antigravity_hook.hook_pretooluse,
                               "dispatch", side_effect=dispatch), \
             redirect_stdout(stdout):
            self.assertEqual(antigravity_hook.main(), 0)
        return json.loads(stdout.getvalue())

    def test_known_good_bom_payload_is_dispatched(self):
        payload = "\ufeff" + json.dumps({
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "Write-Output safe"},
            },
        })
        self.assertEqual(self.run_adapter(payload), {"decision": "allow"})

    def test_malformed_or_missing_command_fails_closed(self):
        payloads = (
            "{not-json",
            "[]",
            json.dumps({}),
            json.dumps({"toolCall": {"name": "run_command", "args": {}}}),
            json.dumps({"toolCall": {
                "name": "run_command", "args": {"CommandLine": "   "}}}),
            json.dumps({"toolCall": {
                "name": "other", "args": {"CommandLine": "echo bypass"}}}),
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                result = self.run_adapter(payload)
                self.assertEqual(result["decision"], "deny")
                self.assertIn("failed closed", result["reason"])

    def test_dispatcher_block_and_exception_both_deny(self):
        payload = json.dumps({
            "toolCall": {
                "name": "run_command",
                "args": {"command": "git push origin main"},
            },
        })
        self.assertEqual(self.run_adapter(payload, dispatch_result=2)["decision"],
                         "deny")
        failed = self.run_adapter(payload, dispatch_error=RuntimeError("boom"))
        self.assertEqual(failed["decision"], "deny")
        self.assertIn("RuntimeError: boom", failed["reason"])


if __name__ == "__main__":
    unittest.main()
