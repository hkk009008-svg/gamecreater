import io
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout
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

    def test_case_insensitive_matches(self):
        self.assertTrue(pp.granted("Me/Repo", "me/repo\n"))
        self.assertTrue(pp.granted("me/repo", "ME/REPO\n"))

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


class TestRepoNameFromGit(unittest.TestCase):
    def test_parses_https_url(self):
        with unittest.mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = unittest.mock.Mock(
                returncode=0,
                stdout="https://github.com/owner/my-repo.git\n")
            self.assertEqual(pp.repo_name_from_git("."), "owner/my-repo")
            self.assertEqual(
                mock_run.call_args.args[0],
                ["git", "remote", "get-url", "--push", "--all", "origin"])

    def test_parses_ssh_url(self):
        ssh_url = "git" + chr(64) + "github.com:owner/my-repo.git\n"
        with unittest.mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = unittest.mock.Mock(
                returncode=0,
                stdout=ssh_url)
            self.assertEqual(pp.repo_name_from_git("."), "owner/my-repo")

    def test_resolves_the_requested_remote_not_origin(self):
        with unittest.mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = unittest.mock.Mock(
                returncode=0,
                stdout="https://github.com/other/upstream.git\n")
            self.assertEqual(
                pp.repo_name_from_git(".", "upstream"), "other/upstream")
            self.assertEqual(
                mock_run.call_args.args[0],
                ["git", "remote", "get-url", "--push", "--all", "upstream"])

    def test_multiple_pushurls_block_before_private_visibility_can_allow(self):
        private_url = "https://github.com/owner/private-first.git"
        public_url = "https://github.com/owner/public-second.git"
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            subprocess.run(
                ["git", "init", "--quiet", str(repo)], check=True,
                capture_output=True, text=True)
            subprocess.run(
                ["git", "-C", str(repo), "remote", "add", "origin",
                 private_url], check=True, capture_output=True, text=True)
            for url in (private_url, public_url):
                subprocess.run(
                    ["git", "-C", str(repo), "remote", "set-url", "--add",
                     "--push", "origin", url], check=True,
                    capture_output=True, text=True)

            real_run = subprocess.run
            gh_calls = []

            def controlled_run(command, *args, **kwargs):
                if command[0] == "gh":
                    gh_calls.append(command)
                    return subprocess.CompletedProcess(
                        command, 0,
                        '{"visibility":"PRIVATE",'
                        '"nameWithOwner":"owner/private-first"}\n', "")
                return real_run(command, *args, **kwargs)

            output = io.StringIO()
            with unittest.mock.patch.object(
                    pp.subprocess, "run", side_effect=controlled_run):
                with redirect_stdout(output):
                    result = pp.main(
                        ["preflight_push", str(repo), "origin"])

        self.assertEqual(result, 1)
        self.assertEqual(gh_calls, [])
        self.assertIn("PUSH BLOCKED", output.getvalue())

    def test_single_pushurl_resolves_normally(self):
        private_url = "https://github.com/owner/private-only.git"
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            subprocess.run(
                ["git", "init", "--quiet", str(repo)], check=True,
                capture_output=True, text=True)
            subprocess.run(
                ["git", "-C", str(repo), "remote", "add", "origin",
                 private_url], check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "-C", str(repo), "remote", "set-url", "--add",
                 "--push", "origin", private_url], check=True,
                capture_output=True, text=True)

            self.assertEqual(
                pp.repo_name_from_git(str(repo)), "owner/private-only")

    def test_fails_gracefully_on_missing_git(self):
        with unittest.mock.patch("subprocess.run", side_effect=OSError("no git")):
            self.assertIsNone(pp.repo_name_from_git("."))

    def test_non_github_or_local_destination_is_not_misbound_to_github(self):
        for url in ("https://gitlab.com/owner/my-repo.git",
                    "git@example.com:owner/my-repo.git",
                    "D:/mirrors/owner/my-repo.git"):
            with self.subTest(url=url):
                self.assertIsNone(pp.repo_name_from_url(url))


if __name__ == "__main__":
    unittest.main()
