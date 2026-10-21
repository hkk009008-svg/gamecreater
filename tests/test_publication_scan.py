"""Pure scanner controls; source fixtures are never publication acceptance."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import publication_scan as scan  # noqa: E402
import scrub_check  # noqa: E402


def object_row(data=b"ordinary text\n", *, kind="blob", oid=None):
    if oid is None:
        oid = hashlib.sha1(kind.encode() + b" " + str(len(data)).encode() + b"\x00" + data).hexdigest()
    return {"oid": oid, "kind": kind, "data": data}


def sources(*objects, paths=None, refs=None, gaps=None):
    return {"objects": list(objects), "paths": paths or [], "refs": refs or [],
            "coverageGaps": gaps or [], "mode": "tree", "selection": {"tree": "a" * 40},
            "sourceIdentity": {"treeOid": "a" * 40}}


class PublicationScanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="publication-scan-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.term = self.root / "terms.txt"
        self.term.write_text("# explicit fixture policy\nsensitive_marker\nre:token_[0-9]+\n", encoding="utf-8")

    def audit(self, collected, term_paths=None):
        return scan.scan_sources(collected, [self.term] if term_paths is None else term_paths)

    def assert_error(self, report, code=None):
        self.assertEqual(report["execution"], "ERROR", report)
        self.assertEqual(report["result"], "ERROR", report)
        self.assertEqual(report["coverage"]["status"], "INCOMPLETE")
        self.assertTrue(report["errors"])
        if code:
            self.assertEqual(report["errors"][0]["code"], code, report)

    def test_known_positive_and_negative_in_same_run(self):
        positive = self.audit(sources(object_row(b"ordinary\nSENSITIVE_MARKER token_129\n")))
        negative = self.audit(sources(object_row(b"ordinary text\n")))
        self.assertEqual(positive["result"], "FINDINGS")
        self.assertEqual(len(positive["findings"]), 2)
        self.assertEqual(negative["result"], "CLEAN_WITHIN_SCOPE")
        self.assertEqual(negative["findings"], [])
        self.assertEqual(negative["counts"]["textObjectsScanned"], 1)
        self.assertFalse(negative["limits"]["authorizationGranted"])

    def test_explicit_line_budget_scans_suffix_without_waiving_gaps(self):
        collected = sources(object_row(("ordinary " * 700 + "sensitive_marker").encode()))
        default = self.audit(collected)
        self.assertEqual(default["result"], "INCOMPLETE")
        self.assertEqual(default["findings"], [])
        self.assertTrue(any(gap["code"] == "line-truncated" for gap in default["coverage"]["gaps"]))
        expanded = scan.scan_sources(collected, [self.term], max_line_chars=8192)
        self.assertEqual(expanded["result"], "FINDINGS")
        self.assertEqual(len(expanded["findings"]), 1)
        self.assertEqual(expanded["coverage"], {"status": "COMPLETE", "gaps": []})
        self.assertEqual(expanded["limits"]["maxLineChars"], 8192)
        still_short = scan.scan_sources(collected, [self.term], max_line_chars=5000)
        self.assertEqual(still_short["result"], "INCOMPLETE")
        self.assertEqual(still_short["coverage"]["gaps"][0]["scannedChars"], 5000)
        self.assertEqual(self.audit(collected), default)

    def test_line_budget_rejects_invalid_types_and_unsupported_values(self):
        for value in [0, -1, True, False, 1.5, "8192", None, scan.MAX_LINE_BUDGET + 1]:
            with self.subTest(value=value):
                report = scan.scan_sources(sources(object_row()), [self.term], max_line_chars=value)
                self.assert_error(report, "invalid-line-budget")

    def test_case_insensitive_rules_and_one_match_per_rule_per_line_reuse_legacy(self):
        text = "SENSITIVE_MARKER sensitive_marker token_1 token_2\n"
        legacy, truncated = scrub_check.scan_text("fixture", text,
                                                scrub_check.load_terms([self.term.read_text()]))
        report = self.audit(sources(object_row(text.encode())))
        self.assertEqual(len(report["findings"]), len(legacy))
        self.assertEqual(len(legacy), 2)
        self.assertEqual(report["counts"]["truncatedLines"], truncated)

    def test_report_redacts_match_rule_and_full_source_line(self):
        payload = "prefix SENSITIVE_MARKER token_9284 private remainder\n"
        report = self.audit(sources(object_row(payload.encode())))
        encoded = json.dumps(report)
        self.assertNotIn("SENSITIVE_MARKER", encoded)
        self.assertNotIn("token_9284", encoded)
        self.assertNotIn("private remainder", encoded)
        self.assertNotIn("token_[0-9]+", encoded)
        self.assertEqual(len(report["findings"][0]["fingerprint"]), 64)
        self.assertTrue(all(row["line"] == 1 for row in report["findings"]))

    def test_fingerprints_are_deterministic_and_bind_content_and_kind(self):
        first = object_row(b"token_129\n")
        report = self.audit(sources(first))
        reordered = self.audit(sources(first))
        self.assertEqual(report["findings"], reordered["findings"])
        changed = self.audit(sources(object_row(b"token_129\nmore context\n", oid=first["oid"])))
        self.assertNotEqual(report["findings"][0]["fingerprint"], changed["findings"][0]["fingerprint"])
        metadata = self.audit(sources(object_row(b"token_129\n", kind="commit", oid=first["oid"])))
        self.assertNotEqual(report["findings"][0]["fingerprint"], metadata["findings"][0]["fingerprint"])

    def test_sha256_object_ids_are_supported_without_assuming_sha1(self):
        report = self.audit(sources(object_row(b"token_39\n", oid="b" * 64)))
        self.assertEqual(report["result"], "FINDINGS")
        self.assertEqual(report["findings"][0]["source"]["oid"], "b" * 64)

    def test_utf16_and_utf32_secrets_are_scanned(self):
        for encoding in ("utf-16", "utf-32"):
            with self.subTest(encoding=encoding):
                report = self.audit(sources(object_row("token_78\n".encode(encoding))))
                self.assertEqual(report["result"], "FINDINGS")
                self.assertEqual(report["coverage"]["status"], "COMPLETE")

    def test_truncated_utf16_remains_incomplete(self):
        data = "token_78\n".encode("utf-16") + b"\x01"
        report = self.audit(sources(object_row(data)))
        self.assertEqual(report["result"], "INCOMPLETE")
        self.assertTrue(report["findings"])
        self.assertIn("invalid-text-encoding", [gap["code"] for gap in report["coverage"]["gaps"]])

    def test_non_text_and_invalid_encoding_never_report_clean(self):
        for data, code in ((b"\x89PNG\x00binary payload", "binary-skipped"),
                           (b"ordinary\xfftext", "invalid-text-encoding"),
                           (b"x" * 8193 + b"\x00tail", "binary-nul-outside-decoder-prefix")):
            with self.subTest(code=code):
                report = self.audit(sources(object_row(data)))
                self.assertEqual(report["result"], "INCOMPLETE")
                self.assertIn(code, [gap["code"] for gap in report["coverage"]["gaps"]])

    def test_invalid_encoding_keeps_detected_findings(self):
        report = self.audit(sources(object_row(b"token_129 \xff tail\n")))
        self.assertEqual(report["result"], "INCOMPLETE")
        self.assertEqual(len(report["findings"]), 1)

    def test_longline_hidden_tail_is_a_coverage_gap_not_clean(self):
        row = object_row(b"x" * (scrub_check.MAX_LINE_CHARS + 1) + b"token_129")
        report = self.audit(sources(row))
        self.assertEqual(report["result"], "INCOMPLETE")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["counts"]["truncatedLines"], 1)
        self.assertIn("line-truncated", [gap["code"] for gap in report["coverage"]["gaps"]])

    def test_longline_retains_prefix_finding_and_incomplete_verdict(self):
        row = object_row(b"token_129" + b"x" * scrub_check.MAX_LINE_CHARS)
        report = self.audit(sources(row))
        self.assertEqual(report["result"], "INCOMPLETE")
        self.assertEqual(len(report["findings"]), 1)

    def test_metadata_commit_tag_ref_and_path_names_are_scanned(self):
        commit = object_row(b"tree " + b"a" * 40 + b"\nauthor sensitive_marker\n\nmessage\n", kind="commit")
        tag = object_row(b"object " + b"a" * 40 + b"\ntagger token_129\n\nannotation\n", kind="tag")
        blob = object_row()
        path = {"path": "sensitive_marker.lua", "oid": blob["oid"], "mode": "100644"}
        ref = {"name": "refs/heads/token_391", "oid": commit["oid"]}
        report = self.audit(sources(commit, tag, blob, paths=[path], refs=[ref]))
        self.assertEqual(report["result"], "FINDINGS")
        self.assertEqual({row["source"]["kind"] for row in report["findings"]}, {"commit", "tag", "path", "ref-name"})
        text = json.dumps(report)
        self.assertNotIn(path["path"], text)
        self.assertNotIn(ref["name"], text)

    def test_historical_same_names_with_distinct_tree_entries_are_legitimate(self):
        row = object_row()
        paths = [{"path": "same.lua", "oid": row["oid"], "mode": "100644", "tree": "a" * 40},
                 {"path": "same.lua", "oid": row["oid"], "mode": "100755", "tree": "b" * 40}]
        report = self.audit(sources(row, paths=paths))
        self.assertEqual(report["result"], "CLEAN_WITHIN_SCOPE")
        self.assertEqual(report["counts"]["paths"], 2)

    def test_lfs_gitlink_and_symlink_payloads_remain_open(self):
        pointer = object_row(b"version https://git-lfs.github.com/spec/v1\noid sha256:" + b"a" * 64 + b"\nsize 13\n")
        for paths, objects, expected in (
            ([], [pointer], "lfs-payload-unavailable"),
            ([{"path": "submodule", "oid": "c" * 40, "mode": "160000"}], [object_row()], "gitlink-payload-unavailable"),
            ([{"path": "symlink", "oid": pointer["oid"], "mode": "120000"}], [pointer], "symlink-target-unfollowed"),
        ):
            with self.subTest(expected=expected):
                report = self.audit(sources(*objects, paths=paths))
                self.assertEqual(report["result"], "INCOMPLETE")
                self.assertIn(expected, [gap["code"] for gap in report["coverage"]["gaps"]])

    def test_collector_gaps_are_preserved_and_precede_findings(self):
        gap = {"code": "collector-bound", "count": 9}
        collected = sources(object_row(b"token_129"), gaps=[gap])
        before = copy.deepcopy(collected)
        report = self.audit(collected)
        self.assertEqual(report["result"], "INCOMPLETE")
        self.assertIn(gap, report["coverage"]["gaps"])
        self.assertTrue(report["findings"])
        self.assertEqual(collected, before)

    def test_missing_empty_and_invalid_term_tiers_are_errors(self):
        empty = self.root / "empty.txt"
        empty.write_text("# only comments\n", encoding="utf-8")
        bad = self.root / "bad.txt"
        bad.write_text("re:[\n", encoding="utf-8")
        blank = self.root / "blank.txt"
        blank.write_text("re:\n", encoding="utf-8")
        invalid = self.root / "bytes.txt"
        invalid.write_bytes(b"\xff\xfe")
        for terms, code in (([], "terms-missing"), ([self.term, self.root / "missing"], "terms-unreadable"),
                            ([self.term, empty], "terms-empty-tier"), ([bad], "terms-invalid-expression"),
                            ([blank], "terms-empty-expression"), ([invalid], "terms-unreadable"),
                            ([self.term, self.term], "terms-duplicate")):
            with self.subTest(code=code):
                self.assert_error(self.audit(sources(object_row()), terms), code)

    def test_bounded_terms_and_deduplicated_rules_keep_tier_identities(self):
        extra = self.root / "extra.txt"
        extra.write_text("sensitive_marker\n", encoding="utf-8")
        report = self.audit(sources(object_row(b"sensitive_marker")), [self.term, extra])
        self.assertEqual(report["counts"]["findings"], 1)
        self.assertEqual(len(report["termFiles"]), 2)
        matched_rule = next(rule for rule in report["rules"] if len(rule["origins"]) == 2)
        self.assertEqual(report["findings"][0]["ruleId"], matched_rule["ruleId"])
        with mock.patch.object(scan, "MAX_TERM_BYTES", 5):
            self.assert_error(self.audit(sources(object_row())), "terms-too-large")

    def test_utf8_bom_terms_are_normalized_and_source_is_identified(self):
        term = self.root / "bom.txt"
        term.write_bytes(b"\xef\xbb\xbfsensitive_marker\n")
        report = self.audit(sources(object_row(b"sensitive_marker")), [term])
        self.assertEqual(report["result"], "FINDINGS")
        self.assertEqual(report["termFiles"][0]["sha256"], hashlib.sha256(term.read_bytes()).hexdigest())

    def test_empty_malformed_and_duplicate_source_collections_are_errors(self):
        row = object_row()
        invalid = [None, {}, sources(), sources(row, row), sources({**row, "data": "not bytes"}),
                   sources({**row, "kind": "tree"}), sources({**row, "oid": "bad"}),
                   sources(row, paths=[{"path": "x", "oid": row["oid"], "mode": "invalid"}]),
                   sources(row, refs=[{"name": "refs/x", "oid": row["oid"]}] * 2),
                   sources(row, gaps=["not an object"])]
        for collected in invalid:
            with self.subTest(collected=repr(collected)[:80]):
                self.assert_error(self.audit(collected))
        path = {"path": "x", "oid": row["oid"], "mode": "100644"}
        self.assert_error(self.audit(sources(row, paths=[path, path])), "path-duplicate")

    def test_fixture_and_baseline_markers_do_not_suppress_findings(self):
        collected = sources(object_row(b"token_129 fixture"), object_row(b"sensitive_marker baseline"))
        collected["dispositions"] = [{"kind": "fixture"}, {"kind": "public-baseline"}]
        report = self.audit(collected)
        self.assertEqual(report["result"], "FINDINGS")
        self.assertEqual(len(report["findings"]), 2)
        self.assertNotIn("dispositions", report)

    def test_no_text_objects_cannot_report_complete_from_only_names(self):
        report = self.audit(sources(paths=[{"path": "sub", "oid": "a" * 40, "mode": "160000"}]))
        self.assertEqual(report["result"], "INCOMPLETE")
        self.assertIn("no-text-object-scanned", [gap["code"] for gap in report["coverage"]["gaps"]])

    def test_pointer_shaped_text_with_crlf_or_bom_is_not_full_payload_coverage(self):
        for prefix in (b"", b"\xef\xbb\xbf"):
            with self.subTest(prefix=prefix):
                report = self.audit(sources(object_row(prefix + b"version https://git-lfs.github.com/spec/v1\r\nsize 13\r\n")))
                self.assertEqual(report["result"], "INCOMPLETE")
                self.assertIn("lfs-payload-unavailable", [gap["code"] for gap in report["coverage"]["gaps"]])

    def test_nonserializable_provenance_is_error_instead_of_broken_saved_report(self):
        for key, value in (("sourceIdentity", b"raw payload"), ("selection", {"bad": float("nan")})):
            collected = sources(object_row())
            collected[key] = value
            self.assert_error(self.audit(collected), "provenance-invalid")

    def test_anchored_positive_is_identical_across_supported_bom_encodings(self):
        self.term.write_text("re:^sensitive_marker$\n", encoding="utf-8")
        for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-32"):
            with self.subTest(encoding=encoding):
                report = self.audit(sources(object_row("sensitive_marker\n".encode(encoding))))
                self.assertEqual(report["result"], "FINDINGS")
                self.assertEqual(len(report["findings"]), 1)
                self.assertEqual(report["coverage"]["status"], "COMPLETE")

    def test_regular_or_symlink_path_payload_cannot_disappear_from_denominator(self):
        for mode in ("100644", "100755", "120000"):
            for oid, objects in (("a" * 40, [object_row()]),
                                 (object_row(kind="commit")["oid"], [object_row(kind="commit")])):
                with self.subTest(mode=mode, oid=oid):
                    report = self.audit(sources(*objects, paths=[{"path": "file", "oid": oid, "mode": mode}]))
                    self.assert_error(report, "path-payload-missing")

    def test_non_utf8_git_names_have_partial_scan_gap(self):
        blob = object_row()
        path = {"path": "bad\udcffname", "oid": blob["oid"], "mode": "100644"}
        ref = {"name": "refs/heads/bad\udcffname", "oid": blob["oid"]}
        for collected in (sources(blob, paths=[path]), sources(blob, refs=[ref])):
            report = self.audit(collected)
            self.assertEqual(report["result"], "INCOMPLETE")
            self.assertIn("invalid-name-encoding", [gap["code"] for gap in report["coverage"]["gaps"]])


if __name__ == "__main__":
    unittest.main()
