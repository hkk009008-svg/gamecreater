"""Real filesystem checks for the read-only project knowledge extractor."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from game_config import GameConfig
import roblox_team as team


class TestRobloxInventory(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[GameConfig, Path]:
        game, harness = root / "game", root / "harness"
        (game / "src").mkdir(parents=True)
        (game / "src" / "Main.server.luau").write_bytes(b"return 42\n")
        (game / "evidence" / "actual-check").mkdir(parents=True)
        (game / "evidence" / "actual-check" / "result.json").write_text('{"status":"pass"}')
        (game / "build").mkdir()
        (game / "build" / "Example.rbxlx").write_bytes(b"saved place bytes")
        manifest = game / "default.project.json"
        manifest.write_text(json.dumps({"tree": {"ServerScriptService": {"$path": "src"}}}))
        for name in ("NOW.md", "LESSONS.md"):
            (game / name).write_text("Current project state\n")
        for name in team.TEAM_FILES:
            target = harness / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("Team source\n")
        config = GameConfig(source=harness / "GAME.local.md", engine_kind="roblox",
                            name="Example", working_root=game, project_root=game,
                            project_file=manifest, now=game / "NOW.md",
                            lessons=game / "LESSONS.md", team_now=harness / "team/NOW.md",
                            integration_owner="Integrator")
        return config, harness

    def test_index_fingerprints_actual_source_and_labels_unhashed_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            config, harness = self.fixture(Path(td))
            self.assertEqual(team.check_setup(config, harness), [])
            before = {p: p.read_bytes() for p in config.project_root.rglob("*") if p.is_file()}
            report = team.inventory_project(config)
            rows = {row["path"]: row for row in report["files"]}
            self.assertEqual(rows["src/Main.server.luau"]["sha256"], hashlib.sha256(b"return 42\n").hexdigest())
            self.assertNotIn("sha256", rows["build/Example.rbxlx"])
            self.assertEqual(report["evidenceDirectories"], {"actual-check": 1})
            self.assertEqual(report["sourceMappings"], [{"instance": "ServerScriptService", "path": "src"}])
            self.assertFalse(report["atomicSnapshot"])
            self.assertEqual(report["errors"], [])
            self.assertEqual({p: p.read_bytes() for p in before}, before)
            output = harness / "team/snapshot.local.json"
            team.write_inventory(report, output, harness)
            self.assertEqual(json.loads(output.read_text())["fileCount"], len(before))

    def test_missing_or_escaping_mapped_source_rejects_setup(self):
        with tempfile.TemporaryDirectory() as td:
            config, harness = self.fixture(Path(td))
            for raw in ("missing", "../outside"):
                with self.subTest(raw=raw):
                    config.project_file.write_text(json.dumps({"tree": {"Game": {"$path": raw}}}))
                    self.assertTrue(team.check_setup(config, harness))

    def test_snapshot_never_overwrites_and_never_writes_outside_harness(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config, harness = self.fixture(root)
            output = harness / "snap.local.json"
            output.write_text("original evidence")
            with self.assertRaises(FileExistsError):
                team.write_inventory({"new": True}, output, harness)
            self.assertEqual(output.read_text(), "original evidence")
            for target in (root / "outside.local.json", harness / "tracked.json"):
                with self.subTest(target=target), self.assertRaises(ValueError):
                    team.write_inventory({}, target, harness)
                self.assertFalse(target.exists())

    def test_unknown_engine_cannot_inventory_a_neighbor_game(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                team.inventory_project(GameConfig(source=Path(td), project_root=Path(td)))


if __name__ == "__main__":
    unittest.main()
