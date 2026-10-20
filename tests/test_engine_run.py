"""Pin the engine run supervisor: command builder, watchdog, mode routing.

The watchdog tests spawn REAL subprocesses. A watchdog mocked into agreeing
with itself proves nothing -- the thing under test is whether an actual
hung process actually dies, so these tests hang or fail for real if it
does not.
"""

import io
import json
import subprocess
import struct
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import engine_run as er
from game_config import GameConfig


def fake_project(tmp: Path) -> tuple[Path, Path, Path]:
    """An engine tree, a uproject and a script that all exist on disk --
    build_command refuses non-existent inputs, which is the point."""
    engine = tmp / "UE_5.8"
    (engine / "Engine" / "Binaries" / "Win64").mkdir(parents=True)
    (engine / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe").write_bytes(b"MZ")
    uproject = tmp / "Kurogane.uproject"
    uproject.write_text("{}", encoding="utf-8")
    script = tmp / "probe.py"
    script.write_text("pass\n", encoding="utf-8")
    return engine, uproject, script


class TestCommandBuilder(unittest.TestCase):
    def test_cli_exposes_epic_mcp_check_under_its_exact_name(self):
        parsed = er.build_parser().parse_args(["epic-mcp-check"])
        self.assertEqual(parsed.cmd, "epic-mcp-check")

        with (patch.object(er, "load_game_config", return_value=GameConfig(source=Path("fixture.md"))),
              patch.object(er, "cmd_epic_mcp_check", return_value=7) as check):
            self.assertEqual(er.main(["engine_run", "epic-mcp-check"]), 7)
        check.assert_called_once_with()

    def test_cli_accepts_dash_prefixed_engine_flag(self):
        """The old trailing positional rejected exactly the values it was
        meant to carry: argparse left ``-- -nullrhi`` unrecognized."""
        parsed = er.build_parser().parse_args([
            "headless", "probe.py", "--extra-flag=-nullrhi",
            "--extra-flag=-NoSound",
        ])
        self.assertEqual(parsed.extra_flag, ["-nullrhi", "-NoSound"])

    def test_refuses_nullrhi_when_the_run_needs_pixels(self):
        """A pre-flight refusal beats a post-hoc log scan: -nullrhi means no
        RHI at all, so the run cannot produce one pixel."""
        with tempfile.TemporaryDirectory() as t:
            e, u, s = fake_project(Path(t))
            with self.assertRaises(er.IntentError) as cm:
                er.build_command(e, u, s, Path(t) / "r.log",
                                 needs_rhi=True, extra=["-nullrhi"])
            self.assertIn("cannot produce one pixel", str(cm.exception))

    def test_nullrhi_allowed_when_the_run_does_not_render(self):
        """The quiet direction -- a blanket ban would be wrong and would get
        the builder bypassed."""
        with tempfile.TemporaryDirectory() as t:
            e, u, s = fake_project(Path(t))
            cmd = er.build_command(e, u, s, Path(t) / "r.log",
                                   needs_rhi=False, extra=["-nullrhi"])
            self.assertIn("-nullrhi", cmd)

    def test_non_rendering_run_defaults_to_exactly_one_nullrhi(self):
        with tempfile.TemporaryDirectory() as t:
            e, u, s = fake_project(Path(t))
            cmd = er.build_command(e, u, s, Path(t) / "r.log",
                                   needs_rhi=False)
            self.assertEqual(cmd.count("-nullrhi"), 1)
            self.assertNotIn("-RenderOffscreen", cmd)

    def test_needs_rhi_adds_renderoffscreen(self):
        with tempfile.TemporaryDirectory() as t:
            e, u, s = fake_project(Path(t))
            cmd = er.build_command(e, u, s, Path(t) / "r.log", needs_rhi=True)
            self.assertIn("-RenderOffscreen", cmd)
            self.assertNotIn("-nullrhi", cmd)

    def test_renderoffscreen_requires_declared_rhi_intent(self):
        with tempfile.TemporaryDirectory() as t:
            e, u, s = fake_project(Path(t))
            with self.assertRaises(er.IntentError) as cm:
                er.build_command(
                    e, u, s, Path(t) / "r.log", needs_rhi=False,
                    extra=["-RenderOffscreen"],
                )
            self.assertIn("requires needs_rhi=True", str(cm.exception))

    def test_renderoffscreen_not_doubled_if_caller_passed_it(self):
        with tempfile.TemporaryDirectory() as t:
            e, u, s = fake_project(Path(t))
            cmd = er.build_command(e, u, s, Path(t) / "r.log", needs_rhi=True,
                                   extra=["-RenderOffscreen"])
            self.assertEqual(cmd.count("-RenderOffscreen"), 1)

    def test_real_game_uses_exec_cmds_not_editor_only_route(self):
        """UE rejects -ExecutePythonScript under -game. The project-proven
        route is one ExecCmds argv value under the current no-space root."""
        with tempfile.TemporaryDirectory() as t:
            e, u, s = fake_project(Path(t))
            cmd = er.build_command(e, u, s, Path(t) / "r.log",
                                   needs_rhi=False, real_game=True)
            self.assertIn("-game", cmd)
            self.assertFalse(any(x.startswith("-ExecutePythonScript=")
                                 for x in cmd))
            exec_cmds = [x for x in cmd if x.startswith("-ExecCmds=")]
            self.assertEqual(len(exec_cmds), 1)
            self.assertEqual(exec_cmds[0], f"-ExecCmds=py {s.resolve()}")
            rendered = subprocess.list2cmdline(cmd)
            self.assertIn(f'"-ExecCmds=py {s.resolve()}"', rendered)
            self.assertNotIn(f'\\"{s.resolve()}\\"', rendered)

    def test_game_extra_without_real_game_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            e, u, s = fake_project(Path(t))
            with self.assertRaises(er.IntentError) as cm:
                er.build_command(e, u, s, Path(t) / "r.log",
                                 needs_rhi=False, extra=["-game"])
            self.assertIn("requires --real-game", str(cm.exception))

    def test_competing_python_entry_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            e, u, s = fake_project(Path(t))
            with self.assertRaises(er.IntentError) as cm:
                er.build_command(e, u, s, Path(t) / "r.log",
                                 needs_rhi=False,
                                 extra=["-ExecCmds=py other.py"])
            self.assertIn("competing Python entry", str(cm.exception))

    def test_real_game_whitespace_script_path_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "path with space"
            e, u, s = fake_project(root)
            with self.assertRaises(er.IntentError) as cm:
                er.build_command(e, u, s, root / "r.log",
                                 needs_rhi=False, real_game=True)
            self.assertIn("unproven", str(cm.exception))

    def test_editor_route_remains_execute_python_script(self):
        with tempfile.TemporaryDirectory() as t:
            e, u, s = fake_project(Path(t))
            cmd = er.build_command(e, u, s, Path(t) / "r.log",
                                   needs_rhi=False)
            self.assertTrue(any(x.startswith("-ExecutePythonScript=")
                                for x in cmd))
            self.assertFalse(any(x.startswith("-ExecCmds=") for x in cmd))

    def test_abslog_is_literal_absolute_and_after_the_uproject(self):
        """A shell-interpolated -abslog costs the whole run silently: the
        editor launches, exits, writes zero bytes, raises nothing."""
        with tempfile.TemporaryDirectory() as t:
            e, u, s = fake_project(Path(t))
            log = Path(t) / "logs" / "r.log"
            cmd = er.build_command(e, u, s, log, needs_rhi=False)
            abslog = [c for c in cmd if c.startswith("-abslog=")]
            self.assertEqual(len(abslog), 1)
            value = abslog[0].split("=", 1)[1]
            self.assertTrue(Path(value).is_absolute())
            self.assertNotIn("$", value)
            self.assertNotIn("%", value)
            self.assertGreater(cmd.index(abslog[0]), cmd.index(str(u)))

    def test_every_base_flag_survives(self):
        with tempfile.TemporaryDirectory() as t:
            e, u, s = fake_project(Path(t))
            cmd = er.build_command(e, u, s, Path(t) / "r.log", needs_rhi=False)
            for flag in er.BASE_FLAGS:
                self.assertIn(flag, cmd)

    def test_headless_help_names_real_extra_and_artifact_contracts(self):
        parser = er.build_parser()
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as cm:
            parser.parse_args(["headless", "--help"])
        self.assertEqual(cm.exception.code, 0)
        text = " ".join(output.getvalue().split())
        self.assertIn("Omitting it makes the run", text)
        self.assertIn("diagnostic-only and non-citable", text)
        self.assertIn("ENGINE_RUN_ARTIFACT", text)
        self.assertIn("legacy plain, non-option extras only", text)
        self.assertIn("prefixed Unreal flags", text)
        self.assertIn("--extra-flag=VALUE", text)

    def test_missing_script_refused_before_launch(self):
        with tempfile.TemporaryDirectory() as t:
            e, u, _ = fake_project(Path(t))
            with self.assertRaises(er.IntentError):
                er.build_command(e, u, Path(t) / "nope.py", Path(t) / "r.log",
                                 needs_rhi=False)

    def test_missing_engine_binary_refused_before_launch(self):
        with tempfile.TemporaryDirectory() as t:
            _, u, s = fake_project(Path(t))
            with self.assertRaises(er.IntentError):
                er.build_command(Path(t) / "no_engine", u, s,
                                 Path(t) / "r.log", needs_rhi=False)


class TestConfiguredDefaults(unittest.TestCase):
    def test_engine_and_sole_uproject_come_from_game_local_config(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            engine, uproject, _ = fake_project(root)
            config = GameConfig(
                source=root / "GAME.local.md",
                project_root=root,
                engine_root=engine,
            )
            with patch.object(er, "load_game_config", return_value=config):
                actual_engine, actual_uproject = er.configured_engine_project(
                    None, None)
            self.assertEqual(actual_engine, engine.resolve())
            self.assertEqual(actual_uproject, uproject.resolve())

    def test_explicit_paths_work_without_game_local_defaults(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            engine, uproject, _ = fake_project(root)
            empty = GameConfig(source=root / "missing-GAME.local.md")
            with patch.object(er, "load_game_config", return_value=empty):
                actual = er.configured_engine_project(engine, uproject)
            self.assertEqual(actual, (engine.resolve(), uproject.resolve()))

    def test_missing_engine_default_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _, uproject, _ = fake_project(root)
            config = GameConfig(
                source=root / "GAME.local.md",
                project_root=uproject,
            )
            with patch.object(er, "load_game_config", return_value=config):
                with self.assertRaises(er.IntentError) as cm:
                    er.configured_engine_project(None, None)
            self.assertIn("pass --engine", str(cm.exception))

    def test_ambiguous_project_default_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            engine, _, _ = fake_project(root)
            (root / "Another.uproject").write_text("{}", encoding="utf-8")
            config = GameConfig(
                source=root / "GAME.local.md",
                project_root=root,
                engine_root=engine,
            )
            with patch.object(er, "load_game_config", return_value=config):
                with self.assertRaises(er.IntentError) as cm:
                    er.configured_engine_project(None, None)
            self.assertIn("exactly one immediate .uproject", str(cm.exception))
            self.assertIn("pass --uproject", str(cm.exception))

    def test_default_run_root_uses_configured_evidence_root(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _, uproject, _ = fake_project(root)
            config = GameConfig(
                source=root / "GAME.local.md",
                project_root=root,
            )
            with patch.object(er, "load_game_config", return_value=config):
                actual = er.default_run_root(uproject)
            self.assertEqual(actual, (root / "Experiments" / "Runs").resolve())

    def test_default_run_root_falls_back_beside_explicit_project(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _, uproject, _ = fake_project(root)
            empty = GameConfig(source=root / "missing-GAME.local.md")
            with patch.object(er, "load_game_config", return_value=empty):
                actual = er.default_run_root(uproject)
            self.assertEqual(actual, (root / "Saved" / "CodexRuns").resolve())


class TestWatchdog(unittest.TestCase):
    """Real processes. Each asserts the kill HAPPENED, not that a mock was
    called."""

    def setUp(self):
        self._poll = er.POLL_S
        er.POLL_S = 0.05

    def tearDown(self):
        er.POLL_S = self._poll

    def test_fast_process_is_not_killed(self):
        """The quiet direction. A watchdog that killed everything would pass
        the two kill tests below and be worthless."""
        with tempfile.TemporaryDirectory() as t:
            log = Path(t) / "r.log"
            rc, killed, elapsed = er.supervise(
                [sys.executable, "-c", "pass"], log, stall_s=30, wall_s=30)
            self.assertEqual(rc, 0)
            self.assertIsNone(killed)
            self.assertLess(elapsed, 20)

    def test_hung_silent_process_is_killed_on_stall(self):
        """A process that is alive but has stopped writing. A wall-clock
        timeout alone cannot tell this from slow-but-working; only the log
        stall can, and only before the wall budget expires."""
        with tempfile.TemporaryDirectory() as t:
            log = Path(t) / "r.log"
            log.write_text("started\n", encoding="utf-8")
            t0 = time.monotonic()
            rc, killed, elapsed = er.supervise(
                [sys.executable, "-c", "import time; time.sleep(120)"],
                log, stall_s=1, wall_s=60)
            self.assertEqual(killed, "stall")
            self.assertLess(time.monotonic() - t0, 30,
                            "stall detector did not fire before the wall budget")

    def test_chatty_but_endless_process_is_killed_on_wall_clock(self):
        """The stall detector cannot stop this one -- the log keeps growing
        forever. That is why there are two independent timers."""
        with tempfile.TemporaryDirectory() as t:
            log = Path(t) / "r.log"
            code = ("import time,sys\n"
                    "p=sys.argv[1]\n"
                    "while True:\n"
                    "    open(p,'a').write('tick\\n')\n"
                    "    time.sleep(0.05)\n")
            rc, killed, elapsed = er.supervise(
                [sys.executable, "-c", code, str(log)],
                log, stall_s=60, wall_s=1)
            self.assertEqual(killed, "timeout")
            self.assertGreater(log.stat().st_size, 0,
                               "fixture never wrote; the stall path may have "
                               "fired instead of the wall path")

    def test_kill_reaps_the_child_tree_not_just_the_parent(self):
        """UnrealEditor-Cmd spawns ShaderCompileWorkers. Killing only the
        parent leaves orphans that trip check_editor_clear on the next
        launch, which reads as a phantom 'editor already running'."""
        with tempfile.TemporaryDirectory() as t:
            log = Path(t) / "r.log"
            grandchild_out = Path(t) / "grandchild.txt"
            child = (
                "import subprocess,sys,time\n"
                "gc=('import time,sys\\n'\n"
                "    'while True:\\n'\n"
                "    '    open(sys.argv[1],\"a\").write(\"x\")\\n'\n"
                "    '    time.sleep(0.05)\\n')\n"
                f"subprocess.Popen([sys.executable,'-c',gc,r'{grandchild_out}'])\n"
                "time.sleep(120)\n"
            )
            rc, killed, _ = er.supervise(
                [sys.executable, "-c", child], log, stall_s=1, wall_s=60)
            self.assertEqual(killed, "stall")
            time.sleep(0.6)
            size_a = grandchild_out.stat().st_size if grandchild_out.exists() else 0
            time.sleep(1.0)
            size_b = grandchild_out.stat().st_size if grandchild_out.exists() else 0
            self.assertGreater(size_a, 0,
                               "grandchild never ran; this test proved nothing")
            self.assertEqual(size_a, size_b,
                             "grandchild is STILL WRITING after the kill -- "
                             "the process tree survived")


class TestModeRouting(unittest.TestCase):
    def _run_headless(self, tmp: Path, *extra: str):
        e, u, s = fake_project(tmp)
        a = er.build_parser().parse_args(
            ["headless", str(s), "--engine", str(e), "--uproject", str(u),
             "--out-dir", str(tmp / "runs"), "--dry-run", *extra])
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = er.cmd_headless(a)
        return rc, out.getvalue() + err.getvalue()

    def test_real_launch_gate_refuses_an_open_editor(self):
        with patch.object(er.cec, "list_processes",
                          return_value=["UnrealEditor-Cmd.exe"]):
            refusal = er.require_headless_available()
        self.assertIn("an Unreal editor is running", refusal)
        self.assertIn("use OpenClaw", refusal)

    def test_real_launch_gate_fails_closed_when_processes_cannot_be_listed(self):
        """An enumerator that crashed is not proof that no editor is running."""
        with patch.object(er.cec, "list_processes",
                          side_effect=er.cec.ProcessListError("boom")):
            refusal = er.require_headless_available()
        self.assertIn("fail-closed", refusal)

    def test_dry_run_does_not_require_editor_clear(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            with patch.object(er, "require_headless_available",
                              side_effect=AssertionError("must not be called")):
                rc, text = self._run_headless(tmp)
            self.assertEqual(rc, 0)
            self.assertIn("--dry-run", text)

    def test_dry_run_still_validates_the_command(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            e, u, script = fake_project(tmp)
            script.unlink()
            a = er.build_parser().parse_args([
                "headless", str(script), "--engine", str(e),
                "--uproject", str(u), "--dry-run",
            ])
            out, err = io.StringIO(), io.StringIO()
            with patch.object(er, "require_headless_available",
                              side_effect=AssertionError("must not be called")), \
                 redirect_stdout(out), redirect_stderr(err):
                rc = er.cmd_headless(a)
            self.assertEqual(rc, 3)
            self.assertIn("script does not exist", out.getvalue() + err.getvalue())

    def test_headless_expect_rhi_requires_needs_rhi(self):
        with tempfile.TemporaryDirectory() as t:
            with patch.object(er, "require_headless_available",
                              side_effect=AssertionError("must not be called")):
                rc, text = self._run_headless(
                    Path(t), "--expect-rhi", "D3D11")
            self.assertEqual(rc, 3)
            self.assertIn("--expect-rhi requires --needs-rhi", text)

    def test_existing_log_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            e, u, s = fake_project(tmp)
            log = tmp / "taken.log"
            log.write_text("precious evidence", encoding="utf-8")
            a = er.build_parser().parse_args(
                ["headless", str(s), "--engine", str(e), "--uproject", str(u),
                 "--out-dir", str(tmp / "runs"), "--log", str(log), "--dry-run"])
            with patch.object(er.cec, "list_processes", return_value=["explorer.exe"]):
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    rc = er.cmd_headless(a)
            self.assertEqual(rc, 3)
            self.assertIn("refusing to overwrite", out.getvalue() + err.getvalue())
            self.assertEqual(log.read_text(encoding="utf-8"), "precious evidence")

    def test_existing_declared_artifact_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            e, u, s = fake_project(tmp)
            artifact = tmp / "precious.json"
            artifact.write_text('{"status":"PASS"}', encoding="utf-8")
            a = er.build_parser().parse_args(
                ["headless", str(s), "--engine", str(e), "--uproject", str(u),
                 "--out-dir", str(tmp / "runs"), "--artifact", str(artifact),
                 "--dry-run"])
            with patch.object(er.cec, "list_processes", return_value=["explorer.exe"]):
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    rc = er.cmd_headless(a)
            self.assertEqual(rc, 3)
            self.assertIn("declared artifact", out.getvalue() + err.getvalue())
            self.assertEqual(artifact.read_text(encoding="utf-8"),
                             '{"status":"PASS"}')


class TestSidecarProvenance(unittest.TestCase):
    def test_harness_hash_changes_when_a_member_changes(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            a = root / "a.py"; a.write_text("x = 1\n", encoding="utf-8")
            b = root / "b.py"; b.write_text("y = 2\n", encoding="utf-8")
            first = er.harness_fingerprint([a, b])
            b.write_text("y = 3\n", encoding="utf-8")
            second = er.harness_fingerprint([a, b])
            self.assertNotEqual(first["sha256"], second["sha256"])
            self.assertEqual(len(first["files"]), 2)

    def test_png_size_is_read_from_ihdr(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "plate.png"
            p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR"
                          + struct.pack(">II", 1920, 1080))
            self.assertEqual(er.png_capture_size(p), [1920, 1080])

    def test_png_signature_without_ihdr_is_not_a_capture_size(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "fake.png"
            p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dNOPE"
                          + struct.pack(">II", 1920, 1080))
            self.assertIsNone(er.png_capture_size(p))

    def test_project_environment_is_script_scoped_and_redacts_secrets(self):
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "probe.py"
            script.write_text(
                "TONE = 'KUROGANE_FACE_TONE'\n"
                "TOKEN = 'KG_TOKEN'\n",
                encoding="utf-8")
            with patch.dict(er.os.environ, {
                "KUROGANE_FACE_TONE": "0.25",
                "KG_TOKEN": "do-not-record-this",
                "KUROGANE_UNRELATED": "ambient-value",
            }, clear=False):
                captured = er.project_environment(script)
            self.assertEqual(captured["KUROGANE_FACE_TONE"], "0.25")
            self.assertEqual(captured["KG_TOKEN"], "<redacted>")
            self.assertNotIn("KUROGANE_UNRELATED", captured)

    def test_project_environment_uses_the_effective_child_environment(self):
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "probe.py"
            script.write_text("OUT = 'ENGINE_RUN_ARTIFACT'\n", encoding="utf-8")
            with patch.dict(er.os.environ,
                            {"ENGINE_RUN_ARTIFACT": "stale-parent.json"},
                            clear=False):
                run_env = er.child_environment([Path("fresh.json").resolve()])
                captured = er.project_environment(script, run_env)
            self.assertEqual(captured["ENGINE_RUN_ARTIFACT"],
                             str(Path("fresh.json").resolve()))

    def test_capture_bucket_reads_selected_adapter(self):
        with tempfile.TemporaryDirectory() as t:
            log = Path(t) / "run.log"
            log.write_text(
                "LogInit: Engine Version: 5.8.1-test\n"
                "LogInit: OS: Windows 11 (25H2), CPU: Example, GPU: Intel\n"
                "LogRHI: Using Default RHI: D3D12\n"
                "LogRHI: Using Highest Feature Level of D3D12: SM6\n"
                "LogRHI:             Name: NVIDIA Test GPU\n"
                "LogRHI:   Driver Version: 610.88\n", encoding="utf-8")
            bucket = er.capture_bucket(log, enabled=True, extra_flags=[])
            self.assertTrue(bucket["complete"])
            self.assertEqual(bucket["gpu"], "NVIDIA Test GPU")
            self.assertEqual(bucket["rhi"], "D3D12")
            self.assertEqual(bucket["shader_model"], "SM6")
            self.assertIsNotNone(bucket["key"])

    def test_atomic_sidecar_has_no_temporary_remnant(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "run.sidecar.json"
            er.atomic_write_json(p, {"answer": 42})
            self.assertEqual(json.loads(p.read_text(encoding="utf-8")),
                             {"answer": 42})
            self.assertEqual(list(Path(t).glob("*.tmp")), [])

    def test_atomic_sidecar_never_replaces_a_collision(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "run.sidecar.json"
            p.write_text('{"precious": true}\n', encoding="utf-8")
            with self.assertRaises(FileExistsError):
                er.atomic_write_json(p, {"replacement": True})
            self.assertEqual(json.loads(p.read_text(encoding="utf-8")),
                             {"precious": True})
            self.assertEqual(list(Path(t).glob("*.tmp")), [])


class TestHeadlessEvidenceBinding(unittest.TestCase):
    CLEAN_LOG = (
        "LogInit: Engine Version: 5.8.1-test\n"
        "LogInit: OS: Windows 11, CPU: Example, GPU: Example\n"
        "LogPython: probe ran\n"
        "LogRHI: Render tracing channels set: Submission\n"
        "LogTemp: finished\n"
        "LogExit: Log file closed\n")

    def _args(self, root: Path, artifact: Path):
        e, u, s = fake_project(root)
        return er.build_parser().parse_args([
            "headless", str(s), "--engine", str(e), "--uproject", str(u),
            "--out-dir", str(root / "runs"), "--artifact", str(artifact)])

    def test_standard_child_output_env_exists_only_for_one_artifact(self):
        one = Path("result.json").resolve()
        with patch.dict(er.os.environ,
                        {"ENGINE_RUN_ARTIFACT": "stale-parent.json"},
                        clear=False):
            env = er.child_environment([one])
            empty = er.child_environment([])
            many = er.child_environment([one, Path("other.json").resolve()])
        self.assertEqual(env["ENGINE_RUN_ARTIFACT"], str(one))
        self.assertNotIn("ENGINE_RUN_ARTIFACT", empty)
        self.assertNotIn("ENGINE_RUN_ARTIFACT", many)

    def test_absent_then_fast_present_is_not_false_stale(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            artifact = root / "result.json"
            args = self._args(root, artifact)

            def produce(_cmd, log, **_kwargs):
                self.assertEqual(
                    _kwargs["env"]["ENGINE_RUN_ARTIFACT"],
                    str(artifact.resolve()))
                artifact.write_text('{"status":"PASS"}', encoding="utf-8")
                log.write_text(self.CLEAN_LOG, encoding="utf-8")
                return 0, None, 0.001

            with patch.object(er.cec, "list_processes", return_value=[]), \
                 patch.object(er, "supervise", side_effect=produce):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    rc = er.cmd_headless(args)
            self.assertEqual(rc, 0)
            sidecar = next((root / "runs").glob("*.sidecar.json"))
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual(data["verdict"]["output"], "PRESENT")
            self.assertTrue(data["verdict"]["citable"])
            self.assertEqual(data["artifacts"][0]["sha256"],
                             er.sha256_full(artifact))

    def test_artifact_arriving_during_provenance_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            artifact = root / "result.json"
            args = self._args(root, artifact)

            def race(_paths):
                artifact.write_text('{"status":"FAIL"}', encoding="utf-8")
                return {"sha256": "x", "changed_line_count": 0, "files": []}

            with patch.object(er.cec, "list_processes", return_value=[]), \
                 patch.object(er, "harness_fingerprint", side_effect=race), \
                 patch.object(er, "supervise") as supervise:
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    rc = er.cmd_headless(args)
            self.assertEqual(rc, 3)
            supervise.assert_not_called()
            self.assertEqual(json.loads(artifact.read_text(encoding="utf-8")),
                             {"status": "FAIL"})


class TestEpicMcpEndpoint(unittest.TestCase):
    def test_endpoint_is_read_from_the_client_config_not_hardcoded(self):
        """If the checker hardcoded the port it would drift from .mcp.json
        and report 'MCP down' while MCP was up on another port."""
        with tempfile.TemporaryDirectory() as t:
            cfg = Path(t) / ".mcp.json"
            cfg.write_text(json.dumps({"mcpServers": {"unreal-mcp": {
                "type": "http", "url": "http://127.0.0.1:9123/other"}}}),
                encoding="utf-8")
            with patch.object(er, "MCP_CONFIG", cfg):
                self.assertEqual(er.mcp_endpoint(), ("127.0.0.1", 9123, "/other"))

    def test_unreadable_config_falls_back_to_plugin_defaults(self):
        with patch.object(er, "MCP_CONFIG", Path("Z:/nope.json")):
            self.assertEqual(er.mcp_endpoint(), ("127.0.0.1", 8000, "/mcp"))

    def test_invalid_present_config_is_not_silently_treated_as_default(self):
        with tempfile.TemporaryDirectory() as t:
            cfg = Path(t) / ".mcp.json"
            cfg.write_text('{"mcpServers":{"unreal-mcp":{"url":"bad"}}}',
                           encoding="utf-8")
            with patch.object(er, "MCP_CONFIG", cfg), \
                 self.assertRaisesRegex(RuntimeError, "endpoint"):
                er.mcp_endpoint()

    def test_port_open_is_true_for_a_real_listener(self):
        """Known-positive control: without it, port_open() returning False
        for everything would look like a correct 'MCP is down' report."""
        import socket
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        host, port = srv.getsockname()
        try:
            self.assertTrue(er.port_open(host, port))
        finally:
            srv.close()
        self.assertFalse(er.port_open(host, port),
                         "port still reads open after the listener closed")

    def _check(self, tmp, *, procs, listening, probe_result):
        import mcp_client
        config = GameConfig(
            source=tmp / "GAME.local.md",
            project_root=tmp / "Project",
        )
        with patch.object(er, "load_game_config", return_value=config), \
             patch.object(er.cec, "list_processes", return_value=procs), \
             patch.object(er, "port_open", return_value=listening), \
             patch.object(mcp_client, "probe", return_value=probe_result):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = er.cmd_epic_mcp_check()
        return rc, out.getvalue()

    DEAD = {"speaks_mcp": False, "error": "connection refused", "tools": []}
    LIVE = {"speaks_mcp": True, "protocol": "2025-06-18",
            "tools": ["list_toolsets", "describe_toolset", "call_tool"]}

    def test_each_reachability_failure_is_reported_separately(self):
        """'MCP is broken' is not a diagnosis: these three have three
        different fixes and must not collapse into one line."""
        with tempfile.TemporaryDirectory() as t:
            rc, text = self._check(Path(t),
                                   procs=["explorer.exe"], listening=False,
                                   probe_result=self.DEAD)
            self.assertEqual(rc, 1)
            self.assertIn("editor running", text)
            self.assertIn("listener on", text)
            self.assertIn("endpoint speaks MCP", text)
            self.assertIn("not covered by the headless grant", text)

    def test_an_open_port_alone_is_not_reported_as_reachable(self):
        """The load-bearing one. A listener is not a protocol -- anything
        could hold port 8000. Only the handshake decides."""
        with tempfile.TemporaryDirectory() as t:
            rc, text = self._check(Path(t),
                                   procs=["UnrealEditor.exe"], listening=True,
                                   probe_result=self.DEAD)
            self.assertEqual(rc, 1)
            self.assertIn("[NO ] endpoint speaks MCP", text)
            self.assertIn("Epic MCP is NOT reachable", text)

    def test_live_server_reachability_needs_no_mode_declaration(self):
        """Reachability is observed directly; there is no marker whose stale
        bookkeeping can contradict a successful protocol handshake."""
        with tempfile.TemporaryDirectory() as t:
            rc, text = self._check(Path(t),
                                   procs=["UnrealEditor.exe"], listening=True,
                                   probe_result=self.LIVE)
            self.assertEqual(rc, 0)
            self.assertIn("EPIC MCP IS REACHABLE", text)
            self.assertNotIn("Epic MCP is NOT reachable", text)
            self.assertNotIn("bookkeeping", text)

    def test_fully_ready_reports_protocol_and_the_headless_cost(self):
        with tempfile.TemporaryDirectory() as t:
            rc, text = self._check(Path(t),
                                   procs=["UnrealEditor.exe"], listening=True,
                                   probe_result=self.LIVE)
            self.assertEqual(rc, 0)
            self.assertIn("2025-06-18", text)
            self.assertIn("3 tool(s)", text)
            self.assertIn("blocked", text)
            self.assertNotIn("bookkeeping", text)


if __name__ == "__main__":
    unittest.main()
