"""One supervised entry point for headless Unreal work.

    python scripts/engine_run.py mode                       # where am I?
    python scripts/engine_run.py epic-mcp-check             # optional Epic MCP
    python scripts/engine_run.py headless SCRIPT.py [opts]  # supervised run

An open editor is observable state, so there is no mode marker to maintain:
no editor means headless work is available; an editor means headless work is
blocked. Codex's live-editor bridge is OpenClaw. ``epic-mcp-check`` probes a
separate, optional Epic ModelContextProtocol HTTP server and never claims to
represent OpenClaw readiness.

It is also the watchdog. Measured over the 2,283 `.log` files under
D:/Kurogane and D:/Unreal on 2026-08-14:

    2,045 engine logs        670 never wrote "Log file closed" (33%)
      211 carry a crash signature -- and 176 of those END ON A NORMAL LINE
      328 print a =PASS sentinel in a run that never closed cleanly
      124 print a =PASS sentinel in a run that CRASHED

Nothing in the old launch path could tell those apart from a good run. Every
supervised run now ends in a `run_verdict` classification and a sidecar, so
a truncated run is a stated fact rather than a result someone quotes.

AUTHORITY. This grants none. Headless launches are already granted in
GAME.local.md; this launcher never starts an interactive editor and only
reports whether one is already open. Nothing is deleted or overwritten:
sidecars and logs go to fresh timestamped paths, and a collision is an error,
not a clobber.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import check_editor_clear as cec          # noqa: E402
from game_config import load_game_config  # noqa: E402
import run_verdict                        # noqa: E402

MCP_CONFIG = ROOT / ".mcp.json"

# Defaults chosen from the corpus, not from taste. Median engine process
# lifetime on this machine is 84 s; the longest legitimate capture runs
# measured here are a few minutes of shader/groom warmup during which the
# log genuinely goes quiet. STALL is therefore generous and WALL is the
# backstop, and the verdict says which one fired.
DEFAULT_STALL_S = 300
DEFAULT_WALL_S = 1800
POLL_S = 2.0


# --- mode ---------------------------------------------------------------

@dataclass
class Mode:
    editor_running: bool | None          # None = could not enumerate

    @property
    def name(self) -> str:
        return {True: "EDITOR", False: "HEADLESS", None: "UNKNOWN"}[
            self.editor_running]


def read_mode() -> Mode:
    try:
        running = bool(cec.matching_processes(cec.list_processes(), "UnrealEditor"))
    except Exception:
        running = None                    # never report this as "no editor"
    return Mode(editor_running=running)


def mcp_endpoint() -> tuple[str, int, str]:
    """Read host/port/path from .mcp.json so the checker cannot drift from
    the client config. Falls back to the plugin defaults."""
    host, port, path = "127.0.0.1", 8000, "/mcp"
    try:
        cfg = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
        url = cfg["mcpServers"]["unreal-mcp"]["url"]
        m = re.match(r"https?://([^:/]+):(\d+)(/.*)?$", url)
        if m:
            host, port, path = m.group(1), int(m.group(2)), m.group(3) or "/"
    except Exception:
        pass
    return host, port, path


def port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def cmd_epic_mcp_check() -> int:
    """Report each precondition separately -- 'Epic MCP is broken' is not a
    diagnosis, and these failures have different fixes.

    Reachability is measured with a protocol handshake, not inferred from an
    open port or an editor process."""
    m = read_mode()
    config = load_game_config()
    project = config.uproject or config.project_root or "the configured project"
    settings = ((config.project_dir / "Saved" / "Config" / "WindowsEditor" /
                 "EditorPerProjectUserSettings.ini")
                if config.project_dir else "EditorPerProjectUserSettings.ini")
    host, port, path = mcp_endpoint()
    listening = port_open(host, port)

    # An open port proves a listener, not a protocol. Only the handshake
    # proves the thing on this port is an MCP server.
    hs = {"speaks_mcp": False, "error": "not attempted (port closed)"}
    if listening:
        try:
            sys.path.insert(0, str(SCRIPTS))
            import mcp_client                                    # noqa: PLC0415
            hs = mcp_client.probe(f"http://{host}:{port}{path}")
        except Exception as e:                                   # noqa: BLE001
            hs = {"speaks_mcp": False, "error": f"{type(e).__name__}: {e}"}

    reach = [
        ("editor running", m.editor_running is True,
         f"open {project} -- an INTERACTIVE editor launch "
         "is not covered by the headless grant, so you must do this"),
        (f"listener on {host}:{port}", listening,
         "the editor is up but the plugin is not serving: check "
         "ModelContextProtocol is enabled and bAutoStartServer=True in "
         f"{settings}"),
        ("endpoint speaks MCP", bool(hs.get("speaks_mcp")),
         f"something is listening but did not complete an MCP handshake: "
         f"{hs.get('error')}"),
    ]
    print(f"Epic MCP readiness  (endpoint http://{host}:{port}{path})")
    for label, ok, fix in reach:
        print(f"  [{'OK ' if ok else 'NO '}] {label}")
        if not ok:
            print(f"         -> {fix}")
    if m.editor_running is None:
        print("  [ ? ] could not enumerate processes -- treating as UNKNOWN, "
              "not as 'no editor'")

    reachable = all(ok for _, ok, _ in reach)
    print()
    if reachable:
        print(f"EPIC MCP IS REACHABLE -- protocol {hs.get('protocol')}, "
              f"{len(hs.get('tools') or [])} tool(s) advertised: "
              f"{', '.join(hs.get('tools') or [])}")
        print("Cost: while this editor is open, EVERY headless capture, probe "
              "and sweep is blocked.")
    else:
        print("Epic MCP is NOT reachable. This says nothing about Codex's "
              "separate OpenClaw integration.")
    return 0 if reachable else 1


def cmd_mode() -> int:
    m = read_mode()
    ed = {True: "an editor IS running", False: "no editor running",
          None: "COULD NOT ENUMERATE PROCESSES"}[m.editor_running]
    print(f"mode: {m.name}; {ed}")
    if m.editor_running is True:
        print("  headless runs are BLOCKED. Use OpenClaw for live-editor work, "
              "or close the editor before a headless run.")
    elif m.editor_running is False:
        project = load_game_config().uproject or "the configured .uproject"
        print("  headless runs are available.")
        print(f"  for live-editor work, open {project} yourself.")
    else:
        print("  headless runs fail closed until process enumeration works.")
    return 0


# --- headless command builder -------------------------------------------

BASE_FLAGS = ["-unattended", "-nosplash", "-NoLiveCoding", "-notraceserver",
              "-nop4", "-stdout", "-NoLogTimes"]


class IntentError(Exception):
    """The requested command line cannot produce the requested result."""


def configured_engine_project(
        engine_override: Path | None,
        uproject_override: Path | None) -> tuple[Path, Path]:
    """Resolve explicit CLI paths, then the sole project in GAME.local.md."""
    config = load_game_config()
    engine = engine_override or config.engine_root
    if engine is None:
        raise IntentError(
            "no engine was supplied and GAME.local.md has no Engine root; "
            "pass --engine")
    uproject = uproject_override or config.uproject
    if uproject is None:
        root = config.project_root
        where = f" under {root}" if root else ""
        raise IntentError(
            "no uproject was supplied and GAME.local.md does not resolve to "
            f"exactly one immediate .uproject{where}; pass --uproject")
    return engine.resolve(), uproject.resolve()


def default_run_root(uproject: Path) -> Path:
    """Keep generated evidence out of source directories by default."""
    config = load_game_config()
    if (config.evidence_root is not None and config.uproject is not None
            and config.uproject.resolve() == uproject.resolve()):
        return (config.evidence_root / "Runs").resolve()
    return (uproject.parent / "Saved" / "CodexRuns").resolve()


def require_headless_available() -> str | None:
    """Return a refusal reason, or None when no editor is running."""
    mode = read_mode()
    if mode.editor_running is None:
        return (
            "could not enumerate processes, so 'no editor is running' is "
            "unproven. The never-concurrent-editors rule is fail-closed.")
    if mode.editor_running:
        return (
            "an Unreal editor is running. Close it before a headless launch; "
            "use OpenClaw for work that belongs in the live editor.")
    return None


def build_command(engine: Path, uproject: Path, script: Path, log: Path,
                  *, needs_rhi: bool, real_game: bool = False,
                  extra: list[str] | None = None) -> list[str]:
    """One builder, per `render-a-headless-capture`. A census of one project
    found 122 hand-written launch sites, 11 with no -abslog at all.

    Refuses at build time rather than diagnosing after: -nullrhi means no
    GPU and no rendering, so a run that needs pixels cannot carry it. This
    is a pre-flight refusal, which beats a post-hoc log scan."""
    extra = list(extra or [])
    extra_lower = [e.lower() for e in extra]
    if needs_rhi and "-nullrhi" in extra_lower:
        raise IntentError(
            "-nullrhi with needs_rhi=True cannot produce one pixel. "
            "-nullrhi is not a window-suppression flag; -RenderOffscreen is.")
    if "-game" in extra_lower and not real_game:
        raise IntentError(
            "-game requires --real-game so the script uses the measured "
            "ExecCmds route instead of editor-only -ExecutePythonScript")
    conflicting = [e for e in extra if e.lower().startswith(
        ("-execcmds=", "-executepythonscript="))]
    if conflicting:
        raise IntentError(
            "extra flags must not supply a competing Python entry route: "
            + ", ".join(conflicting))
    if not script.is_file():
        raise IntentError(f"script does not exist: {script}")
    if not uproject.is_file():
        raise IntentError(f"uproject does not exist: {uproject}")
    exe = engine / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe"
    if not exe.is_file():
        raise IntentError(f"engine binary not found: {exe}")

    cmd = [str(exe), str(uproject), *BASE_FLAGS]
    if needs_rhi and "-renderoffscreen" not in extra_lower:
        cmd.append("-RenderOffscreen")
    if real_game and "-game" not in extra_lower:
        cmd.append("-game")
    cmd += extra
    # Literal, absolute, emitted here and never interpolated by a shell: a
    # mangled -abslog costs the whole run silently -- editor launches, exits,
    # writes zero bytes and zero renders, raises nothing.
    cmd.append(f"-abslog={log}")
    if real_game:
        # UE refuses -ExecutePythonScript outside the editor. The measured
        # project route is one quoted ExecCmds value; an unquoted path is
        # split and silently boots without ever running the probe.
        # For this project's no-space root, keep this as ONE argv element and
        # do not add nested quotes around the path. subprocess.list2cmdline
        # quotes the whole process argument for Windows; this does not prove
        # UE's inner console parser can accept a script path containing spaces.
        # Inner quotes survived into UE as
        #   -ExecCmds="py "D:\\...\\probe.py""
        # and the command never ran.
        if any(c.isspace() for c in str(script.resolve())):
            raise IntentError(
                "the measured -game ExecCmds route is unproven for script "
                f"paths containing whitespace: {script.resolve()}")
        cmd.append(f"-ExecCmds=py {script.resolve()}")
    else:
        cmd.append(f"-ExecutePythonScript={script}")
    return cmd


class NativeResultError(ValueError):
    """A native Unreal report is missing or internally inconsistent."""


def build_native_command(engine: Path, uproject: Path, log: Path, *,
                         operation: str, selector: str | None = None,
                         report_dir: Path | None = None,
                         needs_rhi: bool = False) -> list[str]:
    """Build one of the two bounded native Unreal checks."""
    if not uproject.is_file():
        raise IntentError(f"uproject does not exist: {uproject}")
    exe = engine / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe"
    if not exe.is_file():
        raise IntentError(f"engine binary not found: {exe}")

    cmd = [str(exe), str(uproject), *BASE_FLAGS,
           "-RenderOffscreen" if needs_rhi else "-nullrhi"]
    if operation == "automation":
        selector = (selector or "").strip()
        if not selector:
            raise IntentError("automation selector must not be empty")
        if any(char in selector for char in ";,'\"\r\n"):
            raise IntentError(
                "automation selector must not contain command separators, "
                "quotes, or a newline")
        if report_dir is None:
            raise IntentError("automation requires a report directory")
        cmd.extend([
            f"-ReportExportPath={report_dir}",
            f"-ExecCmds=Automation RunTests {selector};Quit",
        ])
    elif operation == "data-validation":
        if needs_rhi:
            raise IntentError("data validation is a CPU commandlet")
        cmd.extend([
            "-run=DataValidation",
            "-IncludeOnlyOnDiskAssets",
            "-culture=en",
        ])
    else:
        raise IntentError(f"unknown native Unreal operation: {operation}")
    cmd.append(f"-abslog={log}")
    return cmd


def _report_value(data: dict, name: str):
    """Read UE's lower-camel JSON key, accepting older struct-case output."""
    lower_camel = name[:1].lower() + name[1:]
    return data.get(lower_camel, data.get(name))


