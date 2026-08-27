"""Cross-process controls for engine_run's exclusive launch lease."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import engine_run as er


CHILD = textwrap.dedent(r"""
    import os
    import sys
    from pathlib import Path

    sys.path.insert(0, sys.argv[1])
    import engine_run

    try:
        lease = engine_run.acquire_launch_lease(
            ["child-supervisor", sys.argv[3]], path=Path(sys.argv[2]))
    except engine_run.LaunchLeaseBusy as exc:
        print(f"BUSY: {exc}", flush=True)
        raise SystemExit(23)

    print("ACQUIRED", flush=True)
    if sys.argv[3] == "abandon":
        os._exit(0)
    lease.release()
""")


def child_attempt(path: Path, mode: str = "release") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", CHILD, str(SCRIPTS), str(path), mode],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def fake_project(root: Path) -> tuple[Path, Path, Path]:
    engine = root / "EngineRoot"
    exe = engine / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"not launched")
    uproject = root / "Project" / "LeaseTest.uproject"
    uproject.parent.mkdir()
    uproject.write_text("{}", encoding="utf-8")
    script = root / "probe.py"
    script.write_text("pass\n", encoding="utf-8")
    return engine, uproject, script


class FakeLease:
    def __init__(self, events: list[str]):
        self.events = events

    def release(self) -> None:
        self.events.append("release")


class TestCrossProcessLaunchLease(unittest.TestCase):
    def test_second_process_is_blocked_with_current_owner_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "launch.lock"
            lease = er.acquire_launch_lease(
                ["owner-supervisor", "headless", "probe.py"], path=path)
            try:
                blocked = child_attempt(path)
                self.assertEqual(blocked.returncode, 23, blocked.stderr)
                self.assertIn("BUSY:", blocked.stdout)
                self.assertIn(f"owner PID {os.getpid()}", blocked.stdout)
                self.assertIn("lease start", blocked.stdout)
                self.assertIn("owner-supervisor", blocked.stdout)
            finally:
                lease.release()

            allowed = child_attempt(path)
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertIn("ACQUIRED", allowed.stdout)

    def test_process_exit_releases_an_abandoned_lease(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "launch.lock"
            abandoned = child_attempt(path, "abandon")
            self.assertEqual(abandoned.returncode, 0, abandoned.stderr)
            self.assertIn("ACQUIRED", abandoned.stdout)

            recovered = child_attempt(path)
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            self.assertIn("ACQUIRED", recovered.stdout)


class TestLeaseWiring(unittest.TestCase):
    def test_run_names_include_subsecond_identity(self):
        self.assertRegex(er.fresh_run_stamp(), r"^\d{8}-\d{6}-\d{6}$")

    def test_lease_is_held_until_the_owned_action_returns(self):
        events: list[str] = []
        lease = FakeLease(events)

        def action():
            events.append("publish")
            self.assertNotIn("release", events)
            return 17

        with patch.object(er, "acquire_launch_lease", return_value=lease):
            self.assertEqual(er._run_with_launch_lease(["engine_run"], action),
                             17)
        self.assertEqual(events, ["publish", "release"])

    def test_dry_runs_never_acquire_the_launch_lease(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            engine, uproject, script = fake_project(root)
            cases = [
                ["headless", str(script)],
                ["automation", "Project.Lease"],
                ["data-validation"],
            ]
            for index, argv in enumerate(cases):
                args = er.build_parser().parse_args([
                    *argv,
                    "--engine", str(engine),
                    "--uproject", str(uproject),
                    "--out-dir", str(root / f"out-{index}"),
                    "--dry-run",
                ])
                with self.subTest(operation=argv[0]), \
                     patch.object(
                         er, "acquire_launch_lease",
                         side_effect=AssertionError("dry-run acquired lease")), \
                     patch.object(
                         er, "require_headless_available",
                         side_effect=AssertionError("dry-run ran census")), \
                     redirect_stdout(io.StringIO()), \
                     redirect_stderr(io.StringIO()):
                    if args.cmd == "headless":
                        rc = er.cmd_headless(args)
                    else:
                        rc = er.cmd_native(args, args.cmd)
                self.assertEqual(rc, 0)

    def test_every_real_operation_acquires_before_editor_census_and_releases(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            engine, uproject, script = fake_project(root)
            cases = [
                ["headless", str(script)],
                ["automation", "Project.Lease"],
                ["data-validation"],
            ]
            for index, argv in enumerate(cases):
                args = er.build_parser().parse_args([
                    *argv,
                    "--engine", str(engine),
                    "--uproject", str(uproject),
                    "--out-dir", str(root / f"real-{index}"),
                ])
                events: list[str] = []

                def acquire(command):
                    events.append("acquire")
                    self.assertTrue(command)
                    return FakeLease(events)

                def census():
                    events.append("census")
                    return "test refusal before launch"

                output = io.StringIO()
                with self.subTest(operation=argv[0]), \
                     patch.object(er, "acquire_launch_lease", acquire), \
                     patch.object(er, "require_headless_available", census), \
                     redirect_stdout(output), redirect_stderr(output):
                    if args.cmd == "headless":
                        rc = er.cmd_headless(args)
                    else:
                        rc = er.cmd_native(args, args.cmd)
                self.assertEqual(rc, 3)
                self.assertEqual(events, ["acquire", "census", "release"])
                self.assertIn("test refusal before launch", output.getvalue())

    def test_contention_is_a_clear_cli_refusal(self):
        args = type("Args", (), {
            "dry_run": False,
            "script": Path("probe.py"),
        })()
        owner = {
            "pid": 31415,
            "started_utc": "2026-08-27T12:34:56+00:00",
            "command_line": "engine_run automation Project.Lease",
        }
        error = er.LaunchLeaseBusy(Path("lease.lock"), owner)
        output = io.StringIO()
        with patch.object(er, "acquire_launch_lease", side_effect=error), \
             patch.object(
                 er, "_cmd_headless_impl",
                 side_effect=AssertionError("contention still ran command")), \
             redirect_stdout(output), redirect_stderr(output):
            rc = er.cmd_headless(args)
        text = output.getvalue()
        self.assertEqual(rc, 3)
        self.assertIn("REFUSED", text)
        self.assertIn("owner PID 31415", text)
        self.assertIn("lease start 2026-08-27", text)
        self.assertIn("engine_run automation", text)


if __name__ == "__main__":
    unittest.main()
