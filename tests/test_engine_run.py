"""Pin the engine run supervisor: command builder, watchdog, mode routing.

The watchdog tests spawn REAL subprocesses. A watchdog mocked into agreeing
with itself proves nothing -- the thing under test is whether an actual
hung process actually dies, so these tests hang or fail for real if it
does not.
"""

import io
import json
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import engine_run as er


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

    def test_needs_rhi_adds_renderoffscreen(self):
        with tempfile.TemporaryDirectory() as t:
            e, u, s = fake_project(Path(t))
            cmd = er.build_command(e, u, s, Path(t) / "r.log", needs_rhi=True)
            self.assertIn("-RenderOffscreen", cmd)

    def test_renderoffscreen_not_doubled_if_caller_passed_it(self):
        with tempfile.TemporaryDirectory() as t:
            e, u, s = fake_project(Path(t))
            cmd = er.build_command(e, u, s, Path(t) / "r.log", needs_rhi=True,
                                   extra=["-RenderOffscreen"])
            self.assertEqual(cmd.count("-RenderOffscreen"), 1)

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
    def _run_headless(self, tmp: Path):
        e, u, s = fake_project(tmp)
        a = er.build_parser().parse_args(
            ["headless", str(s), "--engine", str(e), "--uproject", str(u),
             "--out-dir", str(tmp / "runs"), "--dry-run"])
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = er.cmd_headless(a)
        return rc, out.getvalue() + err.getvalue()

    def test_headless_refused_while_an_mcp_session_is_declared(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            marker = tmp / ".mcp-session.local"
            marker.write_text('{"started":"now"}', encoding="utf-8")
            with patch.object(er, "MARKER", marker), \
                 patch.object(er.cec, "list_processes",
                              return_value=["UnrealEditor.exe"]):
                rc, text = self._run_headless(tmp)
            self.assertEqual(rc, 3)
            self.assertIn("mutually exclusive", text)
            self.assertIn("mcp_session.py off", text)

    def test_headless_refused_when_an_undeclared_editor_is_open(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            with patch.object(er, "MARKER", tmp / "absent"), \
                 patch.object(er.cec, "list_processes",
                              return_value=["UnrealEditor-Cmd.exe"]):
                rc, text = self._run_headless(tmp)
            self.assertEqual(rc, 3)
            self.assertIn("no MCP session is declared", text)

    def test_headless_fails_closed_when_processes_cannot_be_listed(self):
        """An enumerator that crashed is not proof that no editor is running."""
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            with patch.object(er, "MARKER", tmp / "absent"), \
                 patch.object(er.cec, "list_processes",
                              side_effect=er.cec.ProcessListError("boom")):
                rc, text = self._run_headless(tmp)
            self.assertEqual(rc, 3)
            self.assertIn("fail-closed", text)

    def test_headless_allowed_when_the_machine_is_clear(self):
        """The quiet direction: a router that refused everything would pass
        the three refusal tests above."""
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            with patch.object(er, "MARKER", tmp / "absent"), \
                 patch.object(er.cec, "list_processes",
                              return_value=["explorer.exe", "python.exe"]):
                rc, text = self._run_headless(tmp)
            self.assertEqual(rc, 0)
            self.assertIn("--dry-run", text)

    def test_existing_log_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            e, u, s = fake_project(tmp)
            log = tmp / "taken.log"
            log.write_text("precious evidence", encoding="utf-8")
            a = er.build_parser().parse_args(
                ["headless", str(s), "--engine", str(e), "--uproject", str(u),
                 "--out-dir", str(tmp / "runs"), "--log", str(log), "--dry-run"])
            with patch.object(er, "MARKER", tmp / "absent"), \
                 patch.object(er.cec, "list_processes", return_value=["explorer.exe"]):
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    rc = er.cmd_headless(a)
            self.assertEqual(rc, 3)
            self.assertIn("refusing to overwrite", out.getvalue() + err.getvalue())
            self.assertEqual(log.read_text(encoding="utf-8"), "precious evidence")


class TestMcpEndpoint(unittest.TestCase):
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

    def _check(self, tmp, *, marker: bool, procs, listening, probe_result):
        m = (tmp / "declared.json") if marker else (tmp / "absent")
        if marker:
            m.write_text('{"started":"now"}', encoding="utf-8")
        import mcp_client
        with patch.object(er, "MARKER", m), \
             patch.object(er.cec, "list_processes", return_value=procs), \
             patch.object(er, "port_open", return_value=listening), \
             patch.object(mcp_client, "probe", return_value=probe_result):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = er.cmd_mcp_check()
        return rc, out.getvalue()

    DEAD = {"speaks_mcp": False, "error": "connection refused", "tools": []}
    LIVE = {"speaks_mcp": True, "protocol": "2025-06-18",
            "tools": ["list_toolsets", "describe_toolset", "call_tool"]}

    def test_each_reachability_failure_is_reported_separately(self):
        """'MCP is broken' is not a diagnosis: these three have three
        different fixes and must not collapse into one line."""
        with tempfile.TemporaryDirectory() as t:
            rc, text = self._check(Path(t), marker=False,
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
            rc, text = self._check(Path(t), marker=True,
                                   procs=["UnrealEditor.exe"], listening=True,
                                   probe_result=self.DEAD)
            self.assertEqual(rc, 1)
            self.assertIn("[NO ] endpoint speaks MCP", text)
            self.assertIn("MCP is NOT reachable", text)

    def test_undeclared_mode_does_not_make_a_live_server_unreachable(self):
        """The regression this split exists for: an earlier version folded
        mode-declaration into readiness and printed 'MCP is NOT reachable;
        tool calls will fail to connect' while the server was answering.
        Declaring the mode is bookkeeping for the NEXT session."""
        with tempfile.TemporaryDirectory() as t:
            rc, text = self._check(Path(t), marker=False,
                                   procs=["UnrealEditor.exe"], listening=True,
                                   probe_result=self.LIVE)
            self.assertEqual(rc, 0)
            self.assertIn("MCP IS REACHABLE", text)
            self.assertNotIn("MCP is NOT reachable", text)
            # ...and the bookkeeping gap is still surfaced, just not as a
            # reachability failure.
            self.assertIn("bookkeeping, not reachability", text)
            self.assertIn("mcp_session.py on", text)

    def test_fully_ready_reports_protocol_and_the_headless_cost(self):
        with tempfile.TemporaryDirectory() as t:
            rc, text = self._check(Path(t), marker=True,
                                   procs=["UnrealEditor.exe"], listening=True,
                                   probe_result=self.LIVE)
            self.assertEqual(rc, 0)
            self.assertIn("2025-06-18", text)
            self.assertIn("3 tool(s)", text)
            self.assertIn("blocked", text)
            self.assertNotIn("bookkeeping", text)


if __name__ == "__main__":
    unittest.main()