def _report_int(data: dict, key: str) -> int:
    value = _report_value(data, key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise NativeResultError(f"{key} must be a non-negative integer")
    return value


def parse_automation_report(path: Path) -> dict:
    """Turn Epic's Automation index.json into a strict domain verdict."""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise NativeResultError(f"cannot read Automation report: {e}") from e
    if not isinstance(data, dict):
        raise NativeResultError("Automation report root must be an object")
    tests = _report_value(data, "Tests")
    if not isinstance(tests, list):
        raise NativeResultError("Automation report Tests must be an array")
    counts = {
        "succeeded": _report_int(data, "Succeeded"),
        "succeeded_with_warnings": _report_int(
            data, "SucceededWithWarnings"),
        "failed": _report_int(data, "Failed"),
        "not_run": _report_int(data, "NotRun"),
        "in_process": _report_int(data, "InProcess"),
    }
    total = sum(counts.values())
    if total == 0:
        raise NativeResultError(
            "Automation matched zero tests; an empty run is not a pass")
    if total != len(tests):
        raise NativeResultError(
            f"Automation count mismatch: counters total {total}, "
            f"Tests has {len(tests)} entries")
    accepted = not any(counts[k] for k in ("failed", "not_run", "in_process"))
    status = ("FAIL" if not accepted else
              "PASS_WITH_WARNINGS" if counts["succeeded_with_warnings"] else
              "PASS")
    return {
        "schema": "ue-automation-v1",
        "matched": total,
        **counts,
        "status": status,
    }


AUTOMATION_COMPLETE_RE = re.compile(
    r"^LogAutomationCommandLine:\s*Display:\s*"
    r"\*{4} TEST COMPLETE\. EXIT CODE: (-?\d+) \*{4}\s*$",
    re.MULTILINE,
)
AUTOMATION_NO_MATCH_RE = re.compile(
    r"^LogAutomationCommandLine:\s*Error:\s*"
    r"No automation tests matched '([^']+)'\s*$",
    re.MULTILINE,
)


def automation_completion_code(text: str) -> int:
    matches = AUTOMATION_COMPLETE_RE.findall(text)
    if len(matches) != 1:
        raise NativeResultError(
            f"expected one Automation completion marker, found {len(matches)}")
    return int(matches[0])


def process_exit_agrees(process_exit: int | None, reported_exit: int) -> bool:
    """Windows surfaces RequestExitWithStatus(-1) as process exit 255."""
    return (process_exit == reported_exit
            or process_exit == reported_exit % 256)


VALIDATION_START_RE = re.compile(
    r"Starting to validate (\d+) assets \((\d+) associated objects such as actors\)")
VALIDATION_SUMMARY_RE = re.compile(
    r"Files Checked: (\d+), Passed: (\d+), Failed: (\d+), "
    r"Skipped: (\d+), Unable to validate: (\d+)")
VALIDATION_COMPLETE_RE = re.compile(
    r"^LogCore:\s*Engine exit requested \(reason: Commandlet "
    r"DataValidationCommandlet_\d+ finished execution \(result (-?\d+)\)\)\s*$",
    re.MULTILINE,
)
VALIDATION_ATTEMPT_RE = re.compile(
    r"^AssetCheck:\s+.+\s+Validating asset\s*$", re.MULTILINE)
VALIDATION_OUTCOMES = {
    "valid_with_warnings": "contains valid data, but has warnings.",
    "valid": "contains valid data.",
    "invalid": "contains invalid data.",
    "unable_to_validate": "has no data validation.",
}


def parse_data_validation_log(text: str) -> dict:
    """Parse and cross-check UE 5.8's English Data Validation output."""
    starts = VALIDATION_START_RE.findall(text)
    if len(starts) != 1:
        raise NativeResultError(
            f"expected one Data Validation start line, found {len(starts)}")
    completions = VALIDATION_COMPLETE_RE.findall(text)
    if len(completions) != 1:
        raise NativeResultError(
            "expected one Data Validation commandlet completion marker, "
            f"found {len(completions)}")
    commandlet_result = int(completions[0])
    if commandlet_result != 0:
        raise NativeResultError(
            f"Data Validation commandlet reports result {commandlet_result}")

    requested, associated = (int(v) for v in starts[0])
    if requested == 0:
        raise NativeResultError(
            "Data Validation requested zero assets; an empty scan is not a pass")
    attempted = len(VALIDATION_ATTEMPT_RE.findall(text))
    outcomes = {
        key: len(re.findall(
            rf"^AssetCheck:\s+.*{re.escape(phrase)}\s*$", text, re.MULTILINE))
        for key, phrase in VALIDATION_OUTCOMES.items()
    }
    # The shorter valid phrase is not a substring of the warning phrase due
    # to the comma, so these counts remain disjoint.
    processed = sum(outcomes.values())
    summaries = VALIDATION_SUMMARY_RE.findall(text)
    if len(summaries) > 1:
        raise NativeResultError(
            f"expected at most one Data Validation summary line, found "
            f"{len(summaries)}")
    if summaries:
        checked, passed, failed, skipped, unable = (
            int(v) for v in summaries[0])
        summary_source = "footer"
    else:
        # UE 5.8's stock DataValidation commandlet does not always publish
        # the UI subsystem's Files Checked footer. The real Kurogane run did
        # publish one attempt and outcome for every checked asset plus the
        # exact commandlet completion marker. That measured shape is
        # sufficient to derive the missing aggregate; mismatched attempt and
        # outcome lines remain an error below.
        checked = attempted
        passed = outcomes["valid"] + outcomes["valid_with_warnings"]
        failed = outcomes["invalid"]
        skipped = requested - checked
        unable = outcomes["unable_to_validate"]
        summary_source = "commandlet_outcomes"

    contradictions = []
    if attempted == 0:
        contradictions.append("zero assets reached the validation attempt")
    if attempted != processed:
        contradictions.append(
            f"attempt lines {attempted} != outcome lines {processed}")
    if attempted > requested:
        contradictions.append(
            f"attempt lines {attempted} exceed requested assets {requested}")
    if checked != attempted:
        contradictions.append(f"checked {checked} != attempt lines {attempted}")
    if checked != processed:
        contradictions.append(f"checked {checked} != outcome lines {processed}")
    if passed != outcomes["valid"] + outcomes["valid_with_warnings"]:
        contradictions.append(
            f"passed {passed} != valid outcomes "
            f"{outcomes['valid'] + outcomes['valid_with_warnings']}")
    if failed != outcomes["invalid"]:
        contradictions.append(
            f"failed {failed} != invalid outcomes {outcomes['invalid']}")
    if unable != outcomes["unable_to_validate"]:
        contradictions.append(
            f"unable {unable} != not-validated outcomes "
            f"{outcomes['unable_to_validate']}")
    if requested != checked + skipped:
        contradictions.append(
            f"requested {requested} != checked {checked} + skipped {skipped}")
    if contradictions:
        raise NativeResultError("; ".join(contradictions))

    status = (
        "FAIL" if failed else
        "PASS_WITH_WARNINGS"
        if outcomes["valid_with_warnings"] or skipped or unable else
        "PASS"
    )
    return {
        "schema": "ue-data-validation-v1",
        "requested": requested,
        "associated_objects": associated,
        "commandlet_result": commandlet_result,
        "summary_source": summary_source,
        "attempted": attempted,
        "checked": checked,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        **outcomes,
        "status": status,
    }


# --- the watchdog --------------------------------------------------------

def kill_tree(proc: subprocess.Popen) -> None:
    """Kill the process AND its children. UnrealEditor-Cmd spawns
    ShaderCompileWorkers; killing only the parent leaves orphans that then
    trip check_editor_clear on the next launch, which reads as a phantom
    'editor already running'."""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                       capture_output=True, timeout=60)
    else:
        proc.kill()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        pass


