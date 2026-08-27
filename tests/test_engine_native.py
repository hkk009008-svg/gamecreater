"""Pin the bounded native Unreal Automation and Data Validation surfaces."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import engine_run as er
from game_config import GameConfig


def fake_project(root: Path) -> tuple[Path, Path]:
    engine = root / "UE_5.8"
    binary = engine / "Engine" / "Binaries" / "Win64"
    binary.mkdir(parents=True)
    (binary / "UnrealEditor-Cmd.exe").write_bytes(b"MZ")
    uproject = root / "Kurogane.uproject"
    uproject.write_text("{}", encoding="utf-8")
    return engine, uproject


def automation_report(**overrides) -> dict:
    report = {
        "succeeded": 1,
        "succeededWithWarnings": 0,
        "failed": 0,
        "notRun": 0,
        "inProcess": 0,
        "tests": [{"fullTestPath": "Project.Native.Pass"}],
    }
    report.update(overrides)
    return report


def write_report(root: Path, report: object) -> Path:
    path = root / "index.json"
    # Epic's UE 5.8 report writer emits this lower-camel shape with a BOM.
    path.write_text(json.dumps(report), encoding="utf-8-sig")
    return path


def validation_log(
        *, requested: int, associated: int, outcomes: list[str],
        checked: int, passed: int, failed: int, skipped: int,
        unable: int, include_summary: bool = True,
        commandlet_result: int = 0,
        assets: list[str] | None = None) -> str:
    lines = [
        "LogContentValidation: Starting to validate "
        f"{requested} assets ({associated} associated objects such as actors)"
    ]
    if assets is None:
        assets = [f"/Game/Test.Asset{index}"
                  for index in range(len(outcomes))]
    if len(assets) != len(outcomes):
        raise ValueError("assets and outcomes must have the same length")
    for asset, outcome in zip(assets, outcomes):
        lines.append(f"AssetCheck: {asset} Validating asset")
        lines.append(f"AssetCheck: {asset} {outcome}")
    if include_summary:
        lines.append(
            "LogAssetCheck: Files Checked: "
            f"{checked}, Passed: {passed}, Failed: {failed}, "
            f"Skipped: {skipped}, Unable to validate: {unable}"
        )
    lines.append(
        "LogCore: Engine exit requested (reason: Commandlet "
        "DataValidationCommandlet_0 finished execution "
        f"(result {commandlet_result}))"
    )
    return "\n".join(lines) + "\n"


class TestNativeCommandBuilder(unittest.TestCase):
    def test_automation_argv_is_exact(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            engine, uproject = fake_project(root)
            log = root / "run" / "engine.log"
            report_dir = root / "run" / "report"
            selector = "^Project.Native.Pass$"
            command = er.build_native_command(
                engine, uproject, log,
                operation="automation",
                selector=selector,
                report_dir=report_dir,
            )
            self.assertEqual(command, [
                str(engine / "Engine" / "Binaries" / "Win64" /
                    "UnrealEditor-Cmd.exe"),
                str(uproject),
                *er.BASE_FLAGS,
                "-nullrhi",
                f"-ReportExportPath={report_dir}",
                f"-ExecCmds=Automation RunTests {selector};Quit",
                f"-abslog={log}",
            ])

    def test_data_validation_argv_is_exact(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            engine, uproject = fake_project(root)
            log = root / "run" / "engine.log"
            command = er.build_native_command(
                engine, uproject, log, operation="data-validation")
            self.assertEqual(command, [
                str(engine / "Engine" / "Binaries" / "Win64" /
                    "UnrealEditor-Cmd.exe"),
                str(uproject),
                *er.BASE_FLAGS,
                "-nullrhi",
                "-run=DataValidation",
                "-IncludeOnlyOnDiskAssets",
                "-culture=en",
                f"-abslog={log}",
            ])

    def test_empty_automation_selector_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            engine, uproject = fake_project(root)
            for selector in (None, "", "   "):
                with self.subTest(selector=selector), self.assertRaises(
                        er.IntentError) as cm:
                    er.build_native_command(
                        engine, uproject, root / "engine.log",
                        operation="automation", selector=selector,
                        report_dir=root / "report")
                self.assertIn("must not be empty", str(cm.exception))

    def test_semicolon_in_automation_selector_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            engine, uproject = fake_project(root)
            with self.assertRaises(er.IntentError) as cm:
                er.build_native_command(
                    engine, uproject, root / "engine.log",
                    operation="automation", selector="Pass;Quit",
                    report_dir=root / "report")
            self.assertIn("must not contain", str(cm.exception))

    def test_newline_in_automation_selector_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            engine, uproject = fake_project(root)
            for selector in ("Pass\nQuit", "Pass\rQuit"):
                with self.subTest(selector=repr(selector)), self.assertRaises(
                        er.IntentError) as cm:
                    er.build_native_command(
                        engine, uproject, root / "engine.log",
                        operation="automation", selector=selector,
                        report_dir=root / "report")
                self.assertIn("newline", str(cm.exception))

    def test_exec_command_delimiters_and_quotes_are_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            engine, uproject = fake_project(root)
            for selector in ("Pass,Quit", "Pass'Quoted", 'Pass"Quoted'):
                with self.subTest(selector=selector), self.assertRaises(
                        er.IntentError) as cm:
                    er.build_native_command(
                        engine, uproject, root / "engine.log",
                        operation="automation", selector=selector,
                        report_dir=root / "report")
                self.assertIn("command separators", str(cm.exception))

    def test_automation_switches_from_nullrhi_to_renderoffscreen(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            engine, uproject = fake_project(root)
            cpu = er.build_native_command(
                engine, uproject, root / "cpu.log",
                operation="automation", selector="Pass",
                report_dir=root / "cpu-report")
            rendered = er.build_native_command(
                engine, uproject, root / "rendered.log",
                operation="automation", selector="Pass",
                report_dir=root / "rendered-report", needs_rhi=True)
            self.assertIn("-nullrhi", cpu)
            self.assertNotIn("-RenderOffscreen", cpu)
            self.assertIn("-RenderOffscreen", rendered)
            self.assertNotIn("-nullrhi", rendered)

    def test_data_validation_refuses_rendering(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            engine, uproject = fake_project(root)
            with self.assertRaises(er.IntentError) as cm:
                er.build_native_command(
                    engine, uproject, root / "engine.log",
                    operation="data-validation", needs_rhi=True)
            self.assertIn("CPU commandlet", str(cm.exception))


class TestAutomationReport(unittest.TestCase):
    def test_pass(self):
        with tempfile.TemporaryDirectory() as t:
            result = er.parse_automation_report(
                write_report(Path(t), automation_report()))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["matched"], 1)
            self.assertEqual(result["succeeded"], 1)

    def test_pass_with_warnings(self):
        with tempfile.TemporaryDirectory() as t:
            report = automation_report(
                succeeded=1,
                succeededWithWarnings=1,
                tests=[{}, {}],
            )
            result = er.parse_automation_report(write_report(Path(t), report))
            self.assertEqual(result["status"], "PASS_WITH_WARNINGS")
            self.assertEqual(result["succeeded_with_warnings"], 1)

    def test_failed_test_is_a_domain_failure(self):
        with tempfile.TemporaryDirectory() as t:
            report = automation_report(succeeded=0, failed=1)
            result = er.parse_automation_report(write_report(Path(t), report))
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["failed"], 1)

    def test_zero_tests_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            report = automation_report(
                succeeded=0,
                succeededWithWarnings=0,
                failed=0,
                notRun=0,
                inProcess=0,
                tests=[],
            )
            with self.assertRaises(er.NativeResultError) as cm:
                er.parse_automation_report(write_report(Path(t), report))
            self.assertIn("zero tests", str(cm.exception))

    def test_malformed_json_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "index.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(er.NativeResultError) as cm:
                er.parse_automation_report(path)
            self.assertIn("cannot read", str(cm.exception))

    def test_missing_fields_are_refused(self):
        with tempfile.TemporaryDirectory() as t:
            report = automation_report()
            del report["inProcess"]
            with self.assertRaises(er.NativeResultError) as cm:
                er.parse_automation_report(write_report(Path(t), report))
            self.assertIn("InProcess", str(cm.exception))

    def test_counter_and_test_array_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            report = automation_report(succeeded=2, tests=[{}])
            with self.assertRaises(er.NativeResultError) as cm:
                er.parse_automation_report(write_report(Path(t), report))
            self.assertIn("count mismatch", str(cm.exception))

    def test_completion_marker_is_required_and_exact(self):
        line = ("LogAutomationCommandLine: Display: "
                "**** TEST COMPLETE. EXIT CODE: 0 ****\n")
        self.assertEqual(er.automation_completion_code(line), 0)
        for text in ("", line + line, line.replace("0", "not-a-number")):
            with self.subTest(text=text), self.assertRaises(er.NativeResultError):
                er.automation_completion_code(text)

    def test_windows_negative_exit_mapping_is_recognized(self):
        self.assertTrue(er.process_exit_agrees(255, -1))
        self.assertTrue(er.process_exit_agrees(0, 0))
        self.assertFalse(er.process_exit_agrees(1, 0))

    def test_absent_report_with_exact_no_match_is_a_zero_test_failure(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            log = root / "engine.log"
            log.write_text(
                "LogAutomationCommandLine: Error: No automation tests matched "
                "'^Missing$'\n"
                "LogAutomationCommandLine: Display: "
                "**** TEST COMPLETE. EXIT CODE: -1 ****\n",
                encoding="utf-8",
            )
            result = er._native_result(
                "automation", log, root / "report" / "index.json", 255)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["matched"], 0)
            self.assertEqual(result["automation_exit_code"], -1)

    def test_terminal_reclassification_clears_stale_contradiction(self):
        verdict = er.run_verdict.Verdict(
            execution="TRUNCATED",
            output="PRESENT",
            sentinel_claims_pass=True,
            contradiction=True,
            reasons=[
                "engine log with no crash marker and no clean close",
                "CONTRADICTION: sentinel says pass over truncation",
                "artifact landed",
            ],
        )
        er.reconcile_automation_execution(
            verdict, {"automation_exit_code": 0}, 0, None)
        self.assertEqual(verdict.execution, "COMPLETE")
        self.assertFalse(verdict.contradiction)
        self.assertFalse(any(
            reason.startswith("CONTRADICTION:") for reason in verdict.reasons))
        self.assertIn("artifact landed", verdict.reasons)
        self.assertTrue(verdict.citable)

    def test_terminal_reclassification_requires_exit_agreement(self):
        verdict = er.run_verdict.Verdict(
            execution="TRUNCATED",
            output="PRESENT",
            sentinel_claims_pass=True,
            contradiction=True,
        )
        er.reconcile_automation_execution(
            verdict, {"automation_exit_code": 0}, 1, None)
        self.assertEqual(verdict.execution, "TRUNCATED")
        self.assertTrue(verdict.contradiction)


class TestDataValidationReport(unittest.TestCase):
    def test_pass(self):
        text = validation_log(
            requested=1,
            associated=2,
            outcomes=["contains valid data."],
            checked=1,
            passed=1,
            failed=0,
            skipped=0,
            unable=0,
        )
        result = er.parse_data_validation_log(text)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["requested"], 1)
        self.assertEqual(result["associated_objects"], 2)

    def test_skipped_or_unable_is_pass_with_warnings(self):
        text = validation_log(
            requested=3,
            associated=0,
            outcomes=["contains valid data.", "has no data validation."],
            checked=2,
            passed=1,
            failed=0,
            skipped=1,
            unable=1,
        )
        result = er.parse_data_validation_log(text)
        self.assertEqual(result["status"], "PASS_WITH_WARNINGS")
        self.assertEqual(result["unable_to_validate"], 1)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["unable_to_validate"], 1)

    def test_pass_with_warnings(self):
        text = validation_log(
            requested=1,
            associated=0,
            outcomes=["contains valid data, but has warnings."],
            checked=1,
            passed=1,
            failed=0,
            skipped=0,
            unable=0,
        )
        result = er.parse_data_validation_log(text)
        self.assertEqual(result["status"], "PASS_WITH_WARNINGS")
        self.assertEqual(result["valid_with_warnings"], 1)

    def test_invalid_asset_is_a_domain_failure(self):
        text = validation_log(
            requested=1,
            associated=0,
            outcomes=["contains invalid data."],
            checked=1,
            passed=0,
            failed=1,
            skipped=0,
            unable=0,
        )
        result = er.parse_data_validation_log(text)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["invalid"], 1)

    def test_actionable_asset_identities_are_sorted_by_outcome(self):
        text = validation_log(
            requested=4,
            associated=0,
            outcomes=[
                "contains invalid data.",
                "contains valid data, but has warnings.",
                "has no data validation.",
                "contains invalid data.",
            ],
            assets=[
                "/Script/Engine.Blueprint'/Game/Zeta.AssetZ'",
                "/Script/Engine.World'/Game/Warn.AssetW'",
                "/Script/Engine.DataAsset'/Game/Unable.AssetU'",
                "/Script/Engine.Blueprint'/Game/Alpha.AssetA'",
            ],
            checked=4,
            passed=1,
            failed=2,
            skipped=0,
            unable=1,
        )
        result = er.parse_data_validation_log(text)
        self.assertEqual(result["invalid_assets"], [
            "/Script/Engine.Blueprint'/Game/Alpha.AssetA'",
            "/Script/Engine.Blueprint'/Game/Zeta.AssetZ'",
        ])
        self.assertEqual(result["warning_assets"], [
            "/Script/Engine.World'/Game/Warn.AssetW'",
        ])
        self.assertEqual(
            result["unable_to_validate_assets"], [
                "/Script/Engine.DataAsset'/Game/Unable.AssetU'",
            ])

    def test_real_commandlet_shape_derives_missing_footer(self):
        text = validation_log(
            requested=4,
            associated=1,
            outcomes=[
                "contains valid data.",
                "contains valid data.",
                "contains valid data, but has warnings.",
                "contains invalid data.",
            ],
            checked=4,
            passed=3,
            failed=1,
            skipped=0,
            unable=0,
            include_summary=False,
        )
        result = er.parse_data_validation_log(text)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["summary_source"], "commandlet_outcomes")
        self.assertEqual(result["checked"], 4)
        self.assertEqual(result["passed"], 3)
        self.assertEqual(result["failed"], 1)

    def test_missing_footer_with_incomplete_outcomes_is_refused(self):
        text = validation_log(
            requested=2,
            associated=0,
            outcomes=["contains valid data."],
            checked=1,
            passed=1,
            failed=0,
            skipped=1,
            unable=0,
            include_summary=False,
        )
        text = text.replace(
            "LogCore: Engine exit requested",
            "AssetCheck: /Game/Test.Asset1 Validating asset\n"
            "LogCore: Engine exit requested",
        )
        with self.assertRaises(er.NativeResultError) as cm:
            er.parse_data_validation_log(text)
        self.assertIn("attempt lines 2 != outcome lines 1", str(cm.exception))

    def test_zero_asset_scan_is_refused(self):
        text = validation_log(
            requested=0,
            associated=0,
            outcomes=[],
            checked=0,
            passed=0,
            failed=0,
            skipped=0,
            unable=0,
        )
        with self.assertRaises(er.NativeResultError) as cm:
            er.parse_data_validation_log(text)
        self.assertIn("zero assets", str(cm.exception))

    def test_missing_start_or_completion_is_refused(self):
        complete = validation_log(
            requested=1,
            associated=0,
            outcomes=["contains valid data."],
            checked=1,
            passed=1,
            failed=0,
            skipped=0,
            unable=0,
        )
        lines = complete.splitlines()
        cases = {
            "start": "\n".join(lines[1:]) + "\n",
            "completion": "\n".join(lines[:-1]) + "\n",
        }
        for missing, text in cases.items():
            with self.subTest(missing=missing), self.assertRaises(
                    er.NativeResultError) as cm:
                er.parse_data_validation_log(text)
            self.assertIn("found 0", str(cm.exception))

    def test_duplicate_start_summary_or_completion_is_refused(self):
        complete = validation_log(
            requested=1,
            associated=0,
            outcomes=["contains valid data."],
            checked=1,
            passed=1,
            failed=0,
            skipped=0,
            unable=0,
        )
        lines = complete.splitlines()
        cases = {
            "start": complete + lines[0] + "\n",
            "summary": complete + lines[-2] + "\n",
            "completion": complete + lines[-1] + "\n",
        }
        for duplicate, text in cases.items():
            with self.subTest(duplicate=duplicate), self.assertRaises(
                    er.NativeResultError) as cm:
                er.parse_data_validation_log(text)
            self.assertIn("found 2", str(cm.exception))

    def test_nonzero_commandlet_result_is_refused(self):
        text = validation_log(
            requested=1,
            associated=0,
            outcomes=["contains valid data."],
            checked=1,
            passed=1,
            failed=0,
            skipped=0,
            unable=0,
            commandlet_result=1,
        )
        with self.assertRaises(er.NativeResultError) as cm:
            er.parse_data_validation_log(text)
        self.assertIn("reports result 1", str(cm.exception))

    def test_impossible_requested_checked_relationship_is_refused(self):
        text = validation_log(
            requested=1,
            associated=0,
            outcomes=["contains valid data.", "contains valid data."],
            checked=2,
            passed=2,
            failed=0,
            skipped=0,
            unable=0,
        )
        with self.assertRaises(er.NativeResultError) as cm:
            er.parse_data_validation_log(text)
        self.assertIn("requested 1 != checked 2 + skipped 0", str(cm.exception))

    def test_summary_and_outcome_count_mismatch_is_refused(self):
        text = validation_log(
            requested=2,
            associated=0,
            outcomes=["contains valid data."],
            checked=2,
            passed=2,
            failed=0,
            skipped=0,
            unable=0,
        )
        with self.assertRaises(er.NativeResultError) as cm:
            er.parse_data_validation_log(text)
        self.assertIn("checked 2 != outcome lines 1", str(cm.exception))

    def test_localized_outcome_cannot_false_pass_the_english_parser(self):
        text = validation_log(
            requested=1,
            associated=0,
            outcomes=["유효한 데이터가 포함되어 있습니다."],
            checked=1,
            passed=1,
            failed=0,
            skipped=0,
            unable=0,
        )
        with self.assertRaises(er.NativeResultError) as cm:
            er.parse_data_validation_log(text)
        self.assertIn("outcome lines 0", str(cm.exception))


class TestNativeCli(unittest.TestCase):
    def test_native_subcommands_are_exposed_and_dispatched(self):
        parser = er.build_parser()
        automation = parser.parse_args(["automation", "Project.Native"])
        validation = parser.parse_args(["data-validation"])
        self.assertEqual(automation.cmd, "automation")
        self.assertEqual(automation.selector, "Project.Native")
        self.assertFalse(automation.needs_rhi)
        self.assertEqual(validation.cmd, "data-validation")

        with patch.object(er, "cmd_native", return_value=9) as command:
            self.assertEqual(er.main([
                "engine_run", "automation", "Project.Native"]), 9)
        command.assert_called_once()
        self.assertEqual(command.call_args.args[1], "automation")

        with patch.object(er, "cmd_native", return_value=8) as command:
            self.assertEqual(er.main(["engine_run", "data-validation"]), 8)
        command.assert_called_once()
        self.assertEqual(command.call_args.args[1], "data-validation")

    def test_native_dry_run_creates_no_output_directory(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            engine, uproject = fake_project(root)
            empty = GameConfig(source=root / "missing-GAME.local.md")
            commands = [
                ["automation", "Project.Native"],
                ["data-validation"],
            ]
            for index, command in enumerate(commands):
                out_dir = root / f"out-{index}"
                argv = [
                    *command,
                    "--engine", str(engine),
                    "--uproject", str(uproject),
                    "--out-dir", str(out_dir),
                    "--dry-run",
                ]
                args = er.build_parser().parse_args(argv)
                stdout, stderr = io.StringIO(), io.StringIO()
                with self.subTest(command=command[0]), \
                     patch.object(er, "load_game_config", return_value=empty), \
                     patch.object(
                         er, "require_headless_available",
                         side_effect=AssertionError("must not be called")), \
                     redirect_stdout(stdout), redirect_stderr(stderr):
                    rc = er.cmd_native(args, args.cmd)
                self.assertEqual(rc, 0, stderr.getvalue())
                self.assertIn("no directory created", stdout.getvalue())
                self.assertFalse(out_dir.exists())

    def test_native_expect_rhi_requires_needs_rhi(self):
        args = er.build_parser().parse_args([
            "automation", "Project.Native", "--expect-rhi", "D3D11",
            "--dry-run",
        ])
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(
                er, "require_headless_available",
                side_effect=AssertionError("must not be called")), \
             redirect_stdout(stdout), redirect_stderr(stderr):
            rc = er.cmd_native(args, args.cmd)
        self.assertEqual(rc, 3)
        self.assertIn(
            "--expect-rhi requires --needs-rhi",
            stdout.getvalue() + stderr.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
