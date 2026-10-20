"""Positive paths and failure controls for the offline development map."""

from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import roblox_development_map as engine


class DevelopmentMapTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.map_path = self.root / "map.local.json"
        self.evidence = self.root / "proof.txt"
        self.evidence.write_bytes(b"observed bytes")
        self.addCleanup(patch.stopall)
        patch.object(engine, "ROOT", self.root).start()
        self.value = {
            "schemaVersion": 1, "title": "Development map", "factsCutoffUtc": "2026-10-20T22:00:00Z",
            "builtUtc": "2026-10-20T22:01:00+00:00", "route": {
                "game": "Example", "threadId": "UNASSIGNED", "hostId": "local", "task": "Example"},
            "candidate": {"id": "A", "sha256": "a" * 64, "finalVerdict": "FAIL",
                          "reason": "Needs rendering", "correction": "Proposed only"},
            "basisLegend": sorted(engine.BASES), "limits": ["Fictional fixture, not game evidence."],
            "evidence": {"proof": {"path": "proof.txt", "sha256": hashlib.sha256(b"observed bytes").hexdigest(),
                                  "readUtc": "2026-10-20T22:00:00.100Z", "basis": "Fingerprint only"}},
            "nodes": [self.node("a"), self.node("b"), self.node("c")],
            "views": [{"id": "work", "label": "Work", "context": "Declared relationships",
                       "dimension": "production", "rows": [["a", None], ["b", "c"]],
                       "edges": [self.edge("a", "b"), self.edge("b", "c", "checks")]}],
            "crossViewEdges": [],
        }

    @staticmethod
    def node(key):
        return {"id": key, "label": key.upper(), "kind": "step", "basis": "prescribed workflow",
                "status": "NOT RUN", "owner": "Example owner", "reads": "Inputs", "output": "Output",
                "evidence": ["proof"]}

    @staticmethod
    def edge(source, target, kind="depends-on"):
        return {"source": source, "target": target, "kind": kind, "relation": "declared relationship",
                "feedback": False, "evidence": ["proof"]}

    def save(self, value=None, path=None):
        path = path or self.map_path
        path.write_text(json.dumps(self.value if value is None else value), encoding="utf-8")
        return path

    def cli(self, *arguments):
        output = StringIO()
        with redirect_stdout(output):
            code = engine.main(list(map(str, arguments)))
        return code, json.loads(output.getvalue())

    def test_valid_graph_and_free_text_evidence_basis(self):
        self.save()
        code, result = self.cli("check", "--map", self.map_path)
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "structure-valid")
        self.assertEqual(result["evidenceStatus"], "not-checked")
        self.assertEqual(result["nodes"], 3)

    def test_structural_check_does_not_read_evidence_and_verify_reports_drift(self):
        self.save()
        self.evidence.write_bytes(b"changed later")
        self.assertEqual(self.cli("check", "--map", self.map_path)[0], 0)
        code, result = self.cli("check", "--map", self.map_path, "--verify-evidence")
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "structure-valid")
        self.assertEqual(result["evidence"][0]["status"], "drift")
        self.assertEqual(json.loads(self.map_path.read_text())["evidence"], self.value["evidence"])
        self.evidence.unlink()
        self.assertEqual(self.cli("check", "--map", self.map_path)[0], 0)
        self.assertEqual(self.cli("check", "--map", self.map_path, "--verify-evidence")[1]["evidence"][0]["status"], "unavailable")

    def test_verified_bytes_and_unavailable_local_inputs(self):
        self.save()
        self.assertEqual(self.cli("check", "--map", self.map_path, "--verify-evidence")[1]["evidenceStatus"], "matched")
        for path in ("https://example.com/proof", "//server/share/proof", "\\\\?\\C:\\proof", str(self.root)):
            with self.subTest(path=path):
                self.value["evidence"]["proof"]["path"] = path
                self.save()
                self.assertEqual(self.cli("check", "--map", self.map_path)[0], 0)
                self.assertEqual(self.cli("check", "--map", self.map_path, "--verify-evidence")[0], 2)

    def test_bad_structure_types_enums_references_and_memberships(self):
        cases = [
            lambda v: v.update(schemaVersion=True), lambda v: v.update(extra="unknown"),
            lambda v: v.update(nodes=[]), lambda v: v.update(limits=[]),
            lambda v: v.update(factsCutoffUtc="2026-10-21T07:00:00+09:00"),
            lambda v: v["candidate"].update(sha256="wrong"),
            lambda v: v["nodes"][0].update(level=True), lambda v: v["nodes"][0].update(kind="scheduler"),
            lambda v: v["nodes"][0].update(basis="verified"), lambda v: v["nodes"][0].update(owner=False),
            lambda v: v["nodes"][0].update(evidence=["missing"]),
            lambda v: v["views"][0].update(dimension="arbitrary"),
            lambda v: v["views"][0].update(rows=[["a", "missing"]]),
            lambda v: v["views"][0].update(rows=[["a", "a", "b", "c"]]),
            lambda v: v["views"][0].update(rows=[["a", "b"]]),
            lambda v: v["views"][0]["edges"][0].update(target="missing"),
            lambda v: v["views"][0]["edges"][0].update(kind="executes"),
            lambda v: v["views"][0]["edges"][0].update(feedback=1),
            lambda v: v["views"][0]["edges"][0].update(evidence=[]),
            lambda v: v["views"][0]["edges"][0].pop("evidence"),
            lambda v: v["basisLegend"].__setitem__(0, v["basisLegend"][1]),
        ]
        for index, mutate in enumerate(cases):
            with self.subTest(case=index):
                value = deepcopy(self.value); mutate(value); self.save(value)
                code, result = self.cli("check", "--map", self.map_path)
                self.assertEqual(code, 1)
                self.assertEqual(result["status"], "error")

    def test_duplicate_ids_edges_json_keys_and_nonfinite_json(self):
        for collection, duplicate in (("nodes", self.value["nodes"][0]), ("views", self.value["views"][0])):
            value = deepcopy(self.value); value[collection].append(deepcopy(duplicate)); self.save(value)
            self.assertEqual(self.cli("check", "--map", self.map_path)[0], 1)
        value = deepcopy(self.value); value["views"][0]["edges"].append(self.edge("a", "b")); self.save(value)
        self.assertEqual(self.cli("check", "--map", self.map_path)[0], 1)
        for raw in ('{"schemaVersion":1,"schemaVersion":1}', '{"v":NaN}', '[]', 'true', '{"v":Infinity}'):
            self.map_path.write_text(raw)
            self.assertEqual(self.cli("check", "--map", self.map_path)[0], 1)

    def test_trace_cycle_terminates_and_deduplicates_across_views(self):
        self.value["views"][0]["edges"].append(self.edge("c", "a", "returns-to"))
        self.value["crossViewEdges"].append(self.edge("a", "b"))
        engine.validate(self.value)
        result = engine.trace(self.value, "a", "out", 8)
        self.assertEqual(set(result["distances"]), {"a", "b", "c"})
        self.assertEqual(len(result["edges"]), 3)
        self.assertEqual(list(result["evidence"]), ["proof"])
        self.assertTrue(any("not proved impact" in item for item in result["limits"]))

    def test_trace_direction_depth_and_kind_filters(self):
        self.assertEqual(set(engine.trace(self.value, "a", "out", 1)["distances"]), {"a", "b"})
        self.assertEqual(set(engine.trace(self.value, "a", "out", 2)["distances"]), {"a", "b", "c"})
        self.assertEqual(set(engine.trace(self.value, "b", "in", 1)["distances"]), {"a", "b"})
        self.assertEqual(set(engine.trace(self.value, "b", "both", 1)["distances"]), {"a", "b", "c"})
        self.assertEqual(set(engine.trace(self.value, "a", "out", 8, ["checks"])["distances"]), {"a"})
        self.save()
        code, result = self.cli("trace", "--map", self.map_path, "--node", "a", "--depth", 2,
                                "--direction", "out", "--kind", "depends-on", "--kind", "checks")
        self.assertEqual(code, 0); self.assertEqual(len(result["edges"]), 2)
        for extra in (("--node", "missing"), ("--node", "a", "--depth", "0"), ("--node", "a", "--depth", "9")):
            self.assertEqual(self.cli("trace", "--map", self.map_path, *extra)[0], 1)

    def test_compare_candidate_change_retains_each_declared_verdict(self):
        after = deepcopy(self.value)
        after["candidate"].update(id="B", sha256="b" * 64, finalVerdict="NOT RUN")
        after["nodes"][0]["status"] = "New draft"
        after["views"][0]["edges"][0]["feedback"] = True
        after["evidence"]["proof"]["sha256"] = "c" * 64
        self.save(); second = self.save(after, self.root / "after.json")
        code, result = self.cli("compare", "--before", self.map_path, "--after", second)
        self.assertEqual(code, 0); self.assertTrue(result["candidateIdentityChanged"])
        self.assertEqual(result["candidate"]["finalVerdict"], {"before": "FAIL", "after": "NOT RUN"})
        self.assertEqual(len(result["nodes"]["changed"]), 1)
        self.assertEqual(len(result["edges"]["changed"]), 1)
        self.assertEqual(len(result["evidence"]["changed"]), 1)
        self.assertEqual(json.loads(second.read_text())["candidate"]["finalVerdict"], "NOT RUN")

    def test_compare_exposes_context_changes_and_digest_case_is_not_new_identity(self):
        after = deepcopy(self.value)
        after["route"]["task"] = "Different task"
        after["factsCutoffUtc"] = "2026-10-20T22:00:01Z"
        after["limits"].append("Additional gap")
        after["candidate"]["sha256"] = after["candidate"]["sha256"].upper()
        result = engine.compare(self.value, after)
        self.assertFalse(result["candidateIdentityChanged"])
        self.assertEqual(set(result["metadata"]), {"route", "factsCutoffUtc", "limits"})
        self.assertTrue(result["candidate"])

    def test_unknown_candidate_identity_stays_unknown_without_acceptance(self):
        self.value["candidate"].update(id=None, sha256=None, finalVerdict="UNKNOWN")
        self.save()
        self.assertEqual(self.cli("check", "--map", self.map_path)[0], 0)
        out = self.root / "team/development-maps/unknown.md"
        self.assertEqual(self.cli("report", "--map", self.map_path, "--out", out)[0], 0)
        self.assertIn("candidate.id: unknown", out.read_text())
        for verdict in ("PASS", "GO", "FAIL"):
            self.value["candidate"]["finalVerdict"] = verdict
            self.save()
            self.assertEqual(self.cli("check", "--map", self.map_path)[0], 1)
        self.value["candidate"].update(id="B", finalVerdict="NOT RUN")
        engine.validate(self.value)

    def test_report_deterministic_exclusive_contained_and_escaped(self):
        attack = '"] --> evil["x</script><img src=x onerror=alert(1)>\n```mermaid\nclick n0 "https://bad"'
        self.value["title"] = attack
        self.value["nodes"][0]["label"] = attack
        self.value["views"][0]["edges"][0]["relation"] = attack
        self.save(); out = self.root / "team/development-maps/first.md"
        code, result = self.cli("report", "--map", self.map_path, "--out", out)
        self.assertEqual(code, 0); original = out.read_bytes()
        text = original.decode()
        self.assertNotIn("<script", text); self.assertNotIn("<img", text)
        self.assertNotIn('\nclick n0', text); self.assertNotIn('\n```mermaid\nclick', text)
        self.assertEqual(text.count("```mermaid"), 1)
        self.assertIn("#34;", text)
        self.assertEqual(hashlib.sha256(original).hexdigest(), result["sha256"])
        self.assertEqual(self.cli("report", "--map", self.map_path, "--out", out)[0], 1)
        self.assertEqual(out.read_bytes(), original)
        second = out.with_name("second.md")
        self.assertEqual(self.cli("report", "--map", self.map_path, "--out", second)[0], 0)
        self.assertEqual(second.read_bytes(), original)
        for bad in (self.root / "outside.md", out.parent / "../escape.md", out.with_suffix(".html")):
            self.assertEqual(self.cli("report", "--map", self.map_path, "--out", bad)[0], 1)
            self.assertFalse(bad.exists())

    def test_limits_and_argument_failures_are_structured(self):
        self.save()
        with patch.object(engine, "MAX_MAP", 16):
            self.assertEqual(self.cli("check", "--map", self.map_path)[0], 1)
        with patch.object(engine, "MAX_EVIDENCE", 4):
            self.assertEqual(self.cli("check", "--map", self.map_path, "--verify-evidence")[0], 2)
        with patch.object(engine, "MAX_TOTAL", 4):
            self.assertEqual(self.cli("check", "--map", self.map_path, "--verify-evidence")[0], 2)
        for args in ((), ("check",), ("trace", "--map", str(self.map_path), "--node", "a", "--kind", "bad")):
            self.assertEqual(self.cli(*args)[0], 1)

    def test_windows_aliases_streams_and_devices_refused_before_access(self):
        for raw in ("existing.md:stream.md", "C:relative.md", "folder. /file.md", "folder./file.md",
                    "CON.md", "aux", "COM1.md", "LPT9.txt", "file.md ", "bad?.md"):
            with self.subTest(path=raw), patch.object(engine, "safe_absolute") as filesystem:
                with self.assertRaises(ValueError):
                    engine.local_path(raw, self.root, missing=True)
                filesystem.assert_not_called()
        with patch.object(engine.os, "name", "nt"), patch.object(engine, "safe_absolute") as filesystem:
            with self.assertRaises(ValueError):
                engine.local_path("\\ambiguous\\file.md", self.root, missing=True)
            filesystem.assert_not_called()

    def test_reparse_component_is_refused_before_output(self):
        self.save(); output = self.root / "team/development-maps/result.md"
        root = self.root
        original = Path.lstat
        def marked(path, *args, **kwargs):
            info = original(path, *args, **kwargs)
            if path == root:
                class Reparse:
                    st_mode = info.st_mode
                    st_file_attributes = 0x400
                return Reparse()
            return info
        with patch.object(Path, "lstat", marked):
            with self.assertRaisesRegex(ValueError, "reparse"):
                engine.write_report(self.value, "a" * 64, output)
        self.assertFalse(output.exists())

    def test_real_symlink_input_and_output_when_permitted(self):
        link = self.root / "linked"
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Host does not permit symlink creation; deterministic reparse control still runs")
        self.save()
        self.assertEqual(self.cli("check", "--map", link / self.map_path.name)[0], 1)
        with self.assertRaisesRegex(ValueError, "reparse"):
            engine.write_report(self.value, "a" * 64, link / "team/development-maps/report.md")

    def test_rewritten_stable_file_is_readable_despite_windows_ctime_semantics(self):
        self.save(); self.value["title"] = "Later stable revision"; self.save()
        value, _, _ = engine.load_map(self.map_path)
        self.assertEqual(value["title"], "Later stable revision")


if __name__ == "__main__":
    unittest.main()
