from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import game_config as gc


class TestGameConfig(unittest.TestCase):
    def test_parses_real_label_shapes_and_windows_paths(self):
        text = """# local binding
- Game name: Example Game
- Short slug (used for mirroring): My Game!
- Current phase: RST-02
- Working root (scripts, docs — a git repo): D:/Work Root
- Project root (engine project: content, saved): D:/Project Root
- Expected uproject identity: D:/Project Root/Example.uproject
- Engine root: D:/UE_5.8
- Evidence root: D:/Work Root/evidence
- Historical read-only roots: D:/OldGame, D:/Archive
- Preserved game skill sources: oldgame=D:/Archive, Earlier Game=D:/Older
- Headless engine launch: yes
- Interactive engine launch: no
- Epic MCP operations: yes
- OpenClaw operations: no
- Epic MCP port: 8000
- OpenClaw port: 27184
- NOW.md: D:/Work Root/game/NOW.md
- Lessons inbox: D:/Work Root/game/LESSONS.md
"""
        c = gc.parse_game_config(text, Path("binding.md"))
        self.assertEqual(c.source, Path("binding.md"))
        self.assertEqual(c.name, "Example Game")
        self.assertEqual(c.slug, "mygame")
        self.assertEqual(c.phase, "RST-02")
        self.assertEqual(c.working_root, Path("D:/Work Root"))
        self.assertEqual(c.project_root, Path("D:/Project Root"))
        self.assertEqual(
            c.expected_uproject, Path("D:/Project Root/Example.uproject"))
        self.assertEqual(c.engine_root, Path("D:/UE_5.8"))
        self.assertEqual(c.evidence_root, Path("D:/Work Root/evidence"))
        self.assertEqual(
            c.historical_roots,
            (Path("D:/OldGame"), Path("D:/Archive")),
        )
        self.assertEqual(
            c.preserved_game_skill_sources,
            (("oldgame", Path("D:/Archive")),
             ("earliergame", Path("D:/Older"))),
        )
        self.assertTrue(c.headless_launch_allowed)
        self.assertFalse(c.interactive_launch_allowed)
        self.assertTrue(c.epic_mcp_allowed)
        self.assertFalse(c.openclaw_allowed)
        self.assertEqual(c.epic_mcp_port, 8000)
        self.assertEqual(c.openclaw_port, 27184)
        self.assertEqual(c.now, Path("D:/Work Root/game/NOW.md"))
        self.assertEqual(c.lessons, Path("D:/Work Root/game/LESSONS.md"))

    def test_placeholders_and_missing_fields_are_unset(self):
        c = gc.parse_game_config(
            "- Short slug: <slug>\n- Project root: <project path>\n")
        self.assertIsNone(c.slug)
        self.assertIsNone(c.project_root)
        self.assertIsNone(c.engine_root)

    def test_uproject_requires_one_immediate_match(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = gc.GameConfig(source=root / "GAME.local.md", project_root=root)
            self.assertIsNone(c.uproject)
            first = root / "Example.uproject"
            first.write_text("{}", encoding="utf-8")
            self.assertEqual(c.uproject, first)
            (root / "Other.uproject").write_text("{}", encoding="utf-8")
            self.assertIsNone(c.uproject)

    def test_project_root_may_name_the_uproject_directly(self):
        c = gc.GameConfig(
            source=Path("GAME.local.md"),
            project_root=Path("D:/Project/Example.uproject"),
        )
        self.assertEqual(c.uproject, Path("D:/Project/Example.uproject"))
        self.assertEqual(c.project_dir, Path("D:/Project"))
        self.assertEqual(c.evidence_root,
                         Path("D:/Project/Experiments"))

    def test_directory_project_root_is_its_own_project_dir(self):
        root = Path("D:/ExampleGame")
        c = gc.GameConfig(source=Path("binding.md"), project_root=root)
        self.assertEqual(c.project_dir, root)

    def test_expected_identity_exists_before_the_project_file_does(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            expected = root / "FutureGame.uproject"
            c = gc.GameConfig(
                source=root / "binding.md",
                project_root=root,
                expected_uproject=expected,
            )
            self.assertEqual(c.project_identity, expected)
            self.assertIsNone(c.uproject)

    def test_non_yes_no_and_invalid_ports_never_become_authority(self):
        c = gc.parse_game_config(
            "- Headless engine launch: maybe\n"
            "- Epic MCP operations: enabled\n"
            "- Epic MCP port: 70000\n"
        )
        self.assertIsNone(c.headless_launch_allowed)
        self.assertIsNone(c.epic_mcp_allowed)
        self.assertIsNone(c.epic_mcp_port)


if __name__ == "__main__":
    unittest.main()
