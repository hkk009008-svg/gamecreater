import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
