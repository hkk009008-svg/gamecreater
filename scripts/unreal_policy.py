"""Fail-closed Townblade identity and phase checks for Unreal entry points."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from game_config import GameConfig, load_game_config


class UnrealPolicyError(RuntimeError):
    pass


_UPROJECT_RE = re.compile(
    r'(?:"([^"]+\.uproject)"|\'([^\']+\.uproject)\'|([^\s"\']+\.uproject))',
    re.IGNORECASE,
)
_EDITOR_EXE_RE = re.compile(
    r'(?:"([^"]*UnrealEditor(?:-Cmd)?\.exe)"|'
    r"'([^']*UnrealEditor(?:-Cmd)?\.exe)'|"
    r'([^\s"\']*UnrealEditor(?:-Cmd)?\.exe))',
    re.IGNORECASE,
)


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def same_path(left: Path, right: Path) -> bool:
    return str(_resolved(left)).casefold() == str(_resolved(right)).casefold()


def path_within(path: Path, root: Path) -> bool:
    try:
        _resolved(path).relative_to(_resolved(root))
        return True
    except ValueError:
        return False


def _phase(config: GameConfig) -> str:
    return config.phase or "UNSET"


def launch_binding_refusal(
    config: GameConfig,
    engine: Path,
    uproject: Path,
    *,
    interactive: bool = False,
) -> str | None:
    """Validate exact engine and project identity plus the current phase."""
    if config.engine_kind != "unreal":
        return f"Unreal launch refused: active Engine is {config.engine_kind}"
    kind = "interactive" if interactive else "headless"
    allowed = (config.interactive_launch_allowed
               if interactive else config.headless_launch_allowed)
    if config.engine_root is None:
        return "Unreal launch refused: Engine root is unset in GAME.local.md"
    if not same_path(engine, config.engine_root):
        return (
            f"Unreal launch engine {engine} is not the active Engine root "
            f"{config.engine_root}"
        )
    expected = config.project_identity
    if config.project_root is None or expected is None:
        return "Unreal launch refused: active project identity is incomplete"
    if not path_within(expected, config.project_root):
        return (
            f"configured project identity {expected} escapes Project root "
            f"{config.project_root}"
        )
    if not same_path(uproject, expected):
        return (
            f"Unreal launch project {uproject} is not the active project "
            f"identity {expected}"
        )
    if not _resolved(expected).is_file():
        return f"active project file does not exist: {expected}"
    for historical in config.historical_roots:
        if path_within(uproject, historical):
            return (
                f"Unreal launch project {uproject} is inside historical "
                f"read-only root {historical}"
            )
    if not config.phase:
        return f"{kind} Unreal launch refused: Current phase is unset"
    if allowed is not True:
        return (
            f"{kind} Unreal launch is not authorized in phase {_phase(config)}"
        )
    return None


def resolve_engine_project(
    engine_override: Path | None,
    uproject_override: Path | None,
    *,
    config: GameConfig | None = None,
) -> tuple[Path, Path]:
    """Resolve only the active binding; overrides may confirm, never retarget."""
    config = config or load_game_config()
    if config.engine_kind != "unreal":
        raise UnrealPolicyError(f"Unreal entry refused: active Engine is {config.engine_kind}")
    engine = engine_override or config.engine_root
    uproject = uproject_override or config.uproject
    if engine is None:
        raise UnrealPolicyError("GAME.local.md has no Engine root")
    if uproject is None:
        expected = config.project_identity
        detail = f"; expected {expected}" if expected else ""
        raise UnrealPolicyError(
            "GAME.local.md does not resolve to one existing active .uproject"
            + detail
        )
    refusal = launch_binding_refusal(config, engine, uproject)
    # Path resolution must be usable by dry-run even when launch authority is
    # intentionally off. Identity checks remain mandatory; only the phase
    # permission is deferred to the real-launch gate.
    if refusal and not refusal.startswith("headless Unreal launch is not authorized"):
        raise UnrealPolicyError(refusal)
    return _resolved(engine), _resolved(uproject)


def output_refusal(config: GameConfig, paths: list[Path]) -> str | None:
    """Generated evidence may only land in the active working root."""
    if config.working_root is None:
        return "Working root is unset in GAME.local.md"
    for path in paths:
        if not path_within(path, config.working_root):
            return (
                f"output {path} is outside the active Working root "
                f"{config.working_root}"
            )
        for historical in config.historical_roots:
            if path_within(path, historical):
                return (
                    f"output {path} is inside historical read-only root "
                    f"{historical}"
                )
    return None


def _matches(pattern: re.Pattern[str], command: str) -> list[Path]:
    values: list[Path] = []
    for match in pattern.finditer(command):
        value = next((group for group in match.groups() if group), None)
        if value:
            values.append(Path(value))
    return values


def shell_launch_refusal(command: str, config: GameConfig | None = None) -> str | None:
    """Apply the same binding to a raw shell launch caught by the hook."""
    config = config or load_game_config()
    projects = _matches(_UPROJECT_RE, command)
    executables = _matches(_EDITOR_EXE_RE, command)
    if len(projects) != 1:
        return "Unreal launch must name exactly one explicit .uproject"
    if len(executables) != 1 or not executables[0].is_absolute():
        return "Unreal launch must name one absolute UnrealEditor executable"
    exe = executables[0]
    engine = exe
    for _ in range(4):
        engine = engine.parent
    interactive = "unrealeditor-cmd" not in exe.name.lower()
    return launch_binding_refusal(
        config, engine, projects[0], interactive=interactive
    )


def listener_processes(port: int) -> list[dict]:
    """Return the Windows process records that own one listening port."""
    if sys.platform != "win32":
        raise UnrealPolicyError("listener identity is implemented for Windows only")
    script = (
        f"$ids=@(Get-NetTCPConnection -State Listen -LocalPort {int(port)} "
        "-ErrorAction Stop | Select-Object -ExpandProperty OwningProcess -Unique);"
        "$rows=@(); foreach($ownerId in $ids){$rows+=Get-CimInstance "
        "Win32_Process -Filter \"ProcessId = $ownerId\" | Select-Object "
        "ProcessId,Name,ExecutablePath,CommandLine};"
        "$rows | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        raise UnrealPolicyError(
            f"cannot resolve listener owner on port {port}: "
            f"{result.stderr.strip() or 'PowerShell failed'}"
        )
    raw = result.stdout.lstrip("\ufeff \r\n\t")
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise UnrealPolicyError(
            f"listener owner query returned invalid JSON on port {port}"
        ) from exc
    return payload if isinstance(payload, list) else [payload]


def listener_identity_refusal(
    config: GameConfig,
    port: int,
    records: list[dict] | None = None,
) -> str | None:
    """Prove the port belongs to Unreal running the exact active project."""
    expected = config.project_identity
    if config.project_root is None or expected is None:
        return "active project identity is incomplete in GAME.local.md"
    if not _resolved(expected).is_file():
        return f"active project file does not exist: {expected}"
    try:
        rows = listener_processes(port) if records is None else records
    except (OSError, subprocess.SubprocessError, UnrealPolicyError) as exc:
        return str(exc)
    if len(rows) != 1:
        return f"port {port} has {len(rows)} listener owners; expected exactly one"
    row = rows[0]
    name = str(row.get("Name") or "")
    executable = Path(str(row.get("ExecutablePath") or name))
    if not executable.name.lower().startswith("unrealeditor"):
        return f"port {port} is owned by non-Unreal process {name or 'UNKNOWN'}"
    projects = _matches(_UPROJECT_RE, str(row.get("CommandLine") or ""))
    unique = {str(_resolved(path)).casefold(): path for path in projects}
    if len(unique) != 1:
        return (
            f"port {port} owner command line names {len(unique)} projects; "
            "active identity is unproven"
        )
    actual = next(iter(unique.values()))
    if not same_path(actual, expected):
        return (
            f"port {port} is attached to {actual}, not active project {expected}"
        )
    return None


def channel_refusal(
    config: GameConfig,
    channel: str,
    *,
    records: list[dict] | None = None,
) -> str | None:
    """Gate Epic MCP or OpenClaw by phase, port owner, and project identity."""
    if config.engine_kind != "unreal":
        return f"{channel} refused: active Engine is {config.engine_kind} in phase {_phase(config)}"
    normalized = channel.lower()
    if normalized == "epic-mcp":
        allowed, port = config.epic_mcp_allowed, config.epic_mcp_port
    elif normalized == "openclaw":
        allowed, port = config.openclaw_allowed, config.openclaw_port
    else:
        return f"unknown Unreal channel {channel}"
    if not config.phase:
        return f"{channel} refused: Current phase is unset"
    if allowed is not True:
        return f"{channel} operations are not authorized in phase {_phase(config)}"
    if port is None:
        return f"{channel} port is unset or invalid in GAME.local.md"
    return listener_identity_refusal(config, port, records)
