"""Pin the run-completeness instrument.

Every fixture below is the SHAPE of a real thing measured in the 2,283-log
corpus under D:/Kurogane and D:/Unreal on 2026-08-14, not an invented case.
The corpus itself cannot be committed (game logs are vendor content and
never enter git), so the shapes are reproduced here and the counts are cited
in the test names and comments.

Per `prove-an-instrument-can-fail`: a detector is worth nothing until it has
been shown to say something OTHER than its default. These tests therefore
pin both directions -- the fixtures that must fire and the fixtures that
must stay quiet -- because a classifier that returned CRASHED for everything
would pass a one-sided suite and be useless.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import run_verdict as rv


def engine_log(*body: str) -> str:
    """A minimally credible engine log: enough distinct Log categories to
    clear the is_engine_log floor."""
    head = (
        "LogInit: Display: Running engine for game: Kurogane\n"
        "LogWindows: Display: Custom abort handler registered\n"
        "LogRHI: Using Graphics Adapter: NVIDIA GeForce RTX 4090\n"
        "LogD3D12RHI: Chosen D3D12 Adapter\n"
    )
    return head + "".join(b if b.endswith("\n") else b + "\n" for b in body)


CLEAN_TAIL = "LogCore: Engine exit requested (reason: Win RequestExit)\nLog file closed\n"

# 176 of 211 crashed corpus logs end on exactly this normal-looking line.
CRASH_BODY = (
    "LogWindows: Error: === Critical error: ===\n"
    "LogWindows: Error: Fatal error!\n"
    "LogWindows: Error: Unhandled Exception: EXCEPTION_ACCESS_VIOLATION\n"
    "LogCore: Engine exit requested (reason: Win RequestExit; note: exit was already requested)\n"
)


class TestExecutionClassification(unittest.TestCase):
    def test_clean_close_is_complete(self):
        text = engine_log("LogPython: work done", CLEAN_TAIL)
        ex, _ = rv.classify_log(text, size_bytes=len(text))
        self.assertEqual(ex, "COMPLETE")

    def test_crash_wins_even_though_last_line_reads_clean(self):
        """The load-bearing case. 176/211 crashed logs end on
        'LogCore: Engine exit requested', which is also how a healthy run
        ends. A last-line check calls this COMPLETE."""
        text = engine_log("LogPython: starting", CRASH_BODY)
        last = text.strip().rsplit("\n", 1)[-1]
        self.assertIn("Engine exit requested", last)   # the trap is present
        self.assertNotIn("Fatal", last)                # and invisible at the tail
        ex, reasons = rv.classify_log(text, size_bytes=len(text))
        self.assertEqual(ex, "CRASHED")
        self.assertTrue(any("crash marker" in r for r in reasons))

    def test_no_crash_no_close_is_truncated(self):
        """670 of 2,045 corpus engine logs look like this."""
        text = engine_log("LogPython: [MetaHumanGenerator] Session cache cleared")
        ex, _ = rv.classify_log(text, size_bytes=len(text))
        self.assertEqual(ex, "TRUNCATED")

    def test_alive_process_is_running_not_truncated(self):
        text = engine_log("LogPython: compiling shaders")
        ex, _ = rv.classify_log(text, size_bytes=len(text), process_alive=True)
        self.assertEqual(ex, "RUNNING")

    def test_zero_bytes_is_empty(self):
        ex, _ = rv.classify_log("", size_bytes=0)
        self.assertEqual(ex, "EMPTY")

    def test_tiny_non_engine_file_is_empty_not_a_refusal(self):
        """The mangled -abslog shape: editor launches, exits, writes ~48 B.
        193 corpus logs are under 2 KB."""
        ex, reasons = rv.classify_log("startup failed\n", size_bytes=48)
        self.assertEqual(ex, "EMPTY")
        self.assertTrue(any("abslog" in r for r in reasons))

    def test_large_non_engine_file_is_refused_not_guessed(self):
        """238 corpus files are Blender / shasum / port-listener output.
        Applying engine rules to them would invent a verdict."""
        text = "Blender 4.2\n" + ("mesh op\n" * 900) + "Blender quit\n"
        ex, _ = rv.classify_log(text, size_bytes=len(text))
        self.assertEqual(ex, "NOT_AN_ENGINE_LOG")

    def test_one_repeated_category_is_not_an_engine_log(self):
        text = "LogPython: a\n" * 500
        ex, _ = rv.classify_log(text, size_bytes=len(text))
        self.assertEqual(ex, "NOT_AN_ENGINE_LOG")


class TestKillReasonsSurvive(unittest.TestCase):
    def test_stall_kill_is_named(self):
        text = engine_log("LogPython: waiting")
        ex, _ = rv.classify_log(text, size_bytes=len(text), killed="stall")
        self.assertEqual(ex, "KILLED_STALL")

    def test_timeout_kill_is_named(self):
        text = engine_log("LogPython: waiting")
        ex, _ = rv.classify_log(text, size_bytes=len(text), killed="timeout")
        self.assertEqual(ex, "KILLED_TIMEOUT")

    def test_crash_beats_kill_because_it_is_more_specific(self):
        text = engine_log(CRASH_BODY)
        ex, reasons = rv.classify_log(text, size_bytes=len(text), killed="stall")
        self.assertEqual(ex, "CRASHED")
        self.assertTrue(any("also killed" in r for r in reasons))

    def test_kill_after_clean_close_is_still_complete(self):
        text = engine_log("LogPython: done", CLEAN_TAIL)
        ex, _ = rv.classify_log(text, size_bytes=len(text), killed="timeout")
        self.assertEqual(ex, "COMPLETE")


class TestSentinelIsNeverTheVerdict(unittest.TestCase):
    """124 corpus logs carry a =PASS sentinel AND a crash signature; 328
    carry one in a run that never closed cleanly."""

    def _write(self, tmp, text):
        p = Path(tmp) / "run.log"
        p.write_text(text, encoding="utf-8")
        return p

    def test_pass_sentinel_over_a_crash_is_a_contradiction(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            log = self._write(tmp, engine_log(
                "LogPython: KUROGANE_MH_CAPTURE=PASS", CRASH_BODY))
            v = rv.verdict_for(log)
            self.assertEqual(v.execution, "CRASHED")
            self.assertTrue(v.sentinel_claims_pass)
            self.assertTrue(v.contradiction)
            self.assertFalse(v.citable)
            self.assertTrue(any("CONTRADICTION" in r for r in v.reasons))

    def test_pass_sentinel_over_a_truncation_is_a_contradiction(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            log = self._write(tmp, engine_log("LogPython: KUROGANE_CURSEIMP=PASS"))
            v = rv.verdict_for(log)
            self.assertEqual(v.execution, "TRUNCATED")
            self.assertTrue(v.contradiction)

    def test_no_contradiction_when_the_engine_agrees(self):
        """The quiet direction. Without this, a classifier that always
        reported a contradiction would pass the suite."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            log = self._write(tmp, engine_log(
                "LogPython: KUROGANE_MH_CAPTURE=PASS", CLEAN_TAIL))
            v = rv.verdict_for(log)
            self.assertEqual(v.execution, "COMPLETE")
            self.assertTrue(v.sentinel_claims_pass)
            self.assertFalse(v.contradiction)


