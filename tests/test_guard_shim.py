"""Pin the Antigravity shim's one-decision protocol at script level.

The shim is loaded from its saved absolute path. Controlled adapter modules
exercise its boundary, and disposable subprocess fixtures exercise failed
imports without changing live source. These checks do not establish host hook
activation, trust, or what a host does with a returned decision.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
SHIM = ROOT / ".agents" / "scripts" / "hook_antigravity_pretooluse.py"
ADAPTER_NAME = "hook_antigravity_pretooluse"


class TestGuardShimProtocol(unittest.TestCase):
    def invoke_adapter(self, adapter_main):
        spec = importlib.util.spec_from_file_location("_guard_shim_test_subject", SHIM)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        shim = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(shim)
        adapter = ModuleType(ADAPTER_NAME)
        adapter.main = adapter_main
        captured = StringIO()
        with patch.dict(sys.modules, {ADAPTER_NAME: adapter}), \
                patch.object(sys, "path", sys.path.copy()), redirect_stdout(captured):
            status = shim.main()
        return status, captured.getvalue()

    def assert_one_decision(self, status, output, expected):
        self.assertEqual(status, 0, output)
        self.assertEqual(len(output.splitlines()), 1, output)
        decision = json.loads(output)
        self.assertIsInstance(decision, dict)
        self.assertEqual(decision.get("decision"), expected, output)
        self.assertEqual(set(decision) - {"decision", "reason"}, set(), output)
        if expected == "deny":
            self.assertIsInstance(decision.get("reason"), str)
            self.assertTrue(decision["reason"].strip(), output)
        return decision

    def assert_single_fail_closed_deny(self, status, output):
        decision = self.assert_one_decision(status, output, "deny")
        self.assertIn("failed closed", decision["reason"])
        return decision

    def test_healthy_allow_is_one_normalized_decision(self):
        def allow():
            print('{ "decision" : "allow" }')
            return 0

        status, output = self.invoke_adapter(allow)
        self.assert_one_decision(status, output, "allow")
        self.assertEqual(json.loads(output), {"decision": "allow"})

    def test_healthy_deny_preserves_reason_as_one_decision(self):
        def deny():
            print(json.dumps({"decision": "deny", "reason": "fixture policy refused"}))
            return 0

        status, output = self.invoke_adapter(deny)
        decision = self.assert_one_decision(status, output, "deny")
        self.assertEqual(decision["reason"], "fixture policy refused")

    def test_crash_or_premature_exit_after_allow_outputs_only_deny(self):
        for failure in (RuntimeError("after allow"), SystemExit(0), SystemExit(1),
                        SystemExit(None), KeyboardInterrupt()):
            with self.subTest(failure=repr(failure)):
                def crash(failure=failure):
                    print('{"decision":"allow"}')
                    raise failure

                status, output = self.invoke_adapter(crash)
                self.assert_single_fail_closed_deny(status, output)
                self.assertNotIn('"decision": "allow"', output)
                self.assertNotIn('"decision":"allow"', output)

    def test_nonzero_and_noninteger_status_after_allow_outputs_only_deny(self):
        for result in (1, 2, -1, None, False, True, 0.0, "0"):
            with self.subTest(result=repr(result)):
                def invalid_status(result=result):
                    print('{"decision":"allow"}')
                    return result

                self.assert_single_fail_closed_deny(*self.invoke_adapter(invalid_status))

    def test_malformed_noisy_extra_and_invalid_json_outputs_are_denied(self):
        for output in (
            "", "not-json", '"allow"', "[]", "null", "0",
            '{"decision":"maybe"}', '{"decision":"deny"}',
            '{"decision":"deny","reason":""}',
            '{"decision":"deny","reason":"  "}',
            '{"decision":"deny","reason":3}',
            '{"decision":"allow","unexpected":true}',
            'debug output\n{"decision":"allow"}',
            '{"decision":"allow"}\n{"decision":"deny","reason":"second"}',
        ):
            with self.subTest(output=output):
                def emit(output=output):
                    print(output)
                    return 0

                self.assert_single_fail_closed_deny(*self.invoke_adapter(emit))

    def test_duplicate_json_keys_cannot_replace_a_decision_or_reason(self):
        for output in (
            '{"decision":"deny","decision":"allow","reason":"first refused"}',
            '{"decision":"allow","decision":"allow"}',
            '{"decision":"deny","reason":"first","reason":"second"}',
        ):
            with self.subTest(output=output):
                def emit(output=output):
                    print(output)
                    return 0

                self.assert_single_fail_closed_deny(*self.invoke_adapter(emit))

    def test_missing_adapter_or_import_failure_outputs_only_deny(self):
        for adapter_source in (None, 'print(\'{"decision":"allow"}\')\n'
                               'raise RuntimeError("adapter import crashed")\n'):
            with self.subTest(adapter_present=adapter_source is not None):
                with tempfile.TemporaryDirectory(prefix="gamecreater-guard-shim-") as temp:
                    root = Path(temp) / "fixture checkout"
                    shim_dir = root / ".agents" / "scripts"
                    shim_dir.mkdir(parents=True)
                    real_dir = root / "scripts"
                    real_dir.mkdir()
                    target = shim_dir / SHIM.name
                    shutil.copyfile(SHIM, target)
                    if adapter_source is not None:
                        (real_dir / SHIM.name).write_text(adapter_source, encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, "-I", "-B", str(target)], cwd=temp,
                        input="{}", capture_output=True, text=True,
                        encoding="utf-8", timeout=20,
                    )
                    self.assert_single_fail_closed_deny(result.returncode, result.stdout)
                    self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