def supervise(cmd: list[str], log: Path, *, stall_s: int, wall_s: int,
              on_tick=None) -> tuple[int | None, str | None, float]:
    """Run cmd under two independent timers.

    A wall-clock timeout alone cannot tell a slow run from a hung one; a
    stall detector alone cannot stop a run that stays chatty forever. Return
    (exit_code, killed_reason, elapsed) where killed_reason is
    'stall' | 'timeout' | None.
    """
    start = time.monotonic()
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    last_size, last_growth = -1, start
    killed: str | None = None

    while True:
        rc = proc.poll()
        now = time.monotonic()
        if rc is not None:
            return rc, None, now - start

        try:
            size = log.stat().st_size if log.exists() else 0
        except OSError:
            size = last_size
        if size != last_size:
            last_size, last_growth = size, now

        if on_tick:
            on_tick(now - start, size, now - last_growth)

        if now - start > wall_s:
            killed = "timeout"
        elif now - last_growth > stall_s:
            killed = "stall"

        if killed:
            kill_tree(proc)
            return proc.poll(), killed, time.monotonic() - start

        time.sleep(POLL_S)


def sha256_16(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    except OSError:
        return None


def sha256_full(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def png_capture_size(path: Path) -> list[int] | None:
    """Read PNG dimensions without importing an image stack into the runner."""
    try:
        with path.open("rb") as f:
            head = f.read(24)
        if (len(head) >= 24 and head[:8] == b"\x89PNG\r\n\x1a\n"
                and head[12:16] == b"IHDR"):
            return list(struct.unpack(">II", head[16:24]))
    except OSError:
        pass
    return None


def _log_match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else None


def capture_bucket(log: Path, *, enabled: bool,
                   extra_flags: list[str]) -> dict | None:
    """Extract the configuration that makes a visual baseline comparable.

    Missing values stay null and make the key null. Unknown is not a bucket:
    two runs with equally missing metadata are not thereby comparable.
    """
    if not enabled:
        return None
    try:
        text_ = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text_ = ""
    rhi = run_verdict.extract_rhi(text_)
    if rhi is None and any(f.lower() == "-nullrhi" for f in extra_flags):
        rhi = "NullRHI"
    fields = {
        "platform": _log_match(text_, r"^LogInit:\s*OS:\s*(.*?),\s*CPU:"),
        "engine_version": _log_match(
            text_, r"^LogInit:\s*Engine Version:\s*(.+)$"),
        "rhi": rhi,
        "shader_model": (
            _log_match(text_, r"^LogRHI:\s*Using Highest Feature Level of .*?:\s*(SM\d+)\s*$")
            or _log_match(text_, r"^LogD3D\w*RHI:.*?Max Feature Level\s+(SM\d+)\s*$")),
        "gpu": _log_match(text_, r"^LogRHI:\s+Name:\s*(.+)$"),
        "driver": _log_match(text_, r"^LogRHI:\s+Driver Version:\s*(.+)$"),
    }
    complete = all(fields.values())
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":"))
    return {
        **fields,
        "complete": complete,
        "key": hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        if complete else None,
    }


