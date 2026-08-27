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


class PayloadError(ValueError):
    """The matched Antigravity call did not contain one usable command."""


def extract_command(payload: str) -> str:
    try:
        data = json.loads(payload.lstrip("\ufeff \r\n\t"))
    except json.JSONDecodeError as exc:
        raise PayloadError(f"malformed JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise PayloadError("payload root is not an object")
    tool_call = data.get("toolCall")
    if not isinstance(tool_call, dict):
        raise PayloadError("missing toolCall object")
    if tool_call.get("name") != "run_command":
        raise PayloadError("matched payload is not a run_command call")
    args = tool_call.get("args")
    if not isinstance(args, dict):
        raise PayloadError("run_command is missing its args object")
    cmd = args.get("CommandLine")
    if cmd is None:
        cmd = args.get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        raise PayloadError("run_command has no non-empty command string")
    return cmd


def deny(reason: str) -> int:
    print(json.dumps({"decision": "deny", "reason": reason}))
    return 0


def main() -> int:
    # Ensure stdout/stderr won't crash on Windows console encoding
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")

    raw = sys.stdin.read()
    try:
        cmd = extract_command(raw)
    except PayloadError as exc:
        return deny(f"guard failed closed: {exc}")

    err_buf = io.StringIO()
    try:
        with contextlib.redirect_stderr(err_buf):
            rc = hook_pretooluse.dispatch(cmd)
    except Exception as e:
        return deny(f"guard failed closed: {type(e).__name__}: {e}")

    if rc == 0:
        print(json.dumps({"decision": "allow"}))
    else:
        err_msg = err_buf.getvalue().strip()
        reason = err_msg if err_msg else "Command blocked by gamecreater safety guard."
        deny(reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
