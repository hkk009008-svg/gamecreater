"""Real local Git objects, not a working-tree proxy for publication bytes."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import publication_git as pg  # noqa: E402


class GitFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="publication git ")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "source repository"
        self.repo.mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.upper().startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        self.git("init", "-q")

    def git(self, *args, repo=None, data=None, check=True):
        command = ["git", "-c", f"core.hooksPath={os.devnull}",
                   "-c", "core.fsmonitor=false", "-c", "commit.gpgSign=false",
                   "-c", "user.name=Fixture", "-c", "user.email=fixture@invalid.test",
                   "-C", str(repo or self.repo), *args]
        return subprocess.run(command, input=data, env=self.env, capture_output=True,
                              check=check, timeout=15).stdout

    def put(self, name="file.txt", content=b"safe original", *, commit=True):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        self.git("add", "--", name)
        if commit:
            self.git("commit", "-qm", "fixture commit")
        return self.git("hash-object", "--stdin", data=content).strip().decode()

    @staticmethod
    def payloads(result, kind="blob"):
        return {item["data"] for item in result["objects"] if item["kind"] == kind}


class SelectionTests(GitFixture):
    def test_index_reads_staged_object_not_harmless_working_copy(self):
        self.put(content=b"sensitive fixture marker", commit=False)
        (self.repo / "file.txt").write_bytes(b"harmless decoy")
        before = (self.repo / ".git" / "index").read_bytes()
        data = pg.collect_sources(self.repo, "index")
        self.assertEqual(self.payloads(data), {b"sensitive fixture marker"})
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), before)
        self.assertEqual((self.repo / "file.txt").read_bytes(), b"harmless decoy")
        self.assertEqual(data["counts"]["objectCount"], 1)

    def test_tree_pins_saved_tree_and_ignores_staged_and_working_changes(self):
        oid = self.put(content=b"committed fixture")
        self.put(content=b"staged fixture", commit=False)
        (self.repo / "file.txt").write_bytes(b"working fixture")
        data = pg.collect_sources(self.repo, "tree", "HEAD")
        self.assertEqual(self.payloads(data), {b"committed fixture"})
        self.assertEqual(data["paths"], [{"path": "file.txt", "oid": oid, "mode": "100644"}])
        self.assertEqual(data["refs"], [])
        self.assertEqual(data["counts"]["commitCount"], 0)

    def test_refs_find_deleted_history_and_keep_identity_and_tag_payloads(self):
        lost = self.put("old.txt", b"deleted historic fixture")
        self.git("tag", "-a", "annotated", "-m", "annotation fixture")
        self.git("branch", "earlier")
        self.git("rm", "old.txt")
        self.put("new.txt", b"safe current")
        self.git("update-ref", "refs/notes/fixture", "HEAD")
        data = pg.collect_sources(self.repo, "refs")
        self.assertIn(b"deleted historic fixture", self.payloads(data))
        self.assertIn(b"safe current", self.payloads(data))
        self.assertTrue(any(item["oid"] == lost for item in data["objects"]))
        self.assertTrue(any(b"annotation fixture" in item for item in self.payloads(data, "tag")))
        self.assertTrue(any(b"author Fixture" in item for item in self.payloads(data, "commit")))
        names = {ref["name"] for ref in data["refs"]}
        self.assertTrue({"refs/heads/earlier", "refs/tags/annotated", "refs/notes/fixture", "HEAD"} <= names)
        self.assertTrue(all("tree" in item for item in data["paths"]))
        self.assertEqual(len({item["oid"] for item in data["objects"]}), len(data["objects"]))

    def test_same_historic_path_can_have_different_payloads(self):
        first = self.put(content=b"first")
        second = self.put(content=b"second")
        data = pg.collect_sources(self.repo, "refs")
        matching = [path for path in data["paths"] if path["path"] == "file.txt"]
        self.assertEqual({path["oid"] for path in matching}, {first, second})
        self.assertEqual(len(matching), 2)

    def test_historical_nested_path_retains_full_path_spelling(self):
        self.put("nested/path-marker.txt", b"lost content")
        self.git("rm", "nested/path-marker.txt")
        self.put("other.txt", b"new content")
        data = pg.collect_sources(self.repo, "refs")
        self.assertIn("nested/path-marker.txt", {item["path"] for item in data["paths"]})
        self.assertNotIn("nested/path-marker.txt", {item["path"] for item in pg.collect_sources(self.repo, "tree", "HEAD")["paths"]})

    def test_tree_and_blob_refs_are_selected_without_commit_context(self):
        blob = self.put("nested/value", b"direct fixture")
        subtree = self.git("rev-parse", "HEAD:nested").strip().decode()
        self.git("update-ref", "refs/tags/direct-blob", blob)
        self.git("update-ref", "refs/tags/direct-tree", subtree)
        data = pg.collect_sources(self.repo, "refs")
        self.assertTrue({"nested/value", "value"} <= {item["path"] for item in data["paths"]})
        self.assertIn(b"direct fixture", self.payloads(data))

    def test_shallow_clone_reports_history_gap(self):
        self.put(content=b"first")
        self.put(content=b"second")
        shallow = Path(self.temp.name) / "shallow"
        self.git("clone", "--quiet", "--depth=1", self.repo.as_uri(), str(shallow))
        data = pg.collect_sources(shallow, "refs")
        self.assertIn({"kind": "shallow_history"}, data["coverageGaps"])

    def test_paths_include_spaces_unicode_nested_and_non_utf8(self):
        self.put("nested dir/caf\u00e9.txt", b"value")
        data = pg.collect_sources(self.repo / "nested dir", "tree", "HEAD")
        self.assertEqual(data["paths"][0]["path"], "nested dir/caf\u00e9.txt")
        self.assertEqual(Path(data["repository"]), self.repo.resolve())
        # Git accepts opaque filename bytes even where the OS cannot create it.
        raw = b"100644 blob " + data["paths"][0]["oid"].encode() + b"\tbad\xff.txt\0"
        git = pg._Git(self.repo, pg.DEFAULT_LIMITS)
        self.assertEqual(pg._tree_paths(git, raw)[0]["path"].encode("utf-8", "surrogateescape"), b"bad\xff.txt")

    def test_detached_head_is_selected_and_empty_repo_refuses(self):
        with self.assertRaisesRegex(pg.AuditError, "empty_ref_selection"):
            pg.collect_sources(self.repo, "refs")
        self.put()
        branch = self.git("symbolic-ref", "--short", "HEAD").strip().decode()
        self.git("checkout", "--detach", "-q")
        self.git("branch", "-D", branch)
        data = pg.collect_sources(self.repo, "refs")
        self.assertEqual([ref["name"] for ref in data["refs"]], ["HEAD"])

    def test_bare_repo_tree_and_refs_work_without_checkout(self):
        self.put()
        bare = Path(self.temp.name) / "bare.git"
        self.git("clone", "--bare", "--quiet", str(self.repo), str(bare))
        self.assertEqual(self.payloads(pg.collect_sources(bare, "tree", "HEAD")), {b"safe original"})
        self.assertEqual(self.payloads(pg.collect_sources(bare, "refs")), {b"safe original"})

    def test_sha256_objects_are_verified(self):
        other = Path(self.temp.name) / "sha256 repository"
        other.mkdir()
        self.git("init", "--object-format=sha256", "-q", repo=other)
        (other / "a").write_bytes(b"sha256 fixture")
        self.git("add", "a", repo=other)
        self.git("commit", "-qm", "sha256 commit", repo=other)
        data = pg.collect_sources(other, "refs")
        self.assertEqual({len(item["oid"]) for item in data["objects"]}, {64})
        self.assertEqual(self.payloads(data), {b"sha256 fixture"})

    def test_external_gitlink_and_symlink_are_gaps_without_following(self):
        self.put()
        commit = self.git("rev-parse", "HEAD").strip().decode()
        link = self.git("hash-object", "-w", "--stdin", data=b"outside fixture target").strip().decode()
        records = f"120000 {link}\tlink\n160000 {commit}\tsubmodule\n".encode()
        self.git("update-index", "--index-info", data=records)
        data = pg.collect_sources(self.repo, "index")
        self.assertEqual({gap["kind"] for gap in data["coverageGaps"]},
                         {"external_symlink_target", "external_gitlink"})
        self.assertIn(b"outside fixture target", self.payloads(data))
        self.assertFalse(any(obj["kind"] == "commit" for obj in data["objects"]))

    def test_empty_and_unmerged_index_refuse(self):
        with self.assertRaisesRegex(pg.AuditError, "empty_or_malformed_entries"):
            pg.collect_sources(self.repo, "index")
        oid = self.git("hash-object", "-w", "--stdin", data=b"fixture").strip().decode()
        self.git("update-index", "--index-info", data=f"100644 {oid} 1\tconflict\n".encode())
        with self.assertRaisesRegex(pg.AuditError, "unmerged_index"):
            pg.collect_sources(self.repo, "index")


class BoundaryTests(GitFixture):
    def test_unknown_selection_and_limits_refuse(self):
        self.put()
        for mode, target in (("unknown", None), ([], None), ("index", "HEAD"), ("tree", None),
                             ("tree", "--help"), ("tree", "HEAD\nother")):
            with self.subTest(mode=mode, target=target), self.assertRaises(pg.AuditError):
                pg.collect_sources(self.repo, mode, target)
        for value in ({"missing": 1}, {"timeout": 0}, {"max_objects": True}, {"timeout": 1.5}, []):
            with self.subTest(limits=value), self.assertRaisesRegex(pg.AuditError, "invalid_limits"):
                pg.collect_sources(self.repo, "tree", "HEAD", limits=value)

    def test_object_count_size_total_and_path_budgets_refuse(self):
        self.put("a", b"first payload")
        self.put("b", b"second payload")
        for limit in ({"max_objects": 1}, {"max_object_bytes": 5},
                      {"max_total_bytes": 20}, {"max_tree_entries": 1}):
            with self.subTest(limit=limit), self.assertRaises(pg.AuditError):
                pg.collect_sources(self.repo, "tree", "HEAD", limits=limit)

    def test_replacement_objects_and_inherited_git_selectors_do_not_redirect(self):
        original = self.put(content=b"actual selected payload")
        replacement = self.git("hash-object", "-w", "--stdin", data=b"replacement decoy").strip().decode()
        self.git("replace", original, replacement)
        fake = Path(self.temp.name) / "not a git directory"
        with mock.patch.dict(os.environ, {"GIT_DIR": str(fake), "GIT_WORK_TREE": str(fake),
                                          "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.fsmonitor",
                                          "GIT_CONFIG_VALUE_0": "dangerous fake command"}):
            data = pg.collect_sources(self.repo, "tree", "HEAD")
        self.assertEqual(self.payloads(data), {b"actual selected payload"})

    def test_legacy_grafts_cannot_hide_deleted_ancestor_content(self):
        lost = self.put("lost.txt", b"ancestor fixture marker")
        self.git("rm", "lost.txt")
        self.put("current.txt", b"current content")
        head = self.git("rev-parse", "HEAD").strip()
        grafts = self.repo / ".git" / "info" / "grafts"
        grafts.write_bytes(head + b"\n")
        # Known control: this installed Git honors the fixture graft without
        # collector isolation, and the deleted ancestor then disappears.
        ordinary = self.git("rev-list", "--objects", "--all")
        self.assertNotIn(lost.encode(), ordinary)
        before = grafts.read_bytes()
        data = pg.collect_sources(self.repo, "refs")
        self.assertIn(b"ancestor fixture marker", self.payloads(data))
        self.assertEqual(grafts.read_bytes(), before)

    def test_configured_fsmonitor_and_filters_are_not_executed(self):
        self.put()
        self.put(".gitattributes", b"* filter=fixture\n")
        marker = self.repo / "executed-marker"
        helper = self.repo / "fixture monitor.py"
        helper.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n", encoding="utf-8")
        command = f'"{sys.executable}" "{helper}"'
        self.git("config", "core.fsmonitor", command)
        self.git("config", "filter.fixture.clean", command)
        self.git("config", "filter.fixture.smudge", command)
        # Known-positive fixture checks: the helper actually executes through
        # ordinary Git entry points; a silent/no-op helper cannot make this pass.
        subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain"],
                       env=self.env, check=True, capture_output=True, timeout=15)
        self.assertTrue(marker.exists(), "fsmonitor fixture did not execute")
        marker.unlink()
        self.git("cat-file", "--filters", "HEAD:file.txt")
        self.assertTrue(marker.exists(), "filter fixture did not execute")
        marker.unlink()
        for mode, target in (("index", None), ("tree", "HEAD"), ("refs", None)):
            pg.collect_sources(self.repo, mode, target)
        self.assertFalse(marker.exists())

    def test_index_and_refs_moving_mid_collection_refuse(self):
        self.put()
        original = pg._object_payloads
        for mode in ("index", "refs"):
            def moving(git, oids):
                result = original(git, oids)
                if mode == "index":
                    self.put("later", b"new staged content", commit=False)
                else:
                    self.git("update-ref", "refs/heads/new-alias", "HEAD")
                return result
            with self.subTest(mode=mode), mock.patch.object(pg, "_object_payloads", side_effect=moving):
                with self.assertRaisesRegex(pg.AuditError, "selection_changed_during_collection"):
                    pg.collect_sources(self.repo, mode)

    def test_shallow_marker_removed_after_collection_refuses_history_change(self):
        self.put("lost.txt", b"shallow race fixture marker\n")
        self.git("rm", "lost.txt")
        self.put("current.txt", b"ordinary current text\n")
        shallow = self.repo / ".git" / "shallow"
        shallow.write_bytes(self.git("rev-parse", "HEAD").strip() + b"\n")
        refs_before = self.git("show-ref")
        original = pg._object_payloads

        def remove_overlay(git, oids):
            result = original(git, oids)
            shallow.unlink()
            return result

        with mock.patch.object(pg, "_object_payloads", side_effect=remove_overlay):
            with self.assertRaisesRegex(pg.AuditError, "^history_boundary_changed_during_collection$"):
                pg.collect_sources(self.repo, "refs")
        self.assertEqual(self.git("show-ref"), refs_before)
        self.assertIn(b"shallow race fixture marker\n",
                      self.payloads(pg.collect_sources(self.repo, "refs")))

    def test_transient_shallow_cut_requires_parent_gap_and_not_false_clean(self):
        import publication_scan as ps

        marker = b"transient shallow fixture marker\n"
        self.put("lost.txt", marker)
        self.git("rm", "lost.txt")
        self.put("current.txt", b"ordinary current text\n")
        head = self.git("rev-parse", "HEAD").strip()
        refs_before = self.git("show-ref")
        shallow = self.repo / ".git" / "shallow"
        terms = Path(self.temp.name) / "terms.txt"
        terms.write_bytes(marker)
        original = pg._Git.run

        def transient_overlay(git, args, **kwargs):
            if args[:3] == ["rev-list", "--objects", "--no-object-names"]:
                shallow.write_bytes(head + b"\n")
                try:
                    return original(git, args, **kwargs)
                finally:
                    shallow.unlink()
            return original(git, args, **kwargs)

        with mock.patch.object(pg._Git, "run", new=transient_overlay):
            selected = pg.collect_sources(self.repo, "refs")
        self.assertEqual(self.git("show-ref"), refs_before)
        self.assertFalse(shallow.exists())
        self.assertNotIn(marker, self.payloads(selected))
        self.assertEqual(ps.scan_sources(selected, [terms])["result"], "INCOMPLETE")
        self.assertTrue(any(gap.get("kind") == "history_parent_unavailable"
                            for gap in selected["coverageGaps"]))
        full = pg.collect_sources(self.repo, "refs")
        self.assertIn(marker, self.payloads(full))
        self.assertEqual(ps.scan_sources(full, [terms])["result"], "FINDINGS")

    def test_parent_like_commit_message_does_not_invent_history_gap(self):
        self.put()
        missing = "f" * len(self.git("rev-parse", "HEAD").strip())
        inventory = self.git("cat-file", "--batch-check", data=(missing + "\n").encode())
        self.assertEqual(inventory, (missing + " missing\n").encode())
        message = "fixture subject\n\nparent " + missing + "\n parent " + missing + "\n"
        self.git("commit", "--allow-empty", "-qm", message)
        selected = pg.collect_sources(self.repo, "refs")
        self.assertTrue(any(("\n\nparent " + missing).encode() in payload
                            for payload in self.payloads(selected, "commit")))
        self.assertFalse(any(gap.get("kind") == "history_parent_unavailable"
                             for gap in selected["coverageGaps"]))

    def test_moving_treeish_refuses_but_immutable_tree_can_still_be_read(self):
        self.put()
        saved = self.git("rev-parse", "HEAD^{tree}").strip().decode()
        original = pg._object_payloads
        def moving(git, oids):
            result = original(git, oids)
            self.put("new", b"new committed content")
            return result
        with mock.patch.object(pg, "_object_payloads", side_effect=moving):
            with self.assertRaisesRegex(pg.AuditError, "selection_changed_during_collection"):
                pg.collect_sources(self.repo, "tree", "HEAD")
        self.assertEqual(self.payloads(pg.collect_sources(self.repo, "tree", saved)), {b"safe original"})

    def test_git_execution_and_malformed_object_streams_are_sanitized(self):
        self.put()
        for failure in (FileNotFoundError("private stderr value"), subprocess.TimeoutExpired("private command", 1)):
            with mock.patch.object(pg.subprocess, "run", side_effect=failure):
                with self.assertRaisesRegex(pg.AuditError, "^git_execution_failed$"):
                    pg.collect_sources(self.repo, "tree", "HEAD")
        with mock.patch.object(pg.subprocess, "run", return_value=subprocess.CompletedProcess([], 5, b"", b"sensitive stderr")):
            with self.assertRaisesRegex(pg.AuditError, "^git_command_failed$"):
                pg.collect_sources(self.repo, "tree", "HEAD")
        git = pg._Git(self.repo, pg.DEFAULT_LIMITS)
        oid = self.git("rev-parse", "HEAD:file.txt").strip().decode()
        for responses in ((b"bad inventory\n",),
                          (f"{oid} blob 13\n".encode(), b"wrong payload"),
                          (f"{oid} blob 13\n".encode(), f"{oid} blob 13\nwrong content\n".encode())):
            with self.subTest(responses=responses), mock.patch.object(git, "run", side_effect=list(responses)):
                with self.assertRaises(pg.AuditError):
                    pg._object_payloads(git, [oid])

    def test_collection_has_no_git_mutation_or_network_command(self):
        self.put()
        observed = []
        original = pg.subprocess.run
        def recorded(command, **kwargs):
            observed.append((command, kwargs))
            return original(command, **kwargs)
        with mock.patch.object(pg.subprocess, "run", side_effect=recorded):
            pg.collect_sources(self.repo, "refs")
        commands = {command[command.index("-C") + 2] for command, _ in observed}
        self.assertTrue(commands <= {"rev-parse", "for-each-ref", "rev-list", "cat-file"})
        self.assertNotIn("write-tree", commands)
        for command, kwargs in observed:
            self.assertIsInstance(command, list)
            self.assertNotIn("shell", kwargs)
            self.assertEqual(kwargs["env"]["GIT_OPTIONAL_LOCKS"], "0")
            self.assertEqual(kwargs["env"]["GIT_NO_LAZY_FETCH"], "1")
            self.assertEqual(kwargs["env"]["GIT_GRAFT_FILE"], os.devnull)


if __name__ == "__main__":
    unittest.main()