def git_changed_lines(path: Path) -> int | None:
    """Changed lines against HEAD, including a wholly untracked text file."""
    try:
        root_run = subprocess.run(
            ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10)
        if root_run.returncode:
            return None
        root = Path(root_run.stdout.strip())
        rel = str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
        tracked = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", rel],
            capture_output=True, text=True, timeout=10)
        if tracked.returncode:
            return len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        diff = subprocess.run(
            ["git", "-C", str(root), "diff", "--numstat", "HEAD", "--", rel],
            capture_output=True, text=True, timeout=10, check=True)
        total = 0
        for line in diff.stdout.splitlines():
            fields = line.split("\t", 2)
            if len(fields) >= 2:
                if fields[0] == "-" or fields[1] == "-":
                    return None
                total += int(fields[0]) + int(fields[1])
        return total
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def harness_fingerprint(paths: list[Path]) -> dict:
    """Hash the supervisor, classifier, and target script as one harness."""
    combined = hashlib.sha256()
    files = []
    changed_total = 0
    changed_known = True
    for path in paths:
        resolved = path.resolve()
        digest = sha256_full(resolved)
        changed = git_changed_lines(resolved)
        try:
            size = resolved.stat().st_size
        except OSError:
            size = None
        files.append({"path": str(resolved), "bytes": size,
                      "sha256": digest, "changed_lines": changed})
        combined.update(str(resolved).encode("utf-8"))
        combined.update(b"\0")
        combined.update((digest or "MISSING").encode("ascii"))
        combined.update(b"\0")
        if changed is None:
            changed_known = False
        else:
            changed_total += changed
    return {
        "sha256": combined.hexdigest(),
        "changed_line_count": changed_total if changed_known else None,
        "files": files,
    }


