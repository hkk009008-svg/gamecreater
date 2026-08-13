"""Antigravity PreToolUse hook adapter.

Receives Antigravity's tool call JSON payload on stdin:
  {"toolCall": {"name": "run_command", "args": {"CommandLine": "..."}}}

Dispatches the command through the gamecreater safety guards
(preflight_push and check_editor_clear) and outputs the Antigravity
hook protocol JSON to stdout:
  {"decision": "allow"} or {"decision": "deny", "reason": "..."}
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import hook_pretooluse  # noqa: E402


def extract_command(payload: str) -> str:
    try:
        data = json.loads(payload.lstrip("\ufeff \r\n\t"))
    except json.JSONDecodeError:
        return ""
    tool_call = data.get("toolCall") or {}
    args = tool_call.get("args") or {}
    cmd = args.get("CommandLine") or args.get("command") or ""
    return cmd if isinstance(cmd, str) else ""


def main() -> int:
    # Ensure stdout/stderr won't crash on Windows console encoding
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")

    raw = sys.stdin.read()
    cmd = extract_command(raw)
    if not cmd:
        print(json.dumps({"decision": "allow"}))
        return 0

    err_buf = io.StringIO()
    try:
        with contextlib.redirect_stderr(err_buf):
            rc = hook_pretooluse.dispatch(cmd)
    except Exception as e:
        print(json.dumps({
            "decision": "deny",
            "reason": f"guard failed closed: {type(e).__name__}: {e}"
        }))
        return 0

    if rc == 0:
        print(json.dumps({"decision": "allow"}))
    else:
        err_msg = err_buf.getvalue().strip()
        reason = err_msg if err_msg else "Command blocked by gamecreater safety guard."
        print(json.dumps({"decision": "deny", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
