"""Roblox routing must not fall through to an otherwise valid Unreal binding."""

from __future__ import annotations

import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import engine_run as engine  # noqa: E402
import game_config as gc  # noqa: E402
import session_start as session  # noqa: E402
import unreal_policy as policy  # noqa: E402


def binding_fixture(root: Path) -> gc.GameConfig:
    """Use real temp files, including a tempting but inactive Unreal project."""
    project = root / "Game Project"
    engine_root = root / "Unreal Engine"
    project.mkdir()
    engine_root.mkdir()
    manifest = project / "default.project.json"
    manifest.write_text('{"name":"Test Roblox Game"}', encoding="utf-8")
    uproject = project / "Leftover.uproject"
    uproject.write_text("{}", encoding="utf-8")
    team_now = root / "Team NOW.md"
    team_now.write_text("# Team\n", encoding="utf-8")
    source = root / "GAME.local.md"
    text = f"""# Local test binding
- Game name: Test Roblox Game
- Short slug: test-roblox
- Engine: Roblox Studio
- Current phase: local-build
- Working root: {project}
- Project root: {project}
- Project manifest: {manifest}
- Expected uproject identity: {uproject}
- Engine root: {engine_root}
- Team NOW.md: {team_now}
- Integration owner: Test Release Owner
- Headless engine launch: yes
- Interactive engine launch: yes
- Epic MCP operations: yes
- OpenClaw operations: yes
- Epic MCP port: 8000
- OpenClaw port: 27184
"""
    source.write_text(text, encoding="utf-8")
    return gc.parse_game_config(text, source)


def listener_records(config: gc.GameConfig) -> list[dict]:
    return [{
        "ProcessId": 42,
        "Name": "UnrealEditor.exe",
        "ExecutablePath": str(config.engine_root / "UnrealEditor.exe"),
        "CommandLine": f'"UnrealEditor.exe" "{config.expected_uproject}"',
    }]


