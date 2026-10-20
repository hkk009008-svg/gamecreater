"""Boundary and presentation checks for the offline visual-review workbench."""

from __future__ import annotations

import copy
from html.parser import HTMLParser
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from roblox_visual_html import render_packet


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.elements = []
        self.script_count = 0
        self.script_text = []
        self.in_script = False
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))
        if tag == "script":
            self.script_count += 1
            self.in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.script_text.append(data)


def fixture():
    manifest = {
        "title": "Paper in motion",
        "question": "Do layered edges improve target readability?",
        "direction": {"promise": "A physical miniature in motion.",
                      "rules": ["Readable silhouettes"], "avoid": ["Uniform noise"],
                      "preserve": ["Combat geometry"]},
        "decisions": {"status": "pending", "userVerdict": None, "nextExperiment": "Review native motion."},
    }
    captures = [{
        "id": name, "label": f"View {name}", "kind": "image",
        "mediaPath": f"media/{letter * 64}.png", "sha256": letter * 64,
        "width": 960, "height": 540, "format": "PNG", "build": {"id": name, "sha256": letter * 64},
        "context": {"captureMode": "native-still", "quality": "7", "camera": None},
        "notes": ["Native viewport."],
    } for name, letter in [("before", "a"), ("after", "b")]]
    report = {
        "status": "ready-for-review", "manifestSha256": "f" * 64,
        "captures": captures,
        "comparisons": [{
            "id": "edges", "title": "Folded edge study", "question": "Can the opponent be read?",
            "baseline": "before", "candidate": "after", "purpose": "aesthetic",
            "comparable": True, "issues": [], "differences": [],
        }],
        "coverage": [{"label": "Native touch layout", "captureIds": [], "note": "Physical phone pending."}],
        "decisions": manifest["decisions"], "limits": ["No performance claim."],
    }
    return manifest, report