# Match literal environment-style names in the script, then retain only names
# that are actually present in this process. This stays game-agnostic while
# avoiding an ambient environment dump.
PROJECT_ENV_RE = re.compile(r"(?<![A-Z0-9_])[A-Z][A-Z0-9]{1,31}_[A-Z0-9_]+")
SENSITIVE_ENV_KEY_RE = re.compile(
    r"(?:^|_)(?:API_?KEY|AUTH|BEARER|COOKIE|CREDENTIAL|PASSWORD|PASSWD|"
    r"PRIVATE_?KEY|SECRET|SESSION|SIGNING|TOKEN)(?:_|$)", re.IGNORECASE)


def project_environment(script: Path) -> dict[str, str]:
    """Record only project variables the target script names literally.

    A prefix-wide environment dump can serialize an unrelated future token
    into a sidecar.  The script literals are the smallest useful allowlist for
    reproducibility; credential-shaped names remain redacted even when a probe
    explicitly references one.
    """
    try:
        source = script.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    names = sorted(set(PROJECT_ENV_RE.findall(source)))
    recorded: dict[str, str] = {}
    for name in names:
        if name not in os.environ:
            continue
        recorded[name] = (
            "<redacted>" if SENSITIVE_ENV_KEY_RE.search(name)
            else os.environ[name]
        )
    return recorded


