"""Exercise the saved audit consumer with actual Git bytes and failure controls."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import uuid

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import publication_audit as audit


class PublicationAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="publication-consumer-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.harness = self.base / "harness"
        (self.harness / "team").mkdir(parents=True)
        (self.harness / "scripts").mkdir()
        (self.harness / "scripts/scrub_terms.txt").write_bytes(
            (ROOT / "scripts/scrub_terms.txt").read_bytes())
        self.repo = self.base / "audited repository"
        self.git("-c", "init.templateDir=", "init", "-q", str(self.repo), cwd=self.base)
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture" + "@" + "invalid.test")
        (self.repo / "README.md").write_text("ordinary harmless content\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-qm", "fixture baseline")
        self.terms = self.base / "terms.txt"
        self.terms.write_text("fixture-sensitive-marker\n", encoding="utf-8")

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.repo,
                              capture_output=True, check=True, timeout=20)

    def run_audit(self, *args, name=None, parse_report=True):
        name = name or uuid.uuid4().hex
        report = self.harness / "team" / f"{name}.local.json"
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(audit, "ROOT", self.harness), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            code = audit.main(["--repo", str(self.repo), "--out", str(report), *args])
        return code, json.loads(report.read_text(encoding="utf-8")) if report.exists() and parse_report else None, stdout.getvalue(), stderr.getvalue()

    def plant_staged(self):
        (self.repo / "README.md").write_text("fixture-sensitive-marker\n", encoding="utf-8")
        self.git("add", "README.md")
        # The working copy disagrees; consumer must scan the staged blob.
        (self.repo / "README.md").write_text("harmless decoy\n", encoding="utf-8")

    def test_actual_tree_allow_and_staged_finding_consumer_paths(self):
        code, report, _, _ = self.run_audit("--tree", "HEAD", "--local-terms", str(self.terms))
        self.assertEqual((code, report["result"]), (0, "CLEAN_WITHIN_SCOPE"))
        self.assertFalse(report["authorityGranted"])
        self.plant_staged()
        code, report, stdout, _ = self.run_audit("--index", "--local-terms", str(self.terms))
        self.assertEqual((code, report["result"]), (1, "FINDINGS"))
        self.assertGreater(len(report["findings"]), 0)
        self.assertNotIn("fixture-sensitive-marker", stdout)
        self.assertNotIn("fixture-sensitive-marker", json.dumps(report))

    def test_requested_missing_terms_and_collection_failure_are_errors(self):
        code, report, _, _ = self.run_audit("--tree", "HEAD", "--local-terms", str(self.base / "missing.txt"))
        self.assertEqual((code, report["result"]), (2, "ERROR"))
        import publication_git
        with mock.patch.object(publication_git, "collect_sources", side_effect=SystemExit(0)):
            code, report, _, _ = self.run_audit("--index")
        self.assertEqual((code, report["result"]), (2, "ERROR"))
        self.assertEqual(report["error"]["stage"], "collection")
        with mock.patch.object(publication_git, "collect_sources", side_effect=publication_git.AuditError("object_size_limit")):
            code, report, _, _ = self.run_audit("--index")
        self.assertEqual(code, 2)
        self.assertEqual(report["error"]["code"], "object_size_limit")

    def test_explicit_budgets_reach_real_collector_and_suffix_scanner(self):
        import publication_git
        import publication_scan
        (self.repo / "README.md").write_text("ordinary " * 700 + "fixture-sensitive-marker\n", encoding="utf-8")
        self.git("add", "README.md")
        default_code, default, _, _ = self.run_audit("--index", "--local-terms", str(self.terms))
        self.assertEqual((default_code, default["result"]), (2, "INCOMPLETE"))
        self.assertEqual(default["findings"], [])
        with mock.patch.object(publication_git, "collect_sources", wraps=publication_git.collect_sources) as collect, \
                mock.patch.object(publication_scan, "scan_sources", wraps=publication_scan.scan_sources) as scan:
            code, report, _, _ = self.run_audit(
                "--index", "--local-terms", str(self.terms), "--max-object-bytes", "8192",
                "--max-total-bytes", "16384", "--max-line-chars", "8192")
        self.assertEqual((code, report["result"]), (1, "FINDINGS"))
        self.assertEqual(len(report["findings"]), 1)
        self.assertEqual(collect.call_args.kwargs["limits"],
                         {"max_object_bytes": 8192, "max_total_bytes": 16384})
        self.assertEqual(scan.call_args.kwargs, {"max_line_chars": 8192})
        self.assertEqual(report["budgets"]["scanner"]["maxLineChars"], 8192)
        self.assertEqual(report["budgets"]["collector"]["max_object_bytes"], 8192)
        self.assertEqual(report["request"]["budgets"]["max_line_chars"], 8192)
        self.assertNotEqual(report["scanIdentity"], default["scanIdentity"])
        self.assertFalse(report["authorityGranted"])
        self.assertFalse(report["publicationClearance"])
        too_small_code, too_small, _, _ = self.run_audit("--index", "--max-object-bytes", "1024")
        self.assertEqual((too_small_code, too_small["result"]), (2, "ERROR"))
        self.assertEqual(too_small["error"]["code"], "object_size_limit")

    def test_explicit_budget_errors_refuse_before_collection(self):
        import publication_git
        for args in [("--max-object-bytes", "0"), ("--max-total-bytes", "-1"),
                     ("--max-line-chars", "1048577"), ("--max-object-bytes", str(audit.MAX_OBJECT_BUDGET + 1)),
                     ("--max-total-bytes", str(audit.MAX_TOTAL_BUDGET + 1)),
                     ("--max-object-bytes", "8192", "--max-total-bytes", "4096")]:
            with self.subTest(args=args), mock.patch.object(publication_git, "collect_sources") as collect:
                code, report, _, _ = self.run_audit("--index", *args)
                self.assertEqual((code, report["result"]), (2, "ERROR"))
                self.assertEqual(report["error"]["stage"], "limits")
                collect.assert_not_called()

    def test_collector_and_scanner_calls_receive_real_arguments(self):
        import publication_git
        import publication_scan
        with mock.patch.object(publication_git, "collect_sources", wraps=publication_git.collect_sources) as collect, \
                mock.patch.object(publication_scan, "scan_sources", wraps=publication_scan.scan_sources) as scan:
            code, report, _, _ = self.run_audit("--tree", "HEAD", "--local-terms", str(self.terms))
        self.assertEqual(code, 0, report)
        collect.assert_called_once_with(self.repo, "tree", target="HEAD")
        self.assertEqual(scan.call_count, 1)
        self.assertEqual(scan.call_args.args[1], [self.harness / "scripts/scrub_terms.txt", self.terms])
        self.assertTrue(scan.call_args.args[0]["objects"])

    def test_unknown_scanner_result_refuses_and_keeps_error_report(self):
        import publication_scan
        with mock.patch.object(publication_scan, "scan_sources", return_value={"result": "ALLOW"}):
            code, report, _, _ = self.run_audit("--index")
        self.assertEqual((code, report["result"]), (2, "ERROR"))

    def test_inconsistent_scanner_status_cannot_claim_clean(self):
        import publication_scan
        cases = [
            {"execution": "ERROR", "result": "CLEAN_WITHIN_SCOPE", "findings": [], "coverage": {"status": "COMPLETE"}},
            {"execution": "PASS", "result": "CLEAN_WITHIN_SCOPE", "findings": [{"fingerprint": "fixture"}], "coverage": {"status": "COMPLETE"}},
            {"execution": "PASS", "result": "CLEAN_WITHIN_SCOPE", "findings": [], "coverage": {"status": "INCOMPLETE"}},
            {"execution": "PASS", "result": "CLEAN_WITHIN_SCOPE", "findings": [], "coverage": {"status": "COMPLETE", "gaps": [{"code": "fixture-gap"}]}},
            {"execution": "PASS", "result": "CLEAN_WITHIN_SCOPE", "findings": [], "coverage": {"status": "COMPLETE", "gaps": None}},
        ]
        for case in cases:
            with self.subTest(case=case), mock.patch.object(publication_scan, "scan_sources", return_value=case):
                code, report, _, _ = self.run_audit("--index")
                self.assertEqual((code, report["result"]), (2, "ERROR"))

    def test_no_clobber_or_write_outside_harness_team(self):
        import publication_git
        path = self.harness / "team/existing.local.json"
        path.write_bytes(b"retain exact evidence")
        with mock.patch.object(publication_git, "collect_sources") as collect:
            code, _, _, _ = self.run_audit("--index", name="existing", parse_report=False)
        self.assertEqual(code, 2)
        self.assertEqual(path.read_bytes(), b"retain exact evidence")
        collect.assert_not_called()
        for out in (self.repo / "forbidden.local.json", self.harness / "report.json"):
            with self.subTest(path=out), mock.patch.object(audit, "ROOT", self.harness), \
                    redirect_stderr(io.StringIO()):
                code = audit.main(["--repo", str(self.repo), "--index", "--out", str(out)])
                self.assertEqual(code, 2)
                self.assertFalse(out.exists())

    def test_dispositions_retain_findings_and_finding_exit(self):
        self.plant_staged()
        args = ["--index", "--local-terms", str(self.terms)]
        _, raw, _, _ = self.run_audit(*args)
        entries = [{"fingerprint": finding["fingerprint"], "classification": "synthetic-fixture",
                    "rationale": "Declared invalid-input fixture; no permission or waiver."}
                   for finding in raw["findings"]]
        path = self.base / "dispositions.json"
        path.write_text(json.dumps({"schemaVersion": 1, "scanIdentity": raw["scanIdentity"], "entries": entries}), encoding="utf-8")
        code, report, _, _ = self.run_audit(*args, "--dispositions", str(path))
        self.assertEqual((code, report["result"]), (1, "FINDINGS"))
        self.assertEqual(report["findings"], raw["findings"])
        self.assertEqual(report["dispositions"]["unclassifiedCount"], 0)

    def test_binary_coverage_gap_is_not_a_clean_consumer_result(self):
        (self.repo / "binary.dat").write_bytes(b"fixture-sensitive-marker\x00binary")
        self.git("add", "binary.dat")
        code, report, _, _ = self.run_audit("--index", "--local-terms", str(self.terms))
        self.assertEqual((code, report["result"]), (2, "INCOMPLETE"))
        self.assertEqual(report["coverage"]["status"], "INCOMPLETE")
        self.assertTrue(report["coverage"]["gaps"])

    def test_stale_unknown_duplicate_or_malformed_dispositions_refuse(self):
        self.plant_staged()
        args = ["--index", "--local-terms", str(self.terms)]
        _, raw, _, _ = self.run_audit(*args)
        entry = {"fingerprint": raw["findings"][0]["fingerprint"],
                 "classification": "synthetic-fixture", "rationale": "Declared fixture"}
        good = {"schemaVersion": 1, "scanIdentity": raw["scanIdentity"], "entries": [entry]}
        cases = []
        bad = copy.deepcopy(good); bad["scanIdentity"] = "stale"; cases.append(json.dumps(bad))
        bad = copy.deepcopy(good); bad["entries"][0]["fingerprint"] = "unknown"; cases.append(json.dumps(bad))
        bad = copy.deepcopy(good); bad["entries"] *= 2; cases.append(json.dumps(bad))
        bad = copy.deepcopy(good); bad["entries"][0]["classification"] = "approved"; cases.append(json.dumps(bad))
        # Keep the rest of the payload valid so last-key-wins parsing would
        # actually admit this case, rather than another missing-field guard.
        cases += [json.dumps(good)[:-1] + ', "schemaVersion": 1}', "null"]
        for i, value in enumerate(cases):
            path = self.base / f"bad-{i}.json"; path.write_text(value, encoding="utf-8")
            with self.subTest(case=i):
                code, report, _, _ = self.run_audit(*args, "--dispositions", str(path))
                self.assertEqual((code, report["result"]), (2, "ERROR"))
                self.assertEqual(report["findings"], raw["findings"])
                self.assertEqual(report["rawScanResult"], "FINDINGS")

    def test_actual_saved_cli_entry(self):
        out = ROOT / "team" / f"publication-test-{uuid.uuid4().hex}.local.json"
        self.addCleanup(lambda: out.unlink(missing_ok=True))
        result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/publication_audit.py"),
                                 "--repo", str(self.repo), "--tree", "HEAD", "--out", str(out)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["result"], "CLEAN_WITHIN_SCOPE")


if __name__ == "__main__":
    unittest.main()
