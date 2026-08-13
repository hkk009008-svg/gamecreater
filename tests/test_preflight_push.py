import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import preflight_push as pp


class TestParseGhView(unittest.TestCase):
    def test_good_json(self):
        vis, name = pp.parse_gh_view(
            '{"visibility":"private","nameWithOwner":"me/repo"}')
        self.assertEqual(vis, "PRIVATE")
        self.assertEqual(name, "me/repo")

    def test_garbage(self):
        self.assertEqual(pp.parse_gh_view("not json"), (None, None))
        self.assertEqual(pp.parse_gh_view(""), (None, None))

    def test_missing_fields(self):
        self.assertEqual(pp.parse_gh_view("{}"), (None, None))


class TestGranted(unittest.TestCase):
    def test_exact_line_matches(self):
        self.assertTrue(pp.granted("me/repo", "# note\nme/repo\n"))

    def test_comment_and_other_lines_do_not(self):
        self.assertFalse(pp.granted("me/repo", "# me/repo\nme/other\n"))

    def test_none_name_never_granted(self):
        self.assertFalse(pp.granted(None, "me/repo\n"))


class TestVerdict(unittest.TestCase):
    def test_private_allows(self):
        ok, msg = pp.verdict("PRIVATE", "me/repo", "")
        self.assertTrue(ok)
        self.assertIn("PRIVATE", msg)

    def test_public_blocks_without_grant(self):
        ok, msg = pp.verdict("PUBLIC", "me/repo", "")
        self.assertFalse(ok)
        self.assertIn("BLOCKED", msg)

    def test_public_allowed_with_grant(self):
        ok, _ = pp.verdict("PUBLIC", "me/repo", "me/repo\n")
        self.assertTrue(ok)

    def test_unknown_visibility_blocks_fail_closed(self):
        ok, msg = pp.verdict(None, None, "")
        self.assertFalse(ok)
        self.assertIn("BLOCKED", msg)

    def test_unknown_visibility_with_grant_still_needs_name(self):
        # gh failed entirely -> no name -> grant can't match -> blocked
        ok, _ = pp.verdict(None, None, "me/repo\n")
        self.assertFalse(ok)

    def test_verdict_names_the_grant_file(self):
        ok, msg = pp.verdict("PUBLIC", "me/repo", "me/repo\n",
                             grant_path="/wt/public-grant.txt")
        self.assertTrue(ok)
        self.assertIn("/wt/public-grant.txt", msg)

    def test_block_message_names_the_grant_file(self):
        ok, msg = pp.verdict("PUBLIC", "me/repo", "",
                             grant_path="/wt/public-grant.txt (absent)")
        self.assertFalse(ok)
        self.assertIn("/wt/public-grant.txt", msg)


if __name__ == "__main__":
    unittest.main()
