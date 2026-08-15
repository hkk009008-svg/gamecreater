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
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / ".claude" / "settings.json"

# Every tool in this harness that can execute a shell command string.
REQUIRED = ("Bash", "PowerShell", "Monitor")


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
                self.assertIn("run_pretooluse", h.get("command", ""),
                              "the matcher must route to the dispatcher")


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


if __name__ == "__main__":
    unittest.main()
