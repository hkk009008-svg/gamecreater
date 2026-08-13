import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sync_skills as ss

HARNESS_ROOT = Path(__file__).resolve().parent.parent


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
        self.saved = (ss.ROOT, ss.CANONICAL, ss.SURFACES, ss.SURFACE, ss.GAME_LOCAL)
        ss.ROOT = root
        ss.CANONICAL = root / "skills"
        ss.SURFACES = (root / ".claude" / "skills", root / ".agents" / "skills")
        ss.SURFACE = ss.SURFACES[0]
        ss.GAME_LOCAL = root / "GAME.local.md"
        body = ss.CANONICAL / "harness" / "do-a-thing"
        body.mkdir(parents=True)
        (body / "SKILL.md").write_text("---\nname: do-a-thing\n---\nbody\n",
                                       encoding="utf-8")

    def tearDown(self):
        ss.ROOT, ss.CANONICAL, ss.SURFACES, ss.SURFACE, ss.GAME_LOCAL = self.saved
        self.tmp.cleanup()

    def test_missing_surface_is_drift(self):
        problems = ss.drift(ss.desired_mirror(), ss.current_surface())
        self.assertTrue(any("missing" in p for p in problems))

    def test_write_then_check_clean(self):
        ss.write_mirror(ss.desired_mirror())
        for s in ss.SURFACES:
            self.assertEqual(ss.drift(ss.desired_mirror(), ss.current_surface(s)),
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

    def test_game_canonical_layout_is_preferred(self):
        game = Path(self.tmp.name) / "gamerepo"
        gskill = game / "skills" / "harness" / "fix-a-widget"
        gskill.mkdir(parents=True)
        (gskill / "SKILL.md").write_text("canonical game body",
                                         encoding="utf-8")
        stale = game / ".claude" / "skills" / "fix-a-widget"
        stale.mkdir(parents=True)
        (stale / "SKILL.md").write_text("stale generated copy",
                                        encoding="utf-8")
        ss.GAME_LOCAL.write_text(
            f"- Working root (a git repo): {game}\n- Short slug: demo\n",
            encoding="utf-8")
        desired = ss.desired_mirror()
        self.assertEqual(
            desired["game-demo-fix-a-widget"].read_text(encoding="utf-8"),
            "canonical game body")

    def test_identical_harness_copy_is_not_reprefixed(self):
        game = Path(self.tmp.name) / "gamerepo"
        copy = game / "skills" / "harness" / "do-a-thing"
        copy.mkdir(parents=True)
        (copy / "SKILL.md").write_bytes(
            (ss.CANONICAL / "harness" / "do-a-thing" / "SKILL.md").read_bytes())
        ss.GAME_LOCAL.write_text(
            f"- Working root (a git repo): {game}\n- Short slug: demo\n",
            encoding="utf-8")
        desired = ss.desired_mirror()
        self.assertNotIn("game-demo-do-a-thing", desired)
        self.assertIn("do-a-thing", desired)

    def test_modified_harness_copy_is_kept_as_game_override(self):
        game = Path(self.tmp.name) / "gamerepo"
        copy = game / "skills" / "harness" / "do-a-thing"
        copy.mkdir(parents=True)
        (copy / "SKILL.md").write_text("game-specific tighter binding\n",
                                       encoding="utf-8")
        ss.GAME_LOCAL.write_text(
            f"- Working root (a git repo): {game}\n- Short slug: demo\n",
            encoding="utf-8")
        desired = ss.desired_mirror()
        self.assertIn("game-demo-do-a-thing", desired)
        self.assertIn("do-a-thing", desired)


class TestSessionRouter(unittest.TestCase):
    def test_session_start_builds_the_generated_surface(self):
        text = (HARNESS_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        start = text.split("## Work from skills")[0]
        self.assertIn("sync_skills.py", start)

    def test_work_from_skills_names_the_canonical_tree(self):
        text = (HARNESS_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        work = text.split("## Work from skills")[1].split("## Authorization")[0]
        self.assertIn("`skills/", work)

    def test_frontmatter_name_matches_directory(self):
        for body in sorted((HARNESS_ROOT / "skills").glob("*/*/SKILL.md")):
            text = body.read_text(encoding="utf-8")
            m = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
            self.assertIsNotNone(m, body)
            self.assertEqual(m.group(1).strip(), body.parent.name)

    def test_category_readmes_exist_for_retirement(self):
        for tier in ("harness", "method", "lifecycle"):
            readme = HARNESS_ROOT / "skills" / tier / "README.md"
            self.assertTrue(readme.is_file(), readme)
            self.assertIn("tombstone", readme.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
