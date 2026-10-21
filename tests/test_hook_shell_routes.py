"""Payload contract tests; all shell-looking values are inert fixture strings.

These tests exercise the adapter itself. Integration tests in test_hook_mcp
must separately pin the caller, name-policy order and command-guard arguments.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import hook_shell_routes as routes  # noqa: E402


# Independent contracts: removing a production route must break a positive test.
CONTRACTS = (
    ("Bash", "command"),
    ("PowerShell", "command"),
    ("Monitor", "command"),
    ("exec_command", "cmd"),
    ("mcp__terminal__run_in_terminal", "command"),
)


class TestKnownShellRoutes(unittest.TestCase):
    def test_each_supported_route_returns_the_actual_command(self):
        command = 'git -C "D:/Fixture Repository" push origin main'
        for name, field in CONTRACTS:
            with self.subTest(name=name):
                self.assertEqual(
                    routes.extract_shell_command(name, {field: command}),
                    command)

    def test_allow_path_preserves_whitespace_quotes_and_unicode(self):
        command = '  Write-Output "fixture 한글"\r\n'
        for name, field in CONTRACTS:
            with self.subTest(name=name):
                self.assertEqual(
                    routes.extract_shell_command(name, {field: command}),
                    command)

    def test_known_route_requires_an_object(self):
        for name, _ in CONTRACTS:
            for value in (None, "git push origin main", [], 7, True):
                with self.subTest(name=name, value=value):
                    with self.assertRaisesRegex(ValueError, "tool_input object"):
                        routes.extract_shell_command(name, value)

    def test_missing_renamed_or_nested_commands_are_refused(self):
        for name, field in CONTRACTS:
            for value in ({}, {"script": "git push origin main"},
                          {"args": {field: "git push origin main"}}):
                with self.subTest(name=name, value=value):
                    with self.assertRaisesRegex(ValueError, f"{field} string"):
                        routes.extract_shell_command(name, value)

    def test_blank_or_nonstring_command_is_refused(self):
        for name, field in CONTRACTS:
            for value in (None, "", " \t\r\n", "\u2000", 7, True, [], {}):
                with self.subTest(name=name, value=value):
                    with self.assertRaisesRegex(ValueError, f"{field} string"):
                        routes.extract_shell_command(name, {field: value})

    def test_other_command_field_does_not_act_as_a_fallback(self):
        for name, field in CONTRACTS:
            other = "cmd" if field == "command" else "command"
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "conflicting"):
                    routes.extract_shell_command(
                        name, {other: "git push origin main"})

    def test_a_second_command_field_is_ambiguous_even_if_equal_or_empty(self):
        command = "git push origin main"
        for name, field in CONTRACTS:
            other = "cmd" if field == "command" else "command"
            for value in (command, "Write-Output safe", "", None, 7):
                with self.subTest(name=name, other=value):
                    with self.assertRaisesRegex(ValueError, "conflicting"):
                        routes.extract_shell_command(
                            name, {field: command, other: value})

    def test_unrelated_metadata_is_opaque_and_input_is_not_modified(self):
        for name, field in CONTRACTS:
            tool_input = {field: "Write-Output fixture", "timeout": 1000,
                          "metadata": {"command": "not a shell argument"}}
            original = tool_input.copy()
            with self.subTest(name=name):
                self.assertEqual(routes.extract_shell_command(name, tool_input),
                                 "Write-Output fixture")
                self.assertEqual(tool_input, original)


class TestOpaqueRoutes(unittest.TestCase):
    def test_an_ordinary_mcp_command_field_is_not_treated_as_shell(self):
        for tool_input in ({}, {"command": "git push origin main"},
                           {"command": 7}, {"command": None},
                           {"command": "arbitrary", "cmd": "arbitrary"}):
            with self.subTest(tool_input=tool_input):
                self.assertIsNone(routes.extract_shell_command(
                    "mcp__example__read", tool_input))

    def test_names_are_exact_and_unimplemented_aliases_stay_opaque(self):
        names = (
            "mcp__terminal__run_in_terminal_v2",
            "mcp__terminal__run_in_terminal_extra",
            "mcp__other__run_in_terminal",
            "mcp__desktop_commander__execute_command",
            "mcp__functions__exec_command",
            "mcp__functions__Bash",
            "bash", "powershell", "monitor", "Exec_Command", "Edit", "",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertIsNone(routes.extract_shell_command(
                    name, {"command": "git push origin main",
                           "cmd": "git push origin main"}))

    def test_unknown_route_does_not_impose_a_shell_payload_schema(self):
        for tool_input in (None, [], "protocol-defined input", 7):
            with self.subTest(tool_input=tool_input):
                self.assertIsNone(routes.extract_shell_command(
                    "mcp__example__read", tool_input))


if __name__ == "__main__":
    unittest.main()
