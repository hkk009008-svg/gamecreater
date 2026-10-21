"""Exercise the saved entry in subprocesses and disposable checkout fixtures.

Synthetic targets isolate load/exit faults; real dispatcher copies prove the
consumer route and payload reach the existing guard. No test changes a live
guard, invokes Git, starts an engine, or contacts a provider.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "scripts" / "guard_entry.py"
REAL_DEPENDENCIES = (
    "hook_pretooluse.py", "check_editor_clear.py", "preflight_push.py",
    "game_config.py", "unreal_policy.py", "gitignored_config.py", "hook_shell_routes.py",
)


class TestGuardEntry(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gamecreater-guard-entry-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / "checkout with spaces"
        self.scripts = self.root / "scripts"
        self.scripts.mkdir(parents=True)
        self.entry = self.scripts / "guard_entry.py"
        shutil.copyfile(ENTRY, self.entry)
        self.outside = self.workspace / "outside git"
        self.outside.mkdir()
        self.target = self.scripts / "hook_pretooluse.py"

    def target_source(self, source):
        self.target.write_text(source, encoding="utf-8")

    def real_dispatcher(self):
        for name in REAL_DEPENDENCIES:
            shutil.copyfile(ROOT / "scripts" / name, self.scripts / name)

    def run_entry(self, payload="{}", *, env=None, entry=None, code=None):
        command = [sys.executable, "-I", "-B"]
        command += ["-c", code] if code is not None else [str(entry or self.entry)]
        process_env = os.environ.copy()
        process_env["PYTHONDONTWRITEBYTECODE"] = "1"
        if env:
            process_env.update(env)
        return subprocess.run(
            command, input=payload, cwd=self.outside, env=process_env,
            text=True, encoding="utf-8", capture_output=True, timeout=20,
        )

    def assert_blocked(self, result, reason="guard-entry failed closed:"):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(reason, result.stderr)

    def test_allow_uses_saved_sibling_and_actual_stdin_outside_git(self):
        self.target_source(
            "import sys\n"
            "def main():\n"
            "    print('PAYLOAD=' + sys.stdin.read(), file=sys.stderr)\n"
            "    return 0\n"
            "if __name__ == '__main__':\n"
            "    raise RuntimeError('target must be imported, not run as main')\n"
        )
        result = self.run_entry("exact payload")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "PAYLOAD=exact payload\n")

    def test_only_exact_integer_zero_allows(self):
        for value, expected in (("0", 0), ("2", 2), ("1", 2), ("-1", 2),
                                ("None", 2), ("False", 2), ("0.0", 2), ("'0'", 2)):
            with self.subTest(value=value):
                self.target_source(f"def main():\n    return {value}\n")
                result = self.run_entry()
                self.assertEqual(result.returncode, expected, result.stderr)
                if expected == 2:
                    self.assertIn("guard-entry failed closed:", result.stderr)

    def test_missing_target_is_blocked_even_with_allowing_decoy_checkout(self):
        decoy = self.outside / "scripts"
        decoy.mkdir()
        (decoy / "hook_pretooluse.py").write_text(
            "def main():\n    return 0\n", encoding="utf-8")
        result = self.run_entry(env={
            "CLAUDE_PROJECT_DIR": str(self.outside),
            "CODEX_PROJECT_ROOT": str(self.outside),
            "PYTHONPATH": str(decoy),
        })
        self.assert_blocked(result, "adjacent dispatcher is missing")

    def test_environment_and_cwd_cannot_replace_existing_dispatcher(self):
        self.target_source("def main():\n    return 2\n")
        (self.outside / "hook_pretooluse.py").write_text(
            "def main():\n    return 0\n", encoding="utf-8")
        self.assert_blocked(self.run_entry(env={
            "CLAUDE_PROJECT_DIR": str(self.outside),
            "CODEX_PROJECT_ROOT": str(self.outside),
            "PYTHONPATH": str(self.outside),
        }), "dispatcher returned status 2")

    def test_load_errors_fail_closed(self):
        cases = (
            ("import guard_entry_fixture_missing_dependency\n", "ModuleNotFoundError"),
            ("def broken(:\n", "SyntaxError"),
            ("raise RuntimeError('import failure')\n", "RuntimeError"),
            ("raise SystemExit(0)\n", "SystemExit"),
            ("main = None\n", "has no callable main"),
        )
        for source, reason in cases:
            with self.subTest(reason=reason):
                self.target_source(source)
                self.assert_blocked(self.run_entry(), reason)

    def test_runtime_exceptions_and_all_systemexit_forms_fail_closed(self):
        for failure in ("RuntimeError('crash')", "SystemExit(1)", "SystemExit(2)",
                        "SystemExit(0)", "SystemExit(None)", "KeyboardInterrupt()"):
            with self.subTest(failure=failure):
                self.target_source(f"def main():\n    raise {failure}\n")
                self.assert_blocked(self.run_entry(), "dispatcher execution failed")

    def test_broken_stderr_does_not_change_block_to_exit_one(self):
        self.target_source(
            "import sys\n"
            "def main():\n"
            "    sys.stderr.close()\n"
            "    raise RuntimeError('closed stream')\n"
        )
        self.assertEqual(self.run_entry().returncode, 2)

    def test_missing_relative_and_invalid_entry_contexts_fail_closed(self):
        self.target_source("def main():\n    return 0\n")
        for value in (None, "scripts/guard_entry.py", 7):
            with self.subTest(file=value):
                namespace = {"__name__": "__main__"}
                if value is not None:
                    namespace["__file__"] = value
                code = (
                    f"source = open({str(self.entry)!r}, encoding='utf-8').read(); "
                    f"exec(compile(source, 'fixture-entry', 'exec'), {namespace!r})"
                )
                self.assert_blocked(self.run_entry(code=code), "entry path is missing")
        misplaced = self.outside / "guard_entry.py"
        shutil.copyfile(self.entry, misplaced)
        self.assert_blocked(self.run_entry(entry=misplaced), "does not identify")

    def test_real_dispatcher_allows_harmless_command(self):
        self.real_dispatcher()
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "echo ok"}})
        result = self.run_entry(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")

    def test_real_dispatcher_blocks_payloads_and_reserved_command(self):
        self.real_dispatcher()
        for payload, reason in (
            ("{broken", "malformed JSON"),
            (json.dumps({"tool_name": "Bash", "tool_input": {"command": ""}}),
             "non-empty command"),
            (json.dumps({"tool_name": "mcp__repository__publish", "tool_input": {}}),
             "MCP BLOCKED"),
            (json.dumps({"tool_name": "PowerShell", "tool_input": {
                "command": "Set-Content memory/LESSONS.md overwritten"}}), "inbox-guard"),
        ):
            with self.subTest(reason=reason):
                self.assert_blocked(self.run_entry(payload), reason)

    def test_deleted_real_dispatcher_dependency_fails_closed(self):
        self.real_dispatcher()
        (self.scripts / "hook_shell_routes.py").unlink()
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "echo ok"}})
        self.assert_blocked(self.run_entry(payload), "ModuleNotFoundError")

    def test_deleting_dispatch_call_defeats_block_and_is_detectable(self):
        # Reversion control: deleting the CALL would allow a blocked request.
        # Only the disposable entry is changed, then restored byte-for-byte.
        self.real_dispatcher()
        payload = json.dumps({"tool_name": "mcp__repository__publish", "tool_input": {}})
        self.assert_blocked(self.run_entry(payload), "MCP BLOCKED")
        original = self.entry.read_bytes()
        original_hash = hashlib.sha256(original).hexdigest()
        mutant = original.replace(b"status = dispatch()", b"status = 0 # deleted call")
        self.assertNotEqual(mutant, original, "call-site mutation did not apply")
        try:
            self.entry.write_bytes(mutant)
            result = self.run_entry(payload)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("MCP BLOCKED", result.stderr)
        finally:
            self.entry.write_bytes(original)
        self.assertEqual(hashlib.sha256(self.entry.read_bytes()).hexdigest(), original_hash)
        self.assert_blocked(self.run_entry(payload), "MCP BLOCKED")


if __name__ == "__main__":
    unittest.main()