class TestOutputVerdictIsIndependent(unittest.TestCase):
    def _clean_log(self, tmp):
        p = Path(tmp) / "run.log"
        p.write_text(engine_log("LogPython: done", CLEAN_TAIL), encoding="utf-8")
        return p

    def test_no_artifact_declared_is_undeclared_and_not_citable(self):
        """Exit 0 with no artifact is not a pass -- it is a run that gates on
        nothing."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            v = rv.verdict_for(self._clean_log(tmp), [], exit_code=0)
            self.assertEqual(v.execution, "COMPLETE")
            self.assertEqual(v.output, "UNDECLARED")
            self.assertFalse(v.citable)

    def test_missing_artifact_with_perfect_execution(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            v = rv.verdict_for(self._clean_log(tmp),
                               [Path(tmp) / "never_written.json"], exit_code=0)
            self.assertEqual(v.execution, "COMPLETE")
            self.assertEqual(v.output, "MISSING")
            self.assertFalse(v.citable)

    def test_zero_byte_artifact_counts_as_missing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "report.json"
            art.write_bytes(b"")
            v = rv.verdict_for(self._clean_log(tmp), [art])
            self.assertEqual(v.output, "MISSING")

    def test_both_green_is_the_only_citable_state(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "report.json"
            art.write_text('{"ok": true}', encoding="utf-8")
            v = rv.verdict_for(self._clean_log(tmp), [art], exit_code=0)
            self.assertEqual((v.execution, v.output), ("COMPLETE", "PRESENT"))
            self.assertTrue(v.citable)

    def test_artifact_that_self_reports_failure_is_not_citable(self):
        """The regression that created this state. The first real supervised
        run scored EXECUTION=COMPLETE / OUTPUT=PRESENT / CITABLE=yes over a
        report whose own first field was "status": "FAIL"."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "report.json"
            art.write_text(json.dumps({
                "status": "FAIL",
                "error": "AttributeError: type object 'SystemLibrary' has no "
                         "attribute 'get_project_name'"}), encoding="utf-8")
            v = rv.verdict_for(self._clean_log(tmp), [art], exit_code=0)
            self.assertEqual(v.execution, "COMPLETE")
            self.assertEqual(v.output, "PRESENT_BUT_FAILING")
            self.assertFalse(v.citable)

    def test_truthy_error_alone_fails_the_artifact(self):
        """Each failure signal needs its OWN fixture. A report with both
        status=FAIL and a populated error is caught by the status check
        first, so it cannot prove the error check does anything -- a
        mutation run found that exact hole here on 2026-08-14."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "report.json"
            art.write_text(json.dumps({
                "status": "PASS",
                "error": "GroomBinding target mesh mismatch"}), encoding="utf-8")
            v = rv.verdict_for(self._clean_log(tmp), [art])
            self.assertEqual(v.output, "PRESENT_BUT_FAILING")
            self.assertFalse(v.citable)

    def test_inconclusive_is_also_not_a_result(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "report.json"
            art.write_text('{"status": "INCONCLUSIVE"}', encoding="utf-8")
            v = rv.verdict_for(self._clean_log(tmp), [art])
            self.assertEqual(v.output, "PRESENT_BUT_FAILING")

    def test_non_empty_errors_list_fails_the_artifact(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "report.json"
            art.write_text('{"status": "PASS", "errors": ["groom missing"]}',
                           encoding="utf-8")
            v = rv.verdict_for(self._clean_log(tmp), [art])
            self.assertEqual(v.output, "PRESENT_BUT_FAILING")

    def test_healthy_report_shapes_are_not_flagged(self):
        """The quiet direction, and the one that decides whether this gate
        survives contact: `"error": null` and `"errors": []` are how a
        healthy report says nothing went wrong. Flagging those would make
        every good run fail and the gate would be switched off."""
        import tempfile
        for payload in ('{"status": "PASS", "error": null, "errors": []}',
                        '{"status": "ok"}',
                        '{"frames": 16}',
                        '[1, 2, 3]'):
            with tempfile.TemporaryDirectory() as tmp:
                art = Path(tmp) / "report.json"
                art.write_text(payload, encoding="utf-8")
                v = rv.verdict_for(self._clean_log(tmp), [art])
                self.assertEqual(v.output, "PRESENT", f"flagged: {payload}")
                self.assertTrue(v.citable, f"not citable: {payload}")

    def test_unparseable_json_artifact_is_flagged(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "report.json"
            art.write_text("{truncated mid-wri", encoding="utf-8")
            v = rv.verdict_for(self._clean_log(tmp), [art])
            self.assertEqual(v.output, "PRESENT_BUT_FAILING")

    def test_non_json_artifacts_are_only_checked_for_existence(self):
        """A .png cannot self-report, and pretending to inspect it would be
        a fake gate."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "plate.png"
            art.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
            v = rv.verdict_for(self._clean_log(tmp), [art])
            self.assertEqual(v.output, "PRESENT")

    def test_artifact_present_does_not_rescue_a_crash(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "run.log"
            log.write_text(engine_log(CRASH_BODY), encoding="utf-8")
            art = Path(tmp) / "report.json"
            art.write_text("{}", encoding="utf-8")
            v = rv.verdict_for(log, [art])
            self.assertEqual((v.execution, v.output), ("CRASHED", "PRESENT"))
            self.assertFalse(v.citable)


class TestRhiIsAssertedPositively(unittest.TestCase):
    """Verbatim from a real 5.8.1 run log on this machine."""

    RHI_LINES = (
        "LogRHI: Using Default RHI: D3D12\n"
        "LogRHI: Using Highest Feature Level of D3D12: SM6\n"
        "LogRHI: RHI D3D12 with Feature Level SM6 is supported and will be used.\n"
    )

    def _log(self, tmp, body):
        p = Path(tmp) / "run.log"
        p.write_text(engine_log(body, CLEAN_TAIL), encoding="utf-8")
        return p

    def test_extracts_the_rhi_the_engine_chose(self):
        self.assertEqual(rv.extract_rhi(self.RHI_LINES), "D3D12")

    def test_absent_rhi_line_is_none_not_a_guess(self):
        self.assertIsNone(rv.extract_rhi("LogInit: nothing about rhi here\n"))

    def test_expected_rhi_present_is_confirmed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "r.json"
            art.write_text("{}", encoding="utf-8")
            v = rv.verdict_for(self._log(tmp, self.RHI_LINES), [art],
                               expect_rhi="D3D12")
            self.assertTrue(v.environment_ok)
            self.assertTrue(v.citable)
            self.assertEqual(v.evidence["rhi"], "D3D12")

    def test_silent_log_is_not_a_pass_for_an_expected_rhi(self):
        """Asserting only that 'NullRHI' is ABSENT passes on a truncated log
        too. The assertion has to be positive."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "r.json"
            art.write_text("{}", encoding="utf-8")
            v = rv.verdict_for(self._log(tmp, "LogPython: no rhi line"), [art],
                               expect_rhi="D3D12")
            self.assertFalse(v.environment_ok)
            self.assertFalse(v.citable)
            self.assertTrue(any("never says which RHI" in r for r in v.reasons))

    def test_wrong_rhi_is_caught(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "r.json"
            art.write_text("{}", encoding="utf-8")
            v = rv.verdict_for(
                self._log(tmp, "LogRHI: Using Default RHI: Vulkan"), [art],
                expect_rhi="D3D12")
            self.assertFalse(v.environment_ok)
            self.assertTrue(any("RHI mismatch" in r for r in v.reasons))

    def test_no_expectation_means_no_environment_failure(self):
        """The quiet direction: runs that do not render must not be failed
        for having no RHI."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "r.json"
            art.write_text("{}", encoding="utf-8")
            v = rv.verdict_for(self._log(tmp, "LogPython: pure data write"),
                               [art])
            self.assertTrue(v.environment_ok)
            self.assertTrue(v.citable)


class TestExitCodeIsRecordedNotTrusted(unittest.TestCase):
    def test_exit_zero_does_not_make_a_truncated_run_complete(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "run.log"
            log.write_text(engine_log("LogPython: partial"), encoding="utf-8")
            v = rv.verdict_for(log, exit_code=0)
            self.assertEqual(v.execution, "TRUNCATED")

    def test_large_negative_exit_code_is_explained_as_a_crash(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "run.log"
            log.write_text(engine_log("LogPython: x", CLEAN_TAIL), encoding="utf-8")
            v = rv.verdict_for(log, exit_code=-1073741819)
            self.assertTrue(any("access violation" in r for r in v.reasons))

    def test_missing_log_is_no_log_not_empty(self):
        v = rv.verdict_for(Path("Z:/does/not/exist.log"))
        self.assertEqual(v.execution, "NO_LOG")


class TestDecodingIsNeverAVerdict(unittest.TestCase):
    def test_cp949_bytes_in_a_utf8_log_do_not_crash_the_reader(self):
        """The corpus contains Korean Windows error text mid-log:
        'LogWindows: Windows GetLastError: <cp949 bytes>'."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "run.log"
            log.write_bytes(
                engine_log("LogWindows: Windows GetLastError: ").encode("utf-8")
                + b"\xc0\xdb\xbe\xf7\xc0\xcc\n"
                + CLEAN_TAIL.encode("utf-8"))
            v = rv.verdict_for(log)
            self.assertEqual(v.execution, "COMPLETE")


if __name__ == "__main__":
    unittest.main()


class TestIdenticalArtifactsAreNotResults(unittest.TestCase):
    """The sweep that did not sweep. A 7-variant tone sweep wrote seven
    BYTE-IDENTICAL files on 2026-08-14 and scored PRESENT + CITABLE, because
    existence, non-emptiness and a PASS report were all true of every one."""

    def _clean_log(self, tmp):
        p = Path(tmp) / "run.log"
        p.write_text(engine_log("LogPython: done", CLEAN_TAIL), encoding="utf-8")
        return p

    def test_byte_identical_artifacts_are_flagged(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            arts = []
            for i in range(4):
                a = Path(tmp) / f"v{i}.png"
                a.write_bytes(b"\x89PNG\r\n\x1a\n" + b"same" * 40)
                arts.append(a)
            v = rv.verdict_for(self._clean_log(tmp), arts)
            self.assertEqual(v.output, "PRESENT_BUT_IDENTICAL")
            self.assertFalse(v.citable)
            self.assertTrue(any("varied nothing" in r for r in v.reasons))

    def test_distinct_artifacts_pass(self):
        """The quiet direction: a real sweep must not be failed."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            arts = []
            for i in range(4):
                a = Path(tmp) / f"v{i}.png"
                a.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([i]) * 40)
                arts.append(a)
            v = rv.verdict_for(self._clean_log(tmp), arts)
            self.assertEqual(v.output, "PRESENT")
            self.assertTrue(v.citable)

    def test_a_single_artifact_is_never_a_duplicate(self):
        """One file cannot be identical to anything. Firing here would break
        every ordinary single-report run."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "only.json"
            a.write_text('{"status":"PASS"}', encoding="utf-8")
            v = rv.verdict_for(self._clean_log(tmp), [a])
            self.assertEqual(v.output, "PRESENT")

    def test_partial_duplication_is_still_flagged(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            a1 = Path(tmp) / "a.png"; a1.write_bytes(b"AAAA" * 20)
            a2 = Path(tmp) / "b.png"; a2.write_bytes(b"AAAA" * 20)
            a3 = Path(tmp) / "c.png"; a3.write_bytes(b"BBBB" * 20)
            v = rv.verdict_for(self._clean_log(tmp), [a1, a2, a3])
            self.assertEqual(v.output, "PRESENT_BUT_IDENTICAL")
