"""Read the active game's machine-local binding from ``GAME.local.md``."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from gitignored_config import resolve_gitignored


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "GAME.local.md"


def _value(text: str, label: str) -> str | None:
    """Read one ``- Label (optional detail): value`` field."""
    match = re.search(
        rf"^\s*-\s*{re.escape(label)}(?:\s*\([^)]*\))?\s*:\s*(.*?)\s*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if not match:
        return None
    value = match.group(1).strip().strip("`")
    return None if not value or value.startswith("<") else value


def _path(text: str, label: str) -> Path | None:
    value = _value(text, label)
    return Path(value) if value else None


def _boolean(text: str, label: str) -> bool | None:
    """Read an exact yes/no policy field; anything else stays ungranted."""
    value = _value(text, label)
    if value is None:
        return None
    word = value.split(None, 1)[0].rstrip(";,.").lower()
    return {"yes": True, "no": False}.get(word)


def _integer(text: str, label: str) -> int | None:
    value = _value(text, label)
    if value is None:
        return None
    try:
        number = int(value)
    except ValueError:
        return None
    return number if 1 <= number <= 65535 else None


def _paths(text: str, label: str) -> tuple[Path, ...]:
    value = _value(text, label)
    if value is None:
        return ()
    return tuple(Path(item.strip()) for item in value.split(",") if item.strip())


def _skill_sources(text: str) -> tuple[tuple[str, Path], ...]:
    """Read ``slug=path`` pairs for inactive games kept discoverable."""
    value = _value(text, "Preserved game skill sources")
    if value is None:
        return ()
    out: list[tuple[str, Path]] = []
    for item in value.split(","):
        if "=" not in item:
            continue
        raw_slug, raw_path = (part.strip() for part in item.split("=", 1))
        slug = re.sub(r"[^a-z0-9-]", "", raw_slug.lower())
        if slug and raw_path and not raw_path.startswith("<"):
            out.append((slug, Path(raw_path)))
    return tuple(out)


@dataclass(frozen=True)
class GameConfig:
    source: Path
    name: str | None = None
    slug: str | None = None
    phase: str | None = None
    working_root: Path | None = None
    project_root: Path | None = None
    expected_uproject: Path | None = None
    engine_root: Path | None = None
    evidence_root_path: Path | None = None
    now: Path | None = None
    lessons: Path | None = None
    headless_launch_allowed: bool | None = None
    interactive_launch_allowed: bool | None = None
    epic_mcp_allowed: bool | None = None
    openclaw_allowed: bool | None = None
    epic_mcp_port: int | None = None
    openclaw_port: int | None = None
    historical_roots: tuple[Path, ...] = ()
    preserved_game_skill_sources: tuple[tuple[str, Path], ...] = ()
    engine_kind: str = "unreal"
    project_file: Path | None = None
    team_now: Path | None = None
    integration_owner: str | None = None

    @property
    def project_dir(self) -> Path | None:
        if self.project_root is None:
            return None
        return (self.project_root.parent
                if self.project_root.suffix.lower() == ".uproject"
                else self.project_root)

    @property
    def uproject(self) -> Path | None:
        """Return the sole configured ``.uproject``; ambiguity is an error."""
        if self.engine_kind != "unreal":
            return None
        if self.expected_uproject is not None:
            return self.expected_uproject if self.expected_uproject.is_file() else None
        root = self.project_root
        if root is None:
            return None
        if root.suffix.lower() == ".uproject":
            return root
        if not root.is_dir():
            return None
        matches = sorted(root.glob("*.uproject"))
        return matches[0] if len(matches) == 1 else None

    @property
    def evidence_root(self) -> Path | None:
        if self.evidence_root_path is not None:
            return self.evidence_root_path
        return self.project_dir / "Experiments" if self.project_dir else None

    @property
    def project_identity(self) -> Path | None:
        """Exact source manifest for Roblox, or project file for Unreal.

        Unlike :attr:`uproject`, this may name a planned file that does not
        exist yet. That lets a bootstrap phase state its identity while every
        operational gate still refuses until the file actually exists.
        """
        if self.engine_kind != "unreal":
            return self.project_file
        return self.expected_uproject or self.uproject


def parse_game_config(text: str, source: Path = DEFAULT_PATH) -> GameConfig:
    slug = _value(text, "Short slug")
    if slug:
        slug = re.sub(r"[^a-z0-9-]", "", slug.lower()) or None
    raw_engine = _value(text, "Engine") or "unreal"
    engine_kind = re.sub(r"[^a-z0-9]", "", raw_engine.lower())
    engine_kind = {"robloxstudio": "roblox", "unrealengine": "unreal"}.get(
        engine_kind, engine_kind)
    return GameConfig(
        source=source,
        name=_value(text, "Game name"),
        slug=slug,
        phase=_value(text, "Current phase"),
        working_root=_path(text, "Working root"),
        project_root=_path(text, "Project root"),
        expected_uproject=_path(text, "Expected uproject identity"),
        engine_root=_path(text, "Engine root"),
        evidence_root_path=_path(text, "Evidence root"),
        now=_path(text, "NOW.md"),
        lessons=_path(text, "Lessons inbox"),
        headless_launch_allowed=_boolean(text, "Headless engine launch"),
        interactive_launch_allowed=_boolean(text, "Interactive engine launch"),
        epic_mcp_allowed=_boolean(text, "Epic MCP operations"),
        openclaw_allowed=_boolean(text, "OpenClaw operations"),
        epic_mcp_port=_integer(text, "Epic MCP port"),
        openclaw_port=_integer(text, "OpenClaw port"),
        historical_roots=_paths(text, "Historical read-only roots"),
        preserved_game_skill_sources=_skill_sources(text),
        engine_kind=engine_kind,
        project_file=_path(text, "Project manifest"),
        team_now=_path(text, "Team NOW.md"),
        integration_owner=_value(text, "Integration owner"),
    )


def load_game_config(path: Path = DEFAULT_PATH) -> GameConfig:
    resolved = resolve_gitignored(path, cwd=ROOT)
    if not resolved.is_file():
        return GameConfig(source=resolved)
    return parse_game_config(
        resolved.read_text(encoding="utf-8", errors="replace"), resolved
    )
