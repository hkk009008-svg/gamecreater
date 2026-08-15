"""Declare which of the two mutually exclusive engine modes is active.

    python scripts/mcp_session.py on | off | status

WHY THIS EXISTS. Unreal's MCP server is served BY A RUNNING EDITOR. This
repo mechanically forbids an editor coexisting with headless work:
check_editor_clear.py fails closed on any process named UnrealEditor*, and
CLAUDE.md's never-concurrent-editors rule is the reason. So the project now
has two modes that cannot overlap:

    HEADLESS   no editor. Captures, probes, sweeps. The default.
    MCP        one editor, held open, serving tools on 127.0.0.1:8000.

Without a declaration the collision is indistinguishable from a bug: a
headless launch fails with "editor process(es) running" and the next
session's obvious move is to kill the editor -- which silently ends the MCP
session someone deliberately started. The marker turns an accident-shaped
failure into a stated one, and it is the only thing here that does any
work. This grants no authority and changes no guard: an editor being open
still blocks headless launches, exactly as before.

The marker is machine-local and gitignored. Its absence is the safe
default, so losing it degrades to today's behaviour rather than to a
permissive one.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER = ROOT / ".mcp-session.local"


def editor_running() -> bool | None:
    """None means 'could not tell' -- never report that as 'no editor'."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import check_editor_clear as cec
        return bool(cec.matching_processes(cec.list_processes(),
                                           "UnrealEditor"))
    except Exception:
        return None


def read() -> dict | None:
    if not MARKER.is_file():
        return None
    try:
        return json.loads(MARKER.read_text(encoding="utf-8"))
    except Exception:
        return {"started": "unparseable", "note": "marker file is corrupt"}


def status() -> int:
    m = read()
    running = editor_running()
    ed = {True: "an editor IS running", False: "no editor running",
          None: "COULD NOT ENUMERATE PROCESSES"}[running]
    if m is None:
        print(f"mode: HEADLESS (no MCP session declared); {ed}")
        if running:
            print("  ! an editor is open but no MCP session is declared. "
                  "Headless launches are blocked and nothing records why. "
                  "Either close it, or declare: mcp_session.py on")
        return 0
    print(f"mode: MCP (declared {m.get('started')}); {ed}")
    print(f"  url: {m.get('url')}")
    if running is False:
        print("  ! STALE MARKER: an MCP session is declared but no editor is "
              "running, so every MCP tool call will fail to connect. "
              "Run: mcp_session.py off")
    return 0


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    cmd = (argv[1] if len(argv) > 1 else "status").lower()

    if cmd == "on":
        MARKER.write_text(json.dumps({
            "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "url": "http://127.0.0.1:8000/mcp",
            "note": "Editor held open to serve MCP. Headless captures, "
                    "probes and sweeps are BLOCKED until this ends.",
        }, indent=2) + "\n", encoding="utf-8")
        print("mode: MCP declared. Open D:/Kurogane/Kurogane.uproject if it "
              "is not already open.")
        print("Headless launches are blocked while it runs -- that is the "
              "never-concurrent-editors rule, not a fault.")
        return 0

    if cmd == "off":
        if MARKER.is_file():
            MARKER.unlink()
            print("mode: HEADLESS. Close the editor before a headless launch.")
        else:
            print("mode: HEADLESS already (no marker).")
        return 0

    if cmd == "status":
        return status()

    print(f"unknown command {cmd!r}; use on | off | status", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