class TestRobloxConfig(unittest.TestCase):
    def test_studio_label_selects_manifest_team_state_and_owner(self):
        with tempfile.TemporaryDirectory() as td:
            config = binding_fixture(Path(td))
            self.assertEqual(config.engine_kind, "roblox")
            self.assertEqual(
                config.project_file,
                config.project_root / "default.project.json",
            )
            self.assertEqual(config.project_identity, config.project_file)
            self.assertEqual(config.team_now, Path(td) / "Team NOW.md")
            self.assertEqual(config.integration_owner, "Test Release Owner")
            self.assertTrue(config.project_file.is_file())
            self.assertTrue(config.team_now.is_file())

    def test_no_engine_label_preserves_legacy_unreal_discovery(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            uproject = root / "Legacy.uproject"
            uproject.write_text("{}", encoding="utf-8")
            config = gc.parse_game_config(f"- Project root: {root}\n")
            self.assertEqual(config.engine_kind, "unreal")
            self.assertEqual(config.uproject, uproject)
            self.assertEqual(config.project_identity, uproject)

    def test_roblox_does_not_discover_or_prefer_a_leftover_uproject(self):
        with tempfile.TemporaryDirectory() as td:
            config = binding_fixture(Path(td))
            self.assertTrue(config.expected_uproject.is_file())
            for expected in (config.expected_uproject, None):
                with self.subTest(explicit_identity=expected is not None):
                    candidate = replace(config, expected_uproject=expected)
                    self.assertIsNone(candidate.uproject)
                    self.assertEqual(candidate.project_identity,
                                     config.project_file)
                    # Same files can resolve as Unreal when that is the binding.
                    legacy = replace(candidate, engine_kind="unreal")
                    self.assertEqual(legacy.uproject, config.expected_uproject)


class TestRobloxOrientation(unittest.TestCase):
    def test_reports_manifest_team_and_owner_without_unreal_process_probe(self):
        with tempfile.TemporaryDirectory() as td:
            config = binding_fixture(Path(td))
            with (
                patch.object(session, "load_game_config", return_value=config),
                patch.object(session, "LINES", []) as lines,
                patch.object(session, "WARN", []) as warnings,
                patch.object(engine, "read_mode") as read_mode,
                patch.object(engine.cec, "list_processes") as processes,
            ):
                session.engine_block()
            output = "\n".join(lines)
            self.assertIn("Engine: Roblox Studio", output)
            self.assertIn("source project bound", output)
            self.assertIn(str(config.project_file), output)
            self.assertIn(str(config.team_now), output)
            self.assertIn(config.integration_owner, output)
            self.assertIn("NOT QUERIED", output)
            self.assertEqual(warnings, [])
            read_mode.assert_not_called()
            processes.assert_not_called()

    def test_missing_manifest_is_visible_despite_an_existing_uproject(self):
        with tempfile.TemporaryDirectory() as td:
            config = binding_fixture(Path(td))
            config.project_file.unlink()
            self.assertTrue(config.expected_uproject.is_file())
            with (
                patch.object(session, "load_game_config", return_value=config),
                patch.object(session, "LINES", []) as lines,
                patch.object(session, "WARN", []) as warnings,
                patch.object(engine, "read_mode") as read_mode,
            ):
                session.engine_block()
            self.assertIn("source project UNBOUND", "\n".join(lines))
            self.assertTrue(any("manifest is missing" in item
                                for item in warnings), warnings)
            read_mode.assert_not_called()


class TestRobloxUnrealEntry(unittest.TestCase):
    def test_cli_refuses_every_current_unreal_route_before_dispatch_or_io(self):
        # Exercise actual CLI parsing, including explicit paths and dry-run.
        # The boundary must hold before a handler can enumerate or connect.
        cases = [
            ("mode", []),
            ("epic-mcp-check", []),
            ("headless", ["probe.py"]),
            ("automation", ["^Exact.Test$"]),
            ("data-validation", []),
        ]
        with tempfile.TemporaryDirectory() as td:
            config = binding_fixture(Path(td))
            for command, arguments in cases:
                variants = [arguments]
                if command in {"headless", "automation", "data-validation"}:
                    variants.append(arguments + [
                        "--engine", str(config.engine_root),
                        "--uproject", str(config.expected_uproject),
                        "--dry-run",
                    ])
                for variant in variants:
                    with self.subTest(command=command, arguments=variant):
                        with ExitStack() as stack:
                            stack.enter_context(patch.object(
                                engine, "load_game_config", return_value=config))
                            forbidden = [stack.enter_context(patch.object(
                                engine, name, return_value=91)) for name in (
                                    "cmd_mode", "cmd_epic_mcp_check",
                                    "cmd_native", "cmd_headless", "read_mode",
                                )]
                            forbidden.extend([
                                stack.enter_context(patch.object(
                                    engine.subprocess, "Popen")),
                                stack.enter_context(patch.object(
                                    engine.socket, "create_connection")),
                                stack.enter_context(patch.object(
                                    engine.cec, "list_processes")),
                            ])
                            stderr = stack.enter_context(redirect_stderr(StringIO()))
                            stack.enter_context(redirect_stdout(StringIO()))
                            code = engine.main(["engine_run.py", command, *variant])
                        self.assertEqual(code, 2)
                        self.assertIn("active Engine is roblox", stderr.getvalue())
                        for operation in forbidden:
                            operation.assert_not_called()

    def test_changing_binding_back_to_unreal_reaches_the_requested_handler(self):
        # The reject test must not pass merely because the CLI cannot dispatch.
        cases = [
            (["mode"], "cmd_mode"),
            (["epic-mcp-check"], "cmd_epic_mcp_check"),
            (["headless", "probe.py"], "cmd_headless"),
            (["automation", "^Exact.Test$"], "cmd_native"),
            (["data-validation"], "cmd_native"),
        ]
        with tempfile.TemporaryDirectory() as td:
            config = replace(binding_fixture(Path(td)), engine_kind="unreal")
            for arguments, handler_name in cases:
                with self.subTest(arguments=arguments):
                    with (
                        patch.object(engine, "load_game_config", return_value=config),
                        patch.object(engine, handler_name, return_value=91) as handler,
                        redirect_stdout(StringIO()),
                        redirect_stderr(StringIO()),
                    ):
                        code = engine.main(["engine_run.py", *arguments])
                    self.assertEqual(code, 91)
                    handler.assert_called_once()


class TestRobloxUnrealPolicy(unittest.TestCase):
    def test_launch_and_explicit_resolution_refuse_despite_all_allowed_flags(self):
        with tempfile.TemporaryDirectory() as td:
            config = binding_fixture(Path(td))
            for interactive in (False, True):
                with self.subTest(interactive=interactive):
                    refusal = policy.launch_binding_refusal(
                        config, config.engine_root, config.expected_uproject,
                        interactive=interactive,
                    )
                    self.assertIn("active Engine is roblox", refusal)
            with self.assertRaisesRegex(policy.UnrealPolicyError,
                                        "active Engine is roblox"):
                policy.resolve_engine_project(
                    config.engine_root, config.expected_uproject, config=config)

            legacy = replace(config, engine_kind="unreal")
            self.assertIsNone(policy.launch_binding_refusal(
                legacy, config.engine_root, config.expected_uproject))
            self.assertEqual(policy.resolve_engine_project(
                config.engine_root, config.expected_uproject, config=legacy),
                (config.engine_root.resolve(), config.expected_uproject.resolve()))

    def test_live_channels_refuse_before_listener_probe_with_valid_legacy_identity(self):
        with tempfile.TemporaryDirectory() as td:
            config = binding_fixture(Path(td))
            rows = listener_records(config)
            for channel in ("epic-mcp", "openclaw"):
                with self.subTest(channel=channel):
                    with patch.object(policy, "listener_identity_refusal") as listener:
                        refusal = policy.channel_refusal(config, channel, records=rows)
                    self.assertIn("active Engine is roblox", refusal)
                    listener.assert_not_called()
                    # Same granted flags/ports/project can pass in Unreal mode.
                    self.assertIsNone(policy.channel_refusal(
                        replace(config, engine_kind="unreal"), channel, records=rows))


if __name__ == "__main__":
    unittest.main()
