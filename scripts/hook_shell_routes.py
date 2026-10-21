"""Extract a shell string only from an explicitly supported tool contract.

Supported exact names and their one command field:

* Bash, PowerShell, Monitor -> command (the repository's existing hook contract).
* exec_command -> cmd (the native executor's supplied tool schema).
* mcp__terminal__run_in_terminal -> command (bounded compatibility contract
  from the reported shell-route bypass, 20-analysis-final section 6 S1).

The terminal contract does not establish that this MCP server is installed.
Aliases such as mcp__desktop_commander__execute_command and
mcp__functions__exec_command are not registered without a source contract.
Other MCP payloads stay opaque, including fields called command or cmd. This
module neither evaluates code nor executes commands, and is not a general
shell-tool detector. The caller must apply its tool-name policy, route the
returned string through the command guards, and handle tool execution context
(for example cwd/workdir) separately.
"""

from __future__ import annotations

from types import MappingProxyType


# Exact names matter: a suffix or a matching field name is not a tool contract.
SHELL_COMMAND_FIELDS = MappingProxyType({
    "Bash": "command",
    "PowerShell": "command",
    "Monitor": "command",
    "exec_command": "cmd",
    "mcp__terminal__run_in_terminal": "command",
})


def extract_shell_command(tool_name: str, tool_input: object) -> str | None:
    """Return an unchanged command, None for an opaque route, or raise ValueError.

    Known routes require an object and exactly one command-bearing field.
    A second command/cmd field is refused even when both values match: silently
    choosing one would hide schema drift in the executor's actual input.
    Other arguments such as timeout are retained as opaque execution metadata.
    """
    field = SHELL_COMMAND_FIELDS.get(tool_name)
    if field is None:
        return None
    if not isinstance(tool_input, dict):
        raise ValueError(f"{tool_name} has no tool_input object")
    competing = "cmd" if field == "command" else "command"
    if competing in tool_input:
        raise ValueError(
            f"{tool_name} has conflicting {field}/{competing} command fields")
    command = tool_input.get(field)
    if not isinstance(command, str) or not command.strip():
        raise ValueError(f"{tool_name} has no non-empty {field} string")
    return command
