"""PreToolUse dispatcher for the small set of mechanized safety rules.

Reads the hook JSON from stdin ({tool_name, tool_input:{command}}), and:

- for one standalone `git push <named-remote>` command: resolves that remote's
  push URL and verifies the actual destination is PRIVATE or granted;
- for a headless engine launch (UnrealEditor on the command line): runs
  the editor-clear check;
- refuses shell truncation of either append-only lessons inbox;
- refuses MCP tool names that name reserved outward repository acts.

Exit 0 allows the tool call. Exit 2 blocks it, with the reason on stderr
(shown to the model). Anything outside these named rules is allowed; this is
not a general firewall.

Unexpected exceptions fail closed (exit 2).
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import shlex
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import check_editor_clear  # noqa: E402
import preflight_push  # noqa: E402
from hook_shell_routes import extract_shell_command  # noqa: E402

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
# A lessons inbox is append-only: a single `>` (or an overwriting cmdlet)
# aimed at LESSONS.md replaces every lesson in it with whatever one command
# was running, and the loss is silent until the next session-start check.
# `>>` stays legal -- appending is the inbox's whole job. Deliberately
# narrow: this guards the named files against shell truncation, it does not
# try to police every editing tool (check_lessons_inbox.py is the detector
# for those).
INBOX_TRUNCATE_RE = re.compile(
    r"(?:(?<!>)>(?!>)|\btee\b(?!\s+-a)[^|;&]*?|\bSet-Content\b[^|;&\n]*?"
    r"|\bOut-File\b(?![^|;&\n]*-Append)[^|;&\n]*?)"
    r"\s*[\"']?[^\s\"'|;&]*LESSONS\.md\b",
    re.IGNORECASE)
MSYS_DRIVE_RE = re.compile(r"^/([A-Za-z])(?=/|$)")
SHELL_SEPARATOR_RE = re.compile(r"[;&|\r\n]")
REMOTE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
PUSH_OPTIONS_WITH_VALUE = {"-o", "--push-option", "--receive-pack", "--exec"}
GIT_GLOBAL_OPTIONS_WITH_VALUE = {
    "-C", "-c", "--git-dir", "--work-tree", "--namespace",
    "--config-env", "--exec-path", "--super-prefix",
}


def normalize_dir(d: str) -> str:
    # Git-Bash writes '/d/Unreal'; the preflight runs under Windows
    # Python, whose subprocess cwd cannot be a POSIX drive path — gh
    # never ran and the guard fail-close blocked an authorized push
    # (2026-08-13). Non-drive POSIX paths pass through untouched.
    return MSYS_DRIVE_RE.sub(lambda m: m.group(1).upper() + ":", d)


class HookPayloadError(ValueError):
    """A matched hook call did not carry one usable payload."""


def parse_hook_request(payload: str) -> tuple[str, dict, str]:
    """Parse once and fail closed on shell schema drift.

    Explicitly supported shell tools have one named command field. Other MCP
    payloads remain opaque and use tool-name policy only. An unknown matched
    non-MCP call retains the existing command-field contract.
    """
    try:
        data = json.loads(payload.lstrip("\ufeff \r\n\t"))
    except json.JSONDecodeError as exc:
        raise HookPayloadError(f"malformed JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise HookPayloadError("payload root is not an object")
    name = data.get("tool_name", "")
    if not isinstance(name, str):
        raise HookPayloadError("tool_name is not a string")
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        raise HookPayloadError("missing tool_input object")
    try:
        shell_command = extract_shell_command(name, tool_input)
    except ValueError as exc:
        raise HookPayloadError(str(exc)) from exc
    if shell_command is not None:
        return name, tool_input, shell_command
    if name.startswith("mcp__"):
        # Unregistered MCP contracts stay opaque; a command-like field is not
        # enough to identify a shell executor.
        return name, tool_input, ""
    cmd = tool_input.get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        label = name or "matched shell tool"
        raise HookPayloadError(f"{label} has no non-empty command string")
    return name, tool_input, cmd


def parse_hook_payload(payload: str) -> tuple[str, str]:
    name, _, command = parse_hook_request(payload)
    return name, command


def command_of(payload: str) -> str:
    try:
        return parse_hook_payload(payload)[1]
    except HookPayloadError:
        return ""


def tool_of(payload: str) -> str:
    """Return the tool name for policy, including opaque MCP contracts.

    Only registered shell routes expose a command to this dispatcher. Other
    MCP payloads use name policy because their arguments have no shared schema.
    """
    try:
        return parse_hook_payload(payload)[0]
    except HookPayloadError:
        return ""


# Repository MCP tool names that perform acts AGENTS.md reserves to the user.
# Matched on the NAME because an MCP payload's arguments are server-defined
# and cannot be parsed generically. Deliberately narrow: this blocks the
# named outward/repository acts, it is not a general MCP firewall, and it says
# so when it fires. Live Unreal mutations are intentionally not matched: the
# hook cannot see the conversation's exact authorization or scope, so a static
# name block would also reject every authorized OpenClaw change.
MCP_RESERVED_RE = re.compile(
    r"(?:^|_)(?:push|publish|merge|make_public|set_visibility|delete_repo)"
    r"(?:_|$)", re.IGNORECASE)


def _unquote(word: str) -> str:
    if len(word) >= 2 and word[0] == word[-1] and word[0] in "\"'":
        return word[1:-1]
    return word


def _shell_words(command: str) -> list[str]:
    return [_unquote(word) for word in shlex.split(command, posix=False)]


def _is_git_program(word: str) -> bool:
    name = re.split(r"[\\/]", word)[-1].lower()
    return name in {"git", "git.exe"}


def _direct_push_candidate(command: str) -> bool:
    """Recognize a direct push even when unsafe Git globals precede it."""
    try:
        words = _shell_words(command)
    except ValueError:
        return bool(PUSH_RE.search(command))
    if not words or not _is_git_program(words[0]):
        return bool(PUSH_RE.search(command))
    i = 1
    while i < len(words):
        word = words[i]
        if word.lower() == "push":
            return True
        if word in GIT_GLOBAL_OPTIONS_WITH_VALUE:
            i += 2
            continue
        if word.startswith("--") and "=" in word:
            i += 1
            continue
        if word.startswith("-"):
            i += 1
            continue
        return False
    return False


def push_spec(command: str) -> tuple[str | None, str | None, str | None]:
    """Return (repo, remote, error) for the sole accepted push grammar.

    The accepted prefix is exactly ``git [-C repo] push``. Git global config
    and repository selectors are rejected because reconstructing only some of
    them preflights a different repository from the one Git will push.
    """
    matches = list(PUSH_RE.finditer(command))
    if len(matches) > 1:
        return None, None, "push command must contain exactly one git push"
    if SHELL_SEPARATOR_RE.search(command):
        return None, None, (
            "push command must be standalone; cd/chaining/pipelines make "
            "the actual repository ambiguous")
    try:
        words = _shell_words(command)
    except ValueError as exc:
        return None, None, f"push command does not parse: {exc}"
    if not words or not _is_git_program(words[0]):
        return None, None, "push must start with the git executable"

    i = 1
    repo = "."
    if i < len(words) and words[i] == "-C":
        if i + 1 >= len(words):
            return None, None, "git -C requires one repository path"
        repo = normalize_dir(words[i + 1])
        if re.match(r"^[A-Za-z]:(?![\\/])", repo):
            return None, None, "drive-relative git -C paths are unsupported"
        i += 2
    if i >= len(words) or words[i].lower() != "push":
        return None, None, (
            "before push, only one optional uppercase `-C <repo>` is "
            "accepted; -c, --git-dir, --work-tree, repeated -C, and other "
            "Git globals can change the actual target")
    i += 1

    while i < len(words) and words[i].startswith("-"):
        option = words[i]
        if option == "--":
            i += 1
            break
        if option == "--repo" or option.startswith("--repo="):
            return None, None, (
                "URL/path push destinations are not accepted; configure a "
                "named Git remote first")
        if option in PUSH_OPTIONS_WITH_VALUE:
            if i + 1 >= len(words):
                return None, None, f"push option {option} requires a value"
            i += 2
        else:
            i += 1
    if i >= len(words):
        return None, None, (
            "name the push remote explicitly, for example `git push origin main`")
    remote = words[i]
    if not REMOTE_NAME_RE.fullmatch(remote):
        return None, None, (
            "push destination must be a configured remote name, not a URL, "
            "filesystem path, or owner/repo shorthand")
    return repo, remote, None


def push_target_dir(command: str) -> str:
    repo, _, error = push_spec(command)
    return repo if repo is not None and error is None else "."


def push_remote_name(command: str) -> tuple[str | None, str | None]:
    """Return the one explicit named remote, or a fail-closed reason.

    Pushes are rare, externally visible acts. Requiring one standalone
    `git [-C repo] push <remote> ...` form is cheaper and safer than pretending
    to interpret compound shell state, implicit push.default rules, URL-form
    destinations, or two pushes hidden in one command.
    """
    _, remote, error = push_spec(command)
    return remote, error


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
        print(f"MCP BLOCKED: '{tool_name}' names an act AGENTS.md reserves "
              f"to the user (repository push, merge, publication, visibility, "
              f"or deletion). "
              f"This reserved-act rule keys on the tool name, including "
              f"MCP contracts with opaque arguments. Have the user authorize "
              f"the exact effect, executor and target.", file=sys.stderr)
        return 2
    return 0


def shell_workdir(tool_name: str, tool_input: dict) -> str | None:
    """Resolve supported executor context without changing the hook process cwd.

    Unknown execution-context aliases on a known shell route fail closed rather
    than checking a different repository. Null means the executor's default.
    """
    fields = {"cwd", "workdir", "working_directory", "workingDirectory"}
    expected = {"exec_command": "workdir",
                "mcp__terminal__run_in_terminal": "cwd"}.get(tool_name)
    supplied = fields.intersection(tool_input)
    if supplied - ({expected} if expected else set()):
        raise HookPayloadError(f"{tool_name} has an unsupported working-directory field")
    value = tool_input.get(expected) if expected else None
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise HookPayloadError(f"{tool_name} has no usable {expected} path")
    value = normalize_dir(value)
    if re.match(r"^[A-Za-z]:(?![\\/])", value) or value.startswith(("\\\\", "//")):
        raise HookPayloadError("ambiguous or network working directory is unsupported")
    return str(Path(value).resolve())


def dispatch(command: str, *, cwd: str | None = None) -> int:
    if INBOX_TRUNCATE_RE.search(command):
        print("inbox-guard: that command TRUNCATES a lessons inbox "
              "(single '>' / Set-Content / Out-File / tee without append). "
              "Lessons are append-only; use '>>' to add, and distill-an-arc "
              "is the only sanctioned rewrite. Rule: gamecreater AGENTS.md, "
              "the improvement loop.", file=sys.stderr)
        return 2

    if _direct_push_candidate(command):
        repo, remote, error = push_spec(command)
        if error:
            print(f"PUSH BLOCKED: {error}.", file=sys.stderr)
            return 2
        if cwd is not None:
            # An explicit relative git -C is evaluated by Git from the tool's
            # actual workdir, not from the hook's session cwd.
            repo = str((Path(cwd) / repo).resolve())
        rc = run_guard(preflight_push.main,
                       ["preflight_push", repo, remote])
        if rc != 0:
            print("push-guard: see the rule in gamecreater AGENTS.md "
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
        tool_name, tool_input, command = parse_hook_request(payload)
        rc = dispatch_tool(tool_name)
        if rc != 0:
            return rc
        if not command:
            return 0
        cwd = shell_workdir(tool_name, tool_input)
        return dispatch(command, cwd=cwd) if cwd is not None else dispatch(command)
    except HookPayloadError as e:
        print(f"guard failed closed: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"guard failed closed: {type(e).__name__}: {e}",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
