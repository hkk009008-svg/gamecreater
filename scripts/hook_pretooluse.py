"""PreToolUse hook dispatcher: the two mechanized rules.

Reads the hook JSON from stdin ({tool_name, tool_input:{command}}), and:

- for a `git push` command: runs the push preflight (repo must be PRIVATE
  or granted) in the directory the command targets;
- for a headless engine launch (UnrealEditor on the command line): runs
  the editor-clear check.

Exit 0 allows the tool call. Exit 2 blocks it, with the reason on stderr
(shown to the model). Anything this dispatcher cannot parse is allowed —
the hook mechanizes two named rules; it is not a general firewall.

Unexpected exceptions fail closed (exit 2). A crash that became a non-2
exit would be fail-open: Claude Code treats any exit other than 2 as
"hook error, continue with the tool call".
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import check_editor_clear  # noqa: E402
import preflight_push  # noqa: E402

# git[.exe] then only global options, then the `push` subcommand.
# Must not match: git stash push, git commit -m "push", git log --grep=push.
# Quoted -C paths are legal and were an allow-path hole if dropped.
_SHELL_WORD = r"(?:[^\s\"']|\"[^\"]*\"|'[^']*')+"
_GIT_GLOBAL = (
    r"(?:"
    r"\s+-C\s+" + _SHELL_WORD +
    r"|\s+-c\s+" + _SHELL_WORD +
    r"|\s+--[A-Za-z][A-Za-z0-9-]*(?:=" + _SHELL_WORD + r")?"
    r"|\s+-[A-Za-z]"
    r")*"
)
PUSH_RE = re.compile(
    r"\bgit(?:\.exe)?" + _GIT_GLOBAL + r"\s+push\b",
    re.IGNORECASE,
)
EDITOR_RE = re.compile(
    r"(?:^|&&|\|\||[;&|\n])\s*"
    r"(?:&|Start-Process|start|call)?\s*"
    r"(?:"
    r"\"[^\"]*?[\\/]UnrealEditor(?:-Cmd)?(?:\.exe)?\""
    r"|'[^']*?[\\/]UnrealEditor(?:-Cmd)?(?:\.exe)?'"
    r"|\S*?[\\/]UnrealEditor(?:-Cmd)?(?:\.exe)?\b"
    r"|[\"']?UnrealEditor(?:-Cmd)?(?:\.exe)?[\"']?\b"
    r")"
    r"(?!\.[A-Za-z0-9])",
    re.IGNORECASE,
)
CD_RE = re.compile(
    r"(?:^|&&|\|\||[;&|\n])\s*(?:cd(?:\s+/d)?|Set-Location(?:\s+-Path)?|pushd)\s+"
    r"[\"']?([^\"'\n;&|]+)", re.IGNORECASE | re.MULTILINE)
GIT_C_RE = re.compile(
    r'\bgit(?:\.exe)?\s+-C\s+(?:"([^"]+)"|\'([^\']+)\'|(\S+))',
    re.IGNORECASE)
MSYS_DRIVE_RE = re.compile(r"^/([A-Za-z])(?=/|$)")


def normalize_dir(d: str) -> str:
    # Git-Bash writes '/d/Unreal'; the preflight runs under Windows
    # Python, whose subprocess cwd cannot be a POSIX drive path — gh
    # never ran and the guard fail-close blocked an authorized push
    # (2026-08-13). Non-drive POSIX paths pass through untouched.
    return MSYS_DRIVE_RE.sub(lambda m: m.group(1).upper() + ":", d)


def command_of(payload: str) -> str:
    try:
        data = json.loads(payload.lstrip("﻿ \r\n\t"))
    except json.JSONDecodeError:
        return ""
    tool_input = data.get("tool_input") or {}
    cmd = tool_input.get("command")
    return cmd if isinstance(cmd, str) else ""


def tool_of(payload: str) -> str:
    """The tool NAME, which is the only thing an MCP call reliably carries.

    An MCP tool call has no `tool_input.command`, so command_of() returns ""
    and the dispatcher allowed it unconditionally. That was harmless only
    while zero MCP servers were configured; enabling Unreal's MCP server
    changes that, and any future git-capable MCP server would make
    CLAUDE.md's push rule false without a line of this file changing.
    """
    try:
        data = json.loads(payload.lstrip("﻿ \r\n\t"))
    except json.JSONDecodeError:
        return ""
    name = data.get("tool_name")
    return name if isinstance(name, str) else ""


# MCP tool names that perform the acts CLAUDE.md reserves to the user.
# Matched on the NAME because an MCP payload's arguments are server-defined
# and cannot be parsed generically. Deliberately narrow: this blocks the
# named acts, it is not a general MCP firewall, and it says so when it fires.
MCP_RESERVED_RE = re.compile(
    r"(?:^|_)(?:push|publish|merge|make_public|set_visibility|delete_repo)"
    r"(?:_|$)", re.IGNORECASE)


def push_target_dir(command: str) -> str:
    m = GIT_C_RE.search(command)
    if m:
        target = m.group(1) or m.group(2) or m.group(3)
        if target:
            return normalize_dir(target.strip())
    cds = CD_RE.findall(command)
    if cds:
        return normalize_dir(cds[-1].strip())
    return "."


def run_guard(fn, argv: list[str]) -> int:
    """Run a guard, copy its stdout to stderr, map any failure to exit 2.

    Guard scripts print the verdict on stdout (so `python script.py` is
    readable). Claude Code only feeds stderr to the model on a blocking
    PreToolUse exit. An exception here is fail-closed, never a crash
    that becomes exit 1 (continue).
    """
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = fn(argv)
    except Exception as e:
        print(f"guard failed closed: {type(e).__name__}: {e}",
              file=sys.stderr)
        text = buf.getvalue()
        if text:
            print(text, end="", file=sys.stderr)
        return 2
    text = buf.getvalue()
    if text:
        print(text, end="", file=sys.stderr)
    return 0 if rc == 0 else 2


def dispatch_tool(tool_name: str) -> int:
    """Rules that key on the tool NAME rather than a shell string."""
    if not tool_name.startswith("mcp__"):
        return 0
    if MCP_RESERVED_RE.search(tool_name):
        print(f"MCP BLOCKED: '{tool_name}' names an act CLAUDE.md reserves "
              f"to the user (push / merge / publish / visibility change). "
              f"The shell-command guards cannot see MCP calls at all, so "
              f"this rule keys on the tool name. Have the user authorize "
              f"the exact effect, executor and target.", file=sys.stderr)
        return 2
    return 0


def dispatch(command: str) -> int:
    if PUSH_RE.search(command):
        rc = run_guard(preflight_push.main,
                       ["preflight_push", push_target_dir(command)])
        if rc != 0:
            print("push-guard: see the rule in gamecreater CLAUDE.md "
                  "(Authorization boundary).", file=sys.stderr)
            return 2
        return 0

    if EDITOR_RE.search(command):
        # An interactive editor launch is the user's own act; the guard is
        # for HEADLESS launches colliding with an open editor. Both routes
        # get the same check — a second editor is the failure either way.
        rc = run_guard(check_editor_clear.main,
                       ["check_editor_clear", "UnrealEditor"])
        if rc != 0:
            print("editor-guard: an editor is already running; close it "
                  "(or have the user close it and say go) before another "
                  "launch.", file=sys.stderr)
            return 2
        return 0

    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")
    try:
        payload = sys.stdin.read()
        rc = dispatch_tool(tool_of(payload))
        if rc != 0:
            return rc
        command = command_of(payload)
        if not command:
            return 0
        return dispatch(command)
    except Exception as e:
        print(f"guard failed closed: {type(e).__name__}: {e}",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
