"""Run the saved portable hook in Bash with a fixture-owned interpreter alias.

Git Bash exercises POSIX shell parsing on Windows. It does not establish a
Linux runtime, desktop hook trust or host callback/timeout behavior.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent


def bash_path() -> str | None:
    candidates = [shutil.which("bash")]
    if os.name == "nt":
        candidates += [r"C:\Program Files\Git\bin\bash.exe",
                       r"C:\Program Files\Git\usr\bin\bash.exe"]
    return next((value for value in candidates if value and Path(value).is_file()), None)


def shell_path(path: Path) -> str:
    value = path.resolve().as_posix()
    if os.name == "nt":
        return "/" + value[0].lower() + value[2:]
    return value


class PortableConfiguredEntryTests(unittest.TestCase):
    def setUp(self):
        self.bash = bash_path()
        if self.bash is None:
            self.skipTest("Bash unavailable; portable configured entry not executed on this host")
        self.temp = tempfile.TemporaryDirectory(prefix="guard posix ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "fixture repository"
        self.repo.mkdir()
        p = subprocess.run(["git", "-c", "init.templateDir=", "init", "--quiet", str(self.repo)],
                           capture_output=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.scripts = self.repo / "scripts"
        self.scripts.mkdir()
        for source in (ROOT / "scripts").glob("*.py"):
            shutil.copy2(source, self.scripts / source.name)
        self.bin = self.base / "fixture bin"
        self.bin.mkdir()
        alias = self.bin / "python3"
        alias.write_text("#!/bin/sh\nexec " + shlex.quote(shell_path(Path(sys.executable)))
                         + ' "$@"\n', encoding="utf-8", newline="\n")
        alias.chmod(0o755)
        config = json.loads((ROOT / ".codex/hooks.json").read_text(encoding="utf-8"))
        self.commands = [hook["command"] for entry in config["hooks"]["PreToolUse"]
                         for hook in entry["hooks"] if hook["type"] == "command"]
        self.assertTrue(self.commands)

    def run_hook(self, command, raw, *, cwd=None):
        env = {key: value for key, value in os.environ.items()
               if not key.upper().startswith("GIT_")
               and key not in {"CLAUDE_PROJECT_DIR", "PYTHONPATH"}}
        script = "export PATH=" + shlex.quote(shell_path(self.bin)) + ':"$PATH"\n' + command
        return subprocess.run([self.bash, "--noprofile", "--norc", "-c", script],
                              cwd=cwd or self.repo, env=env, input=raw,
                              capture_output=True, text=True, timeout=25)

    def test_saved_portable_command_allows_blocks_and_rejects_malformed(self):
        for command in self.commands:
            for raw, expected in [
                (json.dumps({"tool_name": "Bash", "tool_input": {"command": "Write-Output fixture"}}), 0),
                (json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push"}}), 2),
                ("{not-json", 2),
            ]:
                with self.subTest(payload=raw):
                    p = self.run_hook(command, raw)
                    self.assertEqual(p.returncode, expected, p.stdout + p.stderr)
                    if expected:
                        self.assertTrue(p.stderr)

    def test_saved_command_refuses_startup_faults_and_outside_git(self):
        raw = json.dumps({"tool_name": "Bash", "tool_input": {"command": "fixture"}})
        entry = self.scripts / "guard_entry.py"
        original = entry.read_bytes()
        for fault in [None, b"raise SystemExit(0)\n", b"def broken(:\n"]:
            if fault is None:
                entry.unlink()
            else:
                entry.write_bytes(fault)
            try:
                for command in self.commands:
                    p = self.run_hook(command, raw)
                    self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                    self.assertIn("guard-wrapper failed closed", p.stderr)
            finally:
                entry.write_bytes(original)
        outside = self.base / "outside git"
        outside.mkdir()
        for command in self.commands:
            p = self.run_hook(command, raw, cwd=outside)
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
