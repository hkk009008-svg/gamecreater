import io
import json
import subprocess
import sys
import tempfile
import unittest
import os
import unittest.mock
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import preflight_push as pp


class TestRecursionConfig(unittest.TestCase):
    def refusal(self, stdout="", *, returncode=0, stderr=""):
        with unittest.mock.patch.object(
                pp.subprocess, "run", return_value=subprocess.CompletedProcess(
                    [], returncode, stdout, stderr)) as run:
            result = pp.recursion_config_refusal("fixture checkout")
        self.assertEqual(run.call_args.args[0], [
            "git", "config", "--null", "--get-regexp", pp.RECURSION_CONFIG_PATTERN])
        self.assertEqual(run.call_args.kwargs["cwd"], "fixture checkout")
        self.assertEqual(run.call_args.kwargs["timeout"], 10)
        return result

    def test_absence_and_recognized_non_pushing_modes(self):
        self.assertIsNone(self.refusal(returncode=1))
        for key in ("push.recursesubmodules", "submodule.recurse"):
            for value in ("", "false", "no", "off", "0", "FALSE"):
                with self.subTest(key=key, value=value):
                    self.assertIsNone(self.refusal(f"{key}\n{value}\0"))
        self.assertIsNone(self.refusal("push.recursesubmodules\ncheck\0"))

    def test_enabling_modes_and_boolean_without_value_refuse(self):
        for key in ("push.recursesubmodules", "submodule.recurse"):
            for value in ("true", "yes", "on", "1"):
                with self.subTest(key=key, value=value):
                    self.assertIn("unchecked", self.refusal(f"{key}\n{value}\0"))
            self.assertIn("unchecked", self.refusal(f"{key}\0"))
        for value in ("on-demand", "only"):
            self.assertIn("unchecked", self.refusal(f"push.recursesubmodules\n{value}\0"))

    def test_each_key_uses_last_value_but_false_push_does_not_hide_submodule(self):
        self.assertIsNone(self.refusal(
            "push.recursesubmodules\non-demand\0push.recursesubmodules\nfalse\0"))
        self.assertIn("unchecked", self.refusal(
            "push.recursesubmodules\nfalse\0submodule.recurse\ntrue\0"))

    def test_unknown_failed_and_malformed_lookup_refuse_without_value_leak(self):
        for output, code, error in (
                ("", 0, ""), ("", 1, "unexpected diagnostic"),
                ("push.recursesubmodules\nfalse\0", 0, "unexpected diagnostic"),
                ("", 2, ""), ("push.recursesubmodules\nfalse", 0, ""),
                ("unexpected.key\nfalse\0", 0, ""),
                ("push.recursesubmodules\nprivate-fixture-value\0", 0, ""),
                ("submodule.recurse\ncheck\0", 0, "")):
            with self.subTest(output=output, code=code):
                result = self.refusal(output, returncode=code, stderr=error)
                self.assertIsInstance(result, str)
                self.assertNotIn("private-fixture-value", result)
        for error in (OSError("missing git"), subprocess.TimeoutExpired("git", 10),
                      UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad config")):
            with self.subTest(error=error):
                with unittest.mock.patch.object(pp.subprocess, "run", side_effect=error):
                    self.assertIn("could not inspect", pp.recursion_config_refusal("."))


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

    def test_all_recognized_visibilities(self):
        for visibility in ("PUBLIC", "PRIVATE", "INTERNAL", "private"):
            with self.subTest(visibility=visibility):
                self.assertEqual(pp.parse_gh_view(json.dumps({
                    "visibility": visibility,
                    "nameWithOwner": "Owner-Name/.repo_name-2",
                })), (visibility.upper(), "Owner-Name/.repo_name-2"))

    def test_malformed_json_types_and_schema_fail_closed(self):
        replies = [
            "null", "[]", '[{"visibility":"PRIVATE"}]',
            '"PRIVATE"', "true", "17",
            '{"visibility":"PRIVATE"}',
            '{"nameWithOwner":"me/repo"}',
            '{"visibility":"PRIVATE","nameWithOwner":"me/repo","extra":1}',
            '{"visibility":"PRIVATE","nameWithOwner":"me/repo"} trailing',
            '{"visibility":"PRIVATE","nameWithOwner":"me/repo",}',
        ]
        for raw in replies:
            with self.subTest(raw=raw):
                self.assertEqual(pp.parse_gh_view(raw), (None, None))
        for raw in (None, [], {}, 1):
            with self.subTest(raw=raw):
                self.assertEqual(pp.parse_gh_view(raw), (None, None))

    def test_duplicate_json_keys_rejected_in_both_orders(self):
        for raw in (
                '{"visibility":"PRIVATE","visibility":"PUBLIC",'
                '"nameWithOwner":"me/repo"}',
                '{"visibility":"PUBLIC","visibility":"PRIVATE",'
                '"nameWithOwner":"me/repo"}',
                '{"visibility":"PRIVATE","nameWithOwner":"other/repo",'
                '"nameWithOwner":"me/repo"}',
                '{"visibility":"PRIVATE","nameWithOwner":"me/repo",'
                '"nameWithOwner":"other/repo"}'):
            with self.subTest(raw=raw):
                self.assertEqual(pp.parse_gh_view(raw), (None, None))

    def test_unrecognized_and_malformed_visibility_reject_entire_reply(self):
        for visibility in (None, True, 1, [], {}, "", "UNKNOWN", "UNLISTED",
                           " PRIVATE", "PRIVATE ", "PRIVATE\n", "PRİVATE",
                           "prıvate"):
            with self.subTest(visibility=visibility):
                self.assertEqual(pp.parse_gh_view(json.dumps({
                    "visibility": visibility, "nameWithOwner": "me/repo",
                })), (None, None))

    def test_noncanonical_identity_rejects_entire_reply(self):
        # Includes host spoofing, separators, controls, URL syntax and Unicode.
        for name in (None, True, 1, [], {}, "", "repo", "me/repo/extra",
                     "github.com/me/repo", "https://github.com/me/repo",
                     "me@github.com/repo", "github.com:me/repo",
                     " me/repo", "me/repo ", "me/repo\n", "me/rep\to",
                     "me/repo\x00", "me/repo\\evil", "mе/repo", "me/répo",
                     "-me/repo", "me-/repo", "me.name/repo", "me_name/repo",
                     "me/.", "me/..", "a" * 40 + "/repo", "me/" + "a" * 101):
            with self.subTest(name=name):
                self.assertEqual(pp.parse_gh_view(json.dumps({
                    "visibility": "PRIVATE", "nameWithOwner": name,
                })), (None, None))


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

    def test_noncanonical_name_never_granted(self):
        for name in (" me/repo", "me/repo ", "me/repo\n", "me/repo/extra"):
            with self.subTest(name=name):
                self.assertFalse(pp.granted(name, name + "\n"))


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
        ok, msg = pp.verdict("PUBLIC", "me/repo", "me/repo\n")
        self.assertTrue(ok)
        self.assertIn("per-act user authorization", msg)

    def test_internal_requires_explicit_grant(self):
        self.assertFalse(pp.verdict("INTERNAL", "me/repo", "")[0])
        self.assertTrue(pp.verdict("INTERNAL", "me/repo", "me/repo\n")[0])

    def test_private_allow_still_names_per_act_authorization(self):
        self.assertIn("per-act user authorization",
                      pp.verdict("PRIVATE", "me/repo", "")[1])

    def test_unknown_visibility_blocks_fail_closed(self):
        ok, msg = pp.verdict(None, None, "")
        self.assertFalse(ok)
        self.assertIn("BLOCKED", msg)

    def test_unknown_visibility_with_grant_still_needs_name(self):
        # gh failed entirely -> no name -> grant can't match -> blocked
        ok, _ = pp.verdict(None, None, "me/repo\n")
        self.assertFalse(ok)

    def test_matching_grant_never_bypasses_unknown_or_malformed_visibility(self):
        for visibility in (None, "", "UNKNOWN", "UNLISTED", "private",
                           "PRIVATE ", True, [], {}):
            with self.subTest(visibility=visibility):
                ok, msg = pp.verdict(visibility, "me/repo", "me/repo\n")
                self.assertFalse(ok)
                self.assertIn("PUSH BLOCKED", msg)
                self.assertIn("grant cannot replace", msg)

    def test_private_and_public_grants_require_a_canonical_identity(self):
        for visibility in ("PRIVATE", "PUBLIC", "INTERNAL"):
            for name in (None, " me/repo", "me/repo\n", "me/repo/extra"):
                with self.subTest(visibility=visibility, name=name):
                    ok, msg = pp.verdict(visibility, name, "me/repo\n")
                    self.assertFalse(ok)
                    self.assertIn("identity", msg)

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
            self.assertEqual(mock_run.call_args.kwargs["cwd"], ".")

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

    def test_failed_or_ambiguous_git_output_never_resolves(self):
        for code, stdout in ((1, "https://github.com/me/repo.git\n"),
                             (0, ""),
                             (0, "https://github.com/me/repo.git\n"
                              "https://github.com/me/other.git\n")):
            with self.subTest(code=code, stdout=stdout):
                with unittest.mock.patch.object(
                        pp.subprocess, "run", return_value=
                        subprocess.CompletedProcess([], code, stdout, "")):
                    self.assertIsNone(pp.repo_name_from_git("."))

    def test_non_github_or_local_destination_is_not_misbound_to_github(self):
        for url in ("https://gitlab.com/owner/my-repo.git",
                    "git@example.com:owner/my-repo.git",
                    "D:/mirrors/owner/my-repo.git",
                    "https://github.com.evil/owner/my-repo.git",
                    "https://gıthub.com/owner/my-repo.git",
                    "https://github.com@evil/owner/my-repo.git",
                    "https://github.com/owner/../my-repo.git",
                    "https://github.com/owner/my-repo.git/extra"):
            with self.subTest(url=url):
                self.assertIsNone(pp.repo_name_from_url(url))


class TestMain(unittest.TestCase):
    def run_main(self, raw, *, returncode=0, gh_error=None, grant=None,
                 grant_error=None, resolver_error=None):
        """Only local temporary grants and controlled git/gh seams are used."""
        with tempfile.TemporaryDirectory() as temp_dir:
            grant_file = Path(temp_dir) / "public-grant.txt"
            if grant is not None:
                grant_file.write_bytes(grant.encode("utf-8"))
            seen = []

            def controlled_run(command, **kwargs):
                seen.append((command, kwargs))
                if command == ["git", "config", "--null", "--get-regexp",
                               pp.RECURSION_CONFIG_PATTERN]:
                    return subprocess.CompletedProcess(command, 1, "", "")
                if command == ["git", "remote", "get-url", "--push",
                               "--all", "release-remote"]:
                    return subprocess.CompletedProcess(
                        command, 0, "https://github.com/me/repo.git\n", "")
                self.assertEqual(command, ["gh", "repo", "view", "https://github.com/me/repo",
                                           "--json", "visibility,nameWithOwner"])
                if gh_error is not None:
                    raise gh_error
                return subprocess.CompletedProcess(command, returncode, raw, "")

            output = io.StringIO()
            with unittest.mock.patch.object(
                    pp.subprocess, "run", side_effect=controlled_run), \
                    unittest.mock.patch.object(
                        pp, "resolve_gitignored", return_value=grant_file,
                        side_effect=resolver_error) as resolve:
                with redirect_stdout(output):
                    if grant_error is None:
                        result = pp.main(["preflight_push", "checkout with spaces",
                                          "release-remote"])
                    else:
                        with unittest.mock.patch.object(
                                Path, "read_text", side_effect=grant_error):
                            result = pp.main(
                                ["preflight_push", "checkout with spaces",
                                 "release-remote"])
            return result, output.getvalue(), seen, resolve.call_count, str(grant_file)

    def test_known_private_allows_without_grant_and_preserves_remote_and_cwd(self):
        result, output, seen, _, _ = self.run_main(
            '{"visibility":"PRIVATE","nameWithOwner":"me/repo"}')
        self.assertEqual(result, 0)
        self.assertIn("per-act user authorization", output)
        self.assertEqual([command for command, _ in seen], [
            ["git", "config", "--null", "--get-regexp", pp.RECURSION_CONFIG_PATTERN],
            ["git", "remote", "get-url", "--push", "--all", "release-remote"],
            ["gh", "repo", "view", "https://github.com/me/repo", "--json", "visibility,nameWithOwner"],
        ])
        for _, kwargs in seen:
            self.assertEqual(kwargs.get("cwd"), "checkout with spaces")
            self.assertTrue(kwargs["capture_output"])
            self.assertTrue(kwargs["text"])

    def test_enterprise_default_cannot_redirect_github_com_visibility_query(self):
        with unittest.mock.patch.dict(os.environ, {"GH_HOST": "enterprise.fixture.invalid"}):
            result, output, seen, _, _ = self.run_main(
                '{"visibility":"PRIVATE","nameWithOwner":"me/repo"}')
        self.assertEqual(result, 0, output)
        self.assertEqual(seen[2][0][3], "https://github.com/me/repo")

    def test_recursive_config_refuses_before_remote_or_network_lookups(self):
        for output, code in (("push.recursesubmodules\non-demand\0", 0),
                             ("submodule.recurse\ntrue\0", 0), ("", 2)):
            with self.subTest(output=output, code=code):
                with unittest.mock.patch.object(
                        pp.subprocess, "run", return_value=subprocess.CompletedProcess(
                            [], code, output, "")) as run, redirect_stdout(io.StringIO()):
                    self.assertEqual(pp.main(["preflight_push", "fixture", "origin"]), 1)
                self.assertEqual(run.call_count, 1)
                self.assertEqual(run.call_args.args[0][1], "config")

    def test_known_public_explicit_grant_allows_and_names_resolved_path(self):
        result, output, _, _, grant_path = self.run_main(
            '{"visibility":"PUBLIC","nameWithOwner":"ME/REPO"}',
            grant="# exact repo grant\nme/repo\n")
        self.assertEqual(result, 0)
        self.assertIn(grant_path, output)
        self.assertIn("per-act user authorization", output)

    def test_known_public_blocks_without_matching_grant(self):
        result, output, _, _, grant_path = self.run_main(
            '{"visibility":"PUBLIC","nameWithOwner":"me/repo"}',
            grant="me/another-repo\n")
        self.assertEqual(result, 1)
        self.assertIn("PUSH BLOCKED", output)
        self.assertIn(grant_path, output)

    def test_invalid_reply_cannot_use_matching_grant(self):
        for raw in (
                "null", "[]", "not json",
                '{"visibility":"UNKNOWN","nameWithOwner":"me/repo"}',
                '{"visibility":null,"nameWithOwner":"me/repo"}',
                '{"visibility":"PRIVATE","nameWithOwner":" me/repo"}',
                '{"visibility":"PUBLIC","visibility":"PRIVATE",'
                '"nameWithOwner":"me/repo"}'):
            with self.subTest(raw=raw):
                result, output, _, resolver_calls, _ = self.run_main(
                    raw, grant="me/repo\n")
                self.assertEqual(result, 1)
                self.assertEqual(resolver_calls, 0)
                self.assertEqual(output,
                                 "PUSH BLOCKED: could not verify repo visibility "
                                 "and identity for me/repo (gh repo view failed "
                                 "or returned invalid data).\n")

    def test_actual_gh_identity_must_match_push_destination_even_with_grant(self):
        for visibility in ("PRIVATE", "PUBLIC", "INTERNAL"):
            with self.subTest(visibility=visibility):
                result, output, _, resolver_calls, _ = self.run_main(
                    json.dumps({"visibility": visibility,
                                "nameWithOwner": "someone/another"}),
                    grant="me/repo\nsomeone/another\n")
                self.assertEqual(result, 1)
                self.assertEqual(resolver_calls, 0)
                self.assertEqual(output,
                                 "PUSH BLOCKED: gh repo view returned "
                                 "someone/another, which does not match named "
                                 "push destination me/repo.\n")

    def test_gh_failures_block_with_stable_message(self):
        failure_cases = [
            {"returncode": 1},
            {"gh_error": FileNotFoundError("gh missing")},
            {"gh_error": subprocess.TimeoutExpired("gh", 30)},
            {"gh_error": UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad reply")},
        ]
        for failure in failure_cases:
            with self.subTest(failure=failure):
                result, output, _, resolver_calls, _ = self.run_main(
                    '{"visibility":"PRIVATE","nameWithOwner":"me/repo"}',
                    grant="me/repo\n", **failure)
                self.assertEqual(result, 1)
                self.assertEqual(resolver_calls, 0)
                self.assertEqual(output,
                                 "PUSH BLOCKED: could not verify repo visibility "
                                 "and identity for me/repo (gh repo view failed "
                                 "or returned invalid data).\n")

    def test_unreadable_grants_block_private_and_public_without_traceback(self):
        for visibility in ("PRIVATE", "PUBLIC"):
            for error in (PermissionError("unreadable"),
                          UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad grant")):
                with self.subTest(visibility=visibility, error=error):
                    result, output, _, _, grant_path = self.run_main(
                        json.dumps({"visibility": visibility,
                                    "nameWithOwner": "me/repo"}),
                        grant="me/repo\n", grant_error=error)
                    self.assertEqual(result, 1)
                    self.assertEqual(output,
                                     "PUSH BLOCKED: could not read visibility "
                                     f"grant configuration at {grant_path}.\n")

    def test_grant_resolution_failure_blocks_with_stable_message(self):
        result, output, _, _, _ = self.run_main(
            '{"visibility":"PRIVATE","nameWithOwner":"me/repo"}',
            resolver_error=OSError("unreadable checkout"))
        self.assertEqual(result, 1)
        self.assertEqual(output,
                         "PUSH BLOCKED: could not read visibility grant "
                         f"configuration at {pp.GRANT_FILE}.\n")


class TestRecursivePushConsumer(unittest.TestCase):
    def test_actual_local_destinations_and_guarded_entry(self):
        """No network: Git pushes only between tempfile-owned repositories.

        The visibility seam says PRIVATE for the parent; real Git config and
        real hook.main decide whether its actual local push may execute.
        Direct bypass controls prove each blocked mode can advance a child.
        """
        import hook_pretooluse as hook

        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("GIT_")}
        environment.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                            "GIT_TERMINAL_PROMPT": "0"})
        with tempfile.TemporaryDirectory(prefix="guard-recursion-") as td, \
                unittest.mock.patch.dict(os.environ, environment, clear=True):
            root = Path(td)
            source, parent = root / "sub-source", root / "parent"
            secondary, accepted = root / "secondary.git", root / "accepted.git"
            real_run = subprocess.run

            def git(arguments, cwd):
                result = real_run(["git", *arguments], cwd=cwd, capture_output=True,
                                  text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout

            def commit(cwd, text):
                git(["add", "-A"], cwd)
                git(["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                     "commit", "-m", text], cwd)

            for bare in (secondary, accepted):
                git(["init", "--bare", str(bare)], root)
            git(["init", "-b", "master", str(source)], root)
            (source / "data").write_text("base", encoding="utf-8")
            commit(source, "base")
            git(["remote", "add", "origin", str(secondary)], source)
            git(["push", "origin", "master"], source)
            git(["init", "-b", "master", str(parent)], root)
            git(["-c", "protocol.file.allow=always", "submodule", "add", str(secondary), "module"], parent)
            commit(parent, "base")
            git(["remote", "add", "origin", str(accepted)], parent)
            git(["push", "origin", "master"], parent)

            def controlled_run(command, *args, **kwargs):
                if command[0] == "gh":
                    return subprocess.CompletedProcess(command, 0,
                        '{"visibility":"PRIVATE","nameWithOwner":"fixture/parent"}', "")
                return real_run(command, *args, **kwargs)

            def guard(options):
                command = "git " + subprocess.list2cmdline(["push", *options, "origin", "master"])
                payload = json.dumps({"tool_name": "exec_command", "tool_input": {
                    "cmd": command, "workdir": str(parent)}})
                with unittest.mock.patch.object(sys, "stdin", io.StringIO(payload)), \
                        unittest.mock.patch.object(pp, "repo_name_from_git", return_value="fixture/parent"), \
                        unittest.mock.patch.object(pp, "resolve_gitignored", return_value=root / "absent-grant"), \
                        unittest.mock.patch.object(pp.subprocess, "run", side_effect=controlled_run), \
                        redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    return hook.main()

            cases = (
                ("ordinary", {}, [], {}, 0),
                ("explicit", {}, ["--recurse-submodules=on-demand"], {}, 2),
                ("inherited", {"push.recurseSubmodules": "on-demand"}, [], {}, 2),
                ("fallback", {"submodule.recurse": "true"}, [], {}, 2),
                ("both", {"push.recurseSubmodules": "false", "submodule.recurse": "true"}, [], {}, 2),
                ("environment", {}, [], {"GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "push.recurseSubmodules", "GIT_CONFIG_VALUE_0": "on-demand"}, 2),
            )
            for label, config, options, additions, expected in cases:
                with self.subTest(label=label):
                    for key in ("push.recurseSubmodules", "submodule.recurse"):
                        real_run(["git", "config", "--local", "--unset-all", key], cwd=parent,
                                 capture_output=True, text=True, timeout=20)
                    for key, value in config.items():
                        git(["config", "--local", key, value], parent)
                    (parent / "module" / "data").write_text(label, encoding="utf-8")
                    commit(parent / "module", label)
                    commit(parent, label + " pointer")
                    before_secondary = git(["show-ref"], secondary)
                    before_parent = git(["show-ref"], accepted)
                    with unittest.mock.patch.dict(os.environ, additions):
                        status = guard(options)
                        if status == 0:
                            git(["push", *options, "origin", "master"], parent)
                        self.assertEqual(status, expected)
                        self.assertEqual(git(["show-ref"], secondary), before_secondary)
                        if expected == 0:
                            self.assertNotEqual(git(["show-ref"], accepted), before_parent)
                        else:
                            self.assertEqual(git(["show-ref"], accepted), before_parent)
                            # Intentional bypass only within tempfiles: the
                            # same actual Git command must advance the child.
                            git(["push", *options, "origin", "master"], parent)
                            self.assertNotEqual(git(["show-ref"], secondary), before_secondary)


if __name__ == "__main__":
    unittest.main()
