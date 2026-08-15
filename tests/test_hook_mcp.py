"""MCP tool calls must not be invisible to the mechanized rules.

WHY (2026-08-14). scripts/hook_pretooluse.py read only
`tool_input["command"]`. An MCP tool call carries no such key, so
command_of() returned "" and main() returned 0 -- allow, unconditionally,
for every MCP tool that could ever exist. That was harmless only because
zero MCP servers were configured. Enabling Unreal's MCP server ends that,
and the blindness would have been re-discovered the expensive way.

The rule keys on the tool NAME, because an MCP payload's arguments are
server-defined and cannot be parsed generically. It is narrow on purpose:
it blocks the acts CLAUDE.md reserves to the user, and it is not a general
MCP firewall. These tests pin both halves -- that reserved names are
blocked, and that ordinary MCP calls still pass, since a guard that blocked
everything would simply be turned off.
"""

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import hook_pretooluse as hp  # noqa: E402


def payload(tool_name: str, **tool_input) -> str:
    return json.dumps({"tool_name": tool_name, "tool_input": tool_input})


def run(raw: str) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stderr(buf):
        rc = hp.dispatch_tool(hp.tool_of(raw))
    return rc, buf.getvalue()


class TestToolNameExtraction(unittest.TestCase):

    def test_reads_tool_name(self):
        self.assertEqual(hp.tool_of(payload("mcp__unreal__call_tool")),
                         "mcp__unreal__call_tool")

    def test_missing_and_malformed_are_empty_not_crashes(self):
        self.assertEqual(hp.tool_of("{}"), "")
        self.assertEqual(hp.tool_of("not json"), "")
        self.assertEqual(hp.tool_of(json.dumps({"tool_name": 7})), "")

    def test_bom_prefixed_payload_still_parses(self):
        # PowerShell 5.1 pipes prepend a UTF-8 BOM to native stdin
        # (GAME.local.md:32). command_of already strips it; so must this.
        self.assertEqual(hp.tool_of("\ufeff" + payload("mcp__x__y")),
                         "mcp__x__y")


class TestReservedActsBlocked(unittest.TestCase):

    def test_push_like_mcp_tools_are_blocked(self):
        for name in ("mcp__git__push", "mcp__github__push_files",
                     "mcp__gh__merge_pull_request",
                     "mcp__forge__set_visibility",
                     "mcp__x__publish", "mcp__x__delete_repo"):
            rc, err = run(payload(name))
            self.assertEqual(rc, 2, f"{name} should be blocked")
            self.assertIn("MCP BLOCKED", err)
            self.assertIn(name, err, "the message must name the tool")

    def test_block_message_points_at_the_authorization_rule(self):
        _, err = run(payload("mcp__git__push"))
        self.assertIn("reserves", err)
        self.assertIn("authorize", err)


class TestOrdinaryMcpStillAllowed(unittest.TestCase):
    """A guard that blocks everything gets disabled, so pin the allow path."""

    def test_unreal_and_harness_mcp_tools_pass(self):
        for name in ("mcp__unreal-mcp__list_toolsets",
                     "mcp__unreal-mcp__describe_toolset",
                     "mcp__unreal-mcp__call_tool",
                     "mcp__visualize__show_widget",
                     "mcp__ccd_session__mark_chapter"):
            rc, err = run(payload(name))
            self.assertEqual(rc, 0, f"{name} should pass: {err}")

    def test_non_mcp_tools_are_untouched_by_this_rule(self):
        for name in ("Bash", "Edit", "Monitor", ""):
            self.assertEqual(run(payload(name))[0], 0)

    def test_substring_alone_does_not_trip_it(self):
        # 'pushdown', 'republish' must not match; the rule is word-bounded
        # by underscores, not a naive substring search.
        for name in ("mcp__x__pushdown_automaton", "mcp__x__republished"):
            self.assertEqual(run(payload(name))[0], 0, name)


class TestShellRulesStillWork(unittest.TestCase):
    """The MCP rule must not have displaced the two original rules."""

    def test_git_push_command_still_reaches_the_push_guard(self):
        self.assertTrue(hp.PUSH_RE.search("git -C D:/x push origin main"))

    def test_command_of_still_reads_shell_payloads(self):
        raw = payload("Bash", command="echo hi")
        self.assertEqual(hp.command_of(raw), "echo hi")


if __name__ == "__main__":
    unittest.main()