class VisualHtmlTests(unittest.TestCase):
    def setUp(self):
        self.manifest, self.report = fixture()

    def render(self):
        return render_packet(self.manifest, self.report)

    def test_user_content_cannot_create_markup_or_executable_script(self):
        attack = '</script><script>alert("injected")</script><img src=x onerror=alert(1)> & "'
        self.manifest["title"] = attack
        self.manifest["direction"]["rules"] = [attack]
        self.manifest["decisions"]["userVerdict"] = attack
        self.report["captures"][0]["label"] = attack
        self.report["comparisons"][0]["differences"] = [
            {"field": attack, "baseline": attack, "candidate": {"nested": attack}, "declared": False}
        ]
        source = self.render()
        doc = Document(source)
        self.assertEqual(doc.script_count, 1)
        self.assertNotIn("injected", "".join(doc.script_text))
        self.assertIn("&lt;/script&gt;", source)
        self.assertFalse(any("onerror" in attrs for _, attrs in doc.elements))
        self.assertFalse(any(attrs.get("src") == "x" for _, attrs in doc.elements))
        self.assertTrue(any(tag == "img" and attrs.get("alt") == attack for tag, attrs in doc.elements))

    def test_media_urls_are_restricted_even_for_unpaired_gallery_items(self):
        for path in ["https://example.com/x.png", "javascript:alert(1)",
                     "../private.png", "media/a.png", "media/" + "a" * 64 + '.png" onload="x']:
            with self.subTest(path=path):
                self.report["captures"][0]["mediaPath"] = path
                with self.assertRaisesRegex(ValueError, "relative"):
                    self.render()

    def test_matching_frames_offer_overlay_but_default_to_original_side_view(self):
        doc = Document(self.render())
        overlay_buttons = [attrs for tag, attrs in doc.elements
                           if tag == "button" and attrs.get("data-view") == "overlay"]
        self.assertEqual(len(overlay_buttons), 1)
        self.assertNotIn("disabled", overlay_buttons[0])
        side = next(attrs for _, attrs in doc.elements if attrs.get("class") == "side-view")
        overlay = next(attrs for _, attrs in doc.elements if attrs.get("class") == "overlay-view")
        self.assertNotIn("hidden", side)
        self.assertIn("hidden", overlay)
        self.assertNotIn("object-fit:cover", self.render())

    def test_missing_eligibility_or_unequal_dimensions_disables_overlay(self):
        for mutate in [
            lambda report: report["comparisons"][0].update(comparable=False, issues=["Subject hidden"]),
            lambda report: report["captures"][1].update(width=1280),
            lambda report: report["captures"][1].update(height=None),
        ]:
            with self.subTest(mutate=mutate):
                self.manifest, self.report = fixture()
                mutate(self.report)
                doc = Document(self.render())
                overlay_button = next(attrs for tag, attrs in doc.elements
                                      if tag == "button" and attrs.get("data-view") == "overlay")
                self.assertIn("disabled", overlay_button)
                self.assertFalse(any(attrs.get("class") == "overlay-view" for _, attrs in doc.elements))

    def test_uncontrolled_difference_and_missing_coverage_remain_visible(self):
        self.report["status"] = "needs-evidence"
        self.report["comparisons"][0].update(
            comparable=False, issues=["Quality differs without a declared change."],
            differences=[{"field": "quality", "baseline": "3", "candidate": "7", "declared": False}],
        )
        source = self.render()
        for expected in ["Needs evidence", "Quality differs without a declared change.",
                         "Uncontrolled difference", "Missing evidence", "Physical phone pending.",
                         "Not recorded", "No performance claim."]:
            self.assertIn(expected, source)
        self.assertNotIn(">Ready for human review<", source)

    def test_many_evidence_gaps_start_collapsed_without_hiding_warning_or_disabling_evidence(self):
        self.report["status"] = "needs-evidence"
        issues = [f"Missing distinct evidence item {index}" for index in range(11)]
        self.report["comparisons"][0].update(comparable=False, issues=issues)
        source = self.render()
        doc = Document(source)
        gap_details = next(attrs for tag, attrs in doc.elements
                           if tag == "details" and attrs.get("class") == "gap-details")
        self.assertNotIn("open", gap_details)
        self.assertIn("This pair needs evidence before a controlled comparison.", source)
        self.assertIn("Inspect 11 evidence gaps", source)
        self.assertTrue(all(issue in source for issue in issues))
        overlay = next(attrs for tag, attrs in doc.elements
                       if tag == "button" and attrs.get("data-view") == "overlay")
        self.assertIn("disabled", overlay)

    def test_image_encoding_is_visible_for_lossy_and_lossless_originals(self):
        self.report["captures"][1]["format"] = "JPEG"
        self.report["captures"][1]["mediaPath"] = "media/" + "b" * 64 + ".jpg"
        source = self.render()
        self.assertIn("PNG · lossless", source)
        self.assertIn("JPEG · lossy", source)

    def test_video_pair_keeps_individual_controls_and_approximate_start_limit(self):
        for capture in self.report["captures"]:
            capture.update(kind="video", mediaPath=capture["mediaPath"].replace(".png", ".mp4"),
                           width=None, height=None)
            capture["context"]["captureMode"] = "stepped-video"
        self.report["comparisons"][0].update(comparable=False, purpose="motion", issues=["Stepped footage"])
        source = self.render()
        doc = Document(source)
        videos = [attrs for tag, attrs in doc.elements if tag == "video"]
        self.assertEqual(len(videos), 4)  # paired views and full reference gallery
        self.assertTrue(all("controls" in attrs for attrs in videos))
        self.assertIn("Approximate simultaneous start; not frame-synchronized.", source)
        self.assertIn("Stepped footage cannot establish native motion.", source)
        self.assertTrue(any("data-play-pair" in attrs for _, attrs in doc.elements))

    def test_reference_only_packet_is_explicitly_incomplete(self):
        self.report.update(comparisons=[], status="needs-evidence")
        source = self.render()
        self.assertIn("Reference gallery only.", source)
        self.assertIn("0 / 0 comparisons eligible", source)
        self.assertIn("View before", source)
        self.assertNotIn('class="comparison-panel"', source)

    def test_null_capture_metadata_is_safe_and_input_is_not_mutated(self):
        self.report["captures"][0].update(build=None, context=None, notes=None)
        before = copy.deepcopy((self.manifest, self.report))
        self.assertIn("Not recorded", self.render())
        self.assertEqual((self.manifest, self.report), before)

    def test_navigation_and_controls_have_accessible_names_and_targets(self):
        second = copy.deepcopy(self.report["comparisons"][0])
        second.update(id="second", title="Another view")
        self.report["comparisons"].append(second)
        doc = Document(self.render())
        ids = {attrs["id"] for _, attrs in doc.elements if "id" in attrs}
        nav = [attrs for tag, attrs in doc.elements if tag == "button" and "data-comparison" in attrs]
        self.assertEqual([attrs["aria-pressed"] for attrs in nav], ["true", "false"])
        self.assertTrue(all(attrs["aria-controls"] in ids for attrs in nav))
        self.assertTrue(all(attrs.get("aria-label") for tag, attrs in doc.elements
                            if tag == "input" and attrs.get("type") == "range"))
        second_panel = next(attrs for _, attrs in doc.elements if attrs.get("id") == "comparison-1")
        self.assertIn("hidden", second_panel)


if __name__ == "__main__":
    unittest.main()