def atomic_write_json(path: Path, payload: dict) -> None:
    """Publish a complete sidecar atomically without replacing a collision."""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with tmp.open("x", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        # Same-directory hard-link publication is atomic and fails if another
        # process created the destination after our preflight. os.replace
        # would silently destroy that newly arrived evidence.
        os.link(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def bound_artifact_records(v: run_verdict.Verdict,
                           artifacts: list[Path]) -> list[dict]:
    """Bind sidecar metadata to the exact artifact bytes the verdict read."""
    classified = {
        str(Path(entry["path"]).resolve()): entry
        for entry in v.evidence.get("artifacts", [])
    }
    records = []
    identity = ("exists", "is_file", "bytes", "mtime_ns", "sha256")
    for path in artifacts:
        key = str(path.resolve())
        original = dict(classified.get(key, {"path": key}))
        size = png_capture_size(path)
        after = run_verdict.artifact_snapshot(path)
        if any(original.get(k) != after.get(k) for k in identity):
            v.environment_ok = False
            v.reasons.append(
                f"artifact changed after verdict classification: {path}. "
                "The sidecar refuses to bind one verdict to different bytes.")
            original["post_classification_snapshot"] = after
            original["capture_size"] = None
        else:
            original["capture_size"] = size
        records.append(original)
    return records


def cmd_headless(a: argparse.Namespace) -> int:
    # argparse does not route dash-prefixed values through the trailing
    # ``nargs='*'`` positional under this subparser (even after ``--``).
    # Engine flags are, by definition, dash-prefixed, so provide an explicit
    # repeatable option. Keep the positional for backward-compatible plain
    # values and combine both in their declared order groups.
    extra_flags = [*a.extra, *getattr(a, "extra_flag", [])]

    refusal = require_headless_available()
    if refusal:
        print(f"REFUSED: {refusal}", file=sys.stderr)
        return 3

    script = a.script.resolve()
    try:
        engine, uproject = configured_engine_project(a.engine, a.uproject)
    except IntentError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3
    artifacts = [p.resolve() for p in a.artifact]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = (a.out_dir or default_run_root(uproject)).resolve()
    base = f"{script.stem}-{stamp}"
    log = a.log.resolve() if a.log else (out_dir / f"{base}.log")
    sidecar = out_dir / f"{base}.sidecar.json"
    for p in (log, sidecar):
        if p.exists():
            print(f"REFUSED: {p} already exists; refusing to overwrite an "
                  f"existing log or sidecar.", file=sys.stderr)
            return 3
    for p in artifacts:
        if p.exists():
            print(f"REFUSED: declared artifact {p} already exists. A "
                  f"supervised run must produce a fresh path; reusing it "
                  f"would overwrite evidence and can make a stale file look "
                  f"like this run's output.", file=sys.stderr)
            return 3
    try:
        cmd = build_command(engine, uproject, script, log,
                            needs_rhi=a.needs_rhi, real_game=a.real_game,
                            extra=extra_flags)
    except IntentError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3

    print(f"run     : {base}")
    print(f"log     : {log}")
    print(f"budget  : stall {a.stall}s / wall {a.wall}s")
    print(f"command : {subprocess.list2cmdline(cmd)}")
    if a.dry_run:
        print("\n--dry-run: nothing launched.")
        return 0
    log.parent.mkdir(parents=True, exist_ok=True)
    print()

    def tick(elapsed, size, quiet):
        print(f"\r  {elapsed:6.0f}s  log {size/1024:9.1f} KB  "
              f"quiet {quiet:5.0f}s ", end="", flush=True)

    # Provenance is a property of the code that is about to run. Hashing it
    # after a long engine session can accidentally describe an edit made
    # while the process was alive instead of the bytes the process loaded.
    harness = harness_fingerprint([
        Path(__file__), Path(run_verdict.__file__), script])

    artifact_baselines = {
        str(p): run_verdict.artifact_snapshot(p) for p in artifacts
    }
    arrived = [p for p in artifacts
               if artifact_baselines[str(p)].get("exists") is not False]
    collisions = [p for p in (log, sidecar) if p.exists()]
    if arrived or collisions:
        for p in arrived:
            print(f"REFUSED: declared artifact {p} appeared after preflight; "
                  "refusing a run that could overwrite or misattribute it.",
                  file=sys.stderr)
        for p in collisions:
            print(f"REFUSED: {p} appeared after preflight; refusing to "
                  "overwrite it.", file=sys.stderr)
        return 3
    t0_ns = time.time_ns()
    t0 = t0_ns / 1_000_000_000
    rc, killed, elapsed = supervise(cmd, log, stall_s=a.stall, wall_s=a.wall,
                                    on_tick=tick)
    print()

    # A run declaring it needs pixels must prove an RHI came up, positively.
    expect_rhi = a.expect_rhi or ("D3D12" if a.needs_rhi else None)
    v = run_verdict.verdict_for(log, artifacts, exit_code=rc, killed=killed,
                                expect_rhi=expect_rhi,
                                artifact_baselines=artifact_baselines,
                                artifact_not_before_ns=t0_ns,
                                max_blueprint_runtime_errors=(
                                    a.max_blueprint_runtime_errors))

    artifact_records = bound_artifact_records(v, artifacts)
    capture_enabled = a.needs_rhi or any(
        p.suffix.lower() in {".png", ".exr", ".bmp", ".jpg", ".jpeg"}
        for p in artifacts)
    project_env = project_environment(script)

    payload = {
        "schema": "engine-run-sidecar-v2",
        "run": base,
        "started_utc": datetime.fromtimestamp(t0, timezone.utc).isoformat(
            timespec="seconds"),
        "started_unix_ns": t0_ns,
        "elapsed_s": round(elapsed, 1),
        "command": cmd,
        "command_line": subprocess.list2cmdline(cmd),
        "intent": {"needs_rhi": a.needs_rhi,
                   "real_game": a.real_game,
                   "extra_flags": extra_flags},
        "budgets": {"stall_s": a.stall, "wall_s": a.wall},
        "killed": killed,
        "exit_code": rc,
        "harness": harness,
        # Fixed, declared environment tuple. Do not dump the whole process
        # environment into evidence that may later be shared.
        "environment": {
            k: os.environ.get(k) for k in (
                "PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE",
                "OMP_NUM_THREADS", "MKL_NUM_THREADS")
        },
        # Only variables named literally by the target script are captured;
        # credential-shaped names are redacted.  This keeps run parameters
        # reproducible without turning a sidecar into an ambient secret dump.
        "env_project": project_env,
        "log": v.evidence["log_snapshot"],
        "artifacts": artifact_records,
        "capture": ({
            "bucket": capture_bucket(
                log, enabled=True, extra_flags=extra_flags),
            # A generic supervisor cannot infer a domain-specific identity
            # pair. Null means the gate did not run; capture instruments must
            # put their measured pair/floor in their own declared artifact.
            "noise_floor": None,
        } if capture_enabled else None),
        "verdict": v.as_dict(),
    }
    try:
        atomic_write_json(sidecar, payload)
    except FileExistsError:
        print(f"REFUSED: {sidecar} appeared before atomic publication; "
              "existing evidence was preserved and this run has no sidecar.",
              file=sys.stderr)
        return 2

    print(run_verdict.render(v))
    print(f"\nsidecar : {sidecar}")
    if killed:
        print(f"WATCHDOG: killed on {killed} after {elapsed:.0f}s. Without "
              f"this the process would still be holding the editor lock.")
    return 0 if v.citable else (1 if v.execution == "COMPLETE" else 2)


def _native_result(operation: str, log: Path, artifact: Path,
                   process_exit: int | None) -> dict:
    if operation == "automation":
        try:
            log_text = log.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            raise NativeResultError(
                f"cannot read Automation log: {e}") from e
        completion = automation_completion_code(log_text)
        if artifact.is_file():
            result = parse_automation_report(artifact)
        else:
            no_match = AUTOMATION_NO_MATCH_RE.findall(log_text)
            if len(no_match) != 1:
                raise NativeResultError(
                    "Automation report is absent and the log does not carry "
                    "one exact zero-match result")
            result = {
                "schema": "ue-automation-v1",
                "matched": 0,
                "succeeded": 0,
                "succeeded_with_warnings": 0,
                "failed": 0,
                "not_run": 0,
                "in_process": 0,
                "status": "FAIL",
                "error": f"no tests matched {no_match[0]!r}",
            }
        result["automation_exit_code"] = completion
        if completion != 0:
            result["status"] = "FAIL"
            result.setdefault(
                "error", f"Automation completion marker reports exit {completion}")
        if not process_exit_agrees(process_exit, completion):
            result["status"] = "ERROR"
            result["error"] = (
                f"process exit {process_exit} disagrees with Automation "
                f"completion marker {completion}")
        return result

    try:
        raw = log.read_bytes()
        result = parse_data_validation_log(raw.decode("utf-8", "replace"))
        result["source_log_sha256"] = hashlib.sha256(raw).hexdigest()
        result["scope"] = (
            "on-disk project and project-plugin assets selected by Unreal's "
            "stock DataValidation commandlet")
        result["blind_spots"] = [
            "engine assets are excluded unless -includeengine is used",
            "unsaved in-memory edits are excluded by IncludeOnlyOnDiskAssets",
            "validation rules do not prove runtime gameplay behavior",
        ]
    except (OSError, NativeResultError) as e:
        result = {
            "schema": "ue-data-validation-v1",
            "source_log_sha256": sha256_full(log),
            "status": "ERROR",
            "error": str(e),
        }
    atomic_write_json(artifact, result)
    return result


def reconcile_automation_execution(
        verdict: run_verdict.Verdict, native: dict,
        process_exit: int | None, killed: str | None) -> None:
    """Apply Automation's exact terminal marker to the generic log verdict."""
    if not (
        verdict.execution == "TRUNCATED"
        and isinstance(native.get("automation_exit_code"), int)
        and process_exit_agrees(process_exit, native["automation_exit_code"])
        and killed is None
    ):
        return
    verdict.execution = "COMPLETE"
    verdict.contradiction = False
    verdict.reasons = [
        reason for reason in verdict.reasons
        if not reason.startswith("engine log with no crash marker")
        and not reason.startswith("CONTRADICTION:")
    ]
    verdict.reasons.append(
        "Epic Automation wrote its terminal TEST COMPLETE marker with "
        f"exit {native['automation_exit_code']}; this RequestExitWithStatus "
        "path does not write the ordinary 'Log file closed' marker")


def cmd_native(a: argparse.Namespace, operation: str) -> int:
    refusal = require_headless_available()
    if refusal:
        print(f"REFUSED: {refusal}", file=sys.stderr)
        return 3
    try:
        engine, uproject = configured_engine_project(a.engine, a.uproject)
    except IntentError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    root = (a.out_dir or default_run_root(uproject)).resolve()
    run_dir = root / f"{operation}-{stamp}"
    log = run_dir / "engine.log"
    sidecar = run_dir / "sidecar.json"
    report_dir = run_dir / "report"
    artifact = (report_dir / "index.json" if operation == "automation"
                else run_dir / "validation.json")
    if run_dir.exists():
        print(f"REFUSED: {run_dir} already exists; native runs require a "
              "fresh evidence directory.", file=sys.stderr)
        return 3
    try:
        cmd = build_native_command(
            engine, uproject, log,
            operation=operation,
            selector=getattr(a, "selector", None),
            report_dir=report_dir if operation == "automation" else None,
            needs_rhi=getattr(a, "needs_rhi", False),
        )
    except IntentError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3

    print(f"run     : {run_dir.name}")
    print(f"log     : {log}")
    print(f"artifact: {artifact}")
    print(f"budget  : stall {a.stall}s / wall {a.wall}s")
    print(f"command : {subprocess.list2cmdline(cmd)}")
    if a.dry_run:
        print("\n--dry-run: nothing launched and no directory created.")
        return 0
    print()

    root.mkdir(parents=True, exist_ok=True)
    try:
        run_dir.mkdir()
    except FileExistsError:
        print(f"REFUSED: {run_dir} appeared after preflight; existing "
              "evidence was preserved.", file=sys.stderr)
        return 3

    harness = harness_fingerprint([Path(__file__), Path(run_verdict.__file__)])
    baseline = {str(artifact): run_verdict.artifact_snapshot(artifact)}
    t0_ns = time.time_ns()
    t0 = t0_ns / 1_000_000_000

    def tick(elapsed, size, quiet):
        print(f"\r  {elapsed:6.0f}s  log {size/1024:9.1f} KB  "
              f"quiet {quiet:5.0f}s ", end="", flush=True)

    rc, killed, elapsed = supervise(
        cmd, log, stall_s=a.stall, wall_s=a.wall, on_tick=tick)
    print()
    try:
        native = _native_result(operation, log, artifact, rc)
    except (OSError, NativeResultError, FileExistsError) as e:
        native = {
            "schema": f"ue-{operation}-v1",
            "status": "ERROR",
            "error": f"could not publish native result: {e}",
        }

    expect_rhi = (a.expect_rhi or "D3D12"
                  if getattr(a, "needs_rhi", False) else None)
    v = run_verdict.verdict_for(
        log, [artifact], exit_code=rc, killed=killed,
        expect_rhi=expect_rhi,
        artifact_baselines=baseline,
        artifact_not_before_ns=t0_ns,
    )
    if operation == "automation":
        reconcile_automation_execution(v, native, rc, killed)
    native_ok = native.get("status") in {"PASS", "PASS_WITH_WARNINGS"}
    if not native_ok:
        v.environment_ok = False
        v.reasons.append(
            f"native {operation} verdict is {native.get('status', 'ERROR')}: "
            f"{native.get('error') or 'see native_result counts'}")
    elif native.get("status") == "PASS_WITH_WARNINGS":
        v.reasons.append(
            f"native {operation} completed with warnings; counts are retained "
            "in native_result")

    artifact_records = bound_artifact_records(v, [artifact])
    payload = {
        "schema": "engine-native-sidecar-v1",
        "run": run_dir.name,
        "started_utc": datetime.fromtimestamp(t0, timezone.utc).isoformat(
            timespec="seconds"),
        "started_unix_ns": t0_ns,
        "elapsed_s": round(elapsed, 1),
        "command": cmd,
        "command_line": subprocess.list2cmdline(cmd),
        "intent": {
            "operation": operation,
            "selector": getattr(a, "selector", None),
            "needs_rhi": getattr(a, "needs_rhi", False),
        },
        "budgets": {"stall_s": a.stall, "wall_s": a.wall},
        "killed": killed,
        "exit_code": rc,
        "harness": harness,
        "environment": {
            k: os.environ.get(k) for k in (
                "PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE",
                "OMP_NUM_THREADS", "MKL_NUM_THREADS")
        },
        "log": v.evidence["log_snapshot"],
        "artifacts": artifact_records,
        "native_result": native,
        "verdict": v.as_dict(),
    }
    try:
        atomic_write_json(sidecar, payload)
    except FileExistsError:
        print(f"REFUSED: {sidecar} appeared before atomic publication; "
              "existing evidence was preserved.", file=sys.stderr)
        return 2

    print(f"NATIVE    : {native.get('status', 'ERROR')}")
    print(run_verdict.render(v))
    print(f"\nsidecar : {sidecar}")
    return 0 if v.citable and native_ok else (
        1 if v.execution == "COMPLETE" else 2)


# --- cli -----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="engine_run", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("mode", help="which engine mode is active, and how to switch")
    sub.add_parser(
        "epic-mcp-check",
        help="is the optional Epic HTTP MCP surface actually reachable")

    h = sub.add_parser("headless", help="supervised headless run")
    h.add_argument("script", type=Path)
    h.add_argument("--engine", type=Path, default=None,
                   help="engine root; defaults to GAME.local.md")
    h.add_argument("--uproject", type=Path, default=None,
                   help="project file; defaults to the sole immediate "
                        ".uproject under GAME.local.md's Project root")
    h.add_argument("--log", type=Path, default=None)
    h.add_argument("--out-dir", type=Path, default=None)
    h.add_argument("--artifact", type=Path, action="append", default=[],
                   help="path this run must write; the OUTPUT verdict gates "
                        "on it. Repeatable. Omitting it means the run gates "
                        "on nothing.")
    h.add_argument("--needs-rhi", action="store_true",
                   help="this run renders; adds -RenderOffscreen, refuses "
                        "-nullrhi, and asserts an RHI actually initialised")
    h.add_argument("--real-game", action="store_true",
                   help="boot the project's player entry with -game and run "
                        "Python through the measured quoted -ExecCmds route")
    h.add_argument("--expect-rhi", default=None,
                   help="override the RHI asserted by --needs-rhi (D3D12)")
    h.add_argument("--max-blueprint-runtime-errors", type=int, default=0,
                   help="maximum explicit Blueprint Runtime Error markers "
                        "allowed before the run becomes non-citable")
    h.add_argument("--stall", type=int, default=DEFAULT_STALL_S)
    h.add_argument("--wall", type=int, default=DEFAULT_WALL_S)
    h.add_argument("--dry-run", action="store_true")
    h.add_argument("--extra-flag", action="append", default=[],
                   help="pass one dash-prefixed flag to Unreal; repeatable. "
                        "Use the equals form, e.g. "
                        "--extra-flag=-nullrhi")
    h.add_argument("extra", nargs="*", default=[],
                   help="extra engine flags, after --")

    def add_native_common(parser: argparse.ArgumentParser, *, rhi: bool) -> None:
        parser.add_argument("--engine", type=Path, default=None,
                            help="engine root; defaults to GAME.local.md")
        parser.add_argument("--uproject", type=Path, default=None,
                            help="project file; defaults to GAME.local.md")
        parser.add_argument("--out-dir", type=Path, default=None,
                            help="parent for the fresh run directory")
        if rhi:
            parser.add_argument(
                "--needs-rhi", action="store_true",
                help="use RenderOffscreen instead of NullRHI and assert D3D12")
            parser.add_argument(
                "--expect-rhi", default=None,
                help="override the RHI asserted by --needs-rhi")
        parser.add_argument("--stall", type=int, default=DEFAULT_STALL_S)
        parser.add_argument("--wall", type=int, default=DEFAULT_WALL_S)
        parser.add_argument("--dry-run", action="store_true")

    automation = sub.add_parser(
        "automation", help="run one bounded Unreal Automation selector")
    automation.add_argument(
        "selector", help="exact test name, prefix, or supported filter")
    add_native_common(automation, rhi=True)

    validation = sub.add_parser(
        "data-validation",
        help="validate all on-disk project assets with Unreal's stock commandlet")
    add_native_common(validation, rhi=False)
    return ap


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    a = build_parser().parse_args(argv[1:])
    if a.cmd == "mode":
        return cmd_mode()
    if a.cmd == "epic-mcp-check":
        return cmd_epic_mcp_check()
    if a.cmd in {"automation", "data-validation"}:
        return cmd_native(a, a.cmd)
    return cmd_headless(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
