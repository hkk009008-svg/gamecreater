import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import scrub_check as sc


class TestLoadTerms(unittest.TestCase):
    def test_literals_and_regexes(self):
        pats = sc.load_terms(["# comment\nsecretword\nre:tok_[0-9]+\n"])
        self.assertEqual(len(pats), 2)

    def test_empty_input_loads_nothing(self):
        self.assertEqual(sc.load_terms([]), [])
        self.assertEqual(sc.load_terms(["# only comments\n"]), [])


class TestScanText(unittest.TestCase):
    def setUp(self):
        self.pats = sc.load_terms(["projectnoun\nre:[a-z0-9.]+@[a-z]+\\.com\n"])

    def test_hit_reports_file_line_term(self):
        hits = sc.scan_text("doc.md", "clean\nhas ProjectNoun here\n",
                            self.pats)
        self.assertEqual(len(hits), 1)
        self.assertIn("doc.md:2", hits[0])

    def test_regex_hits(self):
        hits = sc.scan_text("a.txt", "mail me: someone@example.com",
                            self.pats)
        self.assertEqual(len(hits), 1)

    def test_clean_text_no_hits(self):
        self.assertEqual(
            sc.scan_text("a.txt", "nothing to see", self.pats), [])

    def test_case_insensitive_literal(self):
        hits = sc.scan_text("a.txt", "PROJECTNOUN", self.pats)
        self.assertEqual(len(hits), 1)


if __name__ == "__main__":
    unittest.main()
