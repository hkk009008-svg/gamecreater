"""PreToolUse hook dispatcher: the two mechanized rules.

Reads the hook JSON from stdin ({tool_name, tool_input:{command}}), and:

- for a `git push` command: runs the push preflight (repo must be PRIVATE
  or granted) in the directory the command targets;
- for a headless engine launch (UnrealEditor on the command line): runs
  the editor-clear check.

Exit 0 allows the tool call. Exit 2 blocks it, with the reason on stderr
(shown to the model). Anything this dispatcher cannot parse is allowed —
the hook mechanizes two named rules; it is not a general firewall.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import check_editor_clear  # noqa: E402
import preflight_push  # noqa: E402

PUSH_RE = re.compile(r"\bgit\b[^\n|;&]*\bpush\b")
EDITOR_RE = re.compile(r"UnrealEditor(?:-Cmd)?(?:\.exe)?", re.IGNORECASE)
INTERACTIVE_EDITOR_RE = re.compile(
    r"UnrealEditor\.exe|Start-Process[^\n]*UnrealEditor\b", re.IGNORECASE)
CD_RE = re.compile(
    r"(?:^|&&|;)\s*(?:cd(?:\s+/d)?|Set-Location(?:\s+-Path)?|pushd)\s+"
    r"[\"']?([^\"'\n;&|]+)", re.IGNORECASE)
GIT_C_RE = re.compile(r"\bgit\s+-C\s+[\"']?([^\"'\n;&|]+?)[\"']?\s")
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


def push_target_dir(command: str) -> str:
    m = GIT_C_RE.search(command)
    if m:
        return normalize_dir(m.group(1).strip())
    cds = CD_RE.findall(command)
    if cds:
        return normalize_dir(cds[-1].strip())
    return "."


def main() -> int:
    command = command_of(sys.stdin.read())
    if not command:
        return 0

    if PUSH_RE.search(command):
        rc = preflight_push.main(["preflight_push", push_target_dir(command)])
        if rc != 0:
            print("push-guard: see the rule in gamecreater CLAUDE.md "
                  "(Authorization boundary).", file=sys.stderr)
            return 2
        return 0

    if EDITOR_RE.search(command):
        # An interactive editor launch is the user's own act; the guard is
        # for HEADLESS launches colliding with an open editor. Both routes
        # get the same check — a second editor is the failure either way.
        rc = check_editor_clear.main(["check_editor_clear", "UnrealEditor"])
        if rc != 0:
            print("editor-guard: an editor is already running; close it "
                  "(or have the user close it and say go) before another "
                  "launch.", file=sys.stderr)
            return 2
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
