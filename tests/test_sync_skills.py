import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sync_skills as ss


class TestParseGameLocal(unittest.TestCase):
    def test_reads_root_and_slug(self):
        text = ("- Working root (scripts, docs — a git repo): D:/work\n"
                "- Short slug (used for skill mirroring as `game-<slug>-*`): mygame\n")
        root, slug = ss.parse_game_local(text)
        self.assertEqual(root, Path("D:/work"))
        self.assertEqual(slug, "mygame")

    def test_placeholders_read_as_unset(self):
        text = ("- Working root (a git repo): <path>\n"
                "- Short slug: <slug>\n")
        self.assertEqual(ss.parse_game_local(text), (None, None))

    def test_slug_is_sanitized(self):
        _, slug = ss.parse_game_local("- Short slug: My Game!\n")
        self.assertEqual(slug, "mygame")


class TestMirrorAndDrift(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.saved = (ss.ROOT, ss.CANONICAL, ss.SURFACE, ss.GAME_LOCAL)
        ss.ROOT = root
        ss.CANONICAL = root / "skills"
        ss.SURFACE = root / ".claude" / "skills"
        ss.GAME_LOCAL = root / "GAME.local.md"
        body = ss.CANONICAL / "harness" / "do-a-thing"
        body.mkdir(parents=True)
        (body / "SKILL.md").write_text("---\nname: do-a-thing\n---\nbody\n",
                                       encoding="utf-8")

    def tearDown(self):
        ss.ROOT, ss.CANONICAL, ss.SURFACE, ss.GAME_LOCAL = self.saved
        self.tmp.cleanup()

    def test_missing_surface_is_drift(self):
        problems = ss.drift(ss.desired_mirror(), ss.current_surface())
        self.assertTrue(any("missing" in p for p in problems))

    def test_write_then_check_clean(self):
        ss.write_mirror(ss.desired_mirror())
        self.assertEqual(ss.drift(ss.desired_mirror(), ss.current_surface()),
                         [])

    def test_content_drift_detected(self):
        ss.write_mirror(ss.desired_mirror())
        (ss.SURFACE / "do-a-thing" / "SKILL.md").write_text("tampered",
                                                            encoding="utf-8")
        problems = ss.drift(ss.desired_mirror(), ss.current_surface())
        self.assertTrue(any("drift" in p for p in problems))

    def test_orphan_detected_and_removed_on_write(self):
        ss.write_mirror(ss.desired_mirror())
        orphan = ss.SURFACE / "stale-skill"
        orphan.mkdir()
        (orphan / "SKILL.md").write_text("old", encoding="utf-8")
        problems = ss.drift(ss.desired_mirror(), ss.current_surface())
        self.assertTrue(any("orphan" in p for p in problems))
        ss.write_mirror(ss.desired_mirror())
        self.assertFalse(orphan.exists())

    def test_game_skills_mirrored_with_prefix(self):
        game = Path(self.tmp.name) / "gamerepo"
        gskill = game / ".claude" / "skills" / "fix-a-widget"
        gskill.mkdir(parents=True)
        (gskill / "SKILL.md").write_text("game body", encoding="utf-8")
        ss.GAME_LOCAL.write_text(
            f"- Working root (a git repo): {game}\n- Short slug: demo\n",
            encoding="utf-8")
        desired = ss.desired_mirror()
        self.assertIn("game-demo-fix-a-widget", desired)
        ss.write_mirror(desired)
        self.assertTrue(
            (ss.SURFACE / "game-demo-fix-a-widget" / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
