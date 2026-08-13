import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_editor_clear as cec


class TestMatchingProcesses(unittest.TestCase):
    def test_editor_and_cmd_both_match(self):
        names = ["explorer.exe", "UnrealEditor.exe", "UnrealEditor-Cmd.exe"]
        hits = cec.matching_processes(names, "UnrealEditor")
        self.assertEqual(sorted(hits),
                         ["UnrealEditor-Cmd.exe", "UnrealEditor.exe"])

    def test_case_insensitive(self):
        self.assertEqual(
            cec.matching_processes(["unrealeditor.exe"], "UnrealEditor"),
            ["unrealeditor.exe"])

    def test_no_match_is_empty(self):
        self.assertEqual(
            cec.matching_processes(["python.exe", "code.exe"],
                                   "UnrealEditor"), [])

    def test_prefix_not_substring(self):
        # A process merely CONTAINING the name must not fire the guard.
        self.assertEqual(
            cec.matching_processes(["MyUnrealEditorNotes.exe"],
                                   "UnrealEditor"), [])


class TestEnumeratorFailClosed(unittest.TestCase):
    def test_empty_listing_is_instrument_failure(self):
        with patch.object(cec, "list_processes",
                          side_effect=cec.ProcessListError("no names")):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cec.main(["check_editor_clear"])
            self.assertEqual(rc, 1)
            self.assertIn("BLOCKED", buf.getvalue())
            self.assertIn("cannot enumerate", buf.getvalue())

    def test_missing_binary_raises(self):
        with patch.object(cec.subprocess, "run",
                          side_effect=FileNotFoundError("ps")):
            with self.assertRaises(cec.ProcessListError):
                cec.list_processes()

    def test_zero_parsed_names_raises(self):
        class Fake:
            returncode = 0
            stdout = ""

        with patch.object(cec.subprocess, "run", return_value=Fake()):
            with self.assertRaises(cec.ProcessListError):
                cec.list_processes()

    def test_allow_path_when_enumerator_returns_unrelated(self):
        with patch.object(cec, "list_processes",
                          return_value=["bash", "sshd"]):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cec.main(["check_editor_clear"])
            self.assertEqual(rc, 0)
            self.assertIn("clear:", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
