"""Candidate checks must fail when actual source, evidence or review bindings drift."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from game_config import GameConfig
import roblox_review as review


class TestRobloxReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.harness, self.game = self.base / "harness", self.base / "game"
        (self.harness / "team").mkdir(parents=True)
        (self.game / "src").mkdir(parents=True)
        (self.game / "evidence").mkdir()
        self.source = self.game / "src/Match.luau"
        self.source.write_bytes(b"return 41\n")
        self.evidence = self.game / "evidence/runtime.json"
        self.evidence.write_bytes(b'{"assertions":3,"failed":0}')
        self.binding = self.harness / "GAME.local.md"
        self.binding.write_text(f"- Engine: Roblox Studio\n- Project root: {self.game}\n", encoding="utf-8")
        self.config = GameConfig(source=self.binding, engine_kind="roblox", project_root=self.game)
        self.scope = {
            "task": "Match rules", "author": "Author", "risk": "material-behavior",
            "inputs": [{"root": "game", "path": "src"}],
            "evidence": [{"root": "game", "path": "evidence/runtime.json"}],
        }
        self.out = self.harness / "team/candidate.local.json"

    def capture(self):
        return review.capture(self.scope, self.config, self.out, self.harness)

    def reviewer(self, **changes):
        value = {
            "schemaVersion": 1, "snapshotSha256": hashlib.sha256(self.out.read_bytes()).hexdigest(),
            "reviewer": "Independent QA", "verdict": "GO", "findings": "Checked scoped rules and recorded assertions.",
            "evidence": [{"root": "game", "path": "evidence/runtime.json"}],
        }
        value.update(changes)
        return value

    def test_real_capture_check_and_scoped_review_do_not_modify_game(self):
        before = {path: path.read_bytes() for path in self.game.rglob("*") if path.is_file()}
        snapshot = self.capture()
        self.assertEqual(review.check_snapshot(snapshot, self.config, self.harness), snapshot)
        self.assertEqual(review.check_review(self.reviewer(), snapshot, self.out.read_bytes()), "GO")
        self.assertEqual(review.check_review(self.reviewer(verdict="NITS"), snapshot, self.out.read_bytes()), "NITS")
        source_row = next(row for row in snapshot["files"] if row["role"] == "inputs")
        self.assertEqual(source_row["sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertFalse(snapshot["atomicSnapshot"])
        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_same_size_source_change_invalidates_even_if_mtime_is_restored(self):
        snapshot = self.capture()
        old = self.source.stat()
        self.source.write_bytes(b"return 42\n")
        os.utime(self.source, ns=(old.st_atime_ns, old.st_mtime_ns))
        with self.assertRaisesRegex(ValueError, "Content"):
            review.check_snapshot(snapshot, self.config, self.harness)

    def test_evidence_change_invalidates(self):
        snapshot = self.capture()
        self.evidence.write_bytes(b'{"assertions":3,"failed":1}')
        with self.assertRaises(ValueError):
            review.check_snapshot(snapshot, self.config, self.harness)

    def test_directory_addition_and_removal_invalidate(self):
        snapshot = self.capture()
        extra = self.game / "src/new.luau"
        extra.write_text("new")
        with self.assertRaises(ValueError):
            review.check_snapshot(snapshot, self.config, self.harness)
        extra.unlink()
        self.assertEqual(review.check_snapshot(snapshot, self.config, self.harness), snapshot)
        self.source.unlink()
        with self.assertRaises(ValueError):
            review.check_snapshot(snapshot, self.config, self.harness)

    def test_binding_root_and_binding_bytes_change_invalidate(self):
        snapshot = self.capture()
        other = self.base / "other"
        other.mkdir()
        with self.assertRaisesRegex(ValueError, "roots"):
            review.check_snapshot(snapshot, replace(self.config, project_root=other), self.harness)
        self.binding.write_text(self.binding.read_text() + "- Integration owner: changed\n")
        with self.assertRaisesRegex(ValueError, "Binding"):
            review.check_snapshot(snapshot, self.config, self.harness)

    def test_wrong_digest_self_review_fail_and_empty_or_uncaptured_evidence_refuse(self):
        snapshot = self.capture()
        for changes in (
            {"snapshotSha256": "0" * 64}, {"reviewer": " aUtHoR "}, {"verdict": "FAIL"},
            {"verdict": "PASS"}, {"findings": " "}, {"reviewer": ""},
            {"evidence": []}, {"evidence": [{"root": "game", "path": "src/Match.luau"}]},
            {"evidence": [{"root": "game", "path": "evidence"}]},
            {"evidence": self.scope["evidence"] * 2}, {"unexpected": True},
            {"schemaVersion": True}, {"schemaVersion": 2},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                review.check_review(self.reviewer(**changes), snapshot, self.out.read_bytes())

    def test_high_risk_requires_nonblank_abuse_analysis(self):
        self.scope["risk"] = "high-risk-control"
        snapshot = self.capture()
        for value in (None, "", " "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                review.check_review(self.reviewer(abuseAnalysis=value), snapshot, self.out.read_bytes())
        self.assertEqual(review.check_review(self.reviewer(abuseAnalysis="Tested ownership spoof and evidence substitution."),
                                            snapshot, self.out.read_bytes()), "GO")

    def test_lower_risk_review_accepts_blank_optional_abuse_analysis_and_uppercase_digest(self):
        for risk in ("ordinary-local", "material-behavior"):
            self.scope["risk"] = risk
            self.out = self.harness / "team" / f"{risk}.local.json"
            snapshot = self.capture()
            for abuse in ("", " "):
                value = self.reviewer(abuseAnalysis=abuse)
                value["snapshotSha256"] = value["snapshotSha256"].upper()
                self.assertEqual(review.check_review(value, snapshot, self.out.read_bytes()), "GO")
            for abuse in (None, [], 0):
                with self.subTest(risk=risk, abuse=abuse), self.assertRaises(ValueError):
                    review.check_review(self.reviewer(abuseAnalysis=abuse), snapshot, self.out.read_bytes())

    def test_output_inside_nested_game_root_is_refused(self):
        game = self.harness / "nested-game"
        game.mkdir()
        (game / "source.luau").write_text("source")
        (game / "evidence.json").write_text("{}")
        scope = copy.deepcopy(self.scope)
        scope["inputs"] = [{"root": "game", "path": "source.luau"}]
        scope["evidence"] = [{"root": "game", "path": "evidence.json"}]
        output = game / "snapshot.local.json"
        with self.assertRaisesRegex(ValueError, "game root"):
            review.capture(scope, replace(self.config, project_root=game), output, self.harness)
        self.assertFalse(output.exists())

    def test_output_overwrite_outside_and_inside_selection_refused(self):
        self.capture()
        original = self.out.read_bytes()
        with self.assertRaises(FileExistsError):
            self.capture()
        self.assertEqual(self.out.read_bytes(), original)
        for output in (self.base / "outside.local.json", self.harness / "candidate.json"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                review.capture(self.scope, self.config, output, self.harness)
            self.assertFalse(output.exists())
        (self.harness / "team/input.txt").write_text("input")
        self.scope["inputs"].append({"root": "harness", "path": "team"})
        with self.assertRaisesRegex(ValueError, "captured selection"):
            review.capture(self.scope, self.config, self.harness / "team/new.local.json", self.harness)

    def test_malformed_unknown_empty_and_overlapping_scope_refused(self):
        cases = []
        for path in ("../src", "/absolute", "C:\\absolute", "src/../src", ".", "src//Match.luau",
                     "src/Match.luau.", "src/Match.luau:stream"):
            bad = copy.deepcopy(self.scope)
            bad["inputs"] = [{"root": "game", "path": path}]
            cases.append(bad)
        for key, value in (("risk", "unknown"), ("inputs", []), ("evidence", []), ("task", " "),
                           ("author", ""), ("inputs", {})):
            bad = copy.deepcopy(self.scope)
            bad[key] = value
            cases.append(bad)
        bad = copy.deepcopy(self.scope)
        bad["inputs"].append({"root": "game", "path": "src/Match.luau"})
        cases.append(bad)
        bad = copy.deepcopy(self.scope)
        bad["evidence"] = copy.deepcopy(bad["inputs"])
        cases.append(bad)
        bad = copy.deepcopy(self.scope)
        bad["unexpected"] = True
        cases.append(bad)
        (self.game / "empty").mkdir()
        bad = copy.deepcopy(self.scope)
        bad["inputs"] = [{"root": "game", "path": "empty"}]
        cases.append(bad)
        for bad in cases:
            with self.subTest(scope=bad), self.assertRaises((ValueError, OSError)):
                review.capture(bad, self.config, self.out, self.harness)
            self.assertFalse(self.out.exists())

    def test_unknown_engine_and_snapshot_schema_refuse(self):
        with self.assertRaises(ValueError):
            review.capture(self.scope, replace(self.config, engine_kind="unreal"), self.out, self.harness)
        snapshot = self.capture()
        for key, value in (("schemaVersion", 2), ("schemaVersion", True), ("files", []),
                           ("atomicSnapshot", True), ("limits", []), ("capturedUtc", "2026-10-20"),
                           ("surprise", True)):
            bad = copy.deepcopy(snapshot)
            bad[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                review.check_snapshot(bad, self.config, self.harness)

    def test_ordinary_local_can_capture_without_evidence_but_cannot_claim_review(self):
        self.scope.update(risk="ordinary-local", evidence=[])
        snapshot = self.capture()
        review.check_snapshot(snapshot, self.config, self.harness)
        with self.assertRaises(ValueError):
            review.check_review(self.reviewer(), snapshot, self.out.read_bytes())

    def test_symlink_input_parent_and_output_parent_refused_even_within_root(self):
        linked = self.game / "linked"
        try:
            linked.symlink_to(self.game / "src", target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Symlink privilege unavailable: {exc}")
        self.scope["inputs"] = [{"root": "game", "path": "linked/Match.luau"}]
        with self.assertRaisesRegex(ValueError, "Linked"):
            self.capture()
        self.scope["inputs"] = [{"root": "game", "path": "src"}]
        output_link = self.harness / "linked"
        output_link.symlink_to(self.harness / "team", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Linked"):
            review.capture(self.scope, self.config, output_link / "candidate.local.json", self.harness)
        (self.game / "src/link.luau").symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, "Linked"):
            self.capture()

    def test_nonregular_node_refused_where_supported(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO fixture is not supported on this platform")
        os.mkfifo(self.game / "src/pipe")
        with self.assertRaisesRegex(ValueError, "Nonregular"):
            self.capture()

    def test_reparse_component_is_refused_without_symlink_privilege(self):
        original = Path.lstat
        linked = self.game / "src"

        def reparse(path, *args, **kwargs):
            if path == linked:
                actual = original(path, *args, **kwargs)
                return SimpleNamespace(st_mode=actual.st_mode, st_file_attributes=0x400)
            return original(path, *args, **kwargs)

        with patch.object(Path, "lstat", reparse), self.assertRaisesRegex(ValueError, "reparse"):
            self.capture()
        self.assertFalse(self.out.exists())

    def test_symlink_component_is_refused_without_symlink_privilege(self):
        original = Path.lstat
        linked = self.harness / "team"

        def symlink(path, *args, **kwargs):
            if path == linked:
                return SimpleNamespace(st_mode=0o120777)
            return original(path, *args, **kwargs)

        with patch.object(Path, "lstat", symlink), self.assertRaisesRegex(ValueError, "Linked"):
            self.capture()
        self.assertFalse(self.out.exists())

    def test_capture_rechecks_membership_before_saving(self):
        original = review.scan
        count = 0

        def changing(scope, roots):
            nonlocal count
            result = original(scope, roots)
            count += 1
            if count == 1:
                (self.game / "src/late.luau").write_text("late")
            return result

        with patch.object(review, "scan", side_effect=changing), self.assertRaisesRegex(ValueError, "changed during capture"):
            self.capture()
        self.assertFalse(self.out.exists())

    def test_strict_json_refuses_duplicate_keys_nonobjects_and_nonfinite_numbers(self):
        path = self.harness / "bad.json"
        for raw in ('{"task":"a","task":"b"}', "[1]", "{", '{"value":NaN}', '{"value":Infinity}'):
            path.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                review.read_json(path)

    def test_cli_content_only_success_and_failures_never_print_success(self):
        self.capture()
        with patch.object(review, "ROOT", self.harness), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(review.main(["check", "--snapshot", str(self.out), "--binding", str(self.binding)]), 0)
        self.assertIn("CONTENT MATCH only", output.getvalue())
        self.source.write_bytes(b"return 42\n")
        with patch.object(review, "ROOT", self.harness), contextlib.redirect_stdout(io.StringIO()) as output, \
                contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(review.main(["check", "--snapshot", str(self.out), "--binding", str(self.binding)]), 1)
        self.assertNotIn("CONTENT MATCH", output.getvalue())
        self.assertIn("REFUSED", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
