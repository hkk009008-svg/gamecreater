"""One supervised entry point for engine work, in either engine mode.

    python scripts/engine_run.py mode                       # where am I?
    python scripts/engine_run.py mcp-check                  # is MCP usable?
    python scripts/engine_run.py headless SCRIPT.py [opts]  # supervised run

WHY THIS EXISTS. The repo has two engine modes that cannot overlap --
HEADLESS (no editor; captures, probes, sweeps) and MCP (one editor held
open, serving tools on 127.0.0.1:8000). Before this script, using both meant
remembering which was active, and the collision surfaced as
`check_editor_clear` printing "editor process(es) running", whose obvious
fix is to kill the editor -- silently ending an MCP session someone started
on purpose. This routes on the declared mode instead, and every refusal
names the exact transition back.

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
GAME.local.md; an INTERACTIVE editor launch is NOT, so MCP mode is reported
and never started here. Nothing is deleted or overwritten: sidecars and logs
go to fresh timestamped paths, and a collision is an error, not a clobber.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
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
import run_verdict                        # noqa: E402

MARKER = ROOT / ".mcp-session.local"
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
    declared_mcp: bool
    editor_running: bool | None          # None = could not enumerate
    marker: dict | None

    @property
    def name(self) -> str:
        return "MCP" if self.declared_mcp else "HEADLESS"

    @property
    def stale(self) -> bool:
        return self.declared_mcp and self.editor_running is False

    @property
    def undeclared_editor(self) -> bool:
        return not self.declared_mcp and self.editor_running is True


def read_mode() -> Mode:
    marker = None
    if MARKER.is_file():
        try:
            marker = json.loads(MARKER.read_text(encoding="utf-8"))
        except Exception:
            marker = {"note": "marker file is corrupt"}
    try:
        running = bool(cec.matching_processes(cec.list_processes(), "UnrealEditor"))
    except Exception:
        running = None                    # never report this as "no editor"
    return Mode(declared_mcp=MARKER.is_file(), editor_running=running, marker=marker)


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


def cmd_mcp_check() -> int:
    """Report each precondition separately -- 'MCP is broken' is not a
    diagnosis, and these failures have different fixes.

    REACHABILITY and BOOKKEEPING are deliberately separated. An earlier
    version folded the mode declaration into readiness and printed "MCP is
    NOT reachable" while the server was answering perfectly -- a false
    statement, and the sort that gets a diagnostic distrusted. Declaring the
    mode protects the NEXT session from killing a deliberate editor; it has
    no bearing on whether tool calls connect."""
    m = read_mode()
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
         "open D:/Kurogane/Kurogane.uproject -- an INTERACTIVE editor launch "
         "is not covered by the headless grant, so you must do this"),
        (f"listener on {host}:{port}", listening,
         "the editor is up but the plugin is not serving: check "
         "ModelContextProtocol is enabled and bAutoStartServer=True in "
         "D:/Kurogane/Saved/Config/WindowsEditor/EditorPerProjectUserSettings.ini"),
        ("endpoint speaks MCP", bool(hs.get("speaks_mcp")),
         f"something is listening but did not complete an MCP handshake: "
         f"{hs.get('error')}"),
    ]
    print(f"MCP readiness  (endpoint http://{host}:{port}{path})")
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
        print(f"MCP IS REACHABLE -- protocol {hs.get('protocol')}, "
              f"{len(hs.get('tools') or [])} tool(s) advertised: "
              f"{', '.join(hs.get('tools') or [])}")
        print("Cost: while this editor is open, EVERY headless capture, probe "
              "and sweep is blocked.")
    else:
        print("MCP is NOT reachable; tool calls will fail to connect.")

    # Bookkeeping, reported but never folded into reachability.
    if not m.declared_mcp:
        print()
        print("  [--] mode not declared (bookkeeping, not reachability)")
        print("       -> python scripts/mcp_session.py on, so the next "
              "session sees a deliberate editor instead of one to kill")
    if m.stale:
        print("! STALE DECLARATION: mode says MCP, no editor is running. "
              "Run: python scripts/mcp_session.py off")
    return 0 if reachable else 1


def cmd_mode() -> int:
    m = read_mode()
    ed = {True: "an editor IS running", False: "no editor running",
          None: "COULD NOT ENUMERATE PROCESSES"}[m.editor_running]
    print(f"mode: {m.name}; {ed}")
    if m.declared_mcp:
        print(f"  declared: {(m.marker or {}).get('started', '?')}")
        print("  headless runs are BLOCKED. To switch: "
              "python scripts/mcp_session.py off, then close the editor.")
    else:
        print("  headless runs are available (subject to no editor running).")
        print("  to switch: python scripts/mcp_session.py on, then open "
              "D:/Kurogane/Kurogane.uproject yourself.")
    if m.stale:
        print("  ! STALE: MCP declared, no editor. Every MCP call will fail "
              "to connect. Run: mcp_session.py off")
    if m.undeclared_editor:
        print("  ! An editor is open but no MCP session is declared. Headless "
              "is blocked and nothing records why. Either close it, or "
              "declare it: mcp_session.py on")
    return 0


# --- headless command builder -------------------------------------------

BASE_FLAGS = ["-unattended", "-nosplash", "-NoLiveCoding", "-notraceserver",
              "-nop4", "-stdout", "-NoLogTimes"]


class IntentError(Exception):
    """The requested command line cannot produce the requested result."""


def build_command(engine: Path, uproject: Path, script: Path, log: Path,
                  *, needs_rhi: bool, extra: list[str] | None = None) -> list[str]:
    """One builder, per `render-a-headless-capture`. A census of one project
    found 122 hand-written launch sites, 11 with no -abslog at all.

    Refuses at build time rather than diagnosing after: -nullrhi means no
    GPU and no rendering, so a run that needs pixels cannot carry it. This
    is a pre-flight refusal, which beats a post-hoc log scan."""
    extra = list(extra or [])
    for bad in ("-nullrhi", "-NullRHI"):
        if needs_rhi and bad in extra:
            raise IntentError(
                f"{bad} with needs_rhi=True cannot produce one pixel. "
                f"-nullrhi is not a window-suppression flag; -RenderOffscreen is.")
    if not script.is_file():
        raise IntentError(f"script does not exist: {script}")
    if not uproject.is_file():
        raise IntentError(f"uproject does not exist: {uproject}")
    exe = engine / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe"
    if not exe.is_file():
        raise IntentError(f"engine binary not found: {exe}")

    cmd = [str(exe), str(uproject), *BASE_FLAGS]
    if needs_rhi and not any(e.lower() == "-renderoffscreen" for e in extra):
        cmd.append("-RenderOffscreen")
    cmd += extra
    # Literal, absolute, emitted here and never interpolated by a shell: a
    # mangled -abslog costs the whole run silently -- editor launches, exits,
    # writes zero bytes and zero renders, raises nothing.
    cmd.append(f"-abslog={log}")
    cmd.append(f"-ExecutePythonScript={script}")
    return cmd


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


def cmd_headless(a: argparse.Namespace) -> int:
    m = read_mode()

    # Mode gate. Same verdict check_editor_clear would give; the difference
    # is that the reason is legible and the transition is named.
    if m.declared_mcp:
        print("REFUSED: an MCP session is declared, so an editor is (or "
              "should be) open serving tools. Headless and MCP are mutually "
              "exclusive by construction.\n"
              "  To go headless: python scripts/mcp_session.py off, then "
              "close the editor.", file=sys.stderr)
        return 3
    if m.editor_running is None:
        print("REFUSED: could not enumerate processes, so 'no editor is "
              "running' is unproven. The never-concurrent-editors rule is "
              "fail-closed.", file=sys.stderr)
        return 3
    if m.editor_running:
        print("REFUSED: an editor is running and no MCP session is declared. "
              "Close it (or declare it with mcp_session.py on if it is "
              "deliberate) before a headless launch.", file=sys.stderr)
        return 3

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = a.out_dir or (a.script.parent / "runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"{a.script.stem}-{stamp}"
    log = a.log or (out_dir / f"{base}.log")
    sidecar = out_dir / f"{base}.sidecar.json"
    for p in (log, sidecar):
        if p.exists():
            print(f"REFUSED: {p} already exists; refusing to overwrite an "
                  f"existing log or sidecar.", file=sys.stderr)
            return 3
    log.parent.mkdir(parents=True, exist_ok=True)

    try:
        cmd = build_command(a.engine, a.uproject, a.script, log,
                            needs_rhi=a.needs_rhi, extra=a.extra)
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
    print()

    def tick(elapsed, size, quiet):
        print(f"\r  {elapsed:6.0f}s  log {size/1024:9.1f} KB  "
              f"quiet {quiet:5.0f}s ", end="", flush=True)

    t0 = time.time()
    rc, killed, elapsed = supervise(cmd, log, stall_s=a.stall, wall_s=a.wall,
                                    on_tick=tick)
    print()

    # A run declaring it needs pixels must prove an RHI came up, positively.
    expect_rhi = a.expect_rhi or ("D3D12" if a.needs_rhi else None)
    v = run_verdict.verdict_for(log, a.artifact, exit_code=rc, killed=killed,
                                expect_rhi=expect_rhi)

    payload = {
        "run": base,
        "started_utc": datetime.fromtimestamp(t0, timezone.utc).isoformat(
            timespec="seconds"),
        "elapsed_s": round(elapsed, 1),
        "command": cmd,
        "command_line": subprocess.list2cmdline(cmd),
        "intent": {"needs_rhi": a.needs_rhi, "extra_flags": a.extra},
        "budgets": {"stall_s": a.stall, "wall_s": a.wall},
        "killed": killed,
        "exit_code": rc,
        # The assembly state a render is uninterpretable without.
        "env_KUROGANE": {k: v_ for k, v_ in sorted(os.environ.items())
                         if k.startswith("KUROGANE_")},
        "log": {"path": str(log), "bytes": log.stat().st_size if log.exists()
                else 0, "sha256_16": sha256_16(log)},
        "artifacts": [{"path": str(p), "sha256_16": sha256_16(p)}
                      for p in a.artifact],
        "verdict": v.as_dict(),
    }
    sidecar.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(run_verdict.render(v))
    print(f"\nsidecar : {sidecar}")
    if killed:
        print(f"WATCHDOG: killed on {killed} after {elapsed:.0f}s. Without "
              f"this the process would still be holding the editor lock.")
    return 0 if v.citable else (1 if v.execution == "COMPLETE" else 2)


# --- cli -----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="engine_run", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("mode", help="which engine mode is active, and how to switch")
    sub.add_parser("mcp-check", help="is the MCP surface actually reachable")

    h = sub.add_parser("headless", help="supervised headless run")
    h.add_argument("script", type=Path)
    h.add_argument("--engine", type=Path, default=Path("D:/UE_5.8"))
    h.add_argument("--uproject", type=Path,
                   default=Path("D:/Kurogane/Kurogane.uproject"))
    h.add_argument("--log", type=Path, default=None)
    h.add_argument("--out-dir", type=Path, default=None)
    h.add_argument("--artifact", type=Path, action="append", default=[],
                   help="path this run must write; the OUTPUT verdict gates "
                        "on it. Repeatable. Omitting it means the run gates "
                        "on nothing.")
    h.add_argument("--needs-rhi", action="store_true",
                   help="this run renders; adds -RenderOffscreen, refuses "
                        "-nullrhi, and asserts an RHI actually initialised")
    h.add_argument("--expect-rhi", default=None,
                   help="override the RHI asserted by --needs-rhi (D3D12)")
    h.add_argument("--stall", type=int, default=DEFAULT_STALL_S)
    h.add_argument("--wall", type=int, default=DEFAULT_WALL_S)
    h.add_argument("--dry-run", action="store_true")
    h.add_argument("extra", nargs="*", default=[],
                   help="extra engine flags, after --")
    return ap


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    a = build_parser().parse_args(argv[1:])
    if a.cmd == "mode":
        return cmd_mode()
    if a.cmd == "mcp-check":
        return cmd_mcp_check()
    return cmd_headless(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
