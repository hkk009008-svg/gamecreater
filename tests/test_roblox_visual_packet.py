"""Positive and fault-injected controls for visual evidence inspection."""

from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import roblox_visual_packet as packet


class VisualPacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output_root = self.root / "team" / "visual-packets"
        self.addCleanup(patch.stopall)
        patch.object(packet, "ROOT", self.root).start()
        patch.object(packet, "PACKET_ROOT", self.output_root).start()
        self.manifest = self.root / "test.local.json"
        self.value = {
            "schemaVersion": 1, "title": "Paper depth", "question": "Does the fold read?",
            "direction": {"promise": "Tactile paper", "rules": ["Readable"],
                          "avoid": ["Noise"], "preserve": ["Target geometry"]},
            "captures": [self.capture("a"), self.capture("b", color="blue")],
            "comparisons": [{"id": "ab", "title": "Fold", "question": "Readable?",
                             "baseline": "a", "candidate": "b", "purpose": "aesthetic",
                             "changedFactors": [], "requiredLayers": ["world", "hud"]}],
            "coverage": [{"label": "Desktop", "captureIds": ["a", "b"], "note": "Declared desktop"}],
            "decisions": {"status": "pending", "userVerdict": None, "nextExperiment": "Playtest"},
        }

    def capture(self, name, *, color="red", fmt="PNG"):
        output = BytesIO()
        Image.new("RGB", (32, 24), color).save(output, format=fmt)
        media = output.getvalue()
        path = self.root / f"{name}.{fmt.lower()}"
        path.write_bytes(media)
        return {
            "id": name, "label": name,
            "media": {"path": str(path), "sha256": hashlib.sha256(media).hexdigest()},
            "build": {"id": "build-1", "sha256": "a" * 64},
            "context": {
                "map": "Hollow", "subject": "Bot", "phase": "Idle", "lighting": "Soft",
                "quality": "6", "device": "Desktop", "randomState": "17",
                "camera": [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1], "fov": 70,
                "viewport": [32, 24], "input": "native", "captureMode": "native-still",
                "sequenceTime": 0,
            },
            "eligibility": {
                "subjectVisible": True, "unscaled": True, "repeat": None,
                "controls": [{"layer": layer, "visible": True, "evidence": name}
                             for layer in ("world", "hud")],
            }, "notes": [],
        }

    def save(self):
        self.manifest.write_text(json.dumps(self.value), encoding="utf-8")
        return self.manifest

    def inspect(self):
        return packet.inspect_manifest(self.save())[1]

    def gap(self, expected):
        report = self.inspect()
        self.assertEqual(report["status"], "needs-evidence")
        self.assertFalse(report["comparisons"][0]["comparable"])
        self.assertIn(expected, " ".join(report["comparisons"][0]["issues"]))
        return report

    def test_valid_pair_and_known_declared_factor(self):
        self.assertEqual(self.inspect()["status"], "ready-for-review")
        self.value["captures"][1]["context"]["lighting"] = "Raking"
        self.gap("Undeclared context difference: lighting")
        self.value["comparisons"][0]["changedFactors"] = ["lighting"]
        report = self.inspect()
        self.assertEqual(report["status"], "ready-for-review")
        self.assertTrue(report["comparisons"][0]["differences"][0]["declared"])

    def test_unknown_never_matches_even_for_declared_factor(self):
        self.value["comparisons"][0]["changedFactors"] = ["lighting"]
        for capture in self.value["captures"]:
            capture["context"]["lighting"] = None
        self.gap("unknown lighting")
        for capture in self.value["captures"]:
            capture["context"]["lighting"] = "Soft"
            capture["context"]["sequenceTime"] = None
        self.value["comparisons"][0]["changedFactors"] = ["sequenceTime"]
        self.gap("declared changed factor sequenceTime is unknown")

    def test_missing_hash_missing_file_and_corrupted_image_are_errors(self):
        original = deepcopy(self.value)
        self.value["captures"][0]["media"]["sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.inspect()
        self.value = deepcopy(original)
        self.value["captures"][0]["media"]["path"] = str(self.root / "absent.png")
        with self.assertRaises(FileNotFoundError):
            self.inspect()
        self.value = original
        path = Path(self.value["captures"][0]["media"]["path"])
        raw = path.read_bytes()[:40]
        path.write_bytes(raw)
        self.value["captures"][0]["media"]["sha256"] = hashlib.sha256(raw).hexdigest()
        with self.assertRaises(ValueError):
            self.inspect()

    def test_strict_json_unknown_duplicate_nan_and_boolean_numbers(self):
        valid = deepcopy(self.value)
        self.value["extra"] = True
        with self.assertRaises(ValueError):
            self.inspect()
        self.value = deepcopy(valid)
        self.value["captures"][0]["context"]["fov"] = True
        with self.assertRaises(ValueError):
            self.inspect()
        self.value = deepcopy(valid)
        self.value["captures"][0]["context"]["fov"] = float("nan")
        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            self.inspect()
        self.save()
        self.manifest.write_text('{"schemaVersion":1,"schemaVersion":1}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            packet.inspect_manifest(self.manifest)

    def test_control_failures_occlusion_and_wrong_control_metadata(self):
        original = deepcopy(self.value)
        self.value["captures"][0]["eligibility"]["controls"].pop()
        self.gap("hud visibility control")
        self.value = deepcopy(original)
        self.value["captures"][0]["eligibility"]["controls"][1]["visible"] = False
        self.gap("hud visibility control")
        self.value = deepcopy(original)
        self.value["captures"][0]["eligibility"]["subjectVisible"] = False
        self.gap("subject visibility")
        self.value = deepcopy(original)
        evidence = self.capture("control")
        evidence["context"]["quality"] = "2"
        self.value["captures"].append(evidence)
        self.value["captures"][0]["eligibility"]["controls"][1]["evidence"] = "control"
        self.gap("control evidence has incompatible quality")
        evidence["context"]["quality"] = "6"
        media = BytesIO()
        Image.new("RGB", (16, 12), "green").save(media, format="PNG")
        raw = media.getvalue()
        Path(evidence["media"]["path"]).write_bytes(raw)
        evidence["media"]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.gap("control evidence decoded dimensions do not match")

    def test_image_video_capture_modes_must_match_actual_media(self):
        for capture in self.value["captures"]:
            capture["context"]["captureMode"] = "native-video"
        self.gap("media kind is incompatible")
        with self.assertRaisesRegex(ValueError, "not a supported MP4"):
            packet.inspect_media(b"\x00\x00\x00\x18ftypavif\x00\x00\x00\x00avifmif1")
        with self.assertRaisesRegex(ValueError, "not a supported MP4"):
            packet.inspect_media(b"\x00\x00\x00\x18ftypM4A \x00\x00\x00\x00M4A xxxx")

    def pixel_repeats(self):
        self.value["comparisons"][0]["purpose"] = "pixel"
        for original in self.value["captures"][:2]:
            repeat = self.capture(original["id"] + "r")
            original["eligibility"]["repeat"] = repeat["id"]
            self.value["captures"].append(repeat)

    def test_pixel_positive_and_repeat_faults(self):
        self.pixel_repeats()
        self.assertEqual(self.inspect()["status"], "ready-for-review")
        valid = deepcopy(self.value)
        self.value["captures"][2]["build"]["id"] = "another-build"
        self.gap("same build and context")
        self.value = deepcopy(valid)
        self.value["captures"][2]["context"]["camera"][0] = 5
        self.gap("same build and context")
        self.value = deepcopy(valid)
        self.value["captures"][2]["eligibility"]["controls"][0]["visible"] = False
        self.gap("repeat: ar: world visibility")
        self.value = deepcopy(valid)
        self.value["captures"][2]["media"] = deepcopy(self.value["captures"][0]["media"])
        self.gap("repeat reuses the original")
        self.value = deepcopy(valid)
        self.value["captures"][0]["eligibility"]["repeat"] = None
        self.gap("distinct repeat")

    def test_jpeg_allowed_for_aesthetic_not_pixel_and_dimensions_checked(self):
        self.value["captures"][0] = self.capture("a-jpeg", fmt="JPEG")
        self.value["comparisons"][0]["baseline"] = "a-jpeg"
        self.value["coverage"][0]["captureIds"] = ["a-jpeg", "b"]
        self.assertEqual(self.inspect()["status"], "ready-for-review")
        self.value["comparisons"][0]["purpose"] = "pixel"
        self.gap("requires decoded PNG")
        self.value["comparisons"][0]["purpose"] = "aesthetic"
        self.value["captures"][0]["context"]["viewport"] = [16, 12]
        self.gap("decoded dimensions")

    def test_motion_stepped_is_not_native_and_container_only_limit(self):
        raw = b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isommp42"
        for capture in self.value["captures"]:
            path = self.root / (capture["id"] + ".mp4")
            path.write_bytes(raw)
            capture["media"] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
            capture["context"]["captureMode"] = "native-video"
        self.value["comparisons"][0]["purpose"] = "motion"
        report = self.inspect()
        self.assertEqual(report["status"], "ready-for-review")
        self.assertIn("signature-checked only", " ".join(report["limits"]))
        for capture in self.value["captures"]:
            capture["context"]["captureMode"] = "stepped-video"
        self.gap("native motion requires")

    def test_gallery_and_missing_coverage_stay_needs_evidence(self):
        self.value["coverage"].append({"label": "Phone", "captureIds": [], "note": "Not captured"})
        report = self.inspect()
        self.assertEqual(report["status"], "needs-evidence")
        self.assertEqual(report["missingCoverage"], ["Phone"])
        self.value["comparisons"] = []
        self.assertEqual(self.inspect()["status"], "needs-evidence")

    def test_build_original_bytes_new_only_and_no_output_on_bad_inputs(self):
        self.save()
        out = self.output_root / "candidate"
        with patch.dict(sys.modules, {"roblox_visual_html": type("Renderer", (), {
            "render_packet": staticmethod(lambda manifest, report: "<!doctype html>safe")})}):
            report = packet.build_packet(self.manifest, out)
            self.assertEqual((out / "index.html").read_text(), "<!doctype html>safe")
            self.assertEqual((out / "manifest.json").read_bytes(), self.manifest.read_bytes())
            self.assertEqual(hashlib.sha256((out / "manifest.json").read_bytes()).hexdigest(),
                             report["manifestSha256"])
            for capture in report["captures"]:
                copied = (out / capture["mediaPath"]).read_bytes()
                self.assertEqual(hashlib.sha256(copied).hexdigest(), capture["sha256"])
            with self.assertRaisesRegex(ValueError, "already exists"):
                packet.build_packet(self.manifest, out)
            with self.assertRaisesRegex(ValueError, "inside"):
                packet.build_packet(self.manifest, self.root / "outside")
            self.value["captures"][0]["media"]["sha256"] = "0" * 64
            self.save()
            bad = self.output_root / "bad"
            with self.assertRaises(ValueError):
                packet.build_packet(self.manifest, bad)
            self.assertFalse(bad.exists())

    def test_required_comparable_exit_and_structural_failure_json(self):
        self.value["captures"][0]["context"]["quality"] = None
        self.save()
        stream = StringIO()
        with redirect_stdout(stream):
            code = packet.main(["check", "--manifest", str(self.manifest), "--require-comparable"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stream.getvalue())["status"], "needs-evidence")
        self.value["captures"][0]["media"]["sha256"] = "0" * 64
        self.save()
        stream = StringIO()
        with redirect_stdout(stream):
            code = packet.main(["check", "--manifest", str(self.manifest)])
        self.assertEqual(code, 1)
        self.assertTrue(json.loads(stream.getvalue())["errors"])

    def test_init_hashes_unknown_defaults_fresh_only_and_bound(self):
        out = self.root / "team" / "experiment.local.json"
        paths = [Path(capture["media"]["path"]) for capture in self.value["captures"]]
        result = packet.init_manifest(paths, out)
        self.assertEqual(result["captures"][0]["media"]["sha256"],
                         hashlib.sha256(paths[0].read_bytes()).hexdigest())
        self.assertIsNone(result["captures"][0]["build"]["id"])
        self.assertIsNone(result["captures"][0]["context"]["viewport"])
        self.assertEqual(result["captures"][0]["context"]["captureMode"], "unknown")
        self.assertEqual(packet.inspect_manifest(out)[1]["status"], "needs-evidence")
        with self.assertRaisesRegex(ValueError, "already exists"):
            packet.init_manifest(paths, out)
        with self.assertRaisesRegex(ValueError, "inside"):
            packet.init_manifest(paths, self.root.parent / "outside.local.json")
        with self.assertRaisesRegex(ValueError, "local.json"):
            packet.init_manifest(paths, self.root / "wrong.json")

    def test_reparse_path_rejected_with_deterministic_control(self):
        path = Path(self.value["captures"][0]["media"]["path"])
        original = Path.lstat
        def reparse(target):
            info = original(target)
            if target == path:
                fields = {key: getattr(info, key) for key in dir(info) if key.startswith("st_")}
                fields["st_file_attributes"] = 0x400
                return type("Stat", (), fields)()
            return info
        self.save()
        with patch.object(Path, "lstat", reparse):
            with self.assertRaisesRegex(ValueError, "reparse"):
                packet.inspect_manifest(self.manifest)

    def test_link_input_and_output_refused_when_host_supports_links(self):
        link = self.root / "linked"
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest("Host does not permit symlink creation")
        self.save()
        self.value["captures"][0]["media"]["path"] = str(link / "a.png")
        with self.assertRaisesRegex(ValueError, "Linked/reparse"):
            self.inspect()
        self.value["captures"][0]["media"]["path"] = str(self.root / "a.png")
        self.save()
        with self.assertRaisesRegex(ValueError, "Linked/reparse"):
            packet.build_packet(self.manifest, link / "team" / "visual-packets" / "new")

    def test_size_limits_and_http_input(self):
        self.value["captures"][0]["media"]["path"] = "https://example.org/image.png"
        with self.assertRaisesRegex(ValueError, "local filesystem"):
            self.inspect()
        self.value["captures"][0]["media"]["path"] = str(self.root / "a.png")
        with patch.object(packet, "MAX_MEDIA", 4):
            with self.assertRaisesRegex(ValueError, "no larger"):
                self.inspect()
        for path in ("//server/share/image.png", "\\\\server\\share\\image.png",
                     "\\\\?\\C:\\image.png", "\\\\.\\device"):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "Network shares"):
                packet.local_path(path, self.root)

    def test_cli_json_survives_legacy_console_and_retains_unicode(self):
        self.value["captures"][0]["label"] = "Paper \u2014 \U0001f4dc"
        self.save()
        class LegacyConsole(StringIO):
            def write(self, value):
                value.encode("cp949")
                return super().write(value)
        output = LegacyConsole()
        with redirect_stdout(output):
            code = packet.main(["check", "--manifest", str(self.manifest)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["captures"][0]["label"],
                         self.value["captures"][0]["label"])
        process = subprocess.run(
            [sys.executable, str(Path(packet.__file__)), "check", "--manifest", str(self.manifest)],
            env={**os.environ, "PYTHONIOENCODING": "cp949"}, capture_output=True, check=False)
        self.assertEqual(process.returncode, 0, process.stderr)
        actual = json.loads(process.stdout.decode("cp949"))
        self.assertEqual(actual["captures"][0]["label"], self.value["captures"][0]["label"])

    def test_malformed_metadata_and_unknown_references_are_rejected(self):
        valid = deepcopy(self.value)
        mutations = [
            lambda: self.value["captures"][0]["context"].update(viewport=[32, 24.0]),
            lambda: self.value["captures"][0]["eligibility"].update(subjectVisible="true"),
            lambda: self.value["captures"][0]["eligibility"].update(repeat="absent"),
            lambda: self.value["comparisons"][0].update(changedFactors=["camera", "lighting"]),
            lambda: self.value["captures"][0]["context"].update(camera=[1] * 11),
            lambda: self.value["captures"][0]["context"].update(fov=10 ** 400),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.value = deepcopy(valid)
                mutation()
                with self.assertRaises(ValueError):
                    self.inspect()


if __name__ == "__main__":
    unittest.main()
